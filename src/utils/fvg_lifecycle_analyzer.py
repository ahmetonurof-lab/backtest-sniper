"""
fvg_lifecycle_analyzer.py — FVG Yaşam Döngüsü ve Sweep DNA Analizi.

Ham mum verilerinden (OHLCV) backtest motoru olmadan:
  1. FVG Decay: FVG oluştuktan kaç mum sonra doluyor?
  2. FVG Violation: Yüzde kaçı ihlal ediliyor (fakeout)?
  3. Sweep Recovery: Likidite süpürme sonrası toparlanma hızı (V vs U shape)
"""

import csv
import os
import sys
import time
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
_SNIPER_SRC = os.path.join(os.path.dirname(__file__), "..", "..", "sniper", "src")
if _SNIPER_SRC not in sys.path:
    sys.path.insert(0, _SNIPER_SRC)

import config as cfg

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "daily")
REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
os.makedirs(REPORT_DIR, exist_ok=True)


# ── FVG Detection (lightweight, sadece OHLC'dan) ────────────
def find_fvgs_15m(bars_15m):
    """Gap-based FVG detection on 15m bars (dict-based)."""
    fvgs = []
    for i in range(2, len(bars_15m)):
        b2, b1, b0 = bars_15m[i - 2], bars_15m[i - 1], bars_15m[i]

        if b2["high"] < b0["low"]:
            fvgs.append(
                {
                    "idx": i,
                    "direction": "bullish",
                    "top": b0["low"],
                    "bottom": b2["high"],
                    "size": b0["low"] - b2["high"],
                    "timestamp": b0["timestamp"],
                }
            )
        elif b2["low"] > b0["high"]:
            fvgs.append(
                {
                    "idx": i,
                    "direction": "bearish",
                    "top": b2["low"],
                    "bottom": b0["high"],
                    "size": b2["low"] - b0["high"],
                    "timestamp": b0["timestamp"],
                }
            )
    return fvgs


def find_sweeps(bars_15m, lookback=48):
    """Likidite süpürme tespiti: son N bar'in en yuksek/dusuk seviyesi asilirsa."""
    sweeps = []
    for i in range(lookback, len(bars_15m)):
        window = bars_15m[i - lookback : i]
        recent = bars_15m[i]
        high_prev = max(b["high"] for b in window)
        low_prev = min(b["low"] for b in window)

        if recent["high"] > high_prev:
            sweeps.append(
                {
                    "idx": i,
                    "direction": "above",
                    "level": high_prev,
                    "timestamp": recent["timestamp"],
                }
            )
        if recent["low"] < low_prev:
            sweeps.append(
                {
                    "idx": i,
                    "direction": "below",
                    "level": low_prev,
                    "timestamp": recent["timestamp"],
                }
            )
    return sweeps


def load_15m_bars(symbol):
    """1m CSV'den 15m bar olustur."""
    csv_path = os.path.join(DATA_DIR, f"{symbol}_1m_raw.csv")
    if not os.path.isfile(csv_path):
        # fallback: _1m.csv
        csv_path = os.path.join(DATA_DIR, f"{symbol}_1m.csv")
    if not os.path.isfile(csv_path):
        return None

    bars_1m = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            bars_1m.append(
                {
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "timestamp": int(
                        datetime.strptime(row["open_time"], "%Y-%m-%d %H:%M:%S")
                        .replace(tzinfo=timezone.utc)
                        .timestamp()
                        * 1000
                    ),
                }
            )

    # 15m resample
    m15 = []
    for i in range(0, len(bars_1m), 15):
        c = bars_1m[i : i + 15]
        if len(c) < 15:
            break
        m15.append(
            {
                "open": c[0]["open"],
                "high": max(b["high"] for b in c),
                "low": min(b["low"] for b in c),
                "close": c[-1]["close"],
                "timestamp": c[0]["timestamp"],
            }
        )
    return m15


def analyze_fvg_lifecycle(fvgs, bars):
    """Her FVG icin: doldu mu, ihlal mi, kac mumda dolduruldu."""
    results = []
    for fvg in fvgs:
        start_idx = fvg["idx"] + 1
        filled = False
        violated = False
        bars_to_fill = 0
        max_penetration_pct = 0.0

        for j in range(start_idx, min(start_idx + 200, len(bars))):
            b = bars[j]
            bars_to_fill += 1

            if fvg["direction"] == "bullish":
                in_fvg = fvg["bottom"] <= b["close"] <= fvg["top"]
                below_fvg = b["low"] < fvg["bottom"]
                above_fvg = b["high"] > fvg["top"]
                penetration = (
                    (fvg["bottom"] - b["low"]) / fvg["size"] if fvg["size"] > 0 else 0
                )
            else:
                in_fvg = fvg["bottom"] <= b["close"] <= fvg["top"]
                below_fvg = b["high"] > fvg["top"]
                above_fvg = b["low"] < fvg["bottom"]
                penetration = (
                    (b["high"] - fvg["top"]) / fvg["size"] if fvg["size"] > 0 else 0
                )

            if penetration > max_penetration_pct:
                max_penetration_pct = penetration

            if in_fvg:
                filled = True
                break
            if (fvg["direction"] == "bullish" and below_fvg) or (
                fvg["direction"] == "bearish" and above_fvg
            ):
                violated = True
                break

        results.append(
            {
                "filled": filled,
                "violated": violated,
                "bars_to_fill": bars_to_fill if filled else None,
                "max_penetration_pct": round(max_penetration_pct * 100, 2),
            }
        )
    return results


def analyze_sweep_recovery(sweeps, bars, lookahead=48):
    """Sweep sonrasi kac mumda eski seviyeye donuldugunu olc."""
    results = []
    for sw in sweeps:
        start_idx = sw["idx"] + 1
        recovered = False
        bars_to_recover = 0

        for j in range(start_idx, min(start_idx + lookahead, len(bars))):
            b = bars[j]
            bars_to_recover += 1
            if sw["direction"] == "above":
                if b["close"] < sw["level"]:
                    recovered = True
                    break
            else:
                if b["close"] > sw["level"]:
                    recovered = True
                    break

        results.append(
            {
                "recovered": recovered,
                "bars_to_recover": bars_to_recover if recovered else None,
            }
        )
    return results


def main():
    t0 = time.time()
    print("=" * 100)
    print("  FVG YASAM DONGUSU VE SWEEP DNA ANALIZI")
    print("  (Backtest'siz, sadece OHLCV istatistikleri)")
    print("=" * 100)

    all_symbols = sorted(cfg.SYMBOLS)
    dna_data = {}

    for sym in all_symbols:
        print(f"\n  [{sym}] Yukleniyor...", end=" ", flush=True)
        bars = load_15m_bars(sym)
        if bars is None or len(bars) < 1000:
            print(f"VERI YOK (bars={len(bars) if bars else 0})")
            continue
        print(f"{len(bars):,} bar", flush=True)

        # FVG'leri bul
        fvgs = find_fvgs_15m(bars)
        print(f"    FVG tespit: {len(fvgs)} adet")

        # FVG lifecycle
        life = analyze_fvg_lifecycle(fvgs, bars)
        n_filled = sum(1 for r in life if r["filled"])
        n_violated = sum(1 for r in life if r["violated"])
        n_open = len(life) - n_filled - n_violated
        fill_bars = [r["bars_to_fill"] for r in life if r["filled"]]
        avg_fill = np.mean(fill_bars) if fill_bars else 0
        pct_violated = n_violated / len(life) * 100 if life else 0
        pct_filled = n_filled / len(life) * 100 if life else 0
        avg_pen = (
            np.mean([r["max_penetration_pct"] for r in life if r["violated"]])
            if n_violated
            else 0
        )

        # Sweep'leri bul
        sweeps = find_sweeps(bars)
        sw_recovery = analyze_sweep_recovery(sweeps, bars)
        n_sw_rec = sum(1 for r in sw_recovery if r["recovered"])
        rec_bars = [r["bars_to_recover"] for r in sw_recovery if r["recovered"]]
        avg_rec = np.mean(rec_bars) if rec_bars else 0
        pct_sw_rec = n_sw_rec / len(sweeps) * 100 if sweeps else 0

        # Print
        print(
            f"    Dolan:     {n_filled:>6} (%{pct_filled:5.1f}) | Ort. {avg_fill:5.1f} bar"
        )
        print(
            f"    Ihlal:     {n_violated:>6} (%{pct_violated:5.1f}) | Ihlal sirasinda FVG'nin %%{avg_pen:.1f}'i delinmis"
        )
        print(
            f"    Acik:      {n_open:>6} (%{n_open/len(life)*100:5.1f})" if life else ""
        )
        print(
            f"    Sweep:     {len(sweeps):>6} adet | Toparlanma: %{pct_sw_rec:5.1f} | Ort. {avg_rec:5.1f} bar"
        )

        # DNA profiling
        # fvg_expiry_bars: FVG'lerin %90'inin doldugu bar sayisi
        if fill_bars:
            sorted_bars = sorted(fill_bars)
            expiry = (
                sorted_bars[int(len(sorted_bars) * 0.9)]
                if len(sorted_bars) > 10
                else sorted_bars[-1]
            )
        else:
            expiry = 0

        # violation_tolerance: ihlal edilen FVG'lerde ortalama penetrasyon yuzdesi
        violation_tolerance = round(max(1.0, avg_pen * 1.5), 1) if n_violated else 0.05

        dna_data[sym] = {
            "fvg_expiry_bars": expiry,
            "violation_tolerance": violation_tolerance,
            "avg_fill_bars": round(avg_fill, 1),
            "violation_pct": round(pct_violated, 1),
            "sweep_recovery_bars": round(avg_rec, 1),
            "sweep_recovery_pct": round(pct_sw_rec, 1),
        }
        print(
            f"    🧬 DNA: expiry={expiry} bar, tol=%{violation_tolerance:.1f}, rec={avg_rec:.0f} bar"
        )

    # ── SUMMARY ──
    print("\n" + "=" * 100)
    print("  DNA KARSILASTIRMA TABLOSU")
    print("=" * 100)
    print(
        f"  {'Coin':<10} {'Expiry':>7} {'Dolma':>7} {'Ihlal%':>7} {'Tolerans':>9} {'SweepRec':>9} {'Rec%':>6}"
    )
    print(f"  {'-'*55}")
    for sym in cfg.SYMBOLS:
        d = dna_data.get(sym)
        if d:
            print(
                f"  {sym:<10} {d['fvg_expiry_bars']:>7} {d['avg_fill_bars']:>6.0f}b {d['violation_pct']:>6.1f}% {d['violation_tolerance']:>8.1f}% {d['sweep_recovery_bars']:>8.0f}b {d['sweep_recovery_pct']:>5.1f}%"
            )

    print(f"\n  Toplam sure: {time.time()-t0:.0f}s")
    print("\n  🧬 DNA Profili -> reports/fvg_behavior.json (manuel incele)")

    # JSON ciktisi
    import json

    json_path = os.path.join(REPORT_DIR, "fvg_behavior.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(dna_data, f, indent=2, ensure_ascii=False)
    print(f"  JSON: {json_path}")


if __name__ == "__main__":
    main()
