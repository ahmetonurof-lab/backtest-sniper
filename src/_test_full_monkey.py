"""Full monkey-patch test: run BTC with MULT=0.12 (default) via monkey-patch."""
import sys, os, io, time

_SNIPER_SRC = os.path.join(os.path.dirname(__file__), "..", "..", "sniper", "src")
sys.path.insert(0, _SNIPER_SRC)
sys.path.insert(0, os.path.dirname(__file__))

import config as cfg
import analyzer_v3 as v3
from analyzer_v3 import load_data

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
daily_path = os.path.join(DATA_DIR, "daily", "BTCUSDT_1m_raw.csv")

def _dl(fp):
    return load_data(daily_path)

v3.load_data = _dl

print("Running BTC with MULT=0.12 (monkey-patched)...", flush=True)
t0 = time.time()
cfg.FVG_MIN_SIZE_ATR_MULT = 0.12
old = sys.stdout
sys.stdout = io.StringIO()
m = v3.run_for_symbol("BTCUSDT")
sys.stdout = old
cfg.FVG_MIN_SIZE_ATR_MULT = 0.12  # already default
dt = time.time() - t0

if m:
    print(f"MULT=0.12: {m['total_trades']} trades, PnL={m['total_pnl']:.0f}, WR={m['wr']:.1f}%, [{dt:.0f}s]", flush=True)
else:
    print(f"MULT=0.12: SKIP [{dt:.0f}s]", flush=True)
print("Full monkey-patch test done", flush=True)
