"""
test_cbdr_buckets.py — CBDR esigine gore bucket analizi.
Bucket'lar: 0-1%, 1-1.5%, 1.5-2%, 2-3%, 3-5%, >5%
"""

import csv
import os
import sys
import time
from datetime import datetime, timezone

os.environ["SNIPER_OUTPUT_DIR"] = os.path.join(
    os.path.dirname(__file__), "..", "output"
)
sys.path.insert(0, os.path.dirname(__file__))
_S = os.path.join(os.path.dirname(__file__), "..", "..", "sniper", "src")
if _S not in sys.path:
    sys.path.insert(0, _S)
import config as cfg
from session import SessionState, DailyBias
from fvg import detect_fvgs
from indicators import calculate_true_range, update_atr
from models import Bar
from retrace_state import RetraceStateMachine

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BUCKET_DEF = [(0, 1.0), (1.0, 1.5), (1.5, 2.0), (2.0, 3.0), (3.0, 5.0), (5.0, 999)]
MIN_TRADE = 20


def run(symbol: str, session_name: str = "REAL_CBDR", sh: dict = None):
    if sh is None:
        sh = {"start": 19, "end": 1}
    csv_path = os.path.join(
        os.path.dirname(__file__), "data", "daily", f"{symbol}_1m_raw.csv"
    )
    if not os.path.isfile(csv_path):
        print(f"  VERI YOK: {symbol}")
        return

    ic, rpt, sam, tpr, fbm = (
        cfg.INITIAL_BALANCE,
        cfg.RISK_PER_TRADE,
        cfg.SL_ATR_MULT,
        cfg.TP_RR,
        cfg.FVG_BUFFER_MULT,
    )
    ATM, TMM, BERM, BESP, FM = (
        cfg.ATR_TRAIL_MULT,
        cfg.TRAIL_MIN_MOVE_MULT,
        cfg.BE_RISK_MULT,
        cfg.BE_SPREAD_PTS,
        cfg.FVG_MIN_SIZE_ATR_MULT,
    )

    b1 = _load(csv_path)
    b15 = _res(b1)
    if not b15:
        return
    ss = SessionState(start_hour=sh["start"], end_hour=sh["end"])
    rsm = RetraceStateMachine(max_wick_ratio=cfg.FVG_WICK_RATIO_MAX)
    day_cbdr, day_trades = {}, {}

    atr_val, prev_close = 0.0, b15[0].open
    for bar in b15[1:500]:
        tr = calculate_true_range(bar, prev_close)
        atr_val = update_atr(atr_val if atr_val > 0 else None, tr)
        prev_close = bar.close

    active = []
    for sb in range(500, len(b15)):
        chunk, cur = b15[sb - 500 : sb + 1], b15[sb]
        tr = calculate_true_range(cur, prev_close)
        atr_val = update_atr(atr_val if atr_val > 0 else None, tr)
        prev_close = cur.close
        atr = atr_val
        try:
            edt = datetime.fromtimestamp(cur.timestamp / 1000, tz=timezone.utc)
        except Exception:
            continue
        lb = ss.cbdr_locked
        ss.update(edt, cur.open, cur.high, cur.low, cur.close, atr)
        jl = ss.cbdr_locked and not lb
        if jl and ss.cbdr_body_high > 0:
            w = ((ss.cbdr_body_high - ss.cbdr_body_low) / ss.cbdr_body_low) * 100
            day_cbdr[ss.cbdr_day] = round(w, 4)
        if ss.sweep_confirmed and rsm.state_name == "IDLE":
            rsm.on_sweep(ss.sweep_direction or "bullish", ss.sweep_level or 0.0, None)
        if rsm.state_name == "SWEEP_DETECTED":
            rsm.on_sweep_confirmed(chunk, cur, atr)
        if rsm.can_trigger() and not active:
            sd, db = rsm.direction, ss.daily_bias
            if (
                (sd == "bullish" and db == DailyBias.BEARISH)
                or (sd == "bearish" and db == DailyBias.BULLISH)
                or db == DailyBias.NEUTRAL
            ):
                rsm.reset()
                continue
            h, sp = edt.hour, sh["start"] > sh["end"]
            if (
                (h >= sh["start"] or h < sh["end"])
                if sp
                else (sh["start"] <= h < sh["end"])
            ):
                rsm.reset()
                continue
            side = "long" if sd == "bullish" else "short"
            ep, rp2, tf = cur.close, atr * sam, rsm.trigger_fvg
            if side == "long":
                if tf:
                    fh = tf.top - tf.bottom
                    if fh <= 0:
                        sl = ep - rp2 * 2
                    else:
                        sl = tf.bottom - max(
                            fh * 0.10, max(rp2 * 0.1, min(fh * 0.25, rp2 * fbm))
                        )
                else:
                    sl = ep - rp2 * 2
            else:
                if tf:
                    fh = tf.top - tf.bottom
                    if fh <= 0:
                        sl = ep + rp2 * 2
                    else:
                        sl = tf.top + max(
                            fh * 0.10, max(rp2 * 0.1, min(fh * 0.25, rp2 * fbm))
                        )
                else:
                    sl = ep + rp2 * 2
            rd = abs(sl - ep)
            if rd < atr * 0.1 or rd <= 0:
                rsm.reset()
                continue
            tp = ep + rd * tpr if side == "long" else ep - rd * tpr
            qty = (ic * rpt) / rd if rd > 0 else 0
            if qty <= 0:
                rsm.reset()
                continue
            active.append(
                {
                    "entry_bar": sb,
                    "entry_price": ep,
                    "sl": sl,
                    "tp": tp,
                    "qty": qty,
                    "side": side,
                    "initial_sl": sl,
                    "initial_tp": tp,
                    "trailing_count": 0,
                    "day_key": ss.cbdr_day,
                }
            )
            rsm.reset()

        if active and cur.is_closed:
            for t in active:
                if t.get("closed") or t.get("trailing_count", 0) > 0:
                    continue
                rpt2 = abs(t["initial_sl"] - t["entry_price"])
                th2 = rpt2 * BERM
                be2 = (
                    t["entry_price"] + BESP
                    if t["side"] == "long"
                    else t["entry_price"] - BESP
                )
                if t["side"] == "long":
                    if cur.high >= t["entry_price"] + th2 and t["sl"] < be2:
                        t["sl"] = be2
                        t["trailing_count"] = 1
                else:
                    if cur.low <= t["entry_price"] - th2 and t["sl"] > be2:
                        t["sl"] = be2
                        t["trailing_count"] = 1
            tc, mfs = chunk[:-1], max(atr * FM, 1e-8)
            cfvgs = detect_fvgs(
                tc, lookback=min(50, len(tc)), timeframe="15m", min_fvg_size=mfs
            )
            for t in active:
                if t.get("closed"):
                    continue
                rpt2 = abs(t["initial_sl"] - t["entry_price"])
                upd = False
                for fvg in cfvgs:
                    if t["side"] == "long" and fvg.direction != "bullish":
                        continue
                    if t["side"] == "short" and fvg.direction != "bearish":
                        continue
                    if not _close(fvg, tc):
                        continue
                    ab2 = atr * ATM
                    if t["side"] == "long":
                        ns = fvg.bottom - ab2
                        if ns > t["sl"] and (ns - t["sl"]) > rpt2 * TMM:
                            sd2 = ns - t["sl"]
                            t["sl"] = ns
                            t["tp"] += sd2
                            upd = True
                    else:
                        ns = fvg.top + ab2
                        if ns < t["sl"] and (t["sl"] - ns) > rpt2 * TMM:
                            sd2 = t["sl"] - ns
                            t["sl"] = ns
                            t["tp"] -= sd2
                            upd = True
                if upd:
                    t["trailing_count"] = t.get("trailing_count", 0) + 1

        sa = []
        for t in active:
            ex = False
            if t.get("closed"):
                continue
            if t["side"] == "long":
                if cur.low <= t["sl"]:
                    t["exit_price"] = t["sl"]
                    t["result"] = "SL"
                    t["closed"] = True
                    ex = True
                elif cur.high >= t["tp"]:
                    t["exit_price"] = t["tp"]
                    t["result"] = "TP"
                    t["closed"] = True
                    ex = True
            else:
                if cur.high >= t["sl"]:
                    t["exit_price"] = t["sl"]
                    t["result"] = "SL"
                    t["closed"] = True
                    ex = True
                elif cur.low <= t["tp"]:
                    t["exit_price"] = t["tp"]
                    t["result"] = "TP"
                    t["closed"] = True
                    ex = True
            if ex and "exit_price" in t:
                diff = (
                    (t["exit_price"] - t["entry_price"])
                    if t["side"] == "long"
                    else (t["entry_price"] - t["exit_price"])
                )
                t["pnl"] = round(diff * t["qty"], 2)
                day_trades.setdefault(t.get("day_key", ""), []).append(
                    {
                        "pnl": t["pnl"],
                        "result": t["result"],
                        "trail": t.get("trailing_count", 0),
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
                t["result"] = "OPEN"
                t["closed"] = True
                diff = (
                    (lp - t["entry_price"])
                    if t["side"] == "long"
                    else (t["entry_price"] - lp)
                )
                t["pnl"] = round(diff * t["qty"], 2)
                day_trades.setdefault(t.get("day_key", ""), []).append(
                    {
                        "pnl": t["pnl"],
                        "result": t["result"],
                        "trail": t.get("trailing_count", 0),
                    }
                )

    # Bucket
    print(f"\n  {symbol} — {session_name} [{sh['start']:02d}:00-{sh['end']:02d}:00]")
    print(
        f"  {'CBDR%':<12} {'Gun':>4} {'Trade':>6} {'WR%':>6} {'PF':>6} {'AvgR:R':>7} {'PnL':>10}"
    )
    print(f"  {'-'*55}")
    for lo, hi in BUCKET_DEF:
        b = [d for d in day_cbdr if lo <= day_cbdr[d] < hi]
        if not b:
            continue
        all_t = [t for d in b for t in day_trades.get(d, [])]
        n = len(all_t)
        if n < MIN_TRADE:
            lbl = f"{lo:.0f}-{hi:.0f}%" if hi >= 10 else f"{lo:.1f}-{hi:.1f}%"
            print(
                f"  {lbl:<12} {len(b):>4} {n:>5} {'':>6} {'':>6} {'':>7} {'':>10}  (yetersiz)"
            )
            continue
        pnls = [t["pnl"] for t in all_t]
        wins = sum(1 for p in pnls if p > 0)
        wr = wins / n * 100
        total_pnl = sum(pnls)
        gp = sum(p for p in pnls if p > 0) or 0
        gl = abs(sum(p for p in pnls if p < 0)) or 1
        aw = gp / max(wins, 1)
        al = gl / max(n - wins, 1)
        # Kategori detayi
        sl = [
            t for t in all_t if t.get("result") == "SL" and t.get("trail", 0) == 0
        ]  # direkt stop
        be = [
            t for t in all_t if t.get("result") == "SL" and t.get("trail", 0) == 1
        ]  # 1 trail, kismen kurtarilmis
        sl2 = [
            t for t in all_t if t.get("result") == "SL" and t.get("trail", 0) >= 2
        ]  # trailing calisti, karda
        tp_l = [t for t in all_t if t.get("result") == "TP"]  # TP vurdu
        sl_cnt, be_cnt, sl2_cnt, tp_cnt = len(sl), len(be), len(sl2), len(tp_l)
        sl_pnl = sum(t["pnl"] for t in sl) if sl else 0
        be_pnl = sum(t["pnl"] for t in be) if be else 0
        sl2_pnl = sum(t["pnl"] for t in sl2) if sl2 else 0
        tp_pnl = sum(t["pnl"] for t in tp_l) if tp_l else 0
        # Gercek PnL bazli siniflandirma (etiket degil!)
        wins = [t for t in all_t if t["pnl"] > 0]
        be = [t for t in all_t if t["pnl"] == 0]
        losses = [t for t in all_t if t["pnl"] < 0]
        w_n, be_n, l_n = len(wins), len(be), len(losses)
        w_pnl = sum(t["pnl"] for t in wins) or 0
        be_pnl = sum(t["pnl"] for t in be) or 0
        l_pnl = sum(t["pnl"] for t in losses) or 0
        # Eski kategori detayi (karsilastirma icin)
        sl = [t for t in all_t if t.get("result") == "SL" and t.get("trail", 0) == 0]
        sl1 = [t for t in all_t if t.get("result") == "SL" and t.get("trail", 0) >= 1]
        tp_l = [t for t in all_t if t.get("result") == "TP"]
        # Cash-Flow WR = PnL > 0 olanlar
        cf_wr = w_n / n * 100 if n > 0 else 0
        # BE+ = PnL >= 0 olanlar (zarar yazdirmayan)
        be_plus = (w_n + be_n) / n * 100 if n > 0 else 0
        lbl = f"{lo:.0f}-{hi:.0f}%" if hi >= 10 else f"{lo:.1f}-{hi:.1f}%"
        print(
            f"  {lbl:<12} {len(b):>4} {n:>5} WR={wr:>4.1f}% CF={cf_wr:>4.1f}% BE+={be_plus:>4.1f}% PF={gp/gl:>5.2f} {total_pnl:>+9.0f}"
        )
        print(
            f"  {'':>12} WIN:{w_n:>3} {w_pnl:>+8.0f} | BE:{be_n:>3} {be_pnl:>+8.0f} | LOSS:{l_n:>3} {l_pnl:>+8.0f}"
        )
        print(f"  {'':>12} (SL-:{len(sl):>3} | SL1+:{len(sl1):>3} | TP:{len(tp_l):>3})")


def _load(fp):
    bars = []
    with open(fp, encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f)):
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


def _res(b1):
    m = []
    for i in range(0, len(b1), 15):
        c = b1[i : i + 15]
        if len(c) < 15:
            break
        m.append(
            Bar(
                index=len(m),
                open=c[0].open,
                high=max(b.high for b in c),
                low=min(b.low for b in c),
                close=c[-1].close,
                volume=sum(b.volume for b in c),
                is_closed=True,
                timestamp=c[0].timestamp,
            )
        )
    return m


def _close(fvg, ab):
    sf = fvg.real_index + 2
    for b in ab:
        if b.index < sf:
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


if __name__ == "__main__":
    sym = sys.argv[1] if len(sys.argv) > 1 else "ADAUSDT"
    t0 = time.time()
    run(sym)
    print(f"\n  Sure: {time.time()-t0:.0f}s")
