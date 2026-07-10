"""
sweep_full_v3.py — V3 tum katmanlar entegre, sifirdan backtest.
Coin bazli session + Relative FVG + CBDR Matrix + EL + expiry.
Gerçek 1m/15m OHLCV'dan calisir, parquet okumaz.
"""

# ruff: noqa: E402
import csv
import functools
import math
import os
import sys
import time
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
from fvg import detect_fvgs
from indicators import calculate_true_range, update_atr
from models import Bar
from retrace_state import RetraceStateMachine
from session import DailyBias, SessionState

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
os.makedirs(REPORT_DIR, exist_ok=True)

# ── Session hours ──
SESSION_HOURS_MAP = {
    "DEFAULT": {"start": 22, "end": 2},
    "REAL_CBDR": {"start": 19, "end": 1},
    "ASIA_RANGE": {"start": 1, "end": 5},
}


# ── Helpers ──
def get_session_for_symbol(sym):
    p = cfg.CBDR_RISK_MATRIX.get(sym)
    if p:
        sh = SESSION_HOURS_MAP.get(p["session"])
        if sh:
            return sh["start"], sh["end"]
    return 22, 2


def get_cbdr_mult(sym, cbdr_pct):
    p = cfg.CBDR_RISK_MATRIX.get(sym)
    if not p:
        return 1.0
    for lo, hi, m in p["buckets"]:
        if lo <= cbdr_pct < hi:
            return m
    return 1.0


def is_hq_fvg(fvg_pips, atr_val):
    if atr_val <= 1e-8:
        return False
    return (fvg_pips / atr_val) >= cfg.MIN_REL_FVG_THRESHOLD


# ── Data ──
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


# ── Core backtest ──
def run_backtest(sym):
    csv_path = os.path.join(
        os.path.dirname(__file__), "data", "daily", f"{sym}_1m_raw.csv"
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

    # Coin bazli session
    sh, eh = get_session_for_symbol(sym)
    spans_midnight = sh > eh
    ss = SessionState(start_hour=sh, end_hour=eh)
    rsm = RetraceStateMachine(max_wick_ratio=cfg.FVG_WICK_RATIO_MAX)

    day_cbdr = {}
    day_trades = defaultdict(list)
    active = []
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
            print(f"\r  {sym}: %{pct:.0f}", end="", flush=True)

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
        h = edt.hour

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

            # Session filter: only trade in this coin's window
            if (h >= sh or h < eh) if spans_midnight else (sh <= h < eh):
                rsm.reset()
                continue

            # ── YENI: Relative FVG kalite filtresi ──
            tf = rsm.trigger_fvg
            if tf is not None and not is_hq_fvg(tf.top - tf.bottom, atr):
                rsm.reset()
                continue

            # ── YENI: FVG expiry ──
            if (
                tf is not None
                and (cur.index - tf.bar_index) > cfg.GLOBAL_FVG_EXPIRY_BARS
            ):
                rsm.reset()
                continue

            side = "long" if sd == "bullish" else "short"
            ep = cur.close
            rp2 = atr * sam

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

            # ── YENI: risk carpani hesaplama ──
            cbdr_w = (
                ((ss.cbdr_body_high - ss.cbdr_body_low) / ss.cbdr_body_low * 100)
                if ss.cbdr_body_low > 0 and not math.isinf(ss.cbdr_body_low)
                else None
            )
            cbdr_mult = get_cbdr_mult(sym, cbdr_w) if cbdr_w is not None else 1.0
            if cbdr_mult == 0.0:
                rsm.reset()
                continue
            el_mult = cfg.EARLY_LONDON_RISK_MULT if 2 <= h < 8 else 1.0
            final_mult = el_mult * cbdr_mult

            qty = (ic * rpt * final_mult) / rd if rd > 0 else 0
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
                    "entry_hour": h,
                    "cbdr_mult": cbdr_mult,
                    "el_mult": el_mult,
                }
            )
            rsm.reset()

        # ── Trailing + Exit ──
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
            min_fvg_sz = max(atr * FVG_MIN_SIZE_ATR_MULT, 1e-8)
            cfvgs = detect_fvgs(
                tc, lookback=min(50, len(tc)), timeframe="15m", min_fvg_size=min_fvg_sz
            )
            for t in active:
                if t.get("closed"):
                    continue
                s2, csl, ctp = t["side"], t["sl"], t["tp"]
                rpt2 = abs(t["initial_sl"] - t["entry_price"])
                ltc, upd = 0, False
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
                trade_records.append(
                    {
                        "result": t["result"],
                        "pnl": t["pnl"],
                        "hour": t.get("entry_hour"),
                    }
                )
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
                trade_records.append(
                    {
                        "result": t["result"],
                        "pnl": t["pnl"],
                        "hour": t.get("entry_hour"),
                    }
                )

    print(f"\r  {sym}: %100", end="", flush=True)
    n = len(trade_records)
    wins = sum(1 for r in trade_records if r["pnl"] > 0)
    be = sum(1 for r in trade_records if r["pnl"] == 0)
    losses = n - wins - be
    wr = wins / n * 100 if n else 0
    total_pnl = sum(r["pnl"] for r in trade_records)
    cum, peak, max_dd = 0, 0, 0
    for r in trade_records:
        cum += r["pnl"]
        if cum > peak:
            peak = cum
        dd = peak - cum
        if dd > max_dd:
            max_dd = dd
    max_dd_pct = max_dd / cfg.INITIAL_BALANCE * 100

    return {
        "sym": sym,
        "trades": n,
        "wins": wins,
        "be": be,
        "losses": losses,
        "wr": round(wr, 1),
        "pnl": round(total_pnl, 2),
        "max_dd_pct": round(max_dd_pct, 2),
    }


def main():
    t0 = time.time()
    print("=" * 100)
    print("  V3 FULL BACKTEST — Tum Katmanlar Entegre (Sifirdan OHLCV)")
    print("  Katmanlar: Coin Session + Relative FVG + Expiry + CBDR Matrix + EL 1.5x")
    print("=" * 100)

    results = []
    for sym in sorted(cfg.SYMBOLS):
        print(f"\n  [{sym}] Basliyor...", flush=True)
        r = run_backtest(sym)
        if r:
            results.append(r)
            print(
                f"\n  [{sym}] {r['trades']} islem | WIN:{r['wins']} BE:{r['be']} LOSS:{r['losses']} | "
                f"WR={r['wr']}% PnL={r['pnl']:+.0f} DD={r['max_dd_pct']}%"
            )

    print(f"\n{'='*100}")
    print(f"  V3 FULL — SUMMARY ({len(results)} coin)")
    print(f"{'='*100}")
    print(
        f"  {'Coin':<10} {'Trades':>7} {'WIN':>6} {'BE':>5} {'LOSS':>6} {'WR%':>6} {'PnL':>10} {'MaxDD%':>8}"
    )
    print(f"  {'-'*60}")
    for r in results:
        print(
            f"  {r['sym']:<10} {r['trades']:>7} {r['wins']:>6} {r['be']:>5} {r['losses']:>6} "
            f"{r['wr']:>5.1f}% {r['pnl']:>+9,.0f} {r['max_dd_pct']:>6.2f}%"
        )
    total_t = sum(r["trades"] for r in results)
    total_p = sum(r["pnl"] for r in results)
    avg_wr = sum(r["wr"] for r in results) / len(results) if results else 0
    print(f"  {'-'*60}")
    print(
        f"  {'TOPLAM':<10} {total_t:>7} {'-':>6} {'-':>5} {'-':>6} {avg_wr:>5.1f}% {total_p:>+9,.0f}"
    )

    print(f"\n  Sure: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
