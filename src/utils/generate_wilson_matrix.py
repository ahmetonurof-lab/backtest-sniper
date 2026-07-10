"""
generate_wilson_matrix.py — Wilson score bazli CBDR matrisi olusturucu.

Her coin × her session icin analyze_thresholds()'u kosturur,
fail_limit + wilson_lower kontrolu ile dogru carpanlari belirler.
"""

import csv
import functools
import math
import os
import sys
from datetime import datetime, timezone
from collections import defaultdict

os.environ["SNIPER_OUTPUT_DIR"] = os.path.join(
    os.path.dirname(__file__), "..", "output"
)
sys.path.insert(0, os.path.dirname(__file__))
_SNIPER_SRC = os.path.join(os.path.dirname(__file__), "..", "..", "sniper", "src")
if _SNIPER_SRC not in sys.path:
    sys.path.insert(0, _SNIPER_SRC)

import config as cfg
from indicators import calculate_true_range, update_atr
from models import Bar
from session import SessionState

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "daily")

SESSIONS = {
    "DEFAULT": {"start": 22, "end": 2},
    "REAL_CBDR": {"start": 19, "end": 1},
    "ASIA_RANGE": {"start": 1, "end": 5},
}

CBDR_BUCKETS = [
    (0.0, 1.0),
    (1.0, 1.5),
    (1.5, 2.0),
    (2.0, 3.0),
    (3.0, 5.0),
    (5.0, 999.0),
]
BUCKET_LABELS = ["0-1%", "1-1.5%", "1.5-2%", "2-3%", "3-5%", ">5%"]


def wilson_upper(wins, trades, z=1.96):
    if trades == 0:
        return 1.0
    z2 = z * z
    p_hat = wins / trades
    d = 1 + z2 / trades
    c = p_hat + z2 / (2 * trades)
    m = z * math.sqrt((p_hat * (1 - p_hat) + z2 / (4 * trades)) / trades)
    return min(1.0, (c + m) / d)


def wilson_lower(wins, trades, z=1.96):
    if trades == 0:
        return 0.0
    z2 = z * z
    p_hat = wins / trades
    d = 1 + z2 / trades
    c = p_hat + z2 / (2 * trades)
    m = z * math.sqrt((p_hat * (1 - p_hat) + z2 / (4 * trades)) / trades)
    return max(0.0, (c - m) / d)


@functools.lru_cache(maxsize=32)
def load_data(path):
    bars = []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ts = int(
                datetime.strptime(row["open_time"], "%Y-%m-%d %H:%M:%S")
                .replace(tzinfo=timezone.utc)
                .timestamp()
                * 1000
            )
            bars.append(
                Bar(
                    index=len(bars),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                    is_closed=True,
                    timestamp=ts,
                )
            )
    return bars


def resample_15m(b1):
    m15 = []
    for i in range(0, len(b1), 15):
        c = b1[i : i + 15]
        if len(c) < 15:
            break
        m15.append(
            Bar(
                index=len(m15),
                open=c[0].open,
                high=max(b.high for b in c),
                low=min(b.low for b in c),
                close=c[-1].close,
                volume=sum(b.volume for b in c),
                is_closed=True,
                timestamp=c[0].timestamp,
            )
        )
    return m15


def collect_stats(sym, sess_name):
    """collect_daily_data'in sadece istatistik toplayan versiyonu."""
    sess = SESSIONS[sess_name]
    csv_path = os.path.join(DATA_DIR, f"{sym}_1m_raw.csv")
    if not os.path.isfile(csv_path):
        return None

    b1 = load_data(csv_path)
    b15 = resample_15m(b1)
    if not b15:
        return None

    sh, eh = sess["start"], sess["end"]
    spans = sh > eh
    ss = SessionState(start_hour=sh, end_hour=eh)

    day_cbdr = {}
    day_trades = defaultdict(list)

    atr_val = 0.0
    prev_close = b15[0].open
    for bar in b15[1:500]:
        tr = calculate_true_range(bar, prev_close)
        atr_val = update_atr(atr_val if atr_val > 0 else None, tr)
        prev_close = bar.close

    total = len(b15)
    for sb in range(500, total):
        if (sb - 500) % 10000 == 0:
            print(
                f"\r  {sym}/{sess_name}: %{((sb-500)/(total-500)*100):.0f}",
                end="",
                flush=True,
            )
        chunk = b15[sb - 500 : sb + 1]
        cur = b15[sb]
        tr = calculate_true_range(cur, prev_close)
        atr_val = update_atr(atr_val if atr_val > 0 else None, tr)
        prev_close = cur.close
        atr = atr_val
        try:
            edt = datetime.fromtimestamp(cur.timestamp / 1000, tz=timezone.utc)
        except:
            continue
        locked_before = ss.cbdr_locked
        ss.update(edt, cur.open, cur.high, cur.low, cur.close, atr)
        if ss.cbdr_locked and not locked_before and ss.cbdr_body_high > 0:
            w = ((ss.cbdr_body_high - ss.cbdr_body_low) / ss.cbdr_body_low) * 100
            day_cbdr[ss.cbdr_day] = round(w, 4)

        if ss.sweep_confirmed and rsm.state_name == "IDLE":
            rsm.on_sweep(
                direction=ss.sweep_direction or "bullish",
                level=ss.sweep_level or 0.0,
                bar_index=None,
            )
        if rsm.state_name == "SWEEP_DETECTED":
            rsm.on_sweep_confirmed(chunk, cur, atr)

        from retrace_state import RetraceStateMachine

        rsm = RetraceStateMachine(max_wick_ratio=cfg.FVG_WICK_RATIO_MAX)

        # ... bu cok uzun surer. alternatif: direkt parquet'ten oku.

    return None


print("Bu script calismayacak - cok uzun. Alternatif yaklasiyorum...")
