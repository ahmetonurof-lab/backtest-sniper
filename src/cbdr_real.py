"""
cbdr_real.py — REAL_CBDR [19:00-01:00] CBDR threshold analysis.
Single-session standalone — no overlap filter across sessions.
BE (PnL=0) trades shown separately for win-rate transparency.
"""
# ruff: noqa: E402, E702
import csv
import functools
import math
import os
import sys
import time
from datetime import datetime, timezone
from collections import defaultdict

os.environ["SNIPER_OUTPUT_DIR"] = os.path.join(os.path.dirname(__file__), "..", "output")
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
from quant_logger import QuantLogger

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ─── Session ──────────────────────────────────────────────────────
SESSION_NAME = "REAL_CBDR"
SESSION_HOURS = {'start': 19, 'end': 1}


def wilson_upper(wins: int, trades: int, z: float = 1.96) -> float:
    if trades == 0:
        return 1.0
    z2 = z * z
    p_hat = wins / trades
    denominator = 1 + z2 / trades
    centre = p_hat + z2 / (2 * trades)
    margin = z * math.sqrt((p_hat * (1 - p_hat) + z2 / (4 * trades)) / trades)
    return min(1.0, (centre + margin) / denominator)


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
        m15.append(Bar(index=c[0].index, open=c[0].open,
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


_LOGGER = None  # module-level ref, set in main()


def collect_daily_data(symbol: str):
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
            print(f"\r    [REAL_CBDR] %{pct:.0f} ({sb}/{total_bars})", end="", flush=True)
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
            day_cbdr[ss.cbdr_day] = round(w, 4)

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
            qty = (ic * rpt) / rd if rd > 0 else 0
            if qty <= 0:
                rsm.reset()
                continue

            entry_day = ss.cbdr_day
            active.append({"entry_bar": sb, "entry_price": ep, "sl": sl, "tp": tp,
                           "qty": qty, "side": side, "trigger_fvg": tf,
                           "initial_sl": sl, "initial_tp": tp, "trailing_count": 0,
                           "day_key": entry_day})
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
                trade_records.append({"result": t["result"], "pnl": t["pnl"]})
                if t["pnl"] > 0:
                    wins.append(t)
                else:
                    losses.append(t)
                # QuantLogger
                if _LOGGER is not None:
                    risk_usd = abs(t["initial_sl"] - t["entry_price"]) * t["qty"] if t["initial_sl"] else 0
                    fvg_sz = (t["trigger_fvg"].top - t["trigger_fvg"].bottom) if t.get("trigger_fvg") else None
                    _LOGGER.log_trade({
                        "symbol": symbol,
                        "session": SESSION_NAME,
                        "side": t["side"].upper(),
                        "entry_time": edt,
                        "entry_price": round(t["entry_price"], 6),
                        "exit_price": round(t["exit_price"], 6),
                        "result": t["result"],
                        "final_pnl_usd": round(t["pnl"], 2),
                        "risk_usd": round(risk_usd, 2),
                        "r_multiple": round(t["pnl"] / risk_usd, 4) if risk_usd > 0 else 0.0,
                        "trailing_count": t.get("trailing_count", 0),
                        "fvg_size_pips": round(fvg_sz, 6) if fvg_sz else None,
                        "atr": round(atr, 6),
                    })
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
                trade_records.append({"result": t["result"], "pnl": t["pnl"]})
                if t["pnl"] > 0:
                    wins.append(t)
                else:
                    losses.append(t)
                # QuantLogger — OPEN trade
                if _LOGGER is not None:
                    risk_usd = abs(t["initial_sl"] - t["entry_price"]) * t["qty"] if t["initial_sl"] else 0
                    fvg_sz = (t["trigger_fvg"].top - t["trigger_fvg"].bottom) if t.get("trigger_fvg") else None
                    _LOGGER.log_trade({
                        "symbol": symbol,
                        "session": SESSION_NAME,
                        "side": t["side"].upper(),
                        "entry_time": edt,
                        "entry_price": round(t["entry_price"], 6),
                        "exit_price": round(t["exit_price"], 6),
                        "result": "OPEN",
                        "final_pnl_usd": round(t["pnl"], 2),
                        "risk_usd": round(risk_usd, 2),
                        "r_multiple": round(t["pnl"] / risk_usd, 4) if risk_usd > 0 else 0.0,
                        "trailing_count": t.get("trailing_count", 0),
                        "fvg_size_pips": round(fvg_sz, 6) if fvg_sz else None,
                        "atr": round(atr, 6),
                    })

    print(f"\r    [REAL_CBDR] %100 ({total_bars}/{total_bars})", flush=True)
    daily_rows = []
    all_keys = sorted(set(list(day_cbdr.keys()) + list(day_trades.keys())))
    for dk in all_keys:
        if not dk:
            continue
        w = day_cbdr.get(dk)
        tlist = day_trades.get(dk, [])
        if w is None and not tlist:
            continue
        total_pnl = sum(tlist)
        n_trades = len(tlist)
        n_wins = sum(1 for p in tlist if p > 0)
        n_be = sum(1 for p in tlist if p == 0)
        daily_rows.append({
            "day_key": dk,
            "cbdr_pct": w,
            "trades": n_trades,
            "wins": n_wins,
            "be": n_be,
            "losses": n_trades - n_wins - n_be,
            "pnl": total_pnl,
        })
    return daily_rows, wins, losses, trade_records


# ─── Sabit CBDR esikleri ────────────────────────────────────
CBDR_BUCKETS = [
    (0, 1.0, "0-1%"),
    (1.0, 1.5, "1-1.5%"),
    (1.5, 2.0, "1.5-2%"),
    (2.0, 3.0, "2-3%"),
    (3.0, 5.0, "3-5%"),
    (5.0, 999, ">5%"),
]


def cbdr_bucket(cbdr_pct: float) -> int:
    """CBDR yuzdesine gore bucket index'i doner (0-5)."""
    for i, (lo, hi, _) in enumerate(CBDR_BUCKETS):
        if lo <= cbdr_pct < hi:
            return i
    return len(CBDR_BUCKETS) - 1


def analyze_thresholds(daily_rows, symbol: str, min_bucket_trades: int = 100):
    valid = [d for d in daily_rows if d["cbdr_pct"] is not None and d["trades"] > 0]
    if len(valid) < 3:
        return None

    # Sabit CBDR esigine gore bucket'la
    bucket_data = {i: {"days": set(), "trades": 0, "wins": 0, "be": 0, "losses": 0, "pnl": 0.0}
                   for i in range(len(CBDR_BUCKETS))}
    for d in valid:
        bi = cbdr_bucket(d["cbdr_pct"])
        bd = bucket_data[bi]
        bd["days"].add(d["day_key"])
        bd["trades"] += d["trades"]
        bd["wins"] += d["wins"]
        bd["be"] += d["be"]
        bd["losses"] += d["losses"]
        bd["pnl"] += d["pnl"]

    buckets = []
    for i, (lo, hi, label) in enumerate(CBDR_BUCKETS):
        bd = bucket_data[i]
        if bd["trades"] == 0:
            continue
        lo_pct = lo
        hi_pct = hi if hi < 999 else max(d["cbdr_pct"] for d in valid)
        b_wr = round(bd["wins"] / bd["trades"] * 100, 1) if bd["trades"] > 0 else 0
        b_ber = round((bd["wins"] + bd["be"]) / bd["trades"] * 100, 1) if bd["trades"] > 0 else 0
        buckets.append({
            "range": label,
            "lo_pct": lo_pct,
            "hi_pct": round(hi_pct, 2),
            "days": len(bd["days"]),
            "trades": bd["trades"],
            "wins": bd["wins"],
            "be": bd["be"],
            "losses": bd["losses"],
            "wr": b_wr,
            "be_plus_rate": b_ber,
            "pnl": round(bd["pnl"], 2),
        })

    total_trades = sum(b["trades"] for b in buckets)
    total_wins = sum(b["wins"] for b in buckets)
    overall_wr = total_wins / total_trades if total_trades > 0 else 0

    # Wilson fail limit: en kotu WR bucket'ini bul
    fail_limit = None
    for b in buckets:
        if b["trades"] < min_bucket_trades:
            continue
        if b["wr"] > 0 and wilson_upper(b["wins"], b["trades"]) < overall_wr:
            fail_limit = b["lo_pct"]
            break

    return {
        "symbol": symbol,
        "total_days": len(valid),
        "total_trades": total_trades,
        "overall_wr": round(overall_wr * 100, 1),
        "fail_limit": round(fail_limit, 2) if fail_limit is not None else None,
        "wilson_found": fail_limit is not None,
        "buckets": buckets,
        "total_pnl": sum(d["pnl"] for d in valid),
    }


def compute_session_stats(trade_records, initial_balance):
    n = len(trade_records)
    if n == 0:
        return {'total_trades': 0, 'win_pct': 0, 'profit_factor': 0, 'max_dd_pct': 0, 'avg_mae': 0}
    wins = sum(1 for r in trade_records if r["pnl"] > 0)
    be = sum(1 for r in trade_records if r["pnl"] == 0)
    losses = n - wins - be
    win_pct = wins / n * 100 if n > 0 else 0
    be_plus_pct = (wins + be) / n * 100 if n > 0 else 0

    gross_profit = sum(r["pnl"] for r in trade_records if r["pnl"] > 0) or 0
    gross_loss = abs(sum(r["pnl"] for r in trade_records if r["pnl"] < 0)) or 1e-9
    profit_factor = gross_profit / gross_loss

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
    max_dd_pct = (max_dd / initial_balance) * 100 if initial_balance > 0 else 0

    losses_list = [r["pnl"] for r in trade_records if r["pnl"] < 0]
    avg_mae = abs(sum(losses_list) / len(losses_list)) if losses_list else 0
    total_pnl = sum(r["pnl"] for r in trade_records)

    return {
        'total_trades': n, 'win_pct': win_pct, 'be_plus_pct': be_plus_pct,
        'wins': wins, 'be': be, 'losses': losses,
        'profit_factor': profit_factor, 'max_dd_pct': max_dd_pct,
        'avg_mae': avg_mae, 'total_pnl': total_pnl,
    }


def main():
    t0 = time.time()
    print("=" * 100)
    print(f"  CBDR ESIK ANALIZI — {SESSION_NAME} [{SESSION_HOURS['start']:02d}:00-{SESSION_HOURS['end']:02d}:00]")
    print("=" * 100)

    # QuantLogger — tum trade'leri .parquet'e kaydet
    parquet_path = os.path.join(os.path.dirname(__file__), "..", "reports", f"trades_{SESSION_NAME.lower()}.parquet")
    global _LOGGER
    _LOGGER = QuantLogger(parquet_path)

    all_symbols = sorted(cfg.SYMBOLS)
    results_data = []  # (sym, stats, analysis) for report

    for sym in all_symbols:
        print(f"\n  [{sym}] Basliyor...", flush=True)
        result = collect_daily_data(sym)
        if result is None:
            print(f"    [{sym}] VERI DOSYASI YOK", flush=True)
            continue
        daily_rows, wins, losses, trade_records = result
        if len(daily_rows) < 3:
            print(f"    [{sym}] YETERSIZ VERI", flush=True)
            continue

        stats = compute_session_stats(trade_records, cfg.INITIAL_BALANCE)
        analysis = analyze_thresholds(daily_rows, sym)
        results_data.append((sym, stats, analysis, daily_rows))

        print(f"    [{sym}] {stats['total_trades']} islem | "
              f"WIN:{stats['wins']} BE:{stats['be']} LOSS:{stats['losses']} | "
              f"WR={stats['win_pct']:.1f}% BE+={stats['be_plus_pct']:.1f}% | "
              f"PF={stats['profit_factor']:.2f} | PnL={stats['total_pnl']:+.0f}")

        if analysis:
            fl = analysis["fail_limit"]
            fl_str = f"%{fl:.2f}" if fl is not None else "BULUNAMADI"
            print(f"\n    CBDR% Bucket Analizi (fail: {fl_str})")
            print(f"    {'Aralik%':<16} {'Gun':>4} {'Islem':>6} {'WIN':>5} {'BE':>4} {'LOSS':>5} {'WR%':>5} {'BE+%':>5} {'PnL':>10}")
            print(f"    {'-'*65}")
            for b in analysis["buckets"]:
                print(f"    {b['range']:<16} {b['days']:>4} {b['trades']:>6} {b['wins']:>5} {b['be']:>4} {b['losses']:>5} "
                      f"{b['wr']:>4.1f}% {b['be_plus_rate']:>4.1f}% {b['pnl']:>+9.0f}")

    # ── Parquet'e kaydet ve logger'i kapat (summary re-run'lari double-log yapmasin) ──
    if _LOGGER is not None:
        _LOGGER.save_and_clear()
        _LOGGER = None

    # ── Summary table (terminal) ──
    print(f"\n{'='*100}")
    print(f"  SUMMARY — {SESSION_NAME}")
    print(f"{'='*100}")
    print(f"  {'Symbol':<10} {'Trades':>7} {'WIN':>6} {'BE':>5} {'LOSS':>6} {'WR%':>6} {'BE+%':>6} {'PF':>6} {'PnL':>10}")
    print(f"  {'-'*60}")
    for sym, stats, ana, _ in results_data:
        print(f"  {sym:<10} {stats['total_trades']:>7} {stats['wins']:>6} {stats['be']:>5} {stats['losses']:>6} "
              f"{stats['win_pct']:>5.1f}% {stats['be_plus_pct']:>5.1f}% {stats['profit_factor']:>5.2f} {stats['total_pnl']:>+9.0f}")
    print(f"\n  Total time: {time.time()-t0:.0f}s")

    # ── Write MD report ──
    sname_lower = SESSION_NAME.lower()
    report_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
    os.makedirs(report_dir, exist_ok=True)
    md_path = os.path.join(report_dir, f"cbdr_{sname_lower}_report.md")

    lines = []
    sh = SESSION_HOURS['start']
    eh = SESSION_HOURS['end']
    lines.append(f"# CBDR Threshold Analysis — {SESSION_NAME} [{sh:02d}:00-{eh:02d}:00]")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Strategy:** V3 — Sweep → FVG → Entry → Trailing → Exit")
    lines.append(f"**Session:** {SESSION_NAME} [{sh:02d}:00-{eh:02d}:00]")
    lines.append("**Overlap Filter:** None — single session standalone")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Coin | Trades | WIN | BE | LOSS | WR% | BE+% | PF | MaxDD% | PnL |")
    lines.append("|" + "|".join(["-"*8, "-"*8, "-"*6, "-"*5, "-"*6, "-"*6, "-"*6, "-"*5, "-"*8, "-"*8]) + "|")
    for sym, stats, ana, _ in results_data:
        lines.append(f"| {sym:<8} | {stats['total_trades']:>6} | {stats['wins']:>4} | {stats['be']:>3} | {stats['losses']:>4} | "
                      f"{stats['win_pct']:>4.1f}% | {stats['be_plus_pct']:>4.1f}% | {stats['profit_factor']:>3.2f} | "
                      f"{stats['max_dd_pct']:>5.2f}% | {stats['total_pnl']:>+8.0f} |")
    lines.append("")

    for sym, stats, ana, daily_rows in results_data:
        lines.append(f"### {sym}")
        lines.append("")
        lines.append(f"- **Total Trades:** {stats['total_trades']}")
        lines.append(f"- **WIN/BE/LOSS:** {stats['wins']}/{stats['be']}/{stats['losses']}")
        lines.append(f"- **WR%:** {stats['win_pct']:.1f}%")
        lines.append(f"- **BE+%:** {stats['be_plus_pct']:.1f}%")
        lines.append(f"- **PF:** {stats['profit_factor']:.2f}")
        lines.append(f"- **MaxDD%:** {stats['max_dd_pct']:.2f}%")
        lines.append(f"- **Total PnL:** {stats['total_pnl']:+.0f}")
        if ana:
            fl = ana.get("fail_limit")
            fl_str = f"{fl:.2f}%" if fl is not None else "BULUNAMADI"
            lines.append(f"- **Fail Limit:** {fl_str}")
            lines.append("")
            lines.append(f"| CBDR% Araligi | Gun | Islem | WIN | BE | LOSS | WR% | BE+% | PnL |")
            lines.append(f"|{"-"*15}:|{"-"*4}:|{"-"*6}:|{"-"*5}:|{"-"*4}:|{"-"*6}:|{"-"*5}:|{"-"*5}:|{"-"*8}:|")
            for b in ana.get("buckets", []):
                lines.append(f"| {b['range']:<15} | {b['days']:>4} | {b['trades']:>6} | {b['wins']:>5} | {b['be']:>4} | {b['losses']:>6} | "
                              f"{b['wr']:>4.1f}% | {b['be_plus_rate']:>4.1f}% | {b['pnl']:>+7.0f} |")
        lines.append("")

    lines.append("---")
    lines.append(f"*Report auto-generated by `cbdr_{sname_lower}.py`*")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n  Rapor: {md_path}")


if __name__ == "__main__":
    main()
