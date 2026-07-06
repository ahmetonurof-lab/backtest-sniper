"""
sweep_early_london.py — Erken Londra (02-08 UTC) risk carpani taramasi.
DEFAULT session [22:00-02:00], 13 coin × 6 deger = 78 backtest.
Risk_mult = [1.0, 1.2, 1.4, 1.6, 1.8, 2.0]
"""
# ruff: noqa: E402
import csv, functools, math, os, sys, time
from datetime import datetime, timezone
from collections import defaultdict

os.environ["SNIPER_OUTPUT_DIR"] = os.path.join(os.path.dirname(__file__), "..", "output")
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

SESSION_NAME = "DEFAULT"
SESSION_HOURS = {'start': 22, 'end': 2}
SWEEP_VALUES = [1.0, 1.2, 1.4, 1.6, 1.8, 2.0]
REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
os.makedirs(REPORT_DIR, exist_ok=True)


@functools.lru_cache(maxsize=32)
def load_data(filepath):
    bars = []
    with open(filepath, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            ts = int(datetime.strptime(row["open_time"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp() * 1000)
            bars.append(Bar(index=i, open=float(row["open"]), high=float(row["high"]),
                            low=float(row["low"]), close=float(row["close"]),
                            volume=float(row["volume"]), is_closed=True, timestamp=ts))
    return bars


def resample_15m(bars_1m):
    m15 = []
    for i in range(0, len(bars_1m), 15):
        c = bars_1m[i:i + 15]
        if len(c) < 15:
            break
        m15.append(Bar(index=len(m15), open=c[0].open,
                       high=max(b.high for b in c), low=min(b.low for b in c),
                       close=c[-1].close, volume=sum(b.volume for b in c),
                       is_closed=True, timestamp=c[0].timestamp))
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


def run_backtest(symbol: str, early_london_risk_mult: float) -> dict:
    """Run CBDR DEFAULT backtest with early London risk multiplier.
    Returns {trades, wins, be, losses, total_pnl, max_dd_pct, wr}"""
    csv_path = os.path.join(os.path.dirname(__file__), "data", "daily", f"{symbol}_1m_raw.csv")
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

    sh = SESSION_HOURS['start']
    eh = SESSION_HOURS['end']
    spans_midnight = sh > eh
    ss = SessionState(start_hour=sh, end_hour=eh)
    rsm = RetraceStateMachine(max_wick_ratio=cfg.FVG_WICK_RATIO_MAX)

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
        just_locked = ss.cbdr_locked and not locked_before

        if just_locked and ss.cbdr_body_high > 0:
            w = ((ss.cbdr_body_high - ss.cbdr_body_low) / ss.cbdr_body_low) * 100
            # day_cbdr not stored — not needed for PnL sweep

        if ss.sweep_confirmed and rsm.state_name == "IDLE":
            rsm.on_sweep(direction=ss.sweep_direction or "bullish",
                         level=ss.sweep_level or 0.0, bar_index=None)

        if rsm.state_name == "SWEEP_DETECTED":
            rsm.on_sweep_confirmed(chunk, cur, atr)

        if rsm.can_trigger() and not active:
            sd = rsm.direction
            db = ss.daily_bias
            if (sd == "bullish" and db == DailyBias.BEARISH) or \
               (sd == "bearish" and db == DailyBias.BULLISH) or \
               db == DailyBias.NEUTRAL:
                rsm.reset()
                continue
            h = edt.hour
            if (h >= sh or h < eh) if spans_midnight else (sh <= h < eh):
                rsm.reset()
                continue

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

            # ── EARLY LONDON RISK MULTIPLIER ──
            risk_mult = early_london_risk_mult if 2 <= h < 8 else 1.0
            qty = (ic * rpt * risk_mult) / rd if rd > 0 else 0
            # ──────────────────────────────────

            if qty <= 0:
                rsm.reset()
                continue

            active.append({"entry_bar": sb, "entry_price": ep, "sl": sl, "tp": tp,
                           "qty": qty, "side": side, "trigger_fvg": tf,
                           "initial_sl": sl, "initial_tp": tp, "trailing_count": 0,
                           "day_key": ss.cbdr_day, "entry_hour": h})
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
            cfvgs = detect_fvgs(tc, lookback=min(50, len(tc)), timeframe="15m", min_fvg_size=min_fvg_size)
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
                    t["exit_price"] = t["sl"]; t["exit_bar"] = sb
                    t["result"] = "SL"; t["closed"] = True; ex = True
                elif cur.high >= t["tp"]:
                    t["exit_price"] = t["tp"]; t["exit_bar"] = sb
                    t["result"] = "TP"; t["closed"] = True; ex = True
            else:
                if cur.high >= t["sl"]:
                    t["exit_price"] = t["sl"]; t["exit_bar"] = sb
                    t["result"] = "SL"; t["closed"] = True; ex = True
                elif cur.low <= t["tp"]:
                    t["exit_price"] = t["tp"]; t["exit_bar"] = sb
                    t["result"] = "TP"; t["closed"] = True; ex = True
            if ex:
                diff = (t["exit_price"] - t["entry_price"]) if t["side"] == "long" else (t["entry_price"] - t["exit_price"])
                t["pnl"] = round(diff * t["qty"], 2)
                day_trades[t.get("day_key", "")].append(t["pnl"])
                trade_records.append({"result": t["result"], "pnl": t["pnl"], "hour": t["entry_hour"]})
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
                diff = (lp - t["entry_price"]) if t["side"] == "long" else (t["entry_price"] - lp)
                t["pnl"] = round(diff * t["qty"], 2)
                day_trades[t.get("day_key", "")].append(t["pnl"])
                trade_records.append({"result": t["result"], "pnl": t["pnl"], "hour": t["entry_hour"]})

    n = len(trade_records)
    wins = sum(1 for r in trade_records if r["pnl"] > 0)
    be = sum(1 for r in trade_records if r["pnl"] == 0)
    losses = n - wins - be
    wr = wins / n * 100 if n else 0
    total_pnl = sum(r["pnl"] for r in trade_records)

    # MaxDD
    cumulative = 0
    peak = 0
    max_dd = 0
    for r in trade_records:
        cumulative += r["pnl"]
        if cumulative > peak:
            peak = cumulative
        dd = peak - cumulative
        if dd > max_dd:
            max_dd = dd
    max_dd_pct = (max_dd / cfg.INITIAL_BALANCE) * 100

    # Early-london specific stats
    el_trades = [r for r in trade_records if r["hour"] is not None and 2 <= r["hour"] < 8]
    el_wins = sum(1 for r in el_trades if r["pnl"] > 0)
    el_wr = el_wins / len(el_trades) * 100 if el_trades else 0
    el_pnl = sum(r["pnl"] for r in el_trades)

    return {
        "trades": n, "wins": wins, "be": be, "losses": losses,
        "wr": round(wr, 1), "total_pnl": round(total_pnl, 2),
        "max_dd_pct": round(max_dd_pct, 2),
        "el_trades": len(el_trades), "el_wins": el_wins,
        "el_wr": round(el_wr, 1), "el_pnl": round(el_pnl, 2),
    }


def main():
    t0 = time.time()
    print("=" * 100)
    print(f"  EARLY LONDON RISK MULT SWEEP — {SESSION_NAME}")
    print(f"  Degerler: {SWEEP_VALUES}")
    print(f"  Coin sayisi: {len(cfg.SYMBOLS)} × {len(SWEEP_VALUES)} = {len(cfg.SYMBOLS)*len(SWEEP_VALUES)} backtest")
    print("=" * 100)

    all_symbols = sorted(cfg.SYMBOLS)

    # results[symbol][mult_str] = stats_dict
    results = {}
    for sym in all_symbols:
        results[sym] = {}

    for mult in SWEEP_VALUES:
        print(f"\n--- EARLY_LONDON_RISK_MULT = {mult} ---")
        for sym in all_symbols:
            sys.stdout.write(f"\r  {sym}... ")
            sys.stdout.flush()
            stats = run_backtest(sym, mult)
            if stats:
                results[sym][str(mult)] = stats
                print(f"{sym}: {stats['trades']}t WR={stats['wr']}% PnL={stats['total_pnl']:+.0f} DD={stats['max_dd_pct']}%")
            else:
                print(f"{sym}: VERI YOK")

    print(f"\n\nTotal: {time.time()-t0:.0f}s")

    # ── REPORT ──
    # CSV
    csv_path = os.path.join(REPORT_DIR, "sweep_early_london.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "mult", "trades", "wins", "be", "losses", "wr%", "total_pnl", "max_dd%",
                     "el_trades", "el_wins", "el_wr%", "el_pnl"])
        for sym in all_symbols:
            for mult in SWEEP_VALUES:
                s = results.get(sym, {}).get(str(mult))
                if s:
                    w.writerow([sym, mult, s["trades"], s["wins"], s["be"], s["losses"],
                                s["wr"], s["total_pnl"], s["max_dd_pct"],
                                s["el_trades"], s["el_wins"], s["el_wr"], s["el_pnl"]])

    # MD report
    md = []
    md.append(f"# Early London Risk Multiplier Sweep — {SESSION_NAME}")
    md.append(f"")
    md.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    md.append(f"**Session:** {SESSION_NAME} [{SESSION_HOURS['start']:02d}:00-{SESSION_HOURS['end']:02d}:00]")
    md.append(f"**Risk Multipliers:** {SWEEP_VALUES}")
    md.append(f"**Early London Window:** 02:00-08:00 UTC (kodun `detect_phase()` LONDON baslangici)")
    md.append(f"")
    md.append(f"## Portfolio Summary")
    md.append(f"")
    header = ["Mult", "ToplamPnL", "OrtWR%", "PortMaxDD%", "PnL/DD", "EL_PnL", "EL_WR%"]
    md.append("| " + " | ".join(header) + " |")
    md.append("|" + "|".join(["-"*8]*len(header)) + "|")

    for mult in SWEEP_VALUES:
        total_pnl = sum(results[sym].get(str(mult), {}).get("total_pnl", 0) for sym in all_symbols)
        wrs = [results[sym].get(str(mult), {}).get("wr", 0) for sym in all_symbols]
        dds = [results[sym].get(str(mult), {}).get("max_dd_pct", 0) for sym in all_symbols]
        el_pnl = sum(results[sym].get(str(mult), {}).get("el_pnl", 0) for sym in all_symbols)
        el_wrs = [results[sym].get(str(mult), {}).get("el_wr", 0) for sym in all_symbols]
        avg_wr = sum(wrs) / len(wrs) if wrs else 0
        avg_el_wr = sum(el_wrs) / len(el_wrs) if el_wrs else 0
        port_max_dd = max(dds) if dds else 0
        pnl_dd_ratio = round(total_pnl / port_max_dd, 1) if port_max_dd else 0
        md.append(f"| {mult:.1f}x | {total_pnl:>+9,.0f} | {avg_wr:>5.1f}% | {port_max_dd:>6.2f}% | {pnl_dd_ratio:>6.1f} | {el_pnl:>+9,.0f} | {avg_el_wr:>5.1f}% |")

    md.append("")
    md.append("### Coin Bazinda En Iyi Carpan")
    md.append("")
    md.append("| Coin | Best Mult | PnL | WR% | MaxDD% |")
    md.append("|------|-----------|-----|-----|--------|")

    for sym in all_symbols:
        best_mult = max(SWEEP_VALUES, key=lambda m: results[sym].get(str(m), {}).get("total_pnl", -1e9))
        s = results[sym].get(str(best_mult), {})
        md.append(f"| {sym} | {best_mult:.1f}x | {s.get('total_pnl',0):>+8,.0f} | {s.get('wr',0):>4.1f}% | {s.get('max_dd_pct',0):>5.2f}% |")

    md.append("")
    md.append("### Full Per-Coin Table")
    md.append("")
    coin_header = ["Coin", "Mult", "Trades", "WR%", "PnL", "MaxDD%", "EL_Trades", "EL_WR%", "EL_PnL"]
    md.append("| " + " | ".join(coin_header) + " |")
    md.append("|" + "|".join(["-"*8]*len(coin_header)) + "|")
    for sym in all_symbols:
        for mult in SWEEP_VALUES:
            s = results[sym].get(str(mult))
            if s:
                md.append(f"| {sym} | {mult:.1f}x | {s['trades']} | {s['wr']}% | {s['total_pnl']:>+,.0f} | {s['max_dd_pct']:.2f}% | {s['el_trades']} | {s['el_wr']}% | {s['el_pnl']:>+,.0f} |")

    md.append("")
    md.append(f"*CSV: `sweep_early_london.csv`*")
    md_path = os.path.join(REPORT_DIR, "sweep_early_london_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print(f"\n  Rapor: {md_path}")
    print(f"  CSV:   {csv_path}")


if __name__ == "__main__":
    main()
