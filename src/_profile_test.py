import sys
import os
import time

t0 = time.time()
_THIS_DIR = r"C:\Users\Administrator\Desktop\nexus-mcp\backtest-sniper\src"
sys.path.insert(0, _THIS_DIR)
sys.path.insert(0, os.path.join(_THIS_DIR, "..", "..", "sniper", "src"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
with open(os.path.join(_THIS_DIR, "_profile_test.log"), "w") as f:
    f.write(f"{time.time()-t0:.1f}s: import config\n")
    f.flush()
    import config as cfg

    cfg.MIN_REL_FVG_THRESHOLD = 0.40
    f.write(f"{time.time()-t0:.1f}s: import analyzer\n")
    f.flush()
    from analyzer_v5 import collect_fvg_profile

    f.write(f"{time.time()-t0:.1f}s: calling collect_fvg_profile(BTCUSDT)\n")
    f.flush()
    r = collect_fvg_profile("BTCUSDT")
    f.write(f"{time.time()-t0:.1f}s: done\n")
    f.flush()
    if r and isinstance(r, tuple) and r[0]:
        f.write(
            f"daily_rows={len(r[0])} wins={len(r[1])} losses={len(r[2])} trade_records={len(r[3])}\n"
        )
    else:
        f.write(f"Result: {r}\n")
