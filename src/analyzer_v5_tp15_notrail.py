"""
analyzer_v5_tp15_notrail.py — analyzer_v5 motorunu import eder, TP_RR=1.5 ceker
VE trailing'i bypass eder (detect_fvgs -> bos liste; SL/TP ilk seviyede kalir).
Orijinal (TP_RR=2.0 + trailing) ve TP_RR=1.5 + trailing sonuclariyla karsilastirir.
"""

# ruff: noqa: E402
import os
import sys
import time

os.environ["SNIPER_OUTPUT_DIR"] = os.path.join(os.path.dirname(__file__), "..", "output")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_SNIPER_SRC = os.path.join(os.path.dirname(__file__), "..", "..", "sniper", "src")
if _SNIPER_SRC not in sys.path:
    sys.path.insert(0, _SNIPER_SRC)

import config as cfg

cfg.TP_RR = 1.5

import analyzer_v5 as engine

# Trailing bypass: trailing blogu detect_fvgs() sonucunu kullanir.
# Bos liste -> coklu-hop calismaz, SL/TP ilk seviyede kalir, PROFIT_TRAIL olusmaz.
engine.detect_fvgs = lambda *args: []

# Orijinal rapor (reports/analyzer_v5_summary.md — 2026-07-31 blogu, TP_RR=2.0 + trailing)
ORIGINAL_GMX = {
    "Trades": 4166,
    "TP%": 10.8,
    "PTrail%": 51.9,
    "Loss%": 37.3,
    "PF": 4.00,
    "Sharpe": 0.327,
    "MaxDD%": 0.6,
    "Fee": 61717,
    "NetPnL": 194915,
    "PnL/Fee": 3.16,
    "Score": 789.0,
}

# Onceki kosu: TP_RR=1.5 + trailing ACIK (analyzer_v5_tp15.py)
TP15_TRAIL_GMX = {
    "Trades": 4275,
    "TP%": 13.6,
    "PTrail%": 49.3,
    "Loss%": 37.1,
    "PF": 3.83,
    "Sharpe": 0.313,
    "MaxDD%": 0.58,
    "Fee": 62590,
    "NetPnL": 188502,
    "PnL/Fee": 3.01,
    "Score": 721.0,
}


def main():
    symbol = "GMXUSDT"
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    t0 = time.time()
    print("=" * 96)
    print(f"  analyzer_v5 TP_RR=1.5 + TRAILING YOK | {symbol}")
    print("=" * 96)

    result = engine.collect_fvg_profile(symbol)
    if result is None or (isinstance(result, tuple) and result[0] is None):
        print(f"    [{symbol}] VERI YOK")
        return
    daily_rows, wins, losses, trade_records, rejection_counts = result
    if len(daily_rows) < 1:
        print(f"    [{symbol}] YETERSIZ VERI (daily_rows={len(daily_rows)})")
        return

    stats = engine.compute_session_stats(trade_records, cfg.INITIAL_BALANCE, daily_rows)
    print(f"\n  [{symbol}] {stats['total_trades']} islem | "
          f"TP:{int(stats['tp_pct'] * stats['total_trades'] / 100)} "
          f"PTrail:{int(stats['profit_trail_pct'] * stats['total_trades'] / 100)} "
          f"LOSS:{int(stats['loss_pct'] * stats['total_trades'] / 100)} | "
          f"PE={stats['positive_exit_pct']:.1f}%")
    print(f"    Red: {str(dict(sorted(rejection_counts.items(), key=lambda x: x[0])))}")
    print(f"\n  Sure: {time.time() - t0:.0f}s")

    print("\n" + "=" * 96)
    print("  KARSILASTIRMA  [A] TP_RR=2.0+trail | [B] TP_RR=1.5+trail | [C] TP_RR=1.5 + TRAILING YOK")
    print("=" * 96)
    hdr = f"  {'Metrik':<12} {'[A] 2.0+trail':>14} {'[B] 1.5+trail':>14} {'[C] 1.5 NOTRAIL':>16} {'C vs A':>9} {'C vs B':>9}"
    print(hdr)
    print(f"  {'-' * len(hdr)}")

    def row(label, a, b, c):
        da = c - a
        db = c - b
        print(f"  {label:<12} {a:>14.2f} {b:>14.2f} {c:>16.2f} {da:>+9.0f} {db:>+9.0f}")

    row("Trades", ORIGINAL_GMX["Trades"], TP15_TRAIL_GMX["Trades"], stats["total_trades"])
    row("TP%", ORIGINAL_GMX["TP%"], TP15_TRAIL_GMX["TP%"], stats["tp_pct"])
    row("PTrail%", ORIGINAL_GMX["PTrail%"], TP15_TRAIL_GMX["PTrail%"], stats["profit_trail_pct"])
    row("Loss%", ORIGINAL_GMX["Loss%"], TP15_TRAIL_GMX["Loss%"], stats["loss_pct"])
    row("PF", ORIGINAL_GMX["PF"], TP15_TRAIL_GMX["PF"], stats["profit_factor"])
    row("Sharpe", ORIGINAL_GMX["Sharpe"], TP15_TRAIL_GMX["Sharpe"], stats["sharpe"])
    row("MaxDD%", ORIGINAL_GMX["MaxDD%"], TP15_TRAIL_GMX["MaxDD%"], stats["max_dd_pct"])
    row("Fee", ORIGINAL_GMX["Fee"], TP15_TRAIL_GMX["Fee"], stats["total_fee"])
    row("NetPnL", ORIGINAL_GMX["NetPnL"], TP15_TRAIL_GMX["NetPnL"], stats["total_pnl"])
    row("PnL/Fee", ORIGINAL_GMX["PnL/Fee"], TP15_TRAIL_GMX["PnL/Fee"], stats["pnl_per_fee"])
    row("Score", ORIGINAL_GMX["Score"], TP15_TRAIL_GMX["Score"], stats["score"])


if __name__ == "__main__":
    main()
