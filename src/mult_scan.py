"""
mult_scan.py — FVG_MIN_SIZE_ATR_MULT taramasi, V3 + 2.5y gercek veri.
MULT = [0.02 .. 0.30] adim 0.02 (15 deger × 13 coin = 195 V3 backtest).
Monkey-patches cfg.FVG_MIN_SIZE_ATR_MULT per scan so analyzer_v3's dynamic
ATR-based logic uses the MULT value directly.
"""
import csv
import io
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

os.environ["SNIPER_OUTPUT_DIR"] = os.path.join(os.path.dirname(__file__), "..", "output")
sys.path.insert(0, os.path.dirname(__file__))
_SNIPER_SRC = os.path.join(os.path.dirname(__file__), "..", "..", "sniper", "src")
if _SNIPER_SRC not in sys.path:
    sys.path.insert(0, _SNIPER_SRC)

from models import Bar, ATR_PERIOD
import config as cfg
from indicators import calculate_true_range, update_atr
from analyzer_v3 import load_data, resample_15m

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DAILY_DIR = os.path.join(DATA_DIR, "daily")
REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
os.makedirs(REPORT_DIR, exist_ok=True)

CACHE_PATH = os.path.join(REPORT_DIR, "_mult_scan_cache.json")
MULT_RANGE = [round(0.02 + i * 0.02, 2) for i in range(15)]


def _daily_loader(filepath):
    return load_data(filepath)


def calc_avg_real_atr(bars_15m):
    real_atr = None
    prev_close = bars_15m[0].open
    vals = []
    for i, bar in enumerate(bars_15m):
        tr = calculate_true_range(bar, prev_close)
        real_atr = update_atr(real_atr, tr)
        prev_close = bar.close
        if i >= ATR_PERIOD:
            vals.append(real_atr)
    return sum(vals) / len(vals) if vals else 0


def main():
    print("=== Phase 1: Pre-load all coin data ===", flush=True)
    coin_data = {}

    for sym in cfg.SYMBOLS:
        t0 = time.time()
        csv_path = os.path.join(DATA_DIR, f"{sym}_1m.csv")
        bars_1m = _daily_loader(csv_path)
        bars_15m = resample_15m(bars_1m)
        if len(bars_15m) < 600:
            print(f"  {sym}: yetersiz veri ({len(bars_15m)})", flush=True)
            continue
        avg_atr = calc_avg_real_atr(bars_15m)
        coin_data[sym] = {"bars_1m": bars_1m, "bars_15m": bars_15m, "avg_atr": avg_atr}
        print(f"  {sym}: {len(bars_15m):>6,} bars, avg_real_atr={avg_atr:.4f} [{time.time()-t0:.0f}s]", flush=True)

    print(f"\nLoaded {len(coin_data)} coins.\n", flush=True)

    import analyzer_v3 as v3

    cache = {}
    if os.path.isfile(CACHE_PATH):
        with open(CACHE_PATH, "r") as f:
            cache = json.load(f)
    if "results" not in cache:
        cache["results"] = {}
    if "multi_map" not in cache:
        cache["multi_map"] = {}

    v3.load_data = _daily_loader

    total_runs = len(MULT_RANGE) * len(coin_data)
    done = sum(len(cache["results"].get(str(m), {})) for m in MULT_RANGE)
    print(f"Total runs: {total_runs}, cached: {done}", flush=True)

    for mult in MULT_RANGE:
        mk = str(mult)
        if mk not in cache["results"]:
            cache["results"][mk] = {}
        if mk not in cache["multi_map"]:
            cache["multi_map"][mk] = {}

        for sym in sorted(coin_data.keys()):
            if sym in cache["results"][mk]:
                continue

            avg_atr = coin_data[sym]["avg_atr"]
            min_fvg = round(mult * avg_atr, 4)
            cache["multi_map"][mk][sym] = min_fvg

            # Monkey-patch cfg.FVG_MIN_SIZE_ATR_MULT for this run
            original_fvg_mult = cfg.FVG_MIN_SIZE_ATR_MULT
            cfg.FVG_MIN_SIZE_ATR_MULT = mult

            t0 = time.time()
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            try:
                m = v3.run_for_symbol(sym)
            except Exception as e:
                sys.stdout = old_stdout
                cfg.FVG_MIN_SIZE_ATR_MULT = original_fvg_mult
                print(f"  ERROR {mult:.2f} {sym}: {e}", flush=True)
                continue
            sys.stdout = old_stdout
            cfg.FVG_MIN_SIZE_ATR_MULT = original_fvg_mult
            dt = time.time() - t0

            if m:
                cache["results"][mk][sym] = {
                    "trades": m["total_trades"],
                    "pnl": m["total_pnl"],
                    "wr": m["wr"],
                    "mdd": m["max_dd"],
                    "pf": m["profit_factor"],
                }
                print(f"MULT={mult:.2f} {sym}: min_fvg={min_fvg:.4f} "
                      f"trades={m['total_trades']} WR={m['wr']:.1f}% "
                      f"PnL={m['total_pnl']:+.0f} [{dt:.0f}s]", flush=True)
            else:
                print(f"MULT={mult:.2f} {sym}: SKIP", flush=True)

            with open(CACHE_PATH, "w") as f:
                json.dump(cache, f, indent=2)

    print("\n=== Phase 3: Generating report ===", flush=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    mults_done = sorted([float(k) for k in cache["results"] if cache["results"][k]])

    csv_path = os.path.join(REPORT_DIR, "mult_scan_report.csv")
    csv_cols = ["mult","sym","min_fvg","trades","pnl","wr","mdd","pf"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=csv_cols)
        w.writeheader()
        for mult in mults_done:
            mk = str(mult)
            for sym in sorted(cache["results"][mk]):
                r = cache["results"][mk][sym]
                mf = cache["multi_map"].get(mk, {}).get(sym, 0)
                w.writerow({
                    "mult": mult, "sym": sym, "min_fvg": round(mf, 4),
                    "trades": r["trades"], "pnl": r["pnl"],
                    "wr": r["wr"], "mdd": r["mdd"], "pf": r["pf"],
                })
    print(f"CSV: {csv_path}", flush=True)

    md_path = os.path.join(REPORT_DIR, "mult_scan_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# FVG_MIN_SIZE_ATR_MULT Tarama Raporu\n\n")
        f.write(f"**Generated:** {now}\n")
        f.write(f"**Strategy:** V3 — Sweep → FVG → Entry → Trailing → Exit\n")
        f.write(f"**Data:** 2.5 yil (2024-01-01 → 2026-06-30)\n")
        f.write(f"**MULT range:** {MULT_RANGE[0]:.2f} – {MULT_RANGE[-1]:.2f}, adim 0.02\n")
        f.write(f"**Formul:** `min_fvg_size = atr_val × MULT` (dinamik, bar-bazli)\n")
        f.write(f"**Ornek (BTC):** MULT=0.02 → ~{0.02*coin_data.get('BTCUSDT',{}).get('avg_atr',0):.1f}, MULT=0.12 → ~{0.12*coin_data.get('BTCUSDT',{}).get('avg_atr',0):.1f}, MULT=0.30 → ~{0.30*coin_data.get('BTCUSDT',{}).get('avg_atr',0):.1f}\n\n")

        f.write("## Ozet (Portfoy Toplami, 13 coin)\n\n")
        f.write("| MULT | Toplam Trade | Toplam PnL | WR (ort) | MaxDD (ort) | PF (ort) |\n")
        f.write("|------|-------------|------------|----------|-------------|----------|\n")
        for mult in mults_done:
            mk = str(mult)
            total_t = 0; total_p = 0.0; wrs = []; mdds = []; pfs = []
            for sym in sorted(cache["results"][mk]):
                r = cache["results"][mk][sym]
                total_t += r["trades"]
                total_p += r["pnl"]
                wrs.append(r["wr"])
                mdds.append(r["mdd"])
                pfs.append(r["pf"])
            avg_wr = sum(wrs)/len(wrs) if wrs else 0
            avg_mdd = sum(mdds)/len(mdds) if mdds else 0
            avg_pf = sum(pfs)/len(pfs) if pfs else 0
            f.write(f"| {mult:.2f} | {total_t:,} | {total_p:+,.0f} | {avg_wr:.1f}% | {avg_mdd:.1f}% | {avg_pf:.2f} |\n")

        f.write("\n## Coin Bazli En Iyi MULT (PnL bazinda)\n\n")
        f.write("| Coin | Real ATR | Best MULT | min_fvg | Trade | WR | PnL | MaxDD | PF |\n")
        f.write("|------|----------|-----------|---------|-------|----|-----|-------|----|\n")
        for sym in sorted(coin_data.keys()):
            best_pnl = -1e12; best_mult = None; best_r = None
            for mult in mults_done:
                mk = str(mult)
                if sym in cache["results"].get(mk, {}):
                    r = cache["results"][mk][sym]
                    if r["pnl"] > best_pnl:
                        best_pnl = r["pnl"]
                        best_mult = mult
                        best_r = r
            if best_r:
                avg_atr = coin_data[sym]["avg_atr"]
                mf = cache["multi_map"].get(str(best_mult), {}).get(sym, 0)
                f.write(f"| {sym:<8} | {avg_atr:<8.4f} | {best_mult:.2f} | {mf:<.4f} | {best_r['trades']:<5} | {best_r['wr']:.1f}% | {best_r['pnl']:<+9.0f} | {best_r['mdd']:.1f}% | {best_r['pf']:.2f} |\n")

        f.write("\n## Coin Bazli MULT Duyarliligi\n\n")
        f.write("Satir = coin, sutun = MULT. Hücre: `WR% / PnL`\n\n")
        f.write("| Coin | " + " | ".join(f"M={m:.2f}" for m in mults_done) + " |\n")
        f.write("|------|" + "|".join("---" for _ in mults_done) + "|\n")
        for sym in sorted(coin_data.keys()):
            row = f"| {sym:<8} "
            for mult in mults_done:
                mk = str(mult)
                if sym in cache["results"].get(mk, {}):
                    r = cache["results"][mk][sym]
                    row += f"| {r['wr']:.1f}%/{r['pnl']:<+8.0f} "
                else:
                    row += "| --- "
            f.write(row + "|\n")

        f.write("\n---\n")
        f.write("*Report auto-generated by `mult_scan.py`*\n")

    print(f"MD:  {md_path}", flush=True)
    print("\n=== DONE ===", flush=True)


if __name__ == "__main__":
    main()
