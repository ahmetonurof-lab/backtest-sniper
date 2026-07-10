"""
analyzer_cbdr.py — CBDR threshold filter vs original spaghetti comparison
"""

import os
import sys
import time
import csv
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coins_config import get_config, COINS
from fvg import detect_fvgs
from models import Bar
from retrace_state import RetraceStateMachine
from session import DailyBias, SessionPhase, SessionState, detect_phase_from_timestamp

LRT = 0.003
MFA = 3
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# ─── CBDR THRESHOLDS (from 90-day backtest analysis) ───
CBDR_FILTERS = {
    "BTCUSDT": {"max_bias_pct": 2.24, "fail_limit": 2.74},
    "ETHUSDT": {"max_bias_pct": 3.77, "fail_limit": 3.92},
    "SOLUSDT": {"max_bias_pct": 3.50, "fail_limit": 4.11},
    "APTUSDT": {"max_bias_pct": 2.02, "fail_limit": 3.77},
    "NEARUSDT": {"max_bias_pct": 2.10, "fail_limit": 5.43},
    "BNBUSDT": {"max_bias_pct": 2.42, "fail_limit": 5.21},
    "ADAUSDT": {"max_bias_pct": 3.60, "fail_limit": 4.43},
    "ATOMUSDT": {"max_bias_pct": 2.60, "fail_limit": 3.93},
    "AVAXUSDT": {"max_bias_pct": 3.03, "fail_limit": 9.70},
    "DOTUSDT": {"max_bias_pct": 3.50, "fail_limit": 4.04},
    "LINKUSDT": {"max_bias_pct": 3.11, "fail_limit": 4.11},
    "SUIUSDT": {"max_bias_pct": 3.33, "fail_limit": 4.28},
    "XRPUSDT": {"max_bias_pct": 3.87, "fail_limit": 4.73},
}


def ld(fp):
    b = []
    with open(fp, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for i, row in enumerate(r):
            ts = int(
                datetime.strptime(row["open_time"], "%Y-%m-%d %H:%M:%S").timestamp()
                * 1000
            )
            b.append(
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
    return b


def r15(b1):
    m = []
    for i in range(0, len(b1), 15):
        c = b1[i : i + 15]
        if len(c) < 15:
            break
        m.append(
            Bar(
                index=len(m),
                open=c[0].open,
                high=max(x.high for x in c),
                low=min(x.low for x in c),
                close=c[-1].close,
                volume=sum(x.volume for x in c),
                is_closed=True,
                timestamp=c[0].timestamp,
            )
        )
    return m


def run_bt(sym, cfg, use_filter=False):
    fp = os.path.join(DATA_DIR, f"{sym}_1m.csv")
    if not os.path.isfile(fp):
        return None, []
    mfs = cfg["min_fvg_size"]
    ic = cfg["initial_capital"]
    rpt = cfg["risk_per_trade"]
    rp = cfg.get("risk_primary", rpt)
    rr2 = cfg.get("risk_retrade", rpt)
    sam = cfg["sl_atr_mult"]
    tpr = cfg["tp_rr"]
    fbm = cfg["fvg_buffer_mult"]
    W = 500
    flt = CBDR_FILTERS.get(sym, None) if use_filter else None
    b1 = ld(fp)
    b15 = r15(b1)
    if not b15:
        return None, []
    ss = SessionState()
    rsm = RetraceStateMachine(min_fvg_size=mfs)
    rsm2 = RetraceStateMachine(min_fvg_size=mfs * 0.3)
    trades = []
    active = []
    skip_today = False
    bias_disabled = False
    zone_counts = {"golden": 0, "gray": 0, "red": 0}

    for sb in range(W, len(b15)):
        chunk = b15[sb - W : sb + 1]
        cur = b15[sb]
        atr = max(cur.range, cur.close * 0.0001)
        try:
            edt = datetime.fromtimestamp(cur.timestamp / 1000, tz=timezone.utc)
        except:
            continue
        last_day = ss.cbdr_day
        ss.update(edt, cur.open, cur.high, cur.low, cur.close, atr)

        # Check if day changed → reset daily flags
        if ss.cbdr_day != last_day and last_day:
            skip_today = False
            bias_disabled = False

        # After CBDR locks: apply filter once per day
        if ss.cbdr_locked and flt and not skip_today and not bias_disabled:
            if ss.cbdr_body_high > 0 and ss.cbdr_body_low < float("inf"):
                cw = ss.cbdr_body_high - ss.cbdr_body_low
                cp = (cw / ss.cbdr_body_low) * 100
                if cp > flt["fail_limit"]:
                    skip_today = True
                    zone_counts["red"] += 1
                elif cp > flt["max_bias_pct"]:
                    bias_disabled = True
                    zone_counts["gray"] += 1
                else:
                    zone_counts["golden"] += 1

        if skip_today:
            continue

        if ss.sweep_confirmed and rsm.state_name == "IDLE":
            rsm.on_sweep(
                direction=ss.sweep_direction or "bullish",
                level=ss.sweep_level or 0.0,
                bar_index=cur.index,
            )
        if rsm.state_name == "SWEEP_DETECTED":
            rsm.on_sweep_confirmed(chunk, cur)
        if rsm.can_trigger() and not active:
            sd = rsm.direction
            db = ss.daily_bias
            # Bias lock: skip if filter disabled it
            if not bias_disabled:
                if (
                    (sd == "bullish" and db == DailyBias.BEARISH)
                    or (sd == "bearish" and db == DailyBias.BULLISH)
                    or db == DailyBias.NEUTRAL
                ):
                    rsm.reset()
                    continue
            if detect_phase_from_timestamp(cur.timestamp) not in (
                SessionPhase.NEWYORK,
                SessionPhase.LONDON,
            ):
                rsm.reset()
                continue
            side = "long" if sd == "bullish" else "short"
            ep = cur.close
            rp2 = atr * sam
            tf = rsm.trigger_fvg
            if side == "long":
                sl = tf.bottom - (rp2 * fbm) if tf else ep - rp2 * 2
                tp = ss.london_high if ss.london_high > ep else ep + rp2 * tpr
            else:
                sl = tf.top + (rp2 * fbm) if tf else ep + rp2 * 2
                tp = ss.london_low if ss.london_low < ep else ep - rp2 * tpr
            rd = abs(sl - ep)
            if rd < atr * 0.1:
                continue
            qty = (ic * rp) / rd if rd > 0 else 0
            if qty <= 0:
                rsm.reset()
                continue
            d = datetime.fromtimestamp(cur.timestamp / 1000, tz=timezone.utc).strftime(
                "%Y-%m-%d"
            )
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
                    "is_retrade": False,
                    "date": d,
                }
            )
            ss.trades_today += 1
            rsm.reset()

        if active and cur.is_closed:
            cfgs = detect_fvgs(
                chunk, lookback=min(50, len(chunk)), timeframe="15m", min_fvg_size=mfs
            )
            for t in active:
                if t.get("closed"):
                    continue
                for f in cfgs:
                    if (t["side"] == "long" and f.direction != "bullish") or (
                        t["side"] == "short" and f.direction != "bearish"
                    ):
                        continue
                    if f.filled or f.invalidated:
                        continue
                    buf = abs(t["initial_sl"] - t["entry_price"]) * fbm
                    if t["side"] == "long":
                        ns = f.bottom - buf
                        if ns > t["sl"]:
                            sd2 = ns - t["sl"]
                            t["sl"] = ns
                            t["tp"] += sd2
                            t["trailing_count"] += 1
                    else:
                        ns = f.top + buf
                        if ns < t["sl"]:
                            sd2 = t["sl"] - ns
                            t["sl"] = ns
                            t["tp"] -= sd2
                            t["trailing_count"] += 1

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
                rsk = abs(t["initial_sl"] - t["entry_price"])
                t["rr"] = round(diff / rsk if rsk > 0 else 0, 2)
                trades.append(t)
                if (
                    not t.get("is_retrade")
                    and ss.trades_today == 1
                    and not ss.retrade_armed
                ):
                    ss.retrade_armed = True
                    ss.retrade_side = "short" if t["side"] == "long" else "long"
                    ss.retrade_sweep_level = 0.0
                    ss.retrade_entry_bar = t["entry_bar"]
                    ss.retrade_fvg_attempts = 0
                    ss.retrade_mode = "fvg"
            else:
                sa.append(t)
        active = sa

        # retrade (same as original)
        if ss.retrade_armed and ss.trades_today == 1 and not active:
            sbi = None
            sf = False
            lb = min(5, sb)
            for ci in range(max(0, sb - 4), sb + 1):
                if ci < 0 or ci >= len(b15):
                    continue
                if ci - lb < 0:
                    continue
                rb = b15[ci - lb : ci]
                cb = b15[ci]
                if ss.retrade_side == "short":
                    rh = max(x.high for x in rb)
                    if cb.high > rh and cb.close < rh:
                        sf = True
                        sbi = ci
                        break
                else:
                    rl = min(x.low for x in rb)
                    if cb.low < rl and cb.close > rl:
                        sf = True
                        sbi = ci
                        break
            if sf:
                sdir = "bearish" if ss.retrade_side == "short" else "bullish"
                sb2 = b15[sbi]
                if rsm2.state_name == "IDLE":
                    rsm2.on_sweep(
                        direction=sdir,
                        level=ss.retrade_sweep_level,
                        bar_index=sb2.index,
                    )
            if sf and rsm2.state_name == "SWEEP_DETECTED":
                sb2 = b15[sbi]
                sc = b15[sbi - W : sbi + 1] if sbi >= W else chunk
                rsm2.on_sweep_confirmed(sc, sb2)
            if rsm2.can_trigger():
                if sbi is not None and sbi <= (ss.retrade_entry_bar or 0):
                    rsm2.reset()
                elif detect_phase_from_timestamp(cur.timestamp) not in (
                    SessionPhase.NEWYORK,
                    SessionPhase.LONDON,
                ):
                    rsm2.reset()
                else:
                    rep = cur.close
                    rrp = atr * sam
                    rf = rsm2.trigger_fvg
                    if ss.retrade_side == "long":
                        rsl = rf.bottom - (rrp * fbm) if rf else rep - rrp * 2
                        rtp = (
                            ss.london_high if ss.london_high > rep else rep + rrp * tpr
                        )
                    else:
                        rsl = rf.top + (rrp * fbm) if rf else rep + rrp * 2
                        rtp = ss.london_low if ss.london_low < rep else rep - rrp * tpr
                    rq = (ic * rr2) / abs(rsl - rep) if abs(rsl - rep) > 0 else 0
                    if rq > 0:
                        d2 = datetime.fromtimestamp(
                            cur.timestamp / 1000, tz=timezone.utc
                        ).strftime("%Y-%m-%d")
                        active.append(
                            {
                                "entry_bar": sb,
                                "entry_price": rep,
                                "sl": rsl,
                                "tp": rtp,
                                "qty": rq,
                                "side": ss.retrade_side,
                                "trigger_fvg": rf,
                                "initial_sl": rsl,
                                "initial_tp": rtp,
                                "trailing_count": 0,
                                "is_retrade": True,
                                "date": d2,
                            }
                        )
                        ss.trades_today += 1
                        rsm2.reset()
                        ss.retrade_armed = False
                    else:
                        ss.retrade_fvg_attempts += 1
                        rsm2.reset()
            else:
                ss.retrade_fvg_attempts += 1

            if ss.retrade_fvg_attempts >= MFA:
                ss.retrade_mode = "lhr"
                lh = ss.london_high
                ll2 = ss.london_low
                if ss.retrade_side == "short" and lh > 0:
                    zb = lh * (1 - LRT)
                    zt = lh
                    if zb <= cur.close <= zt:
                        lep = cur.close
                        lsl = lh + atr * 1.0
                        ltp = ll2 if ll2 < lep else lep - atr * 1.0 * tpr
                        lrd = abs(lsl - lep)
                        if lrd >= atr * 0.1:
                            lq = (ic * rr2) / lrd if lrd > 0 else 0
                            if lq > 0:
                                d2 = datetime.fromtimestamp(
                                    cur.timestamp / 1000, tz=timezone.utc
                                ).strftime("%Y-%m-%d")
                                active.append(
                                    {
                                        "entry_bar": sb,
                                        "entry_price": lep,
                                        "sl": lsl,
                                        "tp": ltp,
                                        "qty": lq,
                                        "side": "short",
                                        "trigger_fvg": None,
                                        "initial_sl": lsl,
                                        "initial_tp": ltp,
                                        "trailing_count": 0,
                                        "is_retrade": True,
                                        "date": d2,
                                    }
                                )
                                ss.trades_today += 1
                                ss.retrade_armed = False
                elif ss.retrade_side == "long" and ll2 < float("inf"):
                    zt = ll2 * (1 + LRT)
                    zb = ll2
                    if zb <= cur.close <= zt:
                        lep = cur.close
                        lsl = ll2 - atr * 1.0
                        ltp = lh if lh > lep else lep + atr * 1.0 * tpr
                        lrd = abs(lsl - lep)
                        if lrd >= atr * 0.1:
                            lq = (ic * rr2) / lrd if lrd > 0 else 0
                            if lq > 0:
                                d2 = datetime.fromtimestamp(
                                    cur.timestamp / 1000, tz=timezone.utc
                                ).strftime("%Y-%m-%d")
                                active.append(
                                    {
                                        "entry_bar": sb,
                                        "entry_price": lep,
                                        "sl": lsl,
                                        "tp": ltp,
                                        "qty": lq,
                                        "side": "long",
                                        "trigger_fvg": None,
                                        "initial_sl": lsl,
                                        "initial_tp": ltp,
                                        "trailing_count": 0,
                                        "is_retrade": True,
                                        "date": d2,
                                    }
                                )
                                ss.trades_today += 1
                                ss.retrade_armed = False

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
                rsk = abs(t["initial_sl"] - t["entry_price"])
                t["rr"] = round(diff / rsk if rsk > 0 else 0, 2)
                trades.append(t)

    m = {"symbol": sym, "total_trades": len(trades), "zone_counts": zone_counts}
    if trades:
        tp2 = sum(t["pnl"] for t in trades)
        wins = [t for t in trades if t["pnl"] > 0]
        losses = [t for t in trades if t["pnl"] <= 0]
        wr = len(wins) / len(trades) * 100 if trades else 0
        dpk = ic
        dm = 0.0
        run = ic
        for t in trades:
            run += t["pnl"]
            dpk = max(dpk, run)
            dd = (dpk - run) / dpk * 100 if dpk > 0 else 0
            dm = max(dm, dd)
        wt2 = sum(t["rr"] for t in wins) / len(wins) if wins else 0
        lt2 = sum(t["rr"] for t in losses) / len(losses) if losses else 0
        pf = abs(wt2 / lt2) if wt2 > 0 and lt2 != 0 else 0
        pt = [t for t in trades if not t.get("is_retrade")]
        rt = [t for t in trades if t.get("is_retrade")]
        m.update(
            {
                "total_pnl": tp2,
                "wr": wr,
                "max_dd": dm,
                "profit_factor": pf,
                "primary_trades": len(pt),
                "retrade_trades": len(rt),
                "primary_pnl": sum(t["pnl"] for t in pt),
                "retrade_pnl": sum(t["pnl"] for t in rt),
            }
        )
    return m, trades


def main():
    t0 = time.time()
    old_results = {}
    new_results = {}

    print("=" * 130)
    print("  ANALYZER KARSILASTIRMA: SPAGETTI KOD vs CBDR FILTRELI")
    print("  CBDR Thresholds: max_bias_pct (altin->gri) / fail_limit (gri->kirmizi)")
    print("=" * 130)

    for sym in COINS:
        ts = time.time()
        cfg = get_config(sym)
        flt = CBDR_FILTERS.get(sym, None)
        mb = flt["max_bias_pct"] if flt else 0
        fl = flt["fail_limit"] if flt else 0
        print(
            f"\n{sym:>10} | CBDR filtre: {mb:.2f}% / {fl:.2f}% | ", end="", flush=True
        )

        # Original (spaghetti) - no filter
        m1, _ = run_bt(sym, cfg, use_filter=False)
        # CBDR filtered
        m2, _ = run_bt(sym, cfg, use_filter=True)
        old_results[sym] = m1
        new_results[sym] = m2
        z = m2.get("zone_counts", {}) if m2 else {}
        print(
            f"Eski: {m1['total_trades']:>4} islem PnL={m1['total_pnl']:>+8.0f} WR={m1['wr']:>4.1f}% "
            f"| Yeni: {m2['total_trades']:>4} islem PnL={m2['total_pnl']:>+8.0f} WR={m2['wr']:>4.1f}% "
            f"| Bolge: A={z.get('golden',0)} G={z.get('gray',0)} K={z.get('red',0)} "
            f"| {time.time()-ts:.0f}s",
            flush=True,
        )

    print(f"\n{'='*130}")
    print("  KARSILASTIRMA TABLOSU")
    print(f"{'='*130}")
    h = f"  {'Coin':<10} {'EskIslm':>7} {'EskPnL':>10} {'EskWR':>7} {'EskDD':>7} {'EskPF':>7}"
    h += f" {'YIslm':>7} {'YPnL':>10} {'YWR':>7} {'YDD':>7} {'YPF':>7} {'+/-Islm':>7} {'+/-PnL':>10} {'+/-WR':>7}"
    print(h)
    print("  " + "-" * 125)
    total_old_pnl = 0
    total_new_pnl = 0
    for sym in sorted(COINS):
        o = old_results[sym]
        n = new_results[sym]
        di = n["total_trades"] - o["total_trades"]
        dp = n["total_pnl"] - o["total_pnl"]
        dw = n["wr"] - o["wr"]
        print(
            f"  {sym:<10} {o['total_trades']:>7} {o['total_pnl']:>+10.0f} {o['wr']:>5.1f}% {o['max_dd']:>5.1f}% {o['profit_factor']:>5.2f}"
            f" {n['total_trades']:>7} {n['total_pnl']:>+10.0f} {n['wr']:>5.1f}% {n['max_dd']:>5.1f}% {n['profit_factor']:>5.2f}"
            f" {di:>+7} {dp:>+10.0f} {dw:>+5.1f}%"
        )
        total_old_pnl += o["total_pnl"]
        total_new_pnl += n["total_pnl"]
    print("  " + "-" * 125)
    td = total_new_pnl - total_old_pnl
    print(
        f"  {'TOPLAM':<10} {'':>7} {total_old_pnl:>+10.0f} {'':>7} {'':>7} {'':>7}"
        f" {'':>7} {total_new_pnl:>+10.0f} {'':>7} {'':>7} {'':>7}"
        f" {'':>7} {td:>+10.0f} {'':>7}"
    )
    print(f"\n  Sure: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
