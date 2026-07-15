import sys

sys.path.insert(0, ".")
from analyzer_v5 import collect_fvg_profile, compute_session_stats
import config as cfg

sym = sys.argv[1] if len(sys.argv) > 1 else "BTCUSDT"
r = collect_fvg_profile(sym)
if r is None:
    print(f"[{sym}] VERI YOK")
    sys.exit(1)

daily_rows, wins, losses, trade_records, rejection_counts = r
stats = compute_session_stats(trade_records, cfg.INITIAL_BALANCE, daily_rows)

tp_c = int(stats["tp_pct"] * stats["total_trades"] / 100)
pt_c = int(stats["profit_trail_pct"] * stats["total_trades"] / 100)
ls_c = int(stats["loss_pct"] * stats["total_trades"] / 100)

print(
    f"{sym}: {stats['total_trades']} islem | "
    f"TP:{tp_c} PTrail:{pt_c} LOSS:{ls_c} | "
    f"PE={stats['positive_exit_pct']:.1f}% net PnL={stats['total_pnl']:+.6f}"
)
print(
    f"PF={stats['profit_factor']:.2f} Sharpe={stats['sharpe']:.3f} "
    f"MaxDD={stats['max_dd_pct']:.1f}% Score={stats['score']:.0f}"
)
