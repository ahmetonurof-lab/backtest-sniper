import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))

t0 = time.time()
log = []
log.append(f"[{t0:.0f}] loading BTC data...")
sys.stdout.flush()

import fvg_profile_v4 as p

log.append(f"[{time.time():.0f}] loaded, running profile...")
sys.stdout.flush()

from collections import Counter
r = p.collect_fvg_profile('BTCUSDT')

log.append(f"[{time.time():.0f}] done")
sys.stdout.flush()

if r and r[0]:
    trades, wins, losses, be, captured = r
    c = Counter(f.get('v4_rejected','?') for f in captured)
    total = len(captured)
    log.append(f"BTCUSDT — {len(trades)} trades ({wins}W/{be}BE/{losses}L)")
    log.append(f"Total FVG: {total}")
    for k, v in c.most_common():
        log.append(f"  {k:<25s} {v:>6d} ({v/total*100:5.1f}%)")

out = "\n".join(log)
print(out)
with open(os.path.join(os.path.dirname(__file__), "_btc_result.txt"), "w", encoding="utf-8") as f:
    f.write(out)
