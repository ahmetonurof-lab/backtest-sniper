import sys, os
sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.dirname(__file__))
from fvg_coin_profile import analyze_coin, find_all_swing_points, detect_bos_mss

fvgs, b15 = analyze_coin('BTCUSDT')
print(f'BTC: {len(fvgs)} FVG', flush=True)
hi, lo = find_all_swing_points(b15)
print(f'Swing points: {len(hi[0])} highs, {len(lo[0])} lows', flush=True)
groups = {'NONE':0,'BOS_ONLY':0,'MSS_ONLY':0,'BOTH':0}
for idx, f in enumerate(fvgs):
    if idx % 500 == 0 and idx > 0:
        print(f'  {idx}/{len(fvgs)}', flush=True)
    if idx > 0: pass
    bm = detect_bos_mss(f, b15, hi, lo)
    groups[bm['group']] += 1
print(f'BOS/MSS groups: {groups}', flush=True)
print('DONE', flush=True)
