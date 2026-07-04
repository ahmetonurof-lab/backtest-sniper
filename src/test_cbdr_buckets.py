"""
test_cbdr_buckets.py — Tek coin, esit trade sayili CBDR bucket analizi.
Her bucket: WR%, PF, AvgWin, AvgLoss, AvgR:R gosterir.
Risk carpani onerisi: WR>=42 artir, WR<35 azalt, arada standart.
"""
import csv
import os
import sys
import time
from datetime import datetime, timezone

os.environ["SNIPER_OUTPUT_DIR"] = os.path.join(os.path.dirname(__file__), "..", "output")
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

SH = {'start': 19, 'end': 1}
N_BUCKETS = 6
MIN_TRADE_CUTOFF = 20


def _finalize_bucket(buckets, bars, days, day_cbdr):
    if not bars:
        return
    pnls = [t["pnl"] for _, t in bars]
    n = len(pnls)
    wins = sum(1 for p in pnls if p > 0)
    wr = wins / n * 100 if n > 0 else 0
    total_pnl = sum(pnls)
    gp = sum(p for p in pnls if p > 0) or 0
    gl = abs(sum(p for p in pnls if p < 0)) or 1
    pf = gp / gl
    avg_win = gp / max(wins, 1)
    avg_loss = gl / max(n - wins, 1)
    avg_rr = avg_win / avg_loss if avg_loss > 0 else 0
    lo_w = min(day_cbdr[d] for d in days) if days else 0
    hi_w = max(day_cbdr[d] for d in days) if days else 0
    buckets.append({
        "range": f"{lo_w:.2f}-{hi_w:.2f}", "days": len(days),
        "trades": n, "wr": wr, "pnl": round(total_pnl, 0),
        "pf": round(pf, 2), "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2), "avg_rr": round(avg_rr, 2),
    })


def run(symbol: str):
    csv_path = os.path.join(os.path.dirname(__file__), "data", "daily", f"{symbol}_1m_raw.csv")
    if not os.path.isfile(csv_path):
        print(f"  VERI YOK: {symbol}")
        return

    ic = cfg.INITIAL_BALANCE
    rpt = cfg.RISK_PER_TRADE
    sam = cfg.SL_ATR_MULT
    tpr = cfg.TP_RR
    fbm = cfg.FVG_BUFFER_MULT
    ATM = cfg.ATR_TRAIL_MULT
    TMM = cfg.TRAIL_MIN_MOVE_MULT
    BERM = cfg.BE_RISK_MULT
    BESP = cfg.BE_SPREAD_PTS
    FM = cfg.FVG_MIN_SIZE_ATR_MULT

    b1 = _load_data(csv_path)
    b15 = _resample_15m(b1)
    if not b15:
        return

    ss = SessionState(start_hour=SH['start'], end_hour=SH['end'])
    rsm = RetraceStateMachine(max_wick_ratio=cfg.FVG_WICK_RATIO_MAX)

    day_cbdr = {}
    day_trades = {}

    atr_val = 0.0
    prev_close = b15[0].open
    for bar in b15[1:500]:
        tr = calculate_true_range(bar, prev_close)
        atr_val = update_atr(atr_val if atr_val > 0 else None, tr)
        prev_close = bar.close

    active = []
    for sb in range(500, len(b15)):
        chunk = b15[sb - 500: sb + 1]
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
        jl = ss.cbdr_locked and not locked_before

        if jl and ss.cbdr_body_high > 0:
            w = ((ss.cbdr_body_high - ss.cbdr_body_low) / ss.cbdr_body_low) * 100
            day_cbdr[ss.cbdr_day] = round(w, 4)

        if ss.sweep_confirmed and rsm.state_name == "IDLE":
            rsm.on_sweep(ss.sweep_direction or "bullish", ss.sweep_level or 0.0, None)

        if rsm.state_name == "SWEEP_DETECTED":
            rsm.on_sweep_confirmed(chunk, cur, atr)

        if rsm.can_trigger() and not active:
            sd = rsm.direction
            db = ss.daily_bias
            if (sd == "bullish" and db == DailyBias.BEARISH) or \
               (sd == "bearish" and db == DailyBias.BULLISH) or \
               db == DailyBias.NEUTRAL:
                rsm.reset(); continue
            h = edt.hour
            sh, eh = SH['start'], SH['end']
            sp = sh > eh
            if (h >= sh or h < eh) if sp else (sh <= h < eh):
                rsm.reset(); continue

            side = "long" if sd == "bullish" else "short"
            ep = cur.close
            rp2 = atr * sam
            tf = rsm.trigger_fvg

            if side == "long":
                if tf:
                    fh = tf.top - tf.bottom
                    sl = ep - rp2 * 2 if fh <= 0 else tf.bottom - max(fh * 0.10, max(rp2 * 0.1, min(fh * 0.25, rp2 * fbm)))
                else:
                    sl = ep - rp2 * 2
            else:
                if tf:
                    fh = tf.top - tf.bottom
                    sl = ep + rp2 * 2 if fh <= 0 else tf.top + max(fh * 0.10, max(rp2 * 0.1, min(fh * 0.25, rp2 * fbm)))
                else:
                    sl = ep + rp2 * 2
            rd = abs(sl - ep)
            if rd < atr * 0.1 or rd <= 0:
                rsm.reset(); continue
            if side == "long":
                tp = ep + rd * tpr
            else:
                tp = ep - rd * tpr
            qty = (ic * rpt) / rd if rd > 0 else 0
            if qty <= 0:
                rsm.reset(); continue

            active.append({"entry_bar": sb, "entry_price": ep, "sl": sl, "tp": tp,
                           "qty": qty, "side": side, "trigger_fvg": tf,
                           "initial_sl": sl, "initial_tp": tp, "trailing_count": 0,
                           "day_key": ss.cbdr_day, "base_rd": rd})
            rsm.reset()

        if active and cur.is_closed:
            for t in active:
                if t.get("closed") or t.get("trailing_count", 0) > 0: continue
                s2 = t["side"]; e2 = t["entry_price"]
                rpt2 = abs(t["initial_sl"] - e2)
                th2 = rpt2 * BERM
                be2 = e2 + BESP if s2 == "long" else e2 - BESP
                if s2 == "long":
                    if cur.high >= e2 + th2 and t["sl"] < be2: t["sl"] = be2; t["trailing_count"] = 1
                else:
                    if cur.low <= e2 - th2 and t["sl"] > be2: t["sl"] = be2; t["trailing_count"] = 1

            tc = chunk[:-1]
            mfs = max(atr * FM, 1e-8)
            cfvgs = detect_fvgs(tc, lookback=min(50, len(tc)), timeframe="15m", min_fvg_size=mfs)
            for t in active:
                if t.get("closed"): continue
                s2 = t["side"]; csl = t["sl"]; ctp = t["tp"]
                rpt2 = abs(t["initial_sl"] - t["entry_price"])
                upd = False
                for fvg in cfvgs:
                    if s2 == "long" and fvg.direction != "bullish": continue
                    if s2 == "short" and fvg.direction != "bearish": continue
                    if not _fvg_close_confirmed(fvg, tc): continue
                    ab2 = atr * ATM
                    if s2 == "long":
                        ns = fvg.bottom - ab2
                        if ns > csl and (ns - csl) > rpt2 * TMM:
                            csl = ns; ctp += ns - csl; upd = True
                    else:
                        ns = fvg.top + ab2
                        if ns < csl and (csl - ns) > rpt2 * TMM:
                            csl = ns; ctp -= csl - ns; upd = True
                if upd: t["sl"] = csl; t["tp"] = ctp; t["trailing_count"] = t.get("trailing_count", 0) + 1

        sa = []
        for t in active:
            if t.get("closed"): continue
            ex = False
            if t["side"] == "long":
                if cur.low <= t["sl"]: t["exit_price"] = t["sl"]; t["exit_bar"] = sb; t["result"] = "SL"; t["closed"] = True; ex = True
                elif cur.high >= t["tp"]: t["exit_price"] = t["tp"]; t["exit_bar"] = sb; t["result"] = "TP"; t["closed"] = True; ex = True
            else:
                if cur.high >= t["sl"]: t["exit_price"] = t["sl"]; t["exit_bar"] = sb; t["result"] = "SL"; t["closed"] = True; ex = True
                elif cur.low <= t["tp"]: t["exit_price"] = t["tp"]; t["exit_bar"] = sb; t["result"] = "TP"; t["closed"] = True; ex = True
            if ex:
                diff = (t["exit_price"] - t["entry_price"]) if t["side"] == "long" else (t["entry_price"] - t["exit_price"])
                t["pnl"] = round(diff * t["qty"], 2)
                dk = t.get("day_key", "")
                if dk not in day_trades: day_trades[dk] = []
                day_trades[dk].append({"pnl": t["pnl"], "result": t["result"], "side": t["side"]})
            else:
                sa.append(t)
        active = sa

    if b15:
        lp = b15[-1].close
        for t in active:
            if not t.get("closed"):
                t["exit_price"] = lp; t["exit_bar"] = len(b15) - 1; t["result"] = "OPEN"; t["closed"] = True
                diff = (lp - t["entry_price"]) if t["side"] == "long" else (t["entry_price"] - lp)
                t["pnl"] = round(diff * t["qty"], 2)
                dk = t.get("day_key", "")
                if dk not in day_trades: day_trades[dk] = []
                day_trades[dk].append({"pnl": t["pnl"], "result": t["result"], "side": t["side"]})

    # Bucket (esit trade sayili)
    sorted_days = sorted(day_cbdr.keys(), key=lambda d: day_cbdr[d])
    if not sorted_days:
        return

    all_trades_list = []
    for d in sorted_days:
        all_trades_list.extend(day_trades.get(d, []))
    total_trades = len(all_trades_list)
    if total_trades == 0:
        return

    tpb = max(1, total_trades // N_BUCKETS)
    buckets = []
    cur_bars = []
    cur_days = set()
    cnt = 0

    for d in sorted_days:
        tl = day_trades.get(d, [])
        for t in tl:
            cur_bars.append((d, t))
            cur_days.add(d)
            cnt += 1
            if cnt >= tpb and len(buckets) < N_BUCKETS - 1:
                _finalize_bucket(buckets, cur_bars, cur_days, day_cbdr)
                cur_bars = []; cur_days = set(); cnt = 0
    if cur_bars:
        _finalize_bucket(buckets, cur_bars, cur_days, day_cbdr)

    # Cikti
    print(f"\n  {symbol} — CBDR Bucket ({N_BUCKETS} esit trade sayili) [REAL_CBDR 19-1]")
    print(f"  {'CBDR%':<16} {'Gun':>4} {'Trade':>6} {'WR%':>6} {'PF':>6} {'AvgWin':>8} {'AvgLoss':>8} {'AvgR:R':>7} {'PnL':>10}")
    print(f"  {'-'*75}")
    for b in buckets:
        print(f"  {b['range']:<16} {b['days']:>4} {b['trades']:>6} "
              f"{b['wr']:>5.1f}% {b['pf']:>5.2f} {b['avg_win']:>8.2f} "
              f"{b['avg_loss']:>8.2f} {b['avg_rr']:>6.2f} {b['pnl']:>+9.0f}")

    print(f"\n  ONERILER (min {MIN_TRADE_CUTOFF} trade):")
    for b in buckets:
        if b["trades"] < MIN_TRADE_CUTOFF:
            print(f"    {b['range']}: YETERSIZ ORNEK ({b['trades']} trade)")
        elif b["wr"] >= 42:
            print(f"    {b['range']}: WR={b['wr']:.1f}% PF={b['pf']:.2f} -> RISK ARTIRILABILIR (x1.3+)")
        elif b["wr"] < 35:
            print(f"    {b['range']}: WR={b['wr']:.1f}% PF={b['pf']:.2f} -> RISK AZALTILMALI (x0.5-0.7)")
        else:
            print(f"    {b['range']}: WR={b['wr']:.1f}% PF={b['pf']:.2f} -> STANDART RISK (x1.0)")


def _load_data(filepath):
    bars = []
    with open(filepath, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            ts = int(datetime.strptime(row["open_time"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp() * 1000)
            bars.append(Bar(index=i, open=float(row["open"]), high=float(row["high"]),
                            low=float(row["low"]), close=float(row["close"]),
                            volume=float(row["volume"]), is_closed=True, timestamp=ts))
    return bars


def _resample_15m(bars_1m):
    m15 = []
    for i in range(0, len(bars_1m), 15):
        c = bars_1m[i:i + 15]
        if len(c) < 15: break
        m15.append(Bar(index=c[0].index, open=c[0].open, high=max(b.high for b in c),
                       low=min(b.low for b in c), close=c[-1].close,
                       volume=sum(b.volume for b in c), is_closed=True, timestamp=c[0].timestamp))
    return m15


def _fvg_close_confirmed(fvg, all_bars):
    scan_from = fvg.real_index + 2
    for b in all_bars:
        if b.index < scan_from: continue
        if fvg.direction == "bullish":
            if b.close < fvg.bottom: return False
            if fvg.bottom <= b.close <= fvg.top: return True
        else:
            if b.close > fvg.top: return False
            if fvg.bottom <= b.close <= fvg.top: return True
    return False


if __name__ == "__main__":
    sym = sys.argv[1] if len(sys.argv) > 1 else "ADAUSDT"
    t0 = time.time()
    run(sym)
    print(f"\n  Sure: {time.time()-t0:.0f}s")
