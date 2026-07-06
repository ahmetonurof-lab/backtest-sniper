import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, r'C:\Users\Administrator\Desktop\nexus-mcp\sniper\src')

import fvg_coin_profile as p

all_coin_data = {}
for sym in p.SYMBOLS_TO_TEST:
    t0 = time.time()
    t = p.run_backtest_for_symbol(sym)
    elapsed = time.time() - t0
    if t is None:
        print(f"{sym}: NO DATA")
        continue
    b = sum(1 for x in t if x['side']=='bullish')
    be = sum(1 for x in t if x['side']=='bearish')
    print(f"{sym}: {len(t)} trades ({b}B/{be}S)  [{elapsed:.0f}s]")
