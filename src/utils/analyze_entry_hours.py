"""
analyze_entry_hours.py — Hangi UTC saatlerinde entry acilmis?
Her session/coin icin saat bazli trade histogrami (0-23).
"""

# ruff: noqa: E402
import csv
import os
import sys
from datetime import datetime, timezone
from collections import defaultdict

os.environ["SNIPER_OUTPUT_DIR"] = os.path.join(
    os.path.dirname(__file__), "..", "output"
)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_SNIPER_SRC = os.path.join(os.path.dirname(__file__), "..", "..", "sniper", "src")
if _SNIPER_SRC not in sys.path:
    sys.path.insert(0, _SNIPER_SRC)

import config as cfg
from fvg import detect_fvgs
from indicators import calculate_true_range, update_atr
from models import Bar
from retrace_state import RetraceStateMachine
from session import DailyBias, SessionState

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SESSION_CONFIGS = {
    "REAL_CBDR": {"start": 19, "end": 1},
    "DEFAULT": {"start": 22, "end": 2},
    "ASIA_RANGE": {"start": 1, "end": 5},
}


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


def resample_15m(bars_1m):
    m15 = []
    for i in range(0, len(bars_1m), 15):
        c = bars_1m[i : i + 15]
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


def collect_entry_hours(symbol: str, session_name: str, session_hours: dict):
    """Backtest'i calistir, her trade'in entry hour'ini topla."""
    csv_path = os.path.join(
        os.path.dirname(__file__), "data", "daily", f"{symbol}_1m_raw.csv"
    )
    if not os.path.isfile(csv_path):
        return None

    ic = cfg.INITIAL_BALANCE
    rpt = cfg.RISK_PER_TRADE
    sam = cfg.SL_ATR_MULT
    tpr = cfg.TP_RR
    fbm = cfg.FVG_BUFFER_MULT
    ATM = cfg.ATR_TRAIL_MULT
    TMM = cfg.TRAIL_MIN_MOVE_MULT
    BERM = cfg.BE_RISK_MULT
    BESP = cfg.BE_SPREAD_PTS
    FVG_MIN_SIZE_ATR_MULT = cfg.FVG_MIN_SIZE_ATR_MULT

    b1 = load_data(csv_path)
    b15 = resample_15m(b1)
    if not b15:
        return None

    sh = session_hours["start"]
    eh = session_hours["end"]
    spans_midnight = sh > eh
    ss = SessionState(start_hour=sh, end_hour=eh)
    rsm = RetraceStateMachine(max_wick_ratio=cfg.FVG_WICK_RATIO_MAX)

    hour_hist = defaultdict(int)  # hour -> count
    day_cbdr = {}
    day_trades = defaultdict(list)
    active = []
    wins = []
    losses = []
    trade_records = []

    atr_val = 0.0
    prev_close = b15[0].open
    for bar in b15[1:500]:
        tr = calculate_true_range(bar, prev_close)
        atr_val = update_atr(atr_val if atr_val > 0 else None, tr)
        prev_close = bar.close

    total_bars = len(b15)
    for sb in range(500, total_bars):
        if (sb - 500) % 5000 == 0:
            pct = (sb - 500) / (total_bars - 500) * 100
            print(
                f"\r    [{session_name}] %{pct:.0f} ({sb}/{total_bars})",
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
        except Exception:
            continue

        locked_before = ss.cbdr_locked
        ss.update(edt, cur.open, cur.high, cur.low, cur.close, atr)
        just_locked = ss.cbdr_locked and not locked_before

        if just_locked and ss.cbdr_body_high > 0:
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

        if rsm.can_trigger() and not active:
            sd = rsm.direction
            db = ss.daily_bias
            if (
                (sd == "bullish" and db == DailyBias.BEARISH)
                or (sd == "bearish" and db == DailyBias.BULLISH)
                or db == DailyBias.NEUTRAL
            ):
                rsm.reset()
                continue
            h = edt.hour
            if (h >= sh or h < eh) if spans_midnight else (sh <= h < eh):
                rsm.reset()
                continue

            # ★ ENTRY HOUR captured here
            hour_hist[h] += 1

            side = "long" if sd == "bullish" else "short"
            ep = cur.close
            rp2 = atr * sam
            tf = rsm.trigger_fvg

            if side == "long":
                if tf:
                    fh = tf.top - tf.bottom
                    if fh <= 0:
                        sl = ep - rp2 * 2
                    else:
                        ab = max(fh * 0.10, max(rp2 * 0.1, min(fh * 0.25, rp2 * fbm)))
                        sl = tf.bottom - ab
                else:
                    sl = ep - rp2 * 2
                rd = abs(sl - ep)
                if tf and rd > rp2 * 2.0:
                    sl = ep - rp2 * 2
                    rd = abs(sl - ep)
                if rd <= 0:
                    sl = ep - rp2 * 2
                    rd = abs(sl - ep)
                tp = ep + rd * tpr
            else:
                if tf:
                    fh = tf.top - tf.bottom
                    if fh <= 0:
                        sl = ep + rp2 * 2
                    else:
                        ab = max(fh * 0.10, max(rp2 * 0.1, min(fh * 0.25, rp2 * fbm)))
                        sl = tf.top + ab
                else:
                    sl = ep + rp2 * 2
                rd = abs(sl - ep)
                if tf and rd > rp2 * 2.0:
                    sl = ep + rp2 * 2
                    rd = abs(sl - ep)
                if rd <= 0:
                    sl = ep + rp2 * 2
                    rd = abs(sl - ep)
                tp = ep - rd * tpr

            if rd < atr * 0.1:
                rsm.reset()
                continue
            qty = (ic * rpt) / rd if rd > 0 else 0
            if qty <= 0:
                rsm.reset()
                continue

            entry_day = ss.cbdr_day
            active.append(
                {
                    "entry_bar": sb,
                    "entry_price": ep,
                    "sl": sl,
                    "tp": tp,
                    "qty": qty,
                    "side": side,
                    "trigger_fvg": tf,
                    "initial_sl": sl,
                    "initial_tp": tp,
                    "trailing_count": 0,
                    "day_key": entry_day,
                }
            )
            rsm.reset()

        if active and cur.is_closed:
            for t in active:
                if t.get("closed") or t.get("trailing_count", 0) > 0:
                    continue
                s2 = t["side"]
                e2 = t["entry_price"]
                rpt2 = abs(t["initial_sl"] - e2)
                th2 = rpt2 * BERM
                be2 = e2 + BESP if s2 == "long" else e2 - BESP
                if s2 == "long":
                    if cur.high >= e2 + th2 and t["sl"] < be2:
                        t["sl"] = be2
                        t["trailing_count"] = 1
                else:
                    if cur.low <= e2 - th2 and t["sl"] > be2:
                        t["sl"] = be2
                        t["trailing_count"] = 1

            tc = chunk[:-1]
            min_fvg_size = max(atr * FVG_MIN_SIZE_ATR_MULT, 1e-8)
            cfvgs = detect_fvgs(
                tc,
                lookback=min(50, len(tc)),
                timeframe="15m",
                min_fvg_size=min_fvg_size,
            )
            for t in active:
                if t.get("closed"):
                    continue
                s2 = t["side"]
                csl = t["sl"]
                ctp = t["tp"]
                rpt2 = abs(t["initial_sl"] - t["entry_price"])
                ltc = 0
                upd = False
                for fvg in cfvgs:
                    if s2 == "long" and fvg.direction != "bullish":
                        continue
                    if s2 == "short" and fvg.direction != "bearish":
                        continue
                    if not fvg_close_confirmed(fvg, tc):
                        continue
                    ab2 = atr * ATM
                    if s2 == "long":
                        ns = fvg.bottom - ab2
                        if ns > csl and (ns - csl) > rpt2 * TMM:
                            sd2 = ns - csl
                            csl = ns
                            ctp += sd2
                            ltc += 1
                            upd = True
                    else:
                        ns = fvg.top + ab2
                        if ns < csl and (csl - ns) > rpt2 * TMM:
                            sd2 = csl - ns
                            csl = ns
                            ctp -= sd2
                            ltc += 1
                            upd = True
                if upd:
                    t["sl"] = csl
                    t["tp"] = ctp
                    t["trailing_count"] = t.get("trailing_count", 0) + ltc

        sa = []
        for t in active:
            if t.get("closed"):
                continue
            ex = False
            if t["side"] == "long":
                if cur.low <= t["sl"]:
                    t["exit_price"] = t["sl"]
                    t["exit_bar"] = sb
                    t["result"] = "SL"
                    t["closed"] = True
                    ex = True
                elif cur.high >= t["tp"]:
                    t["exit_price"] = t["tp"]
                    t["exit_bar"] = sb
                    t["result"] = "TP"
                    t["closed"] = True
                    ex = True
            else:
                if cur.high >= t["sl"]:
                    t["exit_price"] = t["sl"]
                    t["exit_bar"] = sb
                    t["result"] = "SL"
                    t["closed"] = True
                    ex = True
                elif cur.low <= t["tp"]:
                    t["exit_price"] = t["tp"]
                    t["exit_bar"] = sb
                    t["result"] = "TP"
                    t["closed"] = True
                    ex = True
            if ex:
                diff = (
                    (t["exit_price"] - t["entry_price"])
                    if t["side"] == "long"
                    else (t["entry_price"] - t["exit_price"])
                )
                t["pnl"] = round(diff * t["qty"], 2)
                day_trades[t.get("day_key", "")].append(t["pnl"])
                trade_records.append({"result": t["result"], "pnl": t["pnl"]})
                if t["pnl"] > 0:
                    wins.append(t)
                else:
                    losses.append(t)
            else:
                sa.append(t)
        active = sa

    if b15:
        lp = b15[-1].close
        for t in active:
            if not t.get("closed"):
                t["exit_price"] = lp
                t["exit_bar"] = len(b15) - 1
                t["result"] = "OPEN"
                t["closed"] = True
                diff = (
                    (lp - t["entry_price"])
                    if t["side"] == "long"
                    else (t["entry_price"] - lp)
                )
                t["pnl"] = round(diff * t["qty"], 2)
                day_trades[t.get("day_key", "")].append(t["pnl"])
                trade_records.append({"result": t["result"], "pnl": t["pnl"]})
                if t["pnl"] > 0:
                    wins.append(t)
                else:
                    losses.append(t)

    print(f"\r    [{session_name}] %100 ({total_bars}/{total_bars})", flush=True)
    return hour_hist


def fvg_close_confirmed(fvg, all_bars):
    scan_from = fvg.real_index + 2
    for b in all_bars:
        if b.index < scan_from:
            continue
        if fvg.direction == "bullish":
            if b.close < fvg.bottom:
                return False
            if fvg.bottom <= b.close <= fvg.top:
                return True
        else:
            if b.close > fvg.top:
                return False
            if fvg.bottom <= b.close <= fvg.top:
                return True
    return False


def print_histogram(hour_hist, label, session_hours):
    sh = session_hours["start"]
    eh = session_hours["end"]
    total = sum(hour_hist.values())
    if total == 0:
        print(f"  {label}: Hic trade yok")
        return

    print(f"\n  {label} (CBDR: {sh:02d}:00-{eh:02d}:00)")
    print(f"  {'Saat':>4} {'Trade':>7} {'%':>6}  Bar")
    print(f"  {'-'*40}")
    for h in range(24):
        cnt = hour_hist.get(h, 0)
        pct = cnt / total * 100 if total > 0 else 0
        bar_len = int(pct / 2)
        bar = "█" * bar_len
        # Phase annotation
        phase = ""
        in_window = (h >= sh or h < eh) if (sh > eh) else (sh <= h < eh)
        if in_window:
            phase = " ← CBDR window"
        print(f"  {h:>4} {cnt:>7} {pct:>5.1f}% {bar}{phase}")
    asia_hours = sum(hour_hist.get(h, 0) for h in range(2, 9))
    london_hours = sum(hour_hist.get(h, 0) for h in range(8, 14))
    ny_hours = sum(hour_hist.get(h, 0) for h in range(13, 22))
    closed_hours = total - asia_hours - london_hours - ny_hours
    print("\n  Phase breakdown:")
    print(f"    Asia   (02-08): {asia_hours:>7} ({asia_hours/total*100:>5.1f}%)")
    print(f"    London (08-13): {london_hours:>7} ({london_hours/total*100:>5.1f}%)")
    print(f"    NY     (13-22): {ny_hours:>7} ({ny_hours/total*100:>5.1f}%)")
    print(f"    Other  (22-02): {closed_hours:>7} ({closed_hours/total*100:>5.1f}%)")


def main():
    # Test coins: BTC (blue chip), ETH (underperformer), DOT (example alt), SOL
    test_coins = ["BTCUSDT", "ETHUSDT", "DOTUSDT", "SOLUSDT", "ADAUSDT"]

    for sym in test_coins:
        print(f"\n{'='*60}")
        print(f"  {sym}")
        print(f"{'='*60}")
        for sname, shours in SESSION_CONFIGS.items():
            print(
                f"\n  --- {sname} [{shours['start']:02d}:00-{shours['end']:02d}:00] ---"
            )
            result = collect_entry_hours(sym, sname, shours)
            if result is None:
                print("    VERI YOK")
                continue
            print_histogram(result, sname, shours)


if __name__ == "__main__":
    main()
