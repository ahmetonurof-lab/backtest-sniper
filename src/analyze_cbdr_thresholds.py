"""
analyze_cbdr_thresholds.py — Coin bazinda CBDR range esigi analizi.
ICT Real CBDR (19:00-01:00 UTC) kullanir.
Her gun icin CBDR genisligi % + o gunku trade sonuclari.
"""
# ruff: noqa: E402, E702 — path manipulation requires late imports;
# semicolons are pre-existing legacy style, kept for minimal diff.
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
from session_router import is_high_quality_fvg, get_cbdr_multiplier, should_trade

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ─── Session configs ───────────────────────────────────────────────
# Her session kendi start/end saatleriyle izole state'te calisir.
# Canli SessionState kullanilir (IctRangeState kopyasi kaldirildi).
SESSION_CONFIGS = {
    'REAL_CBDR':   {'start': 19, 'end': 1},   # ICT Real CBDR
    'DEFAULT':     {'start': 22, 'end': 2},   # Senin default saatlerin
    'ASIA_RANGE':  {'start': 1,  'end': 5},    # Asya seansi
}


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
    """CSV'den bar verisini yukle. Timestamp UTC normalize edilir (DST koruma).
    @lru_cache: ayni dosya 2. kez istenince direkt memory'den doner."""
    bars = []
    with open(filepath, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            # UTC normalize: replace(tzinfo=timezone.utc) ile DST kaymasi engellenir
            ts = int(datetime.strptime(row["open_time"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp() * 1000)
            bars.append(Bar(index=i, open=float(row["open"]), high=float(row["high"]),
                            low=float(row["low"]), close=float(row["close"]),
                            volume=float(row["volume"]), is_closed=True, timestamp=ts))
    return bars


def resample_15m(bars_1m):
    """1m bar'lari 15m bar'a donustur."""
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


# ─── FVG status (3-state, analyzer_v5 ile ayni) ──────────
def get_fvg_status(top, bottom, direction, b):
    if direction == "bullish":
        if b.low < bottom:
            return "INVALIDATED"
        if b.low <= top:
            return "ACTIVE_ENTRY_ZONE"
        return "ALIVE"
    if b.high > top:
        return "INVALIDATED"
    if b.high >= bottom:
        return "ACTIVE_ENTRY_ZONE"
    return "ALIVE"


def collect_daily_data(symbol: str, session_name: str = 'REAL_CBDR', session_hours: dict = None):
    """
    Run CBDR backtest for a specific session config.
    session_hours: {'start': int, 'end': int} — SessionState'a parametre olarak gecer.
    Her session kendi izole state'iyle calisir, global state karismaz.
    Canli sniper/src/session.py'deki SessionState kullanilir (IctRangeState kopyasi yok).
    Return: (daily_rows, wins, losses, trade_records)
    trade_records: overlap filtrelemesi icin her trade'in unique ID'sini icerir.
    """
    if session_hours is None:
        session_hours = {'start': 19, 'end': 1}
    # Veri: data/daily/{symbol}_1m_raw.csv — raw 1m verisi
    csv_path = os.path.join(os.path.dirname(__file__), "data", "daily", f"{symbol}_1m_raw.csv")
    if not os.path.isfile(csv_path):
        return None
    data_path = csv_path

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

    # load_data @lru_cache sayesinde 2./3. session'da ayni coin icin
    # diskten tekrar okumaz, direkt memory'den doner.
    b1 = load_data(data_path)
    b15 = resample_15m(b1)
    if not b15:
        return None

    # Canli SessionState — her session kendi saatleriyle izole (IctRangeState kopyasi kaldirildi)
    sh = session_hours['start']
    eh = session_hours['end']
    spans_midnight = sh > eh
    ss = SessionState(start_hour=sh, end_hour=eh)
    rsm = RetraceStateMachine(max_wick_ratio=cfg.FVG_WICK_RATIO_MAX)

    day_cbdr = {}
    day_trades = defaultdict(list)
    active = []
    wins = []
    losses = []
    trade_records = []  # overlap filtrelemesi icin her trade'in unique ID + pnl kaydi
    rejection_counts: dict = defaultdict(int)

    atr_val: float = 0.0
    prev_close: float = b15[0].open
    for bar in b15[1:500]:
        tr = calculate_true_range(bar, prev_close)
        atr_val = update_atr(atr_val if atr_val > 0 else None, tr)
        prev_close = bar.close

    total_bars = len(b15)
    for sb in range(500, total_bars):
        # Ilerleme gostergesi: her 5000 bar'da bir nokta bas
        if (sb - 500) % 5000 == 0:
            pct = (sb - 500) / (total_bars - 500) * 100
            print(f"\r    [{session_name}] %{pct:.0f} ({sb}/{total_bars})", end="", flush=True)
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
            # _in_window: spans_midnight mantigi (SessionState ile uyumlu)
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

            # ── FVG quality filter (analyzer_v5 ile ayni) ──
            quality_mult = 1.0
            if tf is not None:
                if not is_high_quality_fvg(tf.top - tf.bottom, atr):
                    quality_mult = 0.0
                    rejection_counts["FVG_QUALITY"] += 1
                else:
                    fvg_status = get_fvg_status(tf.top, tf.bottom, tf.direction, cur)
                    if fvg_status == "INVALIDATED":
                        quality_mult = 0.0
                        rejection_counts["FVG_SWEPT"] += 1

            # ── Min risk dist ──
            if rd < atr * cfg.MIN_RISK_DIST_ATR_MULT:
                quality_mult = 0.0
                rejection_counts["MIN_RISK_DIST"] += 1

            # ── CBDR + should_trade ──
            cbdr_w = None
            if ss.cbdr_body_low > 0 and not math.isinf(ss.cbdr_body_low):
                cbdr_w = ((ss.cbdr_body_high - ss.cbdr_body_low) / ss.cbdr_body_low) * 100
            cbdr_mult = get_cbdr_multiplier(symbol, cbdr_w) if cbdr_w is not None else 1.0
            if cbdr_mult == 0.0:
                quality_mult = 0.0
                rejection_counts["CBDR_MULT_ZERO"] += 1

            # ── Weekend bonus (ATOM/SUI/APT) ──
            if quality_mult > 0 and symbol in ("ATOMUSDT", "SUIUSDT", "APTUSDT"):
                if edt.weekday() >= 5:
                    cbdr_mult *= 1.5

            allowed, reason = should_trade(symbol, cbdr_width_pct=cbdr_w)
            if not allowed:
                quality_mult = 0.0
                rejection_counts[f"SHOULD_TRADE_{reason}"] += 1

            # ── Risk carpani: EL (1.5x) + CBDR Matrix ──
            el_mult = cfg.EARLY_LONDON_RISK_MULT if 2 <= edt.hour < 8 else 1.0
            final_mult = el_mult * cbdr_mult * quality_mult

            qty = (ic * rpt * final_mult) / rd if rd > 0 else 0
            if qty <= 0:
                rejection_counts["QTY_ZERO"] += 1
                rsm.reset()
                continue

            entry_day = ss.cbdr_day
            trade_id = f"{session_name}_{entry_day}_{sb}"  # unique trade ID (session + gun + bar index)
            rejection_counts["ENTERED"] += 1
            active.append({"entry_bar": sb, "entry_price": ep, "sl": sl, "tp": tp,
                           "qty": qty, "side": side, "trigger_fvg": tf,
                           "initial_sl": sl, "initial_tp": tp, "trailing_count": 0,
                           "day_key": entry_day, "trade_id": trade_id})
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
                # Overlap filtrelemesi icin trade record'u sakla
                trade_records.append({"trade_id": t.get("trade_id", ""), "pnl": t["pnl"], "result": t["result"]})
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
                diff = (lp - t["entry_price"]) if t["side"] == "long" else (t["entry_price"] - lp)
                t["pnl"] = round(diff * t["qty"], 2)
                day_trades[t.get("day_key", "")].append(t["pnl"])
                # Overlap filtrelemesi icin trade record'u sakla
                trade_records.append({"trade_id": t.get("trade_id", ""), "pnl": t["pnl"], "result": t["result"]})
                if t["pnl"] > 0:
                    wins.append(t)
                else:
                    losses.append(t)

    # Ilerleme satirini temizle
    print(f"\r    [{session_name}] %100 ({total_bars}/{total_bars})", flush=True)
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
        daily_rows.append({
            "day_key": dk,
            "cbdr_pct": w,
            "trades": n_trades,
            "wins": n_wins,
            "pnl": total_pnl,
        })
    return daily_rows, wins, losses, trade_records, rejection_counts


def analyze_thresholds(daily_rows, symbol: str, min_bucket_trades: int = 100):
    valid = [d for d in daily_rows if d["cbdr_pct"] is not None and d["trades"] > 0]
    if len(valid) < 5:
        return None

    valid.sort(key=lambda x: x["cbdr_pct"])
    n = len(valid)

    bucket_size = max(1, n // 5)
    buckets = []
    for i in range(0, n, bucket_size):
        bucket = valid[i:min(i + bucket_size, n)]
        if not bucket:
            break
        bt = sum(d["trades"] for d in bucket)
        bwins = sum(d["wins"] for d in bucket)
        bp = sum(d["pnl"] for d in bucket)
        buckets.append({
            "lo_pct": bucket[0]["cbdr_pct"],
            "hi_pct": bucket[-1]["cbdr_pct"],
            "range": f"{bucket[0]['cbdr_pct']:.2f}-{bucket[-1]['cbdr_pct']:.2f}",
            "days": len(bucket),
            "trades": bt,
            "wins": bwins,
            "wr": round(bwins / bt * 100, 1) if bt > 0 else 0,
            "pnl": round(bp, 2),
        })

    total_trades = sum(d["trades"] for d in valid)
    total_wins = sum(d["wins"] for d in valid)
    overall_wr = total_wins / total_trades if total_trades > 0 else 0

    fail_limit = None
    for i, b in enumerate(buckets):
        if b["trades"] < min_bucket_trades:
            continue
        if wilson_upper(b["wins"], b["trades"]) >= overall_wr:
            continue
        remaining = buckets[i:]
        sig_count = 0
        for r in remaining:
            if r["trades"] >= min_bucket_trades and wilson_upper(r["wins"], r["trades"]) < overall_wr:
                sig_count += 1
                if sig_count >= 3:
                    excluded = sum(r2["trades"] for r2 in buckets if r2["lo_pct"] >= b["lo_pct"])
                    if excluded <= 0.80 * total_trades:
                        fail_limit = b["lo_pct"]
                    break
            else:
                break
        if fail_limit is not None:
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
    """Bir session'daki unique trade listesinden istatistik hesapla."""
    n = len(trade_records)
    if n == 0:
        return {'total_trades': 0, 'win_pct': 0, 'profit_factor': 0, 'max_dd_pct': 0, 'avg_mae': 0}
    wins = sum(1 for r in trade_records if r[2] > 0)
    win_pct = wins / n * 100 if n > 0 else 0

    gross_profit = sum(r[2] for r in trade_records if r[2] > 0) or 0
    gross_loss = abs(sum(r[2] for r in trade_records if r[2] < 0)) or 1e-9
    profit_factor = gross_profit / gross_loss

    cumulative = 0
    peak = 0
    max_dd = 0
    for _, _, pnl, _ in trade_records:
        cumulative += pnl
        if cumulative > peak:
            peak = cumulative
        dd = peak - cumulative
        if dd > max_dd:
            max_dd = dd
    max_dd_pct = (max_dd / initial_balance) * 100 if initial_balance > 0 else 0

    losses_list = [r[2] for r in trade_records if r[2] < 0]
    avg_mae = abs(sum(losses_list) / len(losses_list)) if losses_list else 0
    total_pnl = sum(r[2] for r in trade_records)

    return {'total_trades': n, 'win_pct': win_pct, 'profit_factor': profit_factor,
            'max_dd_pct': max_dd_pct, 'avg_mae': avg_mae, 'total_pnl': total_pnl}


def run_session_analysis(sym: str):
    """Tek bir sembol icin tum session'lari calistir, overlap filtrele, karsilastir."""
    t0 = time.time()

    # 1. Adim: Her session'u ayri ayri calistir (izole state)
    all_trade_records = []  # (trade_id, session_name, pnl, result)
    session_raw_data = {}   # session_name -> raw data for threshold analysis

    for sname, shours in SESSION_CONFIGS.items():
        try:
            result = collect_daily_data(
                sym, session_name=sname, session_hours=shours
            )
            if result is None:
                print(f"    [{sname}] VERI DOSYASI YOK", flush=True)
                continue
            daily_rows, wins, losses, trade_records, rejection_counts = result
            if len(daily_rows) < 3:
                print(f"    [{sname}] YETERSIZ VERI", flush=True)
                continue
            session_raw_data[sname] = {
                'daily_rows': daily_rows, 'wins': wins, 'losses': losses,
                'trade_records': trade_records, 'rejection_counts': rejection_counts,
            }
            for tr in trade_records:
                all_trade_records.append((tr['trade_id'], sname, tr['pnl'], tr['result']))
            rej_str = str(dict(sorted(rejection_counts.items(), key=lambda x: x[0])))
            print(f"    [{sname}] {len(daily_rows)} gun, {len(trade_records)} islem OK", flush=True)
            print(f"    [{sname}] Red: {rej_str}", flush=True)
        except Exception as e:
            print(f"    [{sname}] HATA: {e} — atlaniyor, diger session'lara devam", flush=True)
            continue

    if not session_raw_data:
        print(f"  [{sym}] HICBIR SESSION CALISMADI", flush=True)
        return None

    # 2. Adim: Overlap filtrele — ayni bar_index (sb) sadece ilk session'a sayilsin
    # trade_id = {session_name}_{entry_day}_{sb}
    # overlap_key = sb (bar index) — hangi session olursa olsun ayni bardaki trade tek sayilir
    seen_overlap = set()
    unique_trade_records = []
    for tid, sname, pnl, result in all_trade_records:
        overlap_key = tid.rsplit('_', 1)[-1]  # sb (bar index)
        if overlap_key not in seen_overlap:
            seen_overlap.add(overlap_key)
            unique_trade_records.append((tid, sname, pnl, result))
        # duplicate ise atlanir — sadece ilk session sayilir

    # 3. Adim: Session istatistiklerini hesapla (unique trade'ler uzerinden)
    session_names_ordered = [s for s in SESSION_CONFIGS if s in session_raw_data]
    stats_rows = []
    total_all_trades = 0
    total_unique_trades = 0
    for sname in session_names_ordered:
        session_trades = [r for r in unique_trade_records if r[1] == sname]
        raw_trades = session_raw_data[sname]['trade_records']
        stats = compute_session_stats(session_trades, cfg.INITIAL_BALANCE)
        stats['session'] = sname
        stats['total_trades_raw'] = len(raw_trades)  # overlap oncesi
        stats['unique_trades'] = stats['total_trades']  # overlap sonrasi
        stats_rows.append(stats)
        total_all_trades += len(raw_trades)
        total_unique_trades += stats['total_trades']

    # 4. Adim: Karsilastirmali tabloyu bas
    print(f"\n  ┌─ [{sym}] Multi-Session Karsilastirma ──────────────────────────────────────┐")
    print(f"  │ {'Session':<14} {'Total':>7} {'Unique':>7} {'Win%':>7} {'PF':>7} {'MaxDD%':>8} {'AvgMAE':>9} {'PnL':>10} │")
    print(f"  ├{'─'*14}┼{'─'*7}┼{'─'*7}┼{'─'*7}┼{'─'*7}┼{'─'*8}┼{'─'*9}┼{'─'*10}┤")
    for st in stats_rows:
        print(f"  │ {st['session']:<14} {st['total_trades_raw']:>7} {st['unique_trades']:>7} "
              f"{st['win_pct']:>5.1f}% {st['profit_factor']:>5.2f} "
              f"{st['max_dd_pct']:>6.2f}% {st['avg_mae']:>7.2f} {st['total_pnl']:>+8.0f} │")
    print(f"  └{'─'*14}┴{'─'*7}┴{'─'*7}┴{'─'*7}┴{'─'*7}┴{'─'*8}┴{'─'*9}┴{'─'*10}┘")
    print(f"  Toplam: {total_all_trades} raw trade, {total_unique_trades} unique trade "
          f"({time.time()-t0:.0f}s)", flush=True)

    # 5. Adim: Her session icin CBDR genisligi bucket analizi (Wilson score)
    threshold_results = {}
    for sname in session_names_ordered:
        daily_rows = session_raw_data[sname]['daily_rows']
        analysis = analyze_thresholds(daily_rows, sym)
        if analysis is None:
            continue
        threshold_results[sname] = analysis
        fl = analysis["fail_limit"]
        fl_str = f"%{fl:.2f}" if fl is not None else "BULUNAMADI"
        wil_str = "✓" if analysis.get("wilson_found") else "—"
        print(f"\n  [{sym}] {sname} — CBDR% Bucket Analizi (fail limit: {fl_str}, Wilson: {wil_str})")
        print(f"  {'Aralik%':<18} {'Gun':>4} {'Islem':>6} {'WR%':>6} {'PnL':>10}")
        print(f"  {'-'*48}")
        for b in analysis["buckets"]:
            print(f"  {b['range']:<18} {b['days']:>4} {b['trades']:>6} {b['wr']:>5.1f}% {b['pnl']:>+9.0f}")

    return session_raw_data, unique_trade_records, threshold_results


def main():
    t0 = time.time()
    all_session_results = {}

    print("=" * 120)
    print("  CBDR ESIK ANALIZI — Multi-Session Karsilastirmali")
    print(f"  Session'lar: {', '.join(SESSION_CONFIGS.keys())}")
    print("=" * 120)

    for sym in sorted(cfg.SYMBOLS):
        print(f"\n  [{sym}] Session analizi basliyor...", flush=True)

        result = run_session_analysis(sym)
        if result is None:
            continue
        all_session_results[sym] = result  # (session_raw, unique_trades, threshold_results)

    # ── Ozet CSV & MD rapor ──
    report_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
    os.makedirs(report_dir, exist_ok=True)

    csv_path = os.path.join(report_dir, "ict_cbdr_thresholds.csv")
    md_path = os.path.join(report_dir, "ict_cbdr_thresholds.md")

    # Session bazinda CSV satirlari
    csv_rows = []
    for sym in sorted(all_session_results):
        session_raw, unique_trades, threshold_results = all_session_results[sym]
        for sname in SESSION_CONFIGS:
            if sname not in session_raw:
                continue
            session_trades = [r for r in unique_trades if r[1] == sname]
            stats = compute_session_stats(session_trades, cfg.INITIAL_BALANCE)
            thr = threshold_results.get(sname, {})
            csv_rows.append({
                'Coin': sym, 'Session': sname,
                'Total_Trades_Raw': len(session_raw[sname]['trade_records']),
                'Unique_Trades': stats['total_trades'],
                'Win%': round(stats['win_pct'], 1),
                'Profit_Factor': round(stats['profit_factor'], 2),
                'MaxDD%': round(stats['max_dd_pct'], 2),
                'Avg_MAE': round(stats['avg_mae'], 2),
                'PnL': round(stats['total_pnl'], 0),
                'Fail_Limit': f"{thr['fail_limit']:.2f}%" if thr.get('fail_limit') else 'BULUNAMADI',
                'Wilson': thr.get('wilson_found', False),
            })

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=['Coin', 'Session', 'Total_Trades_Raw', 'Unique_Trades',
                                           'Win%', 'Profit_Factor', 'MaxDD%', 'Avg_MAE', 'PnL',
                                           'Fail_Limit', 'Wilson'])
        w.writeheader()
        w.writerows(csv_rows)
    print(f"\n  CSV rapor: {csv_path}")

    # MD rapor
    lines = []
    lines.append("# ICT CBDR Threshold Analysis — Multi-Session Comparison")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("**Strategy:** V5 — Sweep → RSM → Quality (FVG size + sweep) → CBDR Mult → EL → Entry")
    lines.append(f"**Session Configs:** {', '.join(SESSION_CONFIGS.keys())}")
    lines.append("**Overlap Filter:** Active — same (day, bar_index) counted only in first session")
    lines.append("")
    lines.append("## Multi-Session Comparison Table")
    lines.append("")
    lines.append("| Coin | Session | Total Raw | Unique | Win% | PF | MaxDD% | Avg MAE | PnL | Fail Limit | Wilson |")
    lines.append("|" + "|".join(["-"*8, "-"*10, "-"*11, "-"*8, "-"*6, "-"*5, "-"*8, "-"*9, "-"*8, "-"*13, "-"*8]) + "|")
    for row in csv_rows:
        lines.append(f"| {row['Coin']:<8} | {row['Session']:<10} | {row['Total_Trades_Raw']:>9} | "
                      f"{row['Unique_Trades']:>6} | {row['Win%']:>4.1f}% | {row['Profit_Factor']:>3.2f} | "
                      f"{row['MaxDD%']:>6.2f}% | {row['Avg_MAE']:>7.2f} | {row['PnL']:>+8.0f} | "
                      f"{row['Fail_Limit']:>10} | {'✓' if row['Wilson'] else '—':>3} |")
    lines.append("")

    for sym in sorted(all_session_results):
        session_raw, unique_trades, threshold_results = all_session_results[sym]
        for sname in SESSION_CONFIGS:
            if sname not in session_raw:
                continue
            session_trades = [r for r in unique_trades if r[1] == sname]
            stats = compute_session_stats(session_trades, cfg.INITIAL_BALANCE)
            lines.append(f"### {sym} — {sname}")
            lines.append("")
            lines.append(f"- **Total Trades (raw):** {len(session_raw[sname]['trade_records'])}")
            lines.append(f"- **Unique Trades:** {stats['total_trades']}")
            lines.append(f"- **Win%:** {stats['win_pct']:.1f}%")
            lines.append(f"- **Profit Factor:** {stats['profit_factor']:.2f}")
            lines.append(f"- **MaxDD%:** {stats['max_dd_pct']:.2f}%")
            lines.append(f"- **Avg MAE:** {stats['avg_mae']:.2f}")
            lines.append(f"- **Total PnL:** {stats['total_pnl']:+.0f}")
            thr = threshold_results.get(sname, {})
            if thr:
                fl_str = f"{thr['fail_limit']:.2f}%" if thr.get('fail_limit') else 'BULUNAMADI'
                wil_str = '✓' if thr.get('wilson_found') else '—'
                lines.append(f"- **Fail Limit:** {fl_str} (Wilson: {wil_str})")
                lines.append("")
                lines.append(f"| CBDR% Araligi | Gun | Islem | WR% | PnL |")
                lines.append(f"|{'-'*14}:|{'-'*4}:|{'-'*6}:|{'-'*5}:|{'-'*8}:|")
                for b in thr.get("buckets", []):
                    lines.append(f"| {b['range']:<14} | {b['days']:>4} | {b['trades']:>6} | {b['wr']:>4.1f}% | {b['pnl']:>+7.0f} |")
            lines.append("")

    lines.append("---")
    lines.append("*Report auto-generated by `analyze_cbdr_thresholds.py`*")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  MD rapor: {md_path}")
    print(f"\n  Toplam sure: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
