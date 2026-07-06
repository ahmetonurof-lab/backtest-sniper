import csv
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_SNIPER_SRC = os.path.join(os.path.dirname(__file__), "..", "..", "sniper", "src")
if _SNIPER_SRC not in sys.path:
    sys.path.insert(0, _SNIPER_SRC)

from indicators import calculate_true_range, update_atr
from session import SessionState
from retrace_state import RetraceStateMachine
from models import Bar

# --- Backtest Parametreleri (Canlı sistemle uyumlu) ---
SYMBOLS_TO_TEST = [
    "BTCUSDT",
    "BNBUSDT",
    "SOLUSDT",
    "AVAXUSDT",
    "LINKUSDT",
    "XRPUSDT",
    "ATOMUSDT",
    "ADAUSDT",
    "APTUSDT",
    "DOTUSDT",
    "NEARUSDT",
    "ETHUSDT",
    "SUIUSDT",
]


def load_data(filepath):
    bars = []
    with open(filepath, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            ts = int(
                datetime.strptime(row["open_time"], "%Y-%m-%d %H:%M:%S")
                .replace(tzinfo=timezone.utc)
                .timestamp()
                * 1000
            )
            bars.append(
                Bar(
                    index=i,
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


def run_backtest_for_symbol(symbol):
    csv_path = (
        Path(__file__).resolve().parent / "data" / "daily" / f"{symbol}_1m_raw.csv"
    )
    if not csv_path.exists():
        return None

    bars_1m = load_data(csv_path)

    # 15m'e resample et (Basit haliyle)
    bars_15m = []
    for i in range(0, len(bars_1m), 15):
        c = bars_1m[i : i + 15]
        if len(c) < 15:
            break
        bars_15m.append(
            Bar(
                index=i // 15,
                open=c[0].open,
                high=max(b.high for b in c),
                low=min(b.low for b in c),
                close=c[-1].close,
                volume=sum(b.volume for b in c),
                is_closed=True,
                timestamp=c[0].timestamp,
            )
        )

    # State'leri başlat
    ss = SessionState()
    rsm = RetraceStateMachine()

    # ATR warmup + main loop (cbdr_default.py ile aynı)
    atr_val = 0.0
    prev_close = bars_15m[0].open if bars_15m else 0.0
    for bar in bars_15m[1:500]:
        tr = calculate_true_range(bar, prev_close)
        atr_val = update_atr(atr_val if atr_val > 0 else None, tr)
        prev_close = bar.close

    trades = []

    total_bars = len(bars_15m)
    for i in range(500, total_bars):
        bar = bars_15m[i]
        tr = calculate_true_range(bar, prev_close)
        atr_val = update_atr(atr_val if atr_val > 0 else None, tr)
        prev_close = bar.close
        atr = atr_val

        dt = datetime.fromtimestamp(bar.timestamp / 1000, tz=timezone.utc)

        ss.update(dt, bar.open, bar.high, bar.low, bar.close, atr)
        if ss.cbdr_locked and not ss.sweep_confirmed:
            ss._cbdr.check_sweep(bar.high, bar.low, bar.close, atr)

        if ss.sweep_confirmed and rsm.state_name == "IDLE":
            rsm.on_sweep(direction=ss.sweep_direction or "bullish",
                         level=ss.sweep_level or 0.0, bar_index=None)
        if rsm.state_name == "SWEEP_DETECTED":
            chunk = bars_15m[max(0, i-500): i + 1]
            rsm.on_sweep_confirmed(chunk, bar, atr)

        if rsm.state_name == "TRIGGER_READY" and rsm.trigger_fvg:
            if True:  # DISABLED: is_high_quality_fvg + is_fvg_valid
                trade = {
                    "entry_bar": i,
                    "entry_price": rsm.trigger_fvg.top
                    if rsm.direction == "bearish"
                    else rsm.trigger_fvg.bottom,
                    "side": rsm.direction,
                }
                trades.append(trade)
                rsm.reset()

    return trades


def main():
    results = {}
    for sym in SYMBOLS_TO_TEST:
        print(f"Analyzing {sym}...")
        t = run_backtest_for_symbol(sym)
        results[sym] = t
        if t is not None:
            b = sum(1 for x in t if x['side']=='bullish')
            s = sum(1 for x in t if x['side']=='bearish')
            print(f"  -> {len(t)} trades ({b}B/{s}S)")
        else:
            print(f"  -> NO DATA")

    total = sum(len(v) for v in results.values() if v)
    print(f"\nBacktest completed. Total trades: {total}")

    # Basit rapor yaz
    lines = ["# FVG Coin Profile — Filter Bypass\n"]
    lines.append(f"| Coin | Trades | Bull | Bear |\n|----|----|----|----|\n")
    for sym in SYMBOLS_TO_TEST:
        t = results.get(sym)
        if t:
            b = sum(1 for x in t if x['side']=='bullish')
            s = sum(1 for x in t if x['side']=='bearish')
            lines.append(f"| {sym} | {len(t)} | {b} | {s} |\n")
    lines.append(f"\n**Total: {total}**\n")

    report_path = os.path.join(os.path.dirname(__file__), "..", "reports", "fvg_coin_profile.md")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"Rapor: {report_path}")


if __name__ == "__main__":
    main()
