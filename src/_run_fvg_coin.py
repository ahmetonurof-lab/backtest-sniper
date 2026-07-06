import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, r'C:\Users\Administrator\Desktop\nexus-mcp\sniper\src')

sys.stdout.write("importing...\n"); sys.stdout.flush()
import fvg_coin_profile as p
sys.stdout.write("running BTCUSDT...\n"); sys.stdout.flush()
t0 = time.time()
t = p.run_backtest_for_symbol('BTCUSDT')
sys.stdout.write(f"done in {time.time()-t0:.0f}s, trades={len(t)}\n"); sys.stdout.flush()

bias = sum(1 for x in t if x['side']=='bullish')
bear = sum(1 for x in t if x['side']=='bearish')
sys.stdout.write(f"Bull: {bias}  Bear: {bear}\n"); sys.stdout.flush()
if t:
    sys.stdout.write(f"First: idx={t[0]['entry_bar']} price={t[0]['entry_price']} side={t[0]['side']}\n")
    sys.stdout.write(f"Last:  idx={t[-1]['entry_bar']} price={t[-1]['entry_price']} side={t[-1]['side']}\n")
