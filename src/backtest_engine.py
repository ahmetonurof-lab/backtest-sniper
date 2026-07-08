"""
backtest_engine.py — V5 backtest engine: live-identical trade motoru.
"""
# ruff: noqa: E402, E702
import math
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

import pandas as pd

os.environ["SNIPER_OUTPUT_DIR"] = os.path.join(os.path.dirname(__file__), "..", "output")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_SNIPER_SRC = os.path.join(os.path.dirname(__file__), "..", "..", "sniper", "src")
if _SNIPER_SRC not in sys.path:
    sys.path.insert(0, _SNIPER_SRC)

import config as cfg
# --- V5 overrides ---
cfg.MIN_REL_FVG_THRESHOLD = 0.40  # gap/ATR eşiği 0.50→0.40 (fee drag koruması)
# Coin bazli expiry, _collect_fvg_profile_impl icinde set edilecek
# ---
from fvg import detect_fvgs
from indicators import calculate_true_range, update_atr
from models import Bar
from retrace_state import RetraceStateMachine
from session import DailyBias, SessionState
from session_router import get_cbdr_multiplier, should_trade, is_high_quality_fvg, is_fvg_valid, get_session_hours
from quant_logger import QuantLogger

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ─── Session ──────────────────────────────────────────────────────
SESSION_NAME = "MULTI_SESSION"
SESSION_HOURS = {'start': 22, 'end': 2}

SYMBOLS_TO_TEST = [
    'BTCUSDT', 'BNBUSDT', 'SOLUSDT', 'AVAXUSDT', 'LINKUSDT', 'XRPUSDT',
    'ATOMUSDT', 'ADAUSDT', 'APTUSDT', 'DOTUSDT', 'NEARUSDT', 'ETHUSDT', 'SUIUSDT'
]

_DATA_CACHE: dict[str, list] = {}

def load_data(filepath):
    if filepath in _DATA_CACHE:
        return _DATA_CACHE[filepath]
    t0 = time.time()
    df = pd.read_csv(filepath, usecols=["open_time", "open", "high", "low", "close", "volume"])
    t1 = time.time()
    ts_ms = pd.to_datetime(df["open_time"], format="%Y-%m-%d %H:%M:%S").values.astype("datetime64[ms]").astype("int64")
    n = len(df)
    bars = [None] * n
    o = df["open"].to_numpy(dtype=float)
    h = df["high"].to_numpy(dtype=float)
    l = df["low"].to_numpy(dtype=float)
    c = df["close"].to_numpy(dtype=float)
    v = df["volume"].to_numpy(dtype=float)
    for i in range(n):
        bars[i] = Bar(index=i, open=o[i], high=h[i], low=l[i], close=c[i],
                      volume=v[i], is_closed=True, timestamp=int(ts_ms[i]))
    t2 = time.time()
    print(f"      load_data: {n} bar {t1-t0:.1f}s (csv) + {t2-t1:.1f}s (bar) = {t2-t0:.1f}s")
    _DATA_CACHE[filepath] = bars
    return bars


def resample_15m(bars_1m):
    # BUG 13 FIX: Timestamp bazlı hizalama — veri 00:07'den başlıyorsa naif range()
    # yaklaşımı 00:07, 00:22, ... üretir; doğrusu 00:00, 00:15, 00:30 slot'larıdır
    _15M_MS = 15 * 60 * 1000  # 15 dakika milisaniye cinsinden
    buckets: dict = {}
    for b in bars_1m:
        slot = (b.timestamp // _15M_MS) * _15M_MS  # timestamp'i 15m sınırına yuvarla
        if slot not in buckets:
            buckets[slot] = []
        buckets[slot].append(b)
    m15 = []
    for slot in sorted(buckets):
        c = buckets[slot]
        if len(c) < 15:
            continue  # Eksik veri → bu 15m bar'ı atla
        m15.append(Bar(index=len(m15), open=c[0].open,
                       high=max(b.high for b in c), low=min(b.low for b in c),
                       close=c[-1].close, volume=sum(b.volume for b in c),
                       is_closed=True, timestamp=slot))
    return m15


# ─── FVG close-confirmed helper (trailing için) ─────────
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
            return True
    return False


_LOGGER = None


def collect_fvg_profile(symbol: str):
    """V4 engine (live-identical) + captures every trigger-ready FVG with profiling data."""
    try:
        return _collect_fvg_profile_impl(symbol)
    except Exception as e:
        import traceback
        print(f"    [{symbol}] collect_fvg_profile CRASH: {e}")
        traceback.print_exc()
        return None, None, None, None


def _collect_fvg_profile_impl(symbol: str):
    # --- V5: coin bazli FVG expiry ---
    _EXPIRY_MAP = {"BTCUSDT": 45, "BNBUSDT": 45, "SOLUSDT": 45}
    cfg.GLOBAL_FVG_EXPIRY_BARS = _EXPIRY_MAP.get(symbol, 5)
    # ---
    csv_path = os.path.join(os.path.dirname(__file__), "data", "daily", f"{symbol}_1m_raw.csv")
    if not os.path.isfile(csv_path):
        return None, None, None, None

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
        print(f"    [{symbol}] resample_15m bos dondu")
        return None, None, None, None

    print(f"    [{symbol}] {len(b1)} bar 1m -> {len(b15)} bar 15m")
    # Per-coin session from config (CBDR_RISK_MATRIX)
    _profile = cfg.CBDR_RISK_MATRIX.get(symbol, {})
    _sname = _profile.get("session", "DEFAULT")
    _sh_info = get_session_hours(symbol)
    sh = _sh_info['start']
    eh = _sh_info['end']
    spans_midnight = sh > eh
    ss = SessionState(start_hour=sh, end_hour=eh)
    rsm = RetraceStateMachine(max_wick_ratio=cfg.FVG_WICK_RATIO_MAX)

    day_cbdr = {}
    day_trades = defaultdict(list)
    active = []
    wins = []
    losses = []
    trade_records = []

    # Profiling: captured FVG population
    captured_fvgs = []
    fvg_by_uid = {}
    rejection_counts: dict = defaultdict(int)

    atr_val = 0.0
    prev_close = b15[0].open
    for bar in b15[1:500]:
        tr = calculate_true_range(bar, prev_close)
        if atr_val == 0.0:
            atr_val = tr  # BUG 14 FIX: İlk değer için update_atr(None) kullanma, TR ile seed et
        else:
            atr_val = update_atr(atr_val, tr)
        prev_close = bar.close


    total_bars = len(b15)
    for sb in range(500, total_bars):
        if (sb - 500) % 5000 == 0:
            pct = (sb - 500) / (total_bars - 500) * 100
            print(f"\r    [{_sname}] %{pct:.0f} ({sb}/{total_bars})", end="", flush=True)
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

        if just_locked and ss.cbdr_body_high > 0 and ss.cbdr_body_low > 0:
            w = ((ss.cbdr_body_high - ss.cbdr_body_low) / ss.cbdr_body_low) * 100
            day_cbdr[ss.cbdr_day] = round(w, 4)

        if ss.sweep_confirmed and rsm.state_name == "IDLE":
            rsm.on_sweep(direction=ss.sweep_direction or "bullish",
                         level=ss.sweep_level or 0.0, bar_index=None)

        if rsm.state_name == "SWEEP_DETECTED":
            old_state = rsm.state_name
            rsm.on_sweep_confirmed(chunk, cur, atr)
            if rsm.state_name == "TRIGGER_READY":
                pass # Triggered
            # We can print if sweep is detected but no trigger

        if rsm.can_trigger() and not active:
            sd = rsm.direction
            db = ss.daily_bias
            bias_reject = (sd == "bullish" and db == DailyBias.BEARISH) or \
                          (sd == "bearish" and db == DailyBias.BULLISH) or \
                          db == DailyBias.NEUTRAL
            if bias_reject:
                rsm.reset()
                continue
            
            h = edt.hour

            v4_fvg = rsm.trigger_fvg
            classic_fvg = {
                "direction": v4_fvg.direction if v4_fvg else "bullish",
                "top": v4_fvg.top if v4_fvg else 0,
                "bottom": v4_fvg.bottom if v4_fvg else 0,
                "size": (v4_fvg.top - v4_fvg.bottom) if v4_fvg else 0,
                "bar_index": sb,
                "atr": atr,
                "v4_rejected": None,
            }
            classic_fvg["v4_fvg_top"] = v4_fvg.top if v4_fvg else None
            classic_fvg["v4_fvg_bottom"] = v4_fvg.bottom if v4_fvg else None

            # ── Session hours filter (matches analyzer_v4.py) ──
            h = edt.hour
            if (h >= sh or h < eh) if spans_midnight else (sh <= h < eh):
                rsm.reset()
                continue

            # ── ORIGINAL ENTRY LOGIC (unchanged from analyzer_v4) ──
            side = "long" if sd == "bullish" else "short"
            ep = cur.close
            rp2 = atr * sam
            tf = v4_fvg

            if side == "long":
                if tf:
                    fh = tf.top - tf.bottom
                    if fh <= 0:
                        sl = ep - rp2 * 2
                    else:
                        ab = max(fh * cfg.FVG_BUFFER_MIN_FACTOR, max(rp2 * 0.1, min(fh * 0.25, rp2 * fbm)))
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
                        ab = max(fh * cfg.FVG_BUFFER_MIN_FACTOR, max(rp2 * 0.1, min(fh * 0.25, rp2 * fbm)))
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

            # ── FVG quality filter ──
            quality_mult = 1.0
            if tf is not None:
                if not is_high_quality_fvg(tf.top - tf.bottom, atr):
                    quality_mult = 0.0
                    classic_fvg["v4_rejected"] = "FVG_QUALITY"
                elif not is_fvg_valid(tf.bar_index, cur.index):
                    quality_mult = 0.0
                    classic_fvg["v4_rejected"] = "FVG_VALIDITY"
                else:
                    classic_fvg["v4_rejected"] = None

            # ── Min risk dist ──
            if rd < atr * cfg.MIN_RISK_DIST_ATR_MULT:
                quality_mult = 0.0
                if classic_fvg.get("v4_rejected") is None:
                    classic_fvg["v4_rejected"] = "MIN_RISK_DIST"

            # ── CBDR + should_trade ──
            cbdr_w = None
            if ss.cbdr_body_low > 0 and not math.isinf(ss.cbdr_body_low):
                cbdr_w = ((ss.cbdr_body_high - ss.cbdr_body_low) / ss.cbdr_body_low) * 100
            cbdr_mult = get_cbdr_multiplier(symbol, cbdr_w) if cbdr_w is not None else 1.0
            if cbdr_mult == 0.0:
                quality_mult = 0.0
                if classic_fvg.get("v4_rejected") is None:
                    classic_fvg["v4_rejected"] = "CBDR_MULT_ZERO"

            # ── V5: Haftasonu çarpani (ATOM/SUI/APT) ──
            if quality_mult > 0 and symbol in ("ATOMUSDT", "SUIUSDT", "APTUSDT"):
                if edt.weekday() >= 5:  # Cumartesi=5, Pazar=6
                    cbdr_mult *= 1.5

            allowed, reason = should_trade(symbol, cbdr_width_pct=cbdr_w)
            if not allowed:
                quality_mult = 0.0
                if classic_fvg.get("v4_rejected") is None:
                    classic_fvg["v4_rejected"] = f"SHOULD_TRADE_{reason}"

            # ── Risk carpani: EL (1.5x) + CBDR Matrix ──
            h = edt.hour
            el_mult = cfg.EARLY_LONDON_RISK_MULT if 2 <= h < 8 else 1.0
            final_mult = el_mult * cbdr_mult * quality_mult

            qty = (ic * rpt * final_mult) / rd if rd > 0 else 0
            
            # --- FIX: Only enter if quality/validity checks passed (qty > 0)
            # Do NOT reset RSM if we just failed a quality filter, 
            # allow RSM to continue hunting for the next FVG in this sweep.
            if qty > 0:
                # ── ENTERED ──
                classic_fvg["v4_rejected"] = "ENTERED"
                classic_fvg["v4_entry_price"] = ep
                classic_fvg["v4_sl"] = sl
                classic_fvg["v4_tp"] = tp
                classic_fvg["v4_qty"] = qty
                classic_fvg["v4_side"] = side
                trade_uid = f"{symbol}_{sb}_{side}"
                classic_fvg["trade_uid"] = trade_uid
                classic_fvg["v4_cbdr_mult"] = cbdr_mult
                classic_fvg["v4_final_mult"] = final_mult
                rejection_counts[classic_fvg["v4_rejected"]] += 1
                captured_fvgs.append(classic_fvg)
                fvg_by_uid[trade_uid] = classic_fvg

                entry_day = ss.cbdr_day
                active.append({"entry_bar": sb, "entry_price": ep, "sl": sl, "tp": tp,
                               "qty": qty, "side": side, "trigger_fvg": tf,
                               "initial_sl": sl, "initial_tp": tp, "trailing_count": 0,
                               "day_key": entry_day, "trade_uid": trade_uid})
                rsm.reset()
            else:
                # Filtered setup: record as rejected, reset RSM to avoid duplicate FVGs from same sweep.
                if classic_fvg["v4_rejected"] is None:
                    classic_fvg["v4_rejected"] = "QTY_ZERO"
                rejection_counts[classic_fvg["v4_rejected"]] += 1
                captured_fvgs.append(classic_fvg)
                rsm.reset()
                continue

        # ── Trailing (unchanged) ──
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
                # ── Gerçek sonucu FVG objesine geri yaz ──
                uid = t.get("trade_uid")
                if uid and uid in fvg_by_uid:
                    f_ = fvg_by_uid[uid]
                    f_["v4_real_result"] = t["result"]
                    f_["v4_real_pnl_usd"] = t["pnl"]
                    risk_usd = abs(t["initial_sl"] - t["entry_price"]) * t["qty"] if t["initial_sl"] else 0
                    f_["v4_real_pnl_R"] = (t["pnl"] / risk_usd) if risk_usd > 0 else 0.0
                    f_["v4_real_hit_target"] = (t["result"] == "TP")
                    f_["v4_real_hit_stop"] = (t["result"] == "SL")
                if _LOGGER is not None:
                    risk_usd = abs(t["initial_sl"] - t["entry_price"]) * t["qty"] if t["initial_sl"] else 0
                    fvg_sz = (t["trigger_fvg"].top - t["trigger_fvg"].bottom) if t.get("trigger_fvg") else None
                    _LOGGER.log_trade({"symbol": symbol, "session": _sname, "side": t["side"].upper(),
                        "entry_time": edt, "entry_price": round(t["entry_price"], 6),
                        "exit_price": round(t["exit_price"], 6), "result": t["result"],
                        "final_pnl_usd": round(t["pnl"], 2), "risk_usd": round(risk_usd, 2),
                        "r_multiple": round(t["pnl"] / risk_usd, 4) if risk_usd > 0 else 0.0,
                        "trailing_count": t.get("trailing_count", 0),
                        "fvg_size_pips": round(fvg_sz, 6) if fvg_sz else None, "atr": round(atr, 6),})
            else:
                sa.append(t)
        active = sa

    # ── Open trades ──
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
                # ── Gerçek sonucu FVG objesine geri yaz ──
                uid = t.get("trade_uid")
                if uid and uid in fvg_by_uid:
                    f_ = fvg_by_uid[uid]
                    f_["v4_real_result"] = t["result"]
                    f_["v4_real_pnl_usd"] = t["pnl"]
                    risk_usd = abs(t["initial_sl"] - t["entry_price"]) * t["qty"] if t["initial_sl"] else 0
                    f_["v4_real_pnl_R"] = (t["pnl"] / risk_usd) if risk_usd > 0 else 0.0
                    f_["v4_real_hit_target"] = (t["result"] == "TP")
                    f_["v4_real_hit_stop"] = (t["result"] == "SL")
                if _LOGGER is not None:
                    risk_usd = abs(t["initial_sl"] - t["entry_price"]) * t["qty"] if t["initial_sl"] else 0
                    fvg_sz = (t["trigger_fvg"].top - t["trigger_fvg"].bottom) if t.get("trigger_fvg") else None
                    _LOGGER.log_trade({"symbol": symbol, "session": _sname, "side": t["side"].upper(),
                        "entry_time": edt, "entry_price": round(t["entry_price"], 6),
                        "exit_price": round(t["exit_price"], 6), "result": "OPEN",
                        "final_pnl_usd": round(t["pnl"], 2), "risk_usd": round(risk_usd, 2),
                        "r_multiple": round(t["pnl"] / risk_usd, 4) if risk_usd > 0 else 0.0,
                        "trailing_count": t.get("trailing_count", 0),
                        "fvg_size_pips": round(fvg_sz, 6) if fvg_sz else None, "atr": round(atr, 6),})

    print(f"\r    [{_sname}] %100 ({total_bars}/{total_bars})", flush=True)


    # ── Daily rows ──
    daily_rows = []
    all_keys = sorted(set(list(day_cbdr.keys()) + list(day_trades.keys())))
    print(f"    [{symbol}] Daily rows basliyor... ({len(all_keys)} key)", flush=True)
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
            "day_key": dk, "cbdr_pct": w, "trades": n_trades,
            "wins": n_wins, "be": n_be, "losses": n_trades - n_wins - n_be, "pnl": total_pnl,
        })
    print(f"    [{symbol}] Daily rows tamam ({len(daily_rows)} row)", flush=True)

    day_cbdr_cnt = len(day_cbdr)
    day_trades_cnt = len(day_trades)
    trade_cnt = len(trade_records)
    fvg_cnt = len(captured_fvgs)
    atr_vals = [b.high - b.low for b in b15]
    print(f"    [{symbol}] Tamam: {day_cbdr_cnt} gun CBDR, {day_trades_cnt} gun trade, "
          f"{trade_cnt} islem, {fvg_cnt} FVG, {len(daily_rows)} daily_row", flush=True)
    if day_cbdr_cnt < 3 and fvg_cnt > 0:
        rej_str = str(dict(sorted(rejection_counts.items(), key=lambda x: x[0])))
        print(f"    [{symbol}] CBDR AZ {rej_str}", flush=True)
    if len(daily_rows) < 3:
        print(f"    [{symbol}] daily_rows={len(daily_rows)} < 3, atlaniyor!"
              f" day_cbdr={day_cbdr_cnt} day_trades={day_trades_cnt} trades={trade_cnt} fvgs={fvg_cnt}")

    return daily_rows, wins, losses, trade_records


# ─── Istatistik Hesaplama ────────────────────────────────────
def compute_session_stats(trade_records, initial_balance):
    n = len(trade_records)
    if n == 0:
        return {'total_trades': 0, 'wins': 0, 'be': 0, 'losses': 0, 'win_pct': 0, 'be_plus_pct': 0, 'profit_factor': 0, 'max_dd_pct': 0, 'avg_mae': 0, 'total_pnl': 0}
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


# ─── Main ─────────────────────────────────────────────────────
def main():
    t0 = time.time()

    print("=" * 100)
    print("  FVG PROFILE V5 Engine")
    print("  Engine: V4 (live-identical) — Sweep -> RSM -> Quality -> Entry -> Trailing")
    print(f"  Coinler: {', '.join(SYMBOLS_TO_TEST)}")
    print("=" * 100)

    # QuantLogger (same as analyzer_v4)
    parquet_path = os.path.join(os.path.dirname(__file__), "..", "reports", "trades_multi_session.parquet")
    global _LOGGER
    _LOGGER = QuantLogger(parquet_path)

    results_data = []

    for sym in SYMBOLS_TO_TEST:
        try:
            profile = cfg.CBDR_RISK_MATRIX.get(sym, {})
            sname = profile.get("session", "DEFAULT")
            sh_info = get_session_hours(sym)
            print(f"\n  [{sym}] Session={sname} [{sh_info['start']:02d}:00-{sh_info['end']:02d}:00] Profil basliyor...", flush=True)
            result = collect_fvg_profile(sym)
            if result is None or (isinstance(result, tuple) and result[0] is None):
                print(f"    [{sym}] VERI DOSYASI YOK VEYA ERKEN CIKIS", flush=True)
                continue
            daily_rows, wins, losses, trade_records = result
            if len(daily_rows) < 1:
                print(f"    [{sym}] YETERSIZ VERI (daily_rows={len(daily_rows)})", flush=True)
                continue

            stats = compute_session_stats(trade_records, cfg.INITIAL_BALANCE)
            results_data.append((sym, stats, None, daily_rows, []))

            print(f"    [{sym}] {stats['total_trades']} islem | "
                  f"WIN:{stats['wins']} BE:{stats['be']} LOSS:{stats['losses']} | "
                  f"WR={stats['win_pct']:.1f}%")
        except Exception as e:
            import traceback
            print(f"    [{sym}] HATA: {e}")
            traceback.print_exc()
            continue

    # ── Parquet ──
    if _LOGGER is not None:
        _LOGGER.save_and_clear()
        _LOGGER = None

    # ── Summary ──
    print(f"\n{'='*100}")
    print(f"  SUMMARY")
    print(f"{'='*100}")
    print(f"  {'Symbol':<10} {'Trades':>7} {'WIN':>6} {'BE':>5} {'LOSS':>6} {'WR%':>6} {'BE+%':>6} {'PF':>6} {'PnL':>10} {'FVG':>6}")
    print(f"  {'-'*70}")
    for sym, stats, _, _, fvgs in results_data:
        print(f"  {sym:<10} {stats['total_trades']:>7} {stats['wins']:>6} {stats['be']:>5} {stats['losses']:>6} "
              f"{stats['win_pct']:>5.1f}% {stats['be_plus_pct']:>5.1f}% {stats['profit_factor']:>5.2f} {stats['total_pnl']:>+9.0f} {len(fvgs):>6d}")
    print(f"\n  Total time: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()

