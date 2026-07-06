"""
atr_cmp_real.py — ATR-CMP karsilastirmasi, gercek 2.5 yillik 1m veri ile.
Sentetik/random veri yok. BTC/LINK/ADA (veya tum 13 coin) icin:
  - 15m bara resample
  - her bar icin fake ATR (max(range, close*0.0001)) ve real Wilder's ATR
  - ortalama fake/real/ratio
  - zaman dilimine gore (yillik/ceyreklik) dagilim
  - yeni MULT onerisi
Rapor: sniper/docs/atr_conversion_report.md (guncelleme)
"""
import csv
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))

SNIPER_SRC = os.path.join(os.path.dirname(__file__), "..", "..", "sniper", "src")
sys.path.insert(0, SNIPER_SRC)

from models import Bar, ATR_PERIOD
from indicators import calculate_true_range, update_atr

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "daily")
SNIPER_DOCS = os.path.join(os.path.dirname(__file__), "..", "..", "sniper", "docs")
os.makedirs(SNIPER_DOCS, exist_ok=True)

# Mevcut FVG_SIZE_MAP (config.py'den)
FVG_SIZE_MAP = {
    "BTCUSDT": 10.0, "ETHUSDT": 1.5, "BNBUSDT": 0.8, "SOLUSDT": 0.14,
    "AVAXUSDT": 0.01, "LINKUSDT": 0.01, "XRPUSDT": 0.002, "ATOMUSDT": 0.005,
    "ADAUSDT": 0.0003, "SUIUSDT": 0.001, "APTUSDT": 0.003,
    "DOTUSDT": 0.003, "NEARUSDT": 0.001,
}
CURRENT_MULT = 0.12

# Oncelikli coinler, sonra tumu
PRIORITY = ["BTCUSDT", "LINKUSDT", "ADAUSDT"]
ALL_COINS = sorted(FVG_SIZE_MAP.keys())


def load_1m_raw(sym):
    path = os.path.join(DATA_DIR, f"{sym}_1m_raw.csv")
    if not os.path.isfile(path):
        return None
    bars = []
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            ts_str = row["open_time"]
            ts = int(datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").timestamp() * 1000)
            bars.append(Bar(
                index=i,
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row.get("volume", 0)),
                is_closed=True,
                timestamp=ts,
            ))
    return bars


def resample_15m(bars_1m):
    m15 = []
    for i in range(0, len(bars_1m), 15):
        chunk = bars_1m[i:i + 15]
        if len(chunk) < 15:
            break
        ts = chunk[0].timestamp
        m15.append(Bar(
            index=len(m15),
            open=chunk[0].open,
            high=max(b.high for b in chunk),
            low=min(b.low for b in chunk),
            close=chunk[-1].close,
            volume=sum(b.volume for b in chunk),
            is_closed=True,
            timestamp=ts,
        ))
    return m15


def ts_to_year_quarter(ts_ms):
    """timestamp ms -> (year, quarter)"""
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    return (dt.year, (dt.month - 1) // 3 + 1)


def analyze_coin(sym, bars_15m):
    """Returns dict with per-coin stats."""
    warmup = ATR_PERIOD  # 14 bar warmup

    results = []
    real_atr = None
    prev_close = None

    for i, bar in enumerate(bars_15m):
        fake_atr = max(bar.high - bar.low, bar.close * 0.0001)

        if prev_close is None:
            prev_close = bar.open
        tr = calculate_true_range(bar, prev_close)
        real_atr = update_atr(real_atr, tr)
        prev_close = bar.close

        results.append({
            "year_q": ts_to_year_quarter(bar.timestamp),
            "fake_atr": fake_atr,
            "real_atr": real_atr,
            "ratio": fake_atr / real_atr if real_atr > 0 else 0,
        })

    # Skip warmup
    post_warmup = results[warmup:]

    avg_fake = sum(r["fake_atr"] for r in post_warmup) / len(post_warmup)
    avg_real = sum(r["real_atr"] for r in post_warmup) / len(post_warmup)
    avg_ratio = sum(r["ratio"] for r in post_warmup) / len(post_warmup)

    # Quarterly breakdown
    q_data = defaultdict(list)
    for r in post_warmup:
        q_data[r["year_q"]].append(r["ratio"])

    quarterly = {}
    for yq in sorted(q_data.keys()):
        ratios = q_data[yq]
        quarterly[f"{yq[0]}-Q{yq[1]}"] = {
            "avg_ratio": sum(ratios) / len(ratios),
            "count": len(ratios),
        }

    # Yearly
    y_data = defaultdict(list)
    for r in post_warmup:
        y_data[r["year_q"][0]].append(r["ratio"])

    yearly = {}
    for y in sorted(y_data.keys()):
        ratios = y_data[y]
        yearly[str(y)] = {
            "avg_ratio": sum(ratios) / len(ratios),
            "count": len(ratios),
        }

    return {
        "sym": sym,
        "total_15m": len(bars_15m),
        "warmup": warmup,
        "analyzed": len(post_warmup),
        "avg_fake": avg_fake,
        "avg_real": avg_real,
        "avg_ratio": avg_ratio,
        "quarterly": quarterly,
        "yearly": yearly,
    }


CACHE_PATH = os.path.join(os.path.dirname(__file__), "..", "reports", "_atr_cmp_cache.json")


def main():
    # Load existing cache
    cache = {}
    if os.path.isfile(CACHE_PATH):
        with open(CACHE_PATH, "r") as f:
            cache = json.load(f)

    coins_to_run = PRIORITY + [c for c in ALL_COINS if c not in PRIORITY]

    for sym in coins_to_run:
        if sym in cache:
            print(f"{sym}... cached", flush=True)
            continue
        print(f"{sym}... ", end="", flush=True)
        bars_1m = load_1m_raw(sym)
        if not bars_1m:
            print(f"VERI YOK (data/daily/{sym}_1m_raw.csv)", flush=True)
            continue
        bars_15m = resample_15m(bars_1m)
        if len(bars_15m) < ATR_PERIOD + 10:
            print(f"YETERSIZ VERI ({len(bars_15m)} 15m bar)", flush=True)
            continue
        stats = analyze_coin(sym, bars_15m)
        cache[sym] = stats
        print(f"{stats['analyzed']:,} bar | fake={stats['avg_fake']:.4f} real={stats['avg_real']:.4f} ratio={stats['avg_ratio']:.4f}", flush=True)
        # Save cache after each coin
        with open(CACHE_PATH, "w") as f:
            json.dump(cache, f, indent=2)

    coin_stats = [cache[sym] for sym in coins_to_run if sym in cache]

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = []
    lines.append("# ATR Dönüşümü: Sahte → Gerçek Wilder's ATR (Güncellendi)\n")
    lines.append(f"**Tarih:** {now}\n")
    lines.append(f"**Veri:** 2.5 yıl (2024-01-01 → 2026-06-30) gerçek 1m veri → 15m bar\n")
    lines.append(f"**Yöntem:** Fake ATR = max(range, close × 0.0001); Real ATR = Wilder's smoothing 14-periyot\n")
    lines.append(f"**Not:** Önceki rapor sentetik 500 bar × 5 seed üzerinden hesaplanmıştı. Bu rapor tek bir gerçek 2.5 yıllık zaman serisi kullanır.\n")

    lines.append("---\n\n")
    lines.append("## ATR-CMP: Sahte vs Gerçek Karşılaştırması\n\n")
    lines.append("| Coin | 15m Bar | Fake ATR (ort) | Real ATR (ort) | Ratio (ort) | Ratio Min | Ratio Max |")
    lines.append("|------|---------|----------------|----------------|-------------|-----------|-----------|")

    for s in coin_stats:
        ratios = []
        for r in s["yearly"].values():
            ratios.append(r["avg_ratio"])
        # Compute min/max from yearly since we don't have per-bar data
        # Better: compute from raw but that's too much data. Use quarterly min/max
        q_ratios = [q["avg_ratio"] for q in s["quarterly"].values()]
        min_r = min(q_ratios) if q_ratios else 0
        max_r = max(q_ratios) if q_ratios else 0
        lines.append(
            f"| {s['sym']:<8} | {s['analyzed']:>7,} | {s['avg_fake']:>13.4f} | {s['avg_real']:>13.4f} "
            f"| {s['avg_ratio']:>10.4f} | {min_r:>8.4f} | {max_r:>8.4f} |"
        )

    lines.append("")

    # Ratio over time: yearly
    lines.append("### Zaman İçinde Ratio Değişimi (Yıllık Ortalama)\n")
    lines.append("| Coin | " + " | ".join(str(y) for y in sorted({k for s in coin_stats for k in s["yearly"]})) + " |")
    lines.append("|------|" + "|".join("---" for _ in sorted({k for s in coin_stats for k in s["yearly"]})) + "|")

    for s in coin_stats:
        row = f"| {s['sym']:<8} "
        for y in sorted({k for s2 in coin_stats for k in s2["yearly"]}):
            if y in s["yearly"]:
                row += f"| {s['yearly'][y]['avg_ratio']:.4f} "
            else:
                row += "| --- "
        lines.append(row + "|")

    lines.append("")

    # Ratio over time: quarterly
    lines.append("### Zaman İçinde Ratio Değişimi (Çeyreklik Ortalama)\n")
    all_q = sorted({k for s in coin_stats for k in s["quarterly"]})
    # Print in multiple tables to keep readable — one per coin
    for s in coin_stats:
        lines.append(f"**{s['sym']}:**\n")
        lines.append("| Dönem | Ratio | Bar Sayısı |")
        lines.append("|-------|-------|------------|")
        for q in sorted(s["quarterly"].keys()):
            qd = s["quarterly"][q]
            lines.append(f"| {q} | {qd['avg_ratio']:.4f} | {qd['count']:,} |")
        lines.append("")

    lines.append("---\n")

    # FVG_MIN_SIZE_ATR_MULT yeniden hesaplama
    lines.append("## `FVG_MIN_SIZE_ATR_MULT` Yeniden Hesaplama\n")
    lines.append(f"Mevcut değer: **{CURRENT_MULT}** (sahte ATR bazlı)\n")
    lines.append("Gerçek ATR ile her coin için önerilen MULT:\n")
    lines.append("| Coin | FVG_SIZE_MAP | Real ATR (ort) | Önerilen MULT | Mevcut MULT ile FVG |")
    lines.append("|------|-------------|----------------|---------------|---------------------|")

    mults = []
    for s in coin_stats:
        sym = s["sym"]
        fvg_val = FVG_SIZE_MAP.get(sym, 0)
        suggested = fvg_val / s["avg_real"] if s["avg_real"] > 0 else 0
        current_fvg = CURRENT_MULT * s["avg_real"]
        mults.append((sym, suggested))
        lines.append(
            f"| {sym:<8} | {fvg_val:>12} | {s['avg_real']:>13.4f} | {suggested:>14.6f} | {current_fvg:>20.4f} |"
        )

    lines.append("")
    lines.append("### Değerlendirme\n")

    # BTC-based anchor
    btc_stats = next((s for s in coin_stats if s["sym"] == "BTCUSDT"), None)
    if btc_stats:
        btc_mult = FVG_SIZE_MAP["BTCUSDT"] / btc_stats["avg_real"]
        lines.append(f"- BTC bazlı önerilen MULT: **{btc_mult:.4f}** (FVG 10.0 / Real ATR {btc_stats['avg_real']:.2f})\n")
        lines.append(f"- Mevcut MULT 0.12 ile karşılaştırma: {'DÜŞÜK' if btc_mult < 0.12 else 'YÜKSEK' if btc_mult > 0.12 else 'AYNI'} ({abs(btc_mult-0.12)*100/0.12:.1f}% fark)\n")
        lines.append(f"- Öneri: MULT = {btc_mult:.4f} (BTC anchor ile), veya coin bazlı override ile esneklik\n")

    # Coin-by-coin assessment
    lines.append("### Coin Bazlı MULT Dağılımı\n")
    lines.append("| Coin | MULT | Fark % |")
    lines.append("|------|------|--------|")
    for sym, mult in mults:
        diff_pct = (mult - CURRENT_MULT) / CURRENT_MULT * 100
        marker = "⚠️" if abs(diff_pct) > 20 else ""
        lines.append(f"| {sym:<8} | {mult:.4f} | {diff_pct:+.1f}% {marker} |")

    lines.append("")
    lines.append(f"- {sum(1 for _,m in mults if abs(m-CURRENT_MULT)/CURRENT_MULT>0.2)}/{len(mults)} coin mevcut MULT'tan %20'den fazla sapıyor.\n")

    # Option recommendation
    lines.append("### Seçenekler (ilerisi için)\n")
    lines.append("| Yaklaşım | Artı | Eksi |")
    lines.append("|----------|------|------|")
    lines.append("| A) Tek `FVG_MIN_SIZE_ATR_MULT` tüm coinler için | Basit, tek sabit | Düşük fiyatlı coinlerde FVG eşiği yanlış olabilir |")
    lines.append("| B) Coin bazlı MULT (eski `FVG_SIZE_MAP` gibi ama çarpan olarak) | Hassas, her coine özel | Fazla sabit, optimize etmesi zor |")
    lines.append("| C) `FVG_MIN_SIZE_ATR_MULT` + opsiyonel per-coin override | Esnek, çoğu coin tek çarpan, istisnalar override | Biraz daha kod |")

    lines.append("")
    lines.append("---\n")
    lines.append("## Karşılaştırma: Eski (Sentetik) vs Yeni (Gerçek)\n")
    lines.append("| Coin | Eski Ratio (sentetik) | Yeni Ratio (gerçek 2.5y) | Fark |")
    lines.append("|------|----------------------|--------------------------|------|")
    old_ratios = {"BTCUSDT": 1.01, "LINKUSDT": 1.01, "ADAUSDT": 1.01}
    for s in coin_stats:
        sym = s["sym"]
        old_r = old_ratios.get(sym, "—")
        if isinstance(old_r, str):
            lines.append(f"| {sym:<8} | {old_r:<20} | {s['avg_ratio']:.4f} | — |")
        else:
            diff = s["avg_ratio"] - old_r
            lines.append(f"| {sym:<8} | {old_r:<20.2f} | {s['avg_ratio']:.4f} | {diff:+.4f} |")

    lines.append("")
    lines.append("- Sentetik veride ratio ~1.01'di (fake ≈ real), gerçek veride farklı çıkabilir.\n")
    lines.append("- Gerçek veride ratio sabit değil, volatilite rejimine göre değişiyor.\n")
    lines.append("\n---\n")
    lines.append("*Rapor auto-generated by `atr_cmp_real.py`*\n")

    md_content = "\n".join(lines)

    report_path = os.path.join(SNIPER_DOCS, "atr_conversion_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"\nRapor: {report_path}")
    print("İlk 30 satır:")
    for line in lines[:30]:
        print(line)


if __name__ == "__main__":
    main()
