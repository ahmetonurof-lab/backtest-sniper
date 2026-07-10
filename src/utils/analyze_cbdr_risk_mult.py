"""
analyze_cbdr_risk_mult.py — CBDR genisligine gore risk carpani backtesti.
Tek pass: backtest 1x kosar, tum risk multipleri memory'de scale edilir.
"""

# ruff: noqa: E402, E704, E701, E702
import csv
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

SESSION_HOURS = {"start": 19, "end": 1}
RISK_MULTIPLIERS = [0.5, 0.7, 1.0, 1.3, 1.5, 2.0]
N_BUCKETS = 6


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


def run_backtest(symbol):
    """
    Tek pass backtest. PnL'leri risk_mult=1.0 ile hesaplar.
    Doner: (day_cbdr, day_pnls)
      day_cbdr: {day_key: cbdr_width_pct}
      day_pnls: {day_key: [pnl_1x, ...]}
    """
    csv_path = os.path.join(
        os.path.dirname(__file__), "data", "daily", f"{symbol}_1m_raw.csv"
    )
    if not os.path.isfile(csv_path):
        return None, None

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
    FVG_WICK_RATIO_MAX = cfg.FVG_WICK_RATIO_MAX

    b1 = load_data(csv_path)
    b15 = resample_15m(b1)
    if not b15:
        return None, None

    ss = SessionState(start_hour=SESSION_HOURS["start"], end_hour=SESSION_HOURS["end"])
    rsm = RetraceStateMachine(max_wick_ratio=FVG_WICK_RATIO_MAX)

    day_cbdr = {}
    day_pnls = defaultdict(list)
    active = []
    atr_val = 0.0
    prev_close = b15[0].open
    for bar in b15[1:500]:
        tr = calculate_true_range(bar, prev_close)
        atr_val = update_atr(atr_val if atr_val > 0 else None, tr)
        prev_close = bar.close

    for sb in range(500, len(b15)):
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
            sh, eh = SESSION_HOURS["start"], SESSION_HOURS["end"]
            spans = sh > eh
            if (h >= sh or h < eh) if spans else (sh <= h < eh):
                rsm.reset()
                continue

            side = "long" if sd == "bullish" else "short"
            ep = cur.close
            rp2 = atr * sam
            tf = rsm.trigger_fvg

            if side == "long":
                if tf:
                    fh = tf.top - tf.bottom
                    sl = (
                        ep - rp2 * 2
                        if fh <= 0
                        else tf.bottom
                        - max(fh * 0.10, max(rp2 * 0.1, min(fh * 0.25, rp2 * fbm)))
                    )
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
                    sl = (
                        ep + rp2 * 2
                        if fh <= 0
                        else tf.top
                        + max(fh * 0.10, max(rp2 * 0.1, min(fh * 0.25, rp2 * fbm)))
                    )
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
            qty_base = (ic * rpt) / rd if rd > 0 else 0
            if qty_base <= 0:
                rsm.reset()
                continue

            active.append(
                {
                    "sb": sb,
                    "ep": ep,
                    "sl": sl,
                    "tp": tp,
                    "qty_base": qty_base,
                    "side": side,
                    "is": sl,
                    "it": tp,
                    "tc": 0,
                    "dk": ss.cbdr_day,
                }
            )
            rsm.reset()

        if active and cur.is_closed:
            for t in active:
                if t.get("cl"):
                    continue
                if t.get("tc", 0) > 0:
                    continue
                s2 = t["side"]
                e2 = t["ep"]
                rpt2 = abs(t["is"] - e2)
                th2 = rpt2 * BERM
                be2 = e2 + BESP if s2 == "long" else e2 - BESP
                if s2 == "long":
                    if cur.high >= e2 + th2 and t["sl"] < be2:
                        t["sl"] = be2
                        t["tc"] = 1
                else:
                    if cur.low <= e2 - th2 and t["sl"] > be2:
                        t["sl"] = be2
                        t["tc"] = 1

            tc = chunk[:-1]
            min_fvg_size = max(atr * FVG_MIN_SIZE_ATR_MULT, 1e-8)
            cfvgs = detect_fvgs(
                tc,
                lookback=min(50, len(tc)),
                timeframe="15m",
                min_fvg_size=min_fvg_size,
            )
            for t in active:
                if t.get("cl"):
                    continue
                s2 = t["side"]
                csl = t["sl"]
                ctp = t["tp"]
                rpt2 = abs(t["is"] - t["ep"])
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
                    t["tc"] = t.get("tc", 0) + ltc

        sa = []
        for t in active:
            if t.get("cl"):
                continue
            ex = False
            if t["side"] == "long":
                if cur.low <= t["sl"]:
                    t["xp"] = t["sl"]
                    t["cl"] = True
                    ex = True
                elif cur.high >= t["tp"]:
                    t["xp"] = t["tp"]
                    t["cl"] = True
                    ex = True
            else:
                if cur.high >= t["sl"]:
                    t["xp"] = t["sl"]
                    t["cl"] = True
                    ex = True
                elif cur.low <= t["tp"]:
                    t["xp"] = t["tp"]
                    t["cl"] = True
                    ex = True
            if ex:
                diff = (
                    (t["xp"] - t["ep"]) if t["side"] == "long" else (t["ep"] - t["xp"])
                )
                pnl_base = round(diff * t.get("qty_base", 0), 2)
                day_pnls[t.get("dk", "")].append(pnl_base)
            else:
                sa.append(t)
        active = sa

    if b15:
        lp = b15[-1].close
        for t in active:
            if not t.get("cl"):
                diff = (lp - t["ep"]) if t["side"] == "long" else (t["ep"] - lp)
                pnl_base = round(diff * t.get("qty_base", 0), 2)
                day_pnls[t.get("dk", "")].append(pnl_base)

    return day_cbdr, day_pnls


def compute_bucket_pnls(day_cbdr, day_pnls, risk_mult):
    """
    Esit-genislikli kovalara ayir, pnl_base * risk_mult ile scale et.
    """
    valid = {
        d: day_cbdr[d] for d in day_cbdr if d in day_pnls and day_cbdr[d] is not None
    }
    if len(valid) < 5:
        return []
    sd = sorted(valid.keys(), key=lambda d: valid[d])
    mn, mx = valid[sd[0]], valid[sd[-1]]
    if mx - mn <= 0:
        return []
    bw = (mx - mn) / N_BUCKETS
    buckets = []
    for bi in range(N_BUCKETS):
        lo = mn + bi * bw
        hi = lo + bw
        if bi == N_BUCKETS - 1:
            hi = mx + 0.001
        bd = [d for d in sd if lo <= valid[d] < hi]
        if not bd:
            continue
        tl = [p * risk_mult for d in bd for p in day_pnls.get(d, [])]
        if not tl:
            continue
        n = len(tl)
        wins = sum(1 for p in tl if p > 0)
        wr = wins / n * 100 if n > 0 else 0
        pnl = sum(tl)
        gp = sum(p for p in tl if p > 0) or 0
        gl = abs(sum(p for p in tl if p < 0)) or 1e-9
        buckets.append(
            {
                "range": f"{lo:.2f}-{hi:.2f}",
                "days": len(bd),
                "trades": n,
                "wr": wr,
                "pnl": pnl,
                "pf": gp / gl,
                "rm": risk_mult,
            }
        )
    return buckets


def main():
    t0 = time.time()
    print("=" * 120)
    print("  CBDR GENISLIGI -> RISK CARPANI BACKTESTI (tek pass)")
    print(
        f"  Session: REAL_CBDR ({SESSION_HOURS['start']}:00-{SESSION_HOURS['end']}:00 UTC)"
    )
    print(f"  Risk multipleri: {RISK_MULTIPLIERS}")
    print(f"  Kovasayisi: {N_BUCKETS} (esit genislik)")
    print("=" * 120)

    all_results = {}
    for sym in sorted(cfg.SYMBOLS):
        ts = time.time()
        print(f"\n  [{sym}] Backtest...", end=" ", flush=True)
        day_cbdr, day_pnls = run_backtest(sym)
        if day_cbdr is None or len(day_cbdr) < 5:
            print("YETERSIZ VERI")
            continue
        n_t = sum(len(v) for v in day_pnls.values())
        print(f"{len(day_cbdr)} gun, {n_t} trade ({time.time()-ts:.0f}s)", flush=True)

        sym_res = {}
        for rm in RISK_MULTIPLIERS:
            bs = compute_bucket_pnls(day_cbdr, day_pnls, rm)
            if bs:
                sym_res[rm] = bs
        all_results[sym] = sym_res

        # Tablo
        print(f"  {'Aralik%':<16} {'Gun':>4} {'Trade':>6}", end="")
        for rm in RISK_MULTIPLIERS:
            print(f" {'x'+str(rm):>10}", end="")
        print()
        ref = sym_res[list(sym_res.keys())[0]]
        for bi, rb in enumerate(ref):
            print(f"  {rb['range']:<16} {rb['days']:>4} {rb['trades']:>6}", end="")
            for rm in RISK_MULTIPLIERS:
                if rm in sym_res and bi < len(sym_res[rm]):
                    print(f" {sym_res[rm][bi]['pnl']:>+9.0f}", end="")
                else:
                    print(f" {'N/A':>10}", end="")
            print()

    # Ozet
    print(f"\n{'='*120}")
    print("  OPTIMAL RISK CARPANI (tum coin'ler ortalamasi)")
    print(f"{'='*120}")
    ba = {}
    for sym, sr in all_results.items():
        for rm, bs in sr.items():
            for bi, b in enumerate(bs):
                k = (bi, b["range"])
                if k not in ba:
                    ba[k] = {}
                if rm not in ba[k]:
                    ba[k][rm] = []
                ba[k][rm].append(b["pnl"])
    print(f"  {'Kova':<18} {'Gun':>4}", end="")
    for rm in RISK_MULTIPLIERS:
        print(f" {'x'+str(rm):>10}", end="")
    print(f" {'En iyi':>8}")
    for k in sorted(ba.keys(), key=lambda x: x[0]):
        _, rng = k
        d = ba[k]
        br = None
        ba2 = -float("inf")
        print(f"  {rng:<18} ", end="")
        for rm in RISK_MULTIPLIERS:
            vs = d.get(rm, [])
            av = sum(vs) / len(vs) if vs else 0
            if av > ba2:
                ba2 = av
                br = rm
            if vs:
                print(f" {av:>+9.0f}", end="")
            else:
                print(f" {'N/A':>10}", end="")
        print(f" {'x'+str(br):<6}")

    # CSV
    rdir = os.path.join(os.path.dirname(__file__), "..", "reports")
    os.makedirs(rdir, exist_ok=True)
    csv_path = os.path.join(rdir, "cbdr_risk_mult.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Coin", "RiskMult", "Bucket", "Days", "Trades", "WR%", "PnL", "PF"])
        for sym in sorted(all_results):
            for rm in sorted(all_results[sym].keys()):
                for b in all_results[sym][rm]:
                    w.writerow(
                        [
                            sym,
                            rm,
                            b["range"],
                            b["days"],
                            b["trades"],
                            f"{b['wr']:.1f}",
                            f"{b['pnl']:.2f}",
                            f"{b['pf']:.2f}",
                        ]
                    )
    print(f"\n  CSV: {csv_path}")
    print(f"  Toplam sure: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
