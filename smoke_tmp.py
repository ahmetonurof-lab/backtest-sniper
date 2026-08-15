import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
sys.path.insert(0, r"C:/Users/Administrator/Desktop/nexus-mcp/sniper/src")
sys.path.insert(0, os.path.dirname(__file__))

import analyzer_v5 as eng

res = eng._analyze_one_sym_v5(
    "SOLUSDT",
    "retrace",
    eng.CONT_BUFFER_MULT,
    eng.TRAIL_ACTIVATION_R_MULT,
    None,
    0.0,
    False,
    0.0,
    0.5,
    False,
    0.0,
    0.5,
    3.0,
    1.5,
    2.0,
)
line = "TYPE: " + type(res).__name__
if isinstance(res, dict) and "error" not in res:
    stats = res["stats"]
    rej = res["rejection_counts"]
    line += (
        "\nSOLUSDT SCALE(3pct,50,SL1.5,step2): %d trade | net PnL=%+.2f | partial=%d"
        % (
            stats["total_trades"],
            stats["total_pnl"],
            rej.get("PARTIAL_TP", 0),
        )
    )
    line += "\nOK"
else:
    line += "\nRES: " + repr(res)
with open("smoke_out.txt", "w", encoding="utf-8") as f:
    f.write(line + "\n")
