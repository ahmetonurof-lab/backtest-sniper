import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "sniper", "src"
    ),
)
os.environ["SNIPER_OUTPUT_DIR"] = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "output"
)
import config as cfg

cfg.MIN_REL_FVG_THRESHOLD = 0.40

from analyzer_v5 import _collect_fvg_profile_impl as run

print("BTCUSDT calisiyor...", flush=True)
result = run("BTCUSDT")
if result is None or result[0] is None:
    print("HATA: calistiramadi", flush=True)
    sys.exit(1)

daily_rows, wins, losses, trade_records, captured_fvgs, atr_vals, expiry_used = result
print(f"Toplam FVG: {len(captured_fvgs)}", flush=True)

entered = [f for f in captured_fvgs if f.get("v4_rejected") == "ENTERED"]
print(f"Entered trades: {len(entered)}", flush=True)

# Debug: check v4_real_result values
results = {}
for f in entered:
    r = f.get("v4_real_result", "MISSING")
    results[r] = results.get(r, 0) + 1
print(f"v4_real_result dagilimi: {results}", flush=True)

# trailing SL wins vs TP wins
tp_wins = sum(
    1
    for f in entered
    if f.get("v4_real_result") == "TP" and f.get("v4_real_pnl_usd", 0) > 0
)
sl_wins = sum(
    1
    for f in entered
    if f.get("v4_real_result") == "SL" and f.get("v4_real_pnl_usd", 0) > 0
)
print(f"TP ile win: {tp_wins}, SL (trailing) ile win: {sl_wins}", flush=True)

groups = {"BOS_ONLY": [], "MSS_ONLY": [], "BOTH": [], "NONE": []}
for f in entered:
    g = f.get("bos_mss", {}).get("group", "NONE")
    groups[g].append(f)

print()
print(f"{'Group':<12} {'Total':>6} {'TP':>6} {'SL':>6} {'Win(p>0)':>9} {'Win%':>6}")
print(f"{'-'*12} {'-'*6} {'-'*6} {'-'*6} {'-'*9} {'-'*6}")
for g in ["BOS_ONLY", "MSS_ONLY", "BOTH", "NONE"]:
    fvgs = groups[g]
    total = len(fvgs)
    tp = sum(1 for f in fvgs if f.get("v4_real_result") == "TP")
    sl = sum(1 for f in fvgs if f.get("v4_real_result") == "SL")
    win = sum(1 for f in fvgs if f.get("v4_real_pnl_usd", 0) > 0)
    wr = win / total * 100 if total > 0 else 0
    print(f"{g:<12} {total:>6} {tp:>6} {sl:>6} {win:>9} {wr:>5.1f}%")

print(flush=True)
