"""Test monkey-patch MULT scan: 2 MULT values on BTC only."""
import sys, os, io
sys.path.insert(0, os.path.dirname(__file__))
_SNIPER_SRC = os.path.join(os.path.dirname(__file__), "..", "..", "sniper", "src")
sys.path.insert(0, _SNIPER_SRC)

import config as cfg
from analyzer_v3 import load_data, resample_15m

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
daily_path = os.path.join(DATA_DIR, "daily", "BTCUSDT_1m_raw.csv")

def _dl(fp):
    return load_data(daily_path)

import analyzer_v3 as v3
v3.load_data = _dl

orig = cfg.FVG_MIN_SIZE_ATR_MULT
for mult in [0.02, 0.12]:
    cfg.FVG_MIN_SIZE_ATR_MULT = mult
    old = sys.stdout
    sys.stdout = io.StringIO()
    m = v3.run_for_symbol("BTCUSDT")
    sys.stdout = old
    if m:
        print(f"MULT={mult:.2f}: {m['total_trades']} trades, PnL={m['total_pnl']:.0f}, WR={m['wr']:.1f}%")
    else:
        print(f"MULT={mult:.2f}: SKIP")
    sys.stdout.flush()
cfg.FVG_MIN_SIZE_ATR_MULT = orig
print("Monkey-patch MULT scan OK")
