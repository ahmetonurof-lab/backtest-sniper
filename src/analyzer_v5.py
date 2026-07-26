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
from session_router import (
    get_cbdr_multiplier,
    should_trade,
    get_session_hours,
)

# ── Komisyon ───────────────────────────────────────────────────────
COMMISSION_RATE = 0.0005  # %0.05 Binance futures taker fee (each leg)

# ─── Session ──────────────────────────────────────────────────────
SESSION_NAME = "MULTI_SESSION"
SESSION_HOURS = {"start": 22, "end": 2}

SYMBOLS_TO_TEST = [
    "BNBUSDT",
    "SOLUSDT",
    "AVAXUSDT",
    "LINKUSDT",
    "XRPUSDT",
    "ATOMUSDT",
    "ADAUSDT",
    "APTUSDT",
    "DOTUSDT",
    "NEARUSDT",
    "SUIUSDT",
]

_DATA_CACHE: dict[str, list] = {}


def load_data(filepath):
    if filepath in _DATA_CACHE:
        return _DATA_CACHE[filepath]
    t0 = time.time()
    df = pd.read_feather(filepath)
    t1 = time.time()
    ts_ms = (
        pd.to_datetime(df["open_time"], format="%Y-%m-%d %H:%M:%S")
        .values.astype("datetime64[ms]")
        .astype("int64")
    )
    n = len(df)
    bars = [None] * n
    o = df["open"].to_numpy(dtype=float)
    high_arr = df["high"].to_numpy(dtype=float)
    low_arr = df["low"].to_numpy(dtype=float)
    c = df["close"].to_numpy(dtype=float)
    v = df["volume"].to_numpy(dtype=float)
    for i in range(n):
        bars[i] = Bar(
            index=i,
            open=o[i],
            high=high_arr[i],
            low=low_arr[i],
            close=c[i],
            volume=v[i],
            is_closed=True,
            timestamp=int(ts_ms[i]),
        )
    t2 = time.time()
    print(
        f"      load_data: {n} bar {t1 - t0:.1f}s (feather) + {t2 - t1:.1f}s (bar) = {t2 - t0:.1f}s"
    )
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
        m15.append(
            Bar(
                index=len(m15),
                open=c[0].open,
                high=max(b.high for b in c),
                low=min(b.low for b in c),
                close=c[-1].close,
                volume=sum(b.volume for b in c),
                is_closed=True,
                timestamp=slot,
            )
        )
    return m15


# ─── FVG status (3-state) ───────────────────────────────
def get_fvg_status(top, bottom, direction, b):
    """
    Returns: 'INVALIDATED', 'ACTIVE_ENTRY_ZONE', or 'ALIVE'

    INVALIDATED:  Fiyat gap'in karşı tarafına close yaptı (bullish → close < bottom,
                  bearish → close > top). Bu FVG ölmüştür, pool'dan sil.
    ACTIVE_ENTRY_ZONE: Fiyat FVG gap'inin içine girdi (bar overlap). Entry sinyali.
    ALIVE:        Henüz bir şey olmadı, bekle.
    """
    if direction == "bullish":
        if b.close < bottom:
            return "INVALIDATED"
        if b.high >= bottom and b.low <= top:
            return "ACTIVE_ENTRY_ZONE"
        return "ALIVE"
    # bearish
    if b.close > top:
        return "INVALIDATED"
    if b.high >= bottom and b.low <= top:
        return "ACTIVE_ENTRY_ZONE"
    return "ALIVE"


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
            if fvg.bottom <= b.close <= fvg.top:
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
        return None, None, None, None, None


def _collect_fvg_profile_impl(symbol: str):
    # --- (coin bazli FVG expiry kalkti — yerini is_fvg_alive aldi) ---
    feather_path = os.path.join(
        os.path.dirname(__file__), "data", "daily", f"{symbol}_1m_raw.feather"
    )
    if not os.path.isfile(feather_path):
        return None, None, None, None, None

    ic = cfg.INITIAL_BALANCE
    rpt = cfg.RISK_PER_TRADE
    sam = cfg.SL_ATR_MULT
    tpr = cfg.TP_RR
    fbm = cfg.FVG_BUFFER_MULT
    ATM = cfg.ATR_TRAIL_MULT
    TMM = cfg.TRAIL_MIN_MOVE_MULT
    FVG_MIN_SIZE_ATR_MULT = cfg.FVG_MIN_SIZE_ATR_MULT

    b1 = load_data(feather_path)
    b15 = resample_15m(b1)
    if not b15:
        print(f"    [{symbol}] resample_15m bos dondu")
        return None, None, None, None, None

    print(f"    [{symbol}] {len(b1)} bar 1m -> {len(b15)} bar 15m")
    # Per-coin session from config (CBDR_RISK_MATRIX)
    _profile = cfg.CBDR_RISK_MATRIX.get(symbol, {})
    _sname = _profile.get("session", "DEFAULT")
    _sh_info = get_session_hours(symbol)
    sh = _sh_info["start"]
    eh = _sh_info["end"]
    spans_midnight = sh > eh
    ss = SessionState(start_hour=sh, end_hour=eh)
    rsm = RetraceStateMachine(max_wick_ratio=cfg.FVG_WICK_RATIO_MAX)

    day_cbdr = {}
    day_trades = defaultdict(list)
    active: list = []
    wins = []
    losses = []
    trade_records = []

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
            print(
                f"\r    [{_sname}] %{pct:.0f} ({sb}/{total_bars})", end="", flush=True
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

        if just_locked and ss.cbdr_body_high > 0 and ss.cbdr_body_low > 0:
            w = ((ss.cbdr_body_high - ss.cbdr_body_low) / ss.cbdr_body_low) * 100
            day_cbdr[ss.cbdr_day] = round(w, 4)

        if ss.sweep_confirmed and rsm.state_name == "IDLE":
            rsm.on_sweep(
                direction=ss.sweep_direction or "bullish",
                level=ss.sweep_level or 0.0,
                bar_index=None,
            )

        if rsm.state_name == "SWEEP_DETECTED":
            rsm.on_sweep_confirmed(chunk, cur, atr, symbol)

        if rsm.can_trigger() and not active:
            sd = rsm.direction
            db = ss.daily_bias
            bias_reject = (
                (sd == "bullish" and db == DailyBias.BEARISH)
                or (sd == "bearish" and db == DailyBias.BULLISH)
                or db == DailyBias.NEUTRAL
            )
            if bias_reject:
                rsm.reset()
                continue

            v4_fvg = rsm.trigger_fvg
            classic_fvg = {
                "direction": v4_fvg.direction if v4_fvg else "bullish",
                "top": v4_fvg.top if v4_fvg else 0,
                "bottom": v4_fvg.bottom if v4_fvg else 0,
                "size": (v4_fvg.top - v4_fvg.bottom) if v4_fvg else 0,
                "bar_index": None,
                "atr": atr,
                "v4_rejected": None,
            }
            classic_fvg["v4_fvg_top"] = v4_fvg.top if v4_fvg else None
            classic_fvg["v4_fvg_bottom"] = v4_fvg.bottom if v4_fvg else None

            # ── Session hours filter (CBDR hesaplanirken trade yasak) ──
            h = edt.hour
            if (h >= sh or h < eh) if spans_midnight else (sh <= h < eh):
                rsm.reset()
                continue

            # ── FIX #3: Next-bar-open entry (look-ahead bias giderildi) ──
            if sb + 1 >= total_bars:
                rsm.reset()
                continue
            next_bar = b15[sb + 1]
            side = "long" if sd == "bullish" else "short"
            ep = next_bar.open
            rp2 = atr * sam
            tf = v4_fvg

            if side == "long":
                if tf:
                    fh = tf.top - tf.bottom
                    if fh <= 0:
                        sl = ep - rp2 * 2
                    else:
                        ab = max(
                            fh * cfg.FVG_BUFFER_MIN_FACTOR,
                            max(rp2 * 0.1, min(fh * 0.25, rp2 * fbm)),
                        )
                        sl = tf.bottom - ab
                else:
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
                        ab = max(
                            fh * cfg.FVG_BUFFER_MIN_FACTOR,
                            max(rp2 * 0.1, min(fh * 0.25, rp2 * fbm)),
                        )
                        sl = tf.top + ab
                else:
                    sl = ep + rp2 * 2
                rd = abs(sl - ep)
                if rd <= 0:
                    sl = ep + rp2 * 2
                    rd = abs(sl - ep)
                tp = ep - rd * tpr

            quality_mult = 1.0
            if tf is not None:
                fvg_status = get_fvg_status(tf.top, tf.bottom, tf.direction, cur)
                if fvg_status == "INVALIDATED":
                    quality_mult = 0.0
                    classic_fvg["v4_rejected"] = "FVG_SWEPT"
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
                cbdr_w = (
                    (ss.cbdr_body_high - ss.cbdr_body_low) / ss.cbdr_body_low
                ) * 100
            cbdr_mult = (
                get_cbdr_multiplier(symbol, cbdr_w) if cbdr_w is not None else 1.0
            )
            if cbdr_mult == 0.0:
                quality_mult = 0.0
                if classic_fvg.get("v4_rejected") is None:
                    classic_fvg["v4_rejected"] = "CBDR_MULT_ZERO"

            # ── Haftasonu çarpani (config'den) ──
            _wprofile = cfg.CBDR_RISK_MATRIX.get(symbol, {})
            if quality_mult > 0 and _wprofile.get("weekend_bonus", False):
                if edt.weekday() >= 5:
                    cbdr_mult *= _wprofile.get("weekend_mult", 1.5)

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
                fvg_by_uid[trade_uid] = classic_fvg

                entry_day = ss.cbdr_day
                active.append(
                    {
                        "entry_bar": sb + 1,
                        "entry_price": ep,
                        "sl": sl,
                        "tp": tp,
                        "qty": qty,
                        "side": side,
                        "trigger_fvg": tf,
                        "initial_sl": sl,
                        "initial_tp": tp,
                        "trailing_count": 0,
                        "be_triggered": False,
                        "day_key": entry_day,
                        "trade_uid": trade_uid,
                        "cbdr_body_high": ss.cbdr_body_high,
                        "cbdr_body_low": ss.cbdr_body_low,
                    }
                )
                rsm.reset()
                continue  # ayni-bar trailing/exit calistirma
            else:
                # Filtered setup: record as rejected, reset RSM to avoid duplicate FVGs from same sweep.
                if classic_fvg["v4_rejected"] is None:
                    classic_fvg["v4_rejected"] = "QTY_ZERO"
                rejection_counts[classic_fvg["v4_rejected"]] += 1
                rsm.reset()
                continue

        # ── Trailing (unchanged) ──
        if active and cur.is_closed:
            for t in active:
                if t.get("closed"):
                    continue

            tc = chunk[:-1]
            min_mult = cfg.FVG_SIZE_MAP.get(symbol, FVG_MIN_SIZE_ATR_MULT)
            min_fvg_size = max(atr * min_mult, 1e-8)
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
                    if t.get("trailing_count", 0) > 0 and t["sl"] > t["entry_price"]:
                        t["result"] = "PROFIT_TRAIL"
                    else:
                        t["result"] = "LOSS"
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
                    if t.get("trailing_count", 0) > 0 and t["sl"] < t["entry_price"]:
                        t["result"] = "PROFIT_TRAIL"
                    else:
                        t["result"] = "LOSS"
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
                entry_fee = t["entry_price"] * t["qty"] * COMMISSION_RATE
                exit_fee = t["exit_price"] * t["qty"] * COMMISSION_RATE
                total_fee = entry_fee + exit_fee
                t["entry_fee"] = round(entry_fee, 2)
                t["exit_fee"] = round(exit_fee, 2)
                t["fee"] = round(total_fee, 2)
                t["pnl"] = round(diff * t["qty"] - total_fee, 2)
                day_trades[t.get("day_key", "")].append(t["pnl"])
                risk_usd_rec = (
                    abs(t["initial_sl"] - t["entry_price"]) * t["qty"]
                    if t["initial_sl"]
                    else 0
                )
                trade_records.append(
                    {
                        "result": t["result"],
                        "pnl": t["pnl"],
                        "fee": t["fee"],
                        "day_key": t.get("day_key", ""),
                        "risk_usd": risk_usd_rec,
                        "fvg_direction": t.get("trigger_fvg", {}).direction
                        if t.get("trigger_fvg")
                        else "",
                        "fvg_top": t.get("trigger_fvg", {}).top
                        if t.get("trigger_fvg")
                        else 0,
                        "fvg_bottom": t.get("trigger_fvg", {}).bottom
                        if t.get("trigger_fvg")
                        else 0,
                        "cbdr_body_high": t.get("cbdr_body_high", 0),
                        "cbdr_body_low": t.get("cbdr_body_low", 0),
                    }
                )
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
                    risk_usd = (
                        abs(t["initial_sl"] - t["entry_price"]) * t["qty"]
                        if t["initial_sl"]
                        else 0
                    )
                    f_["v4_real_pnl_R"] = (t["pnl"] / risk_usd) if risk_usd > 0 else 0.0
                    f_["v4_real_hit_target"] = t["result"] == "TP"
                    f_["v4_real_hit_stop"] = t["result"] in ("LOSS", "PROFIT_TRAIL")
                if _LOGGER is not None:
                    risk_usd = (
                        abs(t["initial_sl"] - t["entry_price"]) * t["qty"]
                        if t["initial_sl"]
                        else 0
                    )
                    fvg_sz = (
                        (t["trigger_fvg"].top - t["trigger_fvg"].bottom)
                        if t.get("trigger_fvg")
                        else None
                    )
                    _LOGGER.log_trade(
                        {
                            "symbol": symbol,
                            "session": _sname,
                            "side": t["side"].upper(),
                            "entry_time": edt,
                            "entry_price": round(t["entry_price"], 6),
                            "exit_price": round(t["exit_price"], 6),
                            "result": t["result"],
                            "final_pnl_usd": round(t["pnl"], 2),
                            "risk_usd": round(risk_usd, 2),
                            "r_multiple": round(t["pnl"] / risk_usd, 4)
                            if risk_usd > 0
                            else 0.0,
                            "trailing_count": t.get("trailing_count", 0),
                            "fvg_size_pips": round(fvg_sz, 6) if fvg_sz else None,
                            "atr": round(atr, 6),
                        }
                    )
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
                diff = (
                    (lp - t["entry_price"])
                    if t["side"] == "long"
                    else (t["entry_price"] - lp)
                )
                entry_fee = t["entry_price"] * t["qty"] * COMMISSION_RATE
                exit_fee = lp * t["qty"] * COMMISSION_RATE
                total_fee = entry_fee + exit_fee
                t["entry_fee"] = round(entry_fee, 2)
                t["exit_fee"] = round(exit_fee, 2)
                t["fee"] = round(total_fee, 2)
                t["pnl"] = round(diff * t["qty"] - total_fee, 2)
                day_trades[t.get("day_key", "")].append(t["pnl"])
                risk_usd_rec = (
                    abs(t["initial_sl"] - t["entry_price"]) * t["qty"]
                    if t["initial_sl"]
                    else 0
                )
                trade_records.append(
                    {
                        "result": t["result"],
                        "pnl": t["pnl"],
                        "fee": t["fee"],
                        "day_key": t.get("day_key", ""),
                        "risk_usd": risk_usd_rec,
                        "fvg_direction": t.get("trigger_fvg", {}).direction
                        if t.get("trigger_fvg")
                        else "",
                        "fvg_top": t.get("trigger_fvg", {}).top
                        if t.get("trigger_fvg")
                        else 0,
                        "fvg_bottom": t.get("trigger_fvg", {}).bottom
                        if t.get("trigger_fvg")
                        else 0,
                        "cbdr_body_high": t.get("cbdr_body_high", 0),
                        "cbdr_body_low": t.get("cbdr_body_low", 0),
                    }
                )
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
                    risk_usd = (
                        abs(t["initial_sl"] - t["entry_price"]) * t["qty"]
                        if t["initial_sl"]
                        else 0
                    )
                    f_["v4_real_pnl_R"] = (t["pnl"] / risk_usd) if risk_usd > 0 else 0.0
                    f_["v4_real_hit_target"] = t["result"] == "TP"
                    f_["v4_real_hit_stop"] = t["result"] in ("LOSS", "PROFIT_TRAIL")
                if _LOGGER is not None:
                    risk_usd = (
                        abs(t["initial_sl"] - t["entry_price"]) * t["qty"]
                        if t["initial_sl"]
                        else 0
                    )
                    fvg_sz = (
                        (t["trigger_fvg"].top - t["trigger_fvg"].bottom)
                        if t.get("trigger_fvg")
                        else None
                    )
                    _LOGGER.log_trade(
                        {
                            "symbol": symbol,
                            "session": _sname,
                            "side": t["side"].upper(),
                            "entry_time": edt,
                            "entry_price": round(t["entry_price"], 6),
                            "exit_price": round(t["exit_price"], 6),
                            "result": "OPEN",
                            "final_pnl_usd": round(t["pnl"], 2),
                            "risk_usd": round(risk_usd, 2),
                            "r_multiple": round(t["pnl"] / risk_usd, 4)
                            if risk_usd > 0
                            else 0.0,
                            "trailing_count": t.get("trailing_count", 0),
                            "fvg_size_pips": round(fvg_sz, 6) if fvg_sz else None,
                            "atr": round(atr, 6),
                        }
                    )

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
        daily_rows.append(
            {
                "day_key": dk,
                "cbdr_pct": w,
                "trades": n_trades,
                "wins": n_wins,
                "be": n_be,
                "losses": n_trades - n_wins - n_be,
                "pnl": total_pnl,
            }
        )
    print(f"    [{symbol}] Daily rows tamam ({len(daily_rows)} row)", flush=True)

    day_cbdr_cnt = len(day_cbdr)
    day_trades_cnt = len(day_trades)
    trade_cnt = len(trade_records)
    print(
        f"    [{symbol}] Tamam: {day_cbdr_cnt} gun CBDR, {day_trades_cnt} gun trade, "
        f"{trade_cnt} islem, {len(daily_rows)} daily_row",
        flush=True,
    )
    rej_str = str(dict(sorted(rejection_counts.items(), key=lambda x: x[0])))
    print(f"    [{symbol}] Red: {rej_str}", flush=True)

    return daily_rows, wins, losses, trade_records, rejection_counts


# ─── Istatistik Hesaplama ────────────────────────────────────
def compute_session_stats(trade_records, initial_balance, daily_rows=None):
    n = len(trade_records)
    if n == 0:
        return {
            "total_trades": 0,
            "tp_pct": 0,
            "profit_trail_pct": 0,
            "loss_pct": 0,
            "positive_exit_pct": 0,
            "profit_factor": 0,
            "sharpe": 0,
            "max_dd_pct": 0,
            "total_pnl": 0,
            "total_fee": 0,
            "pnl_per_fee": 0,
            "score": 0,
        }
    tp = sum(1 for r in trade_records if r["result"] == "TP")
    profit_trail = sum(1 for r in trade_records if r["result"] == "PROFIT_TRAIL")
    loss = sum(1 for r in trade_records if r["result"] in ("LOSS", "OPEN"))
    tp_pct = tp / n * 100
    profit_trail_pct = profit_trail / n * 100
    loss_pct = loss / n * 100
    positive_exit_pct = tp_pct + profit_trail_pct
    gross_profit = sum(r["pnl"] for r in trade_records if r["pnl"] > 0) or 0
    gross_loss = abs(sum(r["pnl"] for r in trade_records if r["pnl"] < 0))
    profit_factor = 999.0 if gross_loss == 0 else gross_profit / gross_loss
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
    peak_balance = initial_balance + peak
    max_dd_pct = (max_dd / peak_balance) * 100 if peak_balance > 0 else 0
    # Trade-return based Sharpe (non-annualized, RFR=0)
    trade_returns = []
    for r in trade_records:
        ru = r.get("risk_usd", 0)
        if ru > 0:
            trade_returns.append(r["pnl"] / ru)
    if len(trade_returns) > 1:
        tr_mean = sum(trade_returns) / len(trade_returns)
        tr_std = (
            sum((x - tr_mean) ** 2 for x in trade_returns) / len(trade_returns)
        ) ** 0.5
        sharpe = tr_mean / tr_std if tr_std > 0 else 0

    else:
        sharpe = 0
    total_pnl = sum(r["pnl"] for r in trade_records)
    total_fee = sum(r.get("fee", 0) for r in trade_records)
    pnl_per_fee = total_pnl / total_fee if total_fee > 0 else 0
    score = (
        (profit_factor * positive_exit_pct / 100 * pnl_per_fee)
        / (1 + max_dd_pct / 100)
        * 100
        if max_dd_pct >= 0
        else 0
    )
    return {
        "total_trades": n,
        "tp_pct": tp_pct,
        "profit_trail_pct": profit_trail_pct,
        "loss_pct": loss_pct,
        "positive_exit_pct": positive_exit_pct,
        "profit_factor": profit_factor,
        "max_dd_pct": max_dd_pct,
        "sharpe": sharpe,
        "total_pnl": total_pnl,
        "total_fee": total_fee,
        "pnl_per_fee": pnl_per_fee,
        "score": round(score),
    }


# ─── Main ─────────────────────────────────────────────────────
# ─── Worker: tek sembol analizi (paralel surec) ──────────────
def _analyze_one_sym_v5(sym: str) -> dict | None:
    """Worker: collect_fvg_profile + compute_session_stats.
    Ayri ProcessPoolExecutor worker'inda calisir."""
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    _SNIPER_SRC = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "sniper", "src"
    )
    if _SNIPER_SRC not in sys.path:
        sys.path.insert(0, _SNIPER_SRC)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    import config as cfg

    # Import engine from same module
    from analyzer_v5 import collect_fvg_profile, compute_session_stats

    try:
        result = collect_fvg_profile(sym)
        if result is None or (isinstance(result, tuple) and result[0] is None):
            return {"sym": sym, "error": "VERI YOK"}
        daily_rows, wins, losses, trade_records, rejection_counts = result
        if len(daily_rows) < 1:
            return {"sym": sym, "error": "YETERSIZ VERI"}
        stats = compute_session_stats(trade_records, cfg.INITIAL_BALANCE, daily_rows)
        return {
            "sym": sym,
            "stats": stats,
            "daily_rows": daily_rows,
            "rejection_counts": rejection_counts,
            "trade_records": trade_records,
        }
    except Exception as e:
        return {"sym": sym, "error": str(e)}


def main():
    """V5 ana rapor: Tum sembolleri isler + summary + dosya."""
    global _LOGGER
    import argparse

    parser = argparse.ArgumentParser(description="V5 backtest engine")
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Paralel worker sayisi (1=serial, default=1)",
    )
    parser.add_argument("--serial", action="store_true", help="Serial mod")
    args = parser.parse_args()

    use_serial = args.serial or args.workers <= 1
    n_workers = args.workers if not use_serial else 1

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    t0 = time.time()
    results_data = []
    all_trade_records = []

    print("=" * 100)
    print("  V5 PROFIL — CBDR→Sweep→RSM→FVG→Entry→Trail→Exit")
    print("  Live-identical backtest engine")
    if not use_serial:
        print(f"  Mod: PARALEL ({n_workers} worker)")
    print("=" * 100)

    if use_serial:
        for sym in sorted(cfg.SYMBOLS):
            try:
                profile = cfg.CBDR_RISK_MATRIX.get(sym, {})
                sname = profile.get("session", "DEFAULT")
                sh_info = get_session_hours(sym)
                print(
                    f"\n  [{sym}] Session={sname} [{sh_info['start']:02d}:00-{sh_info['end']:02d}:00]",
                    flush=True,
                )
                result = collect_fvg_profile(sym)
                if result is None or (isinstance(result, tuple) and result[0] is None):
                    print(f"    [{sym}] VERI DOSYASI YOK VEYA ERKEN CIKIS", flush=True)
                    continue
                daily_rows, wins, losses, trade_records, rejection_counts = result
                if len(daily_rows) < 1:
                    print(
                        f"    [{sym}] YETERSIZ VERI (daily_rows={len(daily_rows)})",
                        flush=True,
                    )
                    continue
                stats = compute_session_stats(
                    trade_records, cfg.INITIAL_BALANCE, daily_rows
                )
                results_data.append((sym, stats, daily_rows, rejection_counts))
                all_trade_records.extend(trade_records)
                tp_c = int(stats["tp_pct"] * stats["total_trades"] / 100)
                pt_c = int(stats["profit_trail_pct"] * stats["total_trades"] / 100)
                ls_c = int(stats["loss_pct"] * stats["total_trades"] / 100)
                print(
                    f"    [{sym}] {stats['total_trades']} islem | "
                    f"TP:{tp_c} PTrail:{pt_c} LOSS:{ls_c} | "
                    f"PE={stats['positive_exit_pct']:.1f}%"
                )
            except Exception as e:
                import traceback

                print(f"    [{sym}] HATA: {e}")
                traceback.print_exc()
                continue
    else:
        # ── Paralel mod ──
        import concurrent.futures

        syms = sorted(cfg.SYMBOLS)
        print(f"\n  {len(syms)} coin {n_workers} worker ile isleniyor...\n", flush=True)
        with concurrent.futures.ProcessPoolExecutor(max_workers=n_workers) as executor:
            fut_map = {executor.submit(_analyze_one_sym_v5, sym): sym for sym in syms}
            for future in concurrent.futures.as_completed(fut_map):
                sym = fut_map[future]
                try:
                    res = future.result()
                except Exception as e:
                    print(f"  [!] {sym}: HATA - {e}", flush=True)
                    continue
                if res is None or "error" in res:
                    msg = res.get("error", "BILINMEYEN") if res else "NONE"
                    print(f"  {sym}: {msg}", flush=True)
                    continue
                stats = res["stats"]
                results_data.append(
                    (sym, stats, res["daily_rows"], res["rejection_counts"])
                )
                all_trade_records.extend(res.get("trade_records", []))
                tp_c = int(stats["tp_pct"] * stats["total_trades"] / 100)
                pt_c = int(stats["profit_trail_pct"] * stats["total_trades"] / 100)
                ls_c = int(stats["loss_pct"] * stats["total_trades"] / 100)
                print(
                    f"  {sym}: {stats['total_trades']} islem | "
                    f"TP:{tp_c} PTrail:{pt_c} LOSS:{ls_c} | "
                    f"PE={stats['positive_exit_pct']:.1f}% net PnL={stats['total_pnl']:+0f}",
                    flush=True,
                )

    # ── Parquet ──
    if _LOGGER is not None:
        _LOGGER.save_and_clear()
        _LOGGER = None

    # ── Summary ──
    print(f"\n{'=' * 100}")
    print("  SUMMARY")
    print(f"{'=' * 100}")

    def fvg_created(rej):
        total = 0
        for k, v in rej.items():
            if not k.startswith("SHOULD_TRADE_"):
                total += v
        return total

    hdr = f"  {'Symbol':<10} {'Trades':>7} {'TP%':>6} {'PTrail%':>8} {'Loss%':>7} {'PF':>6} {'Sharpe':>7} {'MaxDD%':>7} {'Fee':>10} {'NetPnL':>10} {'PnL/Fee':>8} {'FVGCr':>6} {'FVGEnt':>6} {'MinRisk':>7} {'Score':>7}"
    print(hdr)
    print(f"  {'-' * len(hdr)}")

    for sym, stats, _, rej in results_data:
        entered = rej.get("ENTERED", 0)
        fvg_c = fvg_created(rej)
        min_risk = rej.get("MIN_RISK_DIST", 0)
        row = f"  {sym:<10} {stats['total_trades']:>7} {stats['tp_pct']:>5.1f}% {stats['profit_trail_pct']:>7.1f}% {stats['loss_pct']:>6.1f}% "
        row += f"{stats['profit_factor']:>5.2f} {stats['sharpe']:>6.3f} {stats['max_dd_pct']:>6.1f}% {stats['total_fee']:>+9.0f} {stats['total_pnl']:>+9.0f} {stats['pnl_per_fee']:>7.2f} {fvg_c:>6} {entered:>6} {min_risk:>7} {stats['score']:>6.1f}"
        print(row)

    total_trades = sum(s["total_trades"] for _, s, _, _ in results_data)
    total_pnl = sum(s["total_pnl"] for _, s, _, _ in results_data)
    total_fee_sum = sum(s["total_fee"] for _, s, _, _ in results_data)
    print(
        f"\n  TOPLAM: {total_trades} trade, Fee={total_fee_sum:+.0f}, net PnL={total_pnl:+.0f} | Sure: {time.time() - t0:.0f}s"
    )

    # ── Report file ──
    rpt_path = os.path.join(
        os.path.dirname(__file__), "..", "reports", "analyzer_v5_summary.md"
    )
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(rpt_path, "a") as f:
        f.write(f"\n---\n# analyzer_v5 Summary — {ts}\n\n")
        hdr2 = f"| {'Symbol':<10} | {'Trades':>7} | {'TP%':>6} | {'PTrail%':>8} | {'Loss%':>7} | {'PF':>6} | {'Sharpe':>7} | {'MaxDD%':>7} | {'Fee':>10} | {'NetPnL':>10} | {'PnL/Fee':>8} | {'FVGCr':>6} | {'FVGEnt':>6} | {'MinRisk':>7} | {'Score':>7} |"
        f.write(hdr2 + "\n")
        sep = "|" + "---|" * (hdr2.count("|") - 1)
        f.write(sep + "\n")
        for sym, stats, _, rej in results_data:
            entered = rej.get("ENTERED", 0)
            fvg_c = fvg_created(rej)
            min_risk = rej.get("MIN_RISK_DIST", 0)
            line = f"| {sym:<10} | {stats['total_trades']:>7} | {stats['tp_pct']:>5.1f}% | {stats['profit_trail_pct']:>7.1f}% | {stats['loss_pct']:>6.1f}% | "
            line += f"{stats['profit_factor']:>5.2f} | {stats['sharpe']:>6.3f} | {stats['max_dd_pct']:>6.1f}% | {stats['total_fee']:>+9.0f} | {stats['total_pnl']:>+9.0f} | {stats['pnl_per_fee']:>7.2f} | {fvg_c:>6} | {entered:>6} | {min_risk:>7} | {stats['score']:>6.1f} |"
            f.write(line + "\n")
        f.write(
            f"\n**TOPLAM:** {total_trades} trade, Fee={total_fee_sum:+.0f}, net PnL={total_pnl:+.0f}\n"
        )
    print(f"  Rapor: {rpt_path}")

    # ── FVG Zone + Fibonacci Analizi ──
    try:
        from fvg_zone_analyzer import (
            Trade,
            classify_trades,
            compute_zone_fibo_stats,
            generate_zone_fibo_report,
            run_holdout_validation,
            generate_holdout_report,
        )

        report_dir = os.path.join(os.path.dirname(__file__), "..", "reports")

        trades = []
        for rec in all_trade_records:
            result_map = {
                "TP": "TP",
                "PROFIT_TRAIL": "PTrail",
                "LOSS": "Loss",
                "OPEN": "Loss",
            }
            trades.append(
                Trade(
                    timestamp=float(rec.get("risk_usd", 0)),
                    fvg_direction=rec.get("fvg_direction", "bullish"),
                    fvg_top=rec.get("fvg_top", 0),
                    fvg_bottom=rec.get("fvg_bottom", 0),
                    swing_high=rec.get("cbdr_body_high", 0),
                    swing_low=rec.get("cbdr_body_low", 0),
                    result=result_map.get(rec.get("result", ""), "Loss"),
                    r_multiple=(
                        rec["pnl"] / rec["risk_usd"]
                        if rec.get("risk_usd", 0) > 0
                        else 0.0
                    ),
                    pnl=rec.get("pnl", 0),
                )
            )

        classify_trades(trades)
        stats = compute_zone_fibo_stats(trades)
        fibo_report = generate_zone_fibo_report(stats)
        fibo_path = os.path.join(report_dir, "fvg_zone_fibo_analysis.md")
        os.makedirs(report_dir, exist_ok=True)
        with open(fibo_path, "w", encoding="utf-8") as f:
            f.write(fibo_report)
        print("  [FVG Zone] Fiyat bölgesi + Fibonacci analizi raporu yazıldı")

        h_result = run_holdout_validation(trades)
        holdout_report = generate_holdout_report(h_result)
        holdout_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "docs",
            "fibo_zone_holdout_validation.md",
        )
        os.makedirs(os.path.dirname(holdout_path), exist_ok=True)
        with open(holdout_path, "a", encoding="utf-8") as f:
            f.write("\n" + holdout_report)
        print(
            f"  [Holdout] Doğrulama: validated={h_result.validated} "
            f"reason={h_result.reason}"
        )
    except Exception as e:
        print(f"  [FVG Zone] Rapor olusturma hatasi: {e}")


if __name__ == "__main__":
    main()
