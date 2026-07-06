import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import fvg_profile_v4 as p
from collections import Counter

r = p.collect_fvg_profile('BTCUSDT')
if r[0] is None:
    print("No results")
    sys.exit(1)

daily_rows, wins_list, losses_list, trade_records, captured = r

c = Counter(f.get('v4_rejected','?') for f in captured)
total_fvg = len(captured)

n_trades = len(trade_records)
n_wins = len([t for t in trade_records if t.get('result') in ('TP',)])
n_be = len([t for t in trade_records if t.get('result') == 'BE'])
n_losses = len([t for t in trade_records if t.get('result') in ('SL',)])
n_tc = len([t for t in trade_records if t.get('result') == 'TRAIL_CLOSE'])
total_pnl = sum(t.get('pnl', 0) for t in trade_records)

print(f"BTCUSDT — QUALITY + VALIDITY DEVRE DISI")
print(f"Trades: {n_trades}  W:{n_wins}  BE:{n_be}  L:{n_losses}  TC:{n_tc}  WR:{n_wins/n_trades*100:.1f}%")
print(f"Total PnL: {total_pnl:.2f}")
print(f"\nFilter breakdown (total FVG: {total_fvg}):")
for k, v in c.most_common():
    print(f"  {k:<25s} {v:>6d} ({v/total_fvg*100:5.1f}%)")
