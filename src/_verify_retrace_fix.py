import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import analyzer_v5 as an

res = an._analyze_one_sym_v5("ADAUSDT")
stats = res["stats"]
trs = res["trade_records"]
tp = sum(1 for r in trs if r["result"] == "TP")
ptrail = sum(1 for r in trs if r["result"] == "PROFIT_TRAIL")
loss = sum(1 for r in trs if r["result"] in ("LOSS", "OPEN"))
print(
    f"[ADAUSDT] {stats['total_trades']} islem | TP:{tp} PTrail:{ptrail} "
    f"LOSS:{loss} | PE={stats['positive_exit_pct']:.1f}% "
    f"net PnL={stats['total_pnl']:+.2f}"
)
