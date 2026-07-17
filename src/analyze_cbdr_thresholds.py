"""
analyze_cbdr_thresholds.py — Coin bazinda CBDR range esigi analizi.
ICT Real CBDR (19:00-01:00 UTC) kullanir.
Her gun icin CBDR genisligi % + o gunku trade sonuclari.
"""

# ruff: noqa: E402, E702 — path manipulation requires late imports;
# semicolons are pre-existing legacy style, kept for minimal diff.
import argparse
import calendar
import csv
import functools
import math
import os
import re
import sys
import time
import pandas as pd
from collections import defaultdict
from datetime import datetime, timezone

os.environ["SNIPER_OUTPUT_DIR"] = os.path.join(
    os.path.dirname(__file__), "..", "output"
)
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)
_SNIPER_SRC = os.path.join(_THIS_DIR, "..", "..", "sniper", "src")
if _SNIPER_SRC not in sys.path:
    sys.path.insert(0, _SNIPER_SRC)

from fvg import detect_fvgs
from indicators import calculate_true_range, update_atr
from models import Bar
from retrace_state import RetraceStateMachine
from session import DailyBias, SessionState


import config as cfg  # noqa: E402 — tek kaynak, _cfg kopyasi kaldirildi


def get_cbdr_multiplier(symbol: str, cbdr_pct: float) -> float:
    profile = cfg.CBDR_RISK_MATRIX.get(symbol)
    if not profile:
        return 1.0
    for lo, hi, mult in profile["buckets"]:
        if lo <= cbdr_pct < hi:
            return mult
    return 1.0


def should_trade(symbol: str, cbdr_width_pct: float | None = None) -> tuple[bool, str]:
    profile = cfg.CBDR_RISK_MATRIX.get(symbol)
    if profile is None:
        return True, ""  # sıfırdan test: matrix'te yoksa her CBDR'ye izin ver
    if cbdr_width_pct is not None:
        cbdr_mult = get_cbdr_multiplier(symbol, cbdr_width_pct)
        if cbdr_mult == 0.0:
            return (
                False,
                symbol
                + " CBDR="
                + f"{cbdr_width_pct:.2f}%"
                + " Zehirli Bolge (mult=0.0)",
            )
    return True, ""


# ─── Session configs ───────────────────────────────────────────────
# Her session kendi start/end saatleriyle izole state'te calisir.
# Canli SessionState kullanilir (IctRangeState kopyasi kaldirildi).
SESSION_CONFIGS = {
    "REAL_CBDR": {"start": 19, "end": 1},
    "DEFAULT": {"start": 22, "end": 2},
    "ASIA_RANGE": {"start": 1, "end": 5},
}

FVG_SIZE_MAP_FILES = {
    sname: os.path.join(
        os.path.dirname(__file__), "..", "reports", f"fvg_profile_{sname}.md"
    )
    for sname in SESSION_CONFIGS
}


def _parse_fvg_size_from_md(filepath: str) -> dict[str, float] | None:
    if not os.path.isfile(filepath):
        return None
    result = {}
    with open(filepath, encoding="utf-8") as f:
        in_block = False
        for line in f:
            s = line.strip()
            if s.startswith("```python"):
                in_block = True
                continue
            if in_block and s.startswith("```"):
                break
            if in_block:
                m = re.match(r'\s*"(\w+USDT)":\s*([\d.]+)', s)
                if m:
                    result[m.group(1)] = float(m.group(2))
    return result if result else None


# ─── Wilson Score CI ───────────────────────────────────────────
def wilson_upper(wins: int, trades: int, z: float = 1.96) -> float:
    if trades == 0:
        return 1.0
    z2 = z * z
    p_hat = wins / trades
    denominator = 1 + z2 / trades
    centre = p_hat + z2 / (2 * trades)
    margin = z * math.sqrt((p_hat * (1 - p_hat) + z2 / (4 * trades)) / trades)
    return min(1.0, (centre + margin) / denominator)


def wilson_lower(wins: int, trades: int, z: float = 1.96) -> float:
    if trades == 0:
        return 0.0
    z2 = z * z
    p_hat = wins / trades
    denominator = 1 + z2 / trades
    centre = p_hat + z2 / (2 * trades)
    margin = z * math.sqrt((p_hat * (1 - p_hat) + z2 / (4 * trades)) / trades)
    return max(0.0, (centre - margin) / denominator)


# ─── CBDR Bucket Esigi Analizi ─────────────────────────────────
_BUCKET_LABEL_MAP = {
    (0.0, 1.0): "0-1%",
    (1.0, 1.5): "1-1.5%",
    (1.5, 2.0): "1.5-2%",
    (2.0, 3.0): "2-3%",
    (3.0, 5.0): "3-5%",
    (5.0, 999.0): ">5%",
}


def _bucket_label(lo: float, hi: float) -> str:
    for (blo, bhi), lbl in _BUCKET_LABEL_MAP.items():
        if abs(lo - blo) < 0.01 and abs(hi - bhi) < 0.01:
            return lbl
    return f"{lo:.1f}-{hi:.1f}%"


def analyze_thresholds(daily_rows, symbol: str, min_bucket_trades: int = 100):
    valid = [d for d in daily_rows if d["cbdr_pct"] is not None and d["trades"] > 0]
    if len(valid) < 5:
        return None
    valid.sort(key=lambda x: x["cbdr_pct"])
    n = len(valid)
    bucket_size = max(1, n // 5)
    buckets = []
    for i in range(0, n, bucket_size):
        bucket = valid[i : min(i + bucket_size, n)]
        if not bucket:
            break
        bt = sum(d["trades"] for d in bucket)
        bwins = sum(d["wins"] for d in bucket)
        bp = sum(d["pnl"] for d in bucket)
        buckets.append(
            {
                "lo_pct": bucket[0]["cbdr_pct"],
                "hi_pct": bucket[-1]["cbdr_pct"],
                "range": f"{bucket[0]['cbdr_pct']:.2f}-{bucket[-1]['cbdr_pct']:.2f}",
                "days": len(bucket),
                "trades": bt,
                "wins": bwins,
                "wr": round(bwins / bt * 100, 1) if bt > 0 else 0,
                "pnl": round(bp, 2),
            }
        )
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
            if (
                r["trades"] >= min_bucket_trades
                and wilson_upper(r["wins"], r["trades"]) < overall_wr
            ):
                sig_count += 1
                if sig_count >= 3:
                    excluded = sum(
                        r2["trades"] for r2 in buckets if r2["lo_pct"] >= b["lo_pct"]
                    )
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


def analyze_bucket_scaling(
    daily_rows: list[dict], symbol: str, min_bucket_trades: int = 100
) -> dict:
    profile = cfg.CBDR_RISK_MATRIX.get(symbol)
    if not profile:
        return None
    matrix_buckets = profile.get("buckets", [])
    if not matrix_buckets:
        return None
    valid = [d for d in daily_rows if d["cbdr_pct"] is not None]
    if not valid:
        return None
    bucket_data: dict = defaultdict(lambda: {"trades": 0, "wins": 0})
    for d in valid:
        cbdr_w = d["cbdr_pct"]
        for lo, hi, _mult in matrix_buckets:
            if lo <= cbdr_w < hi:
                bucket_data[(lo, hi)]["trades"] += d.get("trades", 0)
                bucket_data[(lo, hi)]["wins"] += d.get("wins", 0)
                break
    bucket_stats = []
    for lo, hi, mult in matrix_buckets:
        bd = bucket_data.get((lo, hi), {"trades": 0, "wins": 0})
        n = bd["trades"]
        w = bd["wins"]
        wr = w / n if n > 0 else 0.0
        bucket_stats.append(
            {
                "lo": lo,
                "hi": hi,
                "mult": mult,
                "label": _bucket_label(lo, hi),
                "trades": n,
                "wins": w,
                "wr": round(wr * 100, 1),
                "wilson_upper": round(wilson_upper(w, n) * 100, 1),
                "wilson_lower": round(wilson_lower(w, n) * 100, 1),
            }
        )
    qualifying = [b for b in bucket_stats if b["trades"] >= min_bucket_trades]
    comparisons = []
    divergent_count = 0
    for i in range(len(qualifying)):
        for j in range(i + 1, len(qualifying)):
            bi, bj = qualifying[i], qualifying[j]
            ci_i_lo, ci_i_hi = bi["wilson_lower"] / 100.0, bi["wilson_upper"] / 100.0
            ci_j_lo, ci_j_hi = bj["wilson_lower"] / 100.0, bj["wilson_upper"] / 100.0
            overlap = not (ci_j_hi < ci_i_lo or ci_j_lo > ci_i_hi)
            verdict = "FARK YOK" if overlap else "ANLAMLI FARK VAR"
            if not overlap:
                divergent_count += 1
            comparisons.append(
                {
                    "bucket_a": bi["label"],
                    "bucket_b": bj["label"],
                    "n_a": bi["trades"],
                    "n_b": bj["trades"],
                    "wr_a": bi["wr"],
                    "wr_b": bj["wr"],
                    "ci_overlap": "Evet" if overlap else "Hayır",
                    "verdict": verdict,
                }
            )
    return {
        "symbol": symbol,
        "bucket_stats": bucket_stats,
        "comparisons": comparisons,
        "divergent_pairs": divergent_count,
        "total_qualifying_buckets": len(qualifying),
        "summary": (
            f"{divergent_count}/{len(comparisons)} bucket cifti birbirinden ayrisiyor"
            if comparisons
            else "Yeterli bucket yok (n>=100)"
        ),
    }


def _make_bar(idx, op, hi, lo, cl, vo, ts):
    bar = object.__new__(Bar)
    object.__setattr__(bar, "index", idx)
    object.__setattr__(bar, "open", op)
    object.__setattr__(bar, "high", hi)
    object.__setattr__(bar, "low", lo)
    object.__setattr__(bar, "close", cl)
    object.__setattr__(bar, "volume", vo)
    object.__setattr__(bar, "is_closed", True)
    object.__setattr__(bar, "timestamp", ts)
    return bar


@functools.lru_cache(maxsize=32)
def load_data(filepath):
    """CSV veya Feather'den bar verisini yukle."""
    if filepath.endswith(".feather"):
        df = pd.read_feather(filepath)
        df.columns = [c.strip() for c in df.columns]
        o = df["open"].to_numpy(dtype=float)
        ha = df["high"].to_numpy(dtype=float)
        la = df["low"].to_numpy(dtype=float)
        c = df["close"].to_numpy(dtype=float)
        v = df["volume"].to_numpy(dtype=float)
        ts_ms = (
            pd.to_datetime(df["open_time"], format="%Y-%m-%d %H:%M:%S")
            .values.astype("datetime64[ms]")
            .astype("int64")
        )
        ts_list = ts_ms.tolist()
        return [
            _make_bar(i, o[i], ha[i], la[i], c[i], v[i], ts_list[i])
            for i in range(len(df))
        ]
    bars = []
    with open(filepath, encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        for i, row in enumerate(reader):
            ts_str = row[0]
            year = int(ts_str[0:4])
            month = int(ts_str[5:7])
            day = int(ts_str[8:10])
            hour = int(ts_str[11:13])
            minute = int(ts_str[14:16])
            second = int(ts_str[17:19])
            ts = int(calendar.timegm((year, month, day, hour, minute, second)) * 1000)
            bars.append(
                Bar(
                    index=i,
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[5]),
                    is_closed=True,
                    timestamp=ts,
                )
            )
    return bars


def resample_15m(bars_1m):
    """1m bar'lari 15m bar'a donustur.
    @lru_cache: ayni bar listesi 2. kez istenince tekrar hesaplama."""
    return _resample_15m_impl(tuple(bars_1m))


@functools.lru_cache(maxsize=32)
def _resample_15m_impl(bars_tuple):
    """Timestamp-bazli 15m resample (analyzer_v5 ile ayni).
    15m slot'larina kure göre grupla, eksik dilimleri atla."""
    _15M_MS = 15 * 60 * 1000
    buckets = {}
    for b in bars_tuple:
        slot = (b.timestamp // _15M_MS) * _15M_MS
        if slot not in buckets:
            buckets[slot] = []
        buckets[slot].append(b)
    m15 = []
    for slot in sorted(buckets):
        c = buckets[slot]
        if len(c) < 15:
            continue
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


def collect_daily_data(
    symbol: str,
    session_name: str = "REAL_CBDR",
    session_hours: dict = None,
    quiet: bool = False,
):
    """
    Run CBDR backtest for a specific session config.
    session_hours: {'start': int, 'end': int} — SessionState'a parametre olarak gecer.
    Her session kendi izole state'iyle calisir, global state karismaz.
    Canli sniper/src/session.py'deki SessionState kullanilir (IctRangeState kopyasi yok).
    Return: (daily_rows, wins, losses, trade_records)
    trade_records: overlap filtrelemesi icin her trade'in unique ID'sini icerir.
    quiet: True ise progress print'leri atlanir (paralel mod icin).
    """
    if session_hours is None:
        session_hours = {"start": 19, "end": 1}
    # Veri: data/daily/{symbol}_1m_raw.feather — raw 1m verisi
    feather_path = os.path.join(
        os.path.dirname(__file__), "data", "daily", f"{symbol}_1m_raw.feather"
    )
    if not os.path.isfile(feather_path):
        return None
    data_path = feather_path

    ic = cfg.INITIAL_BALANCE
    rpt = cfg.RISK_PER_TRADE
    sam = cfg.SL_ATR_MULT
    tpr = cfg.TP_RR
    fbm = cfg.FVG_BUFFER_MULT
    ATM = cfg.ATR_TRAIL_MULT
    TMM = cfg.TRAIL_MIN_MOVE_MULT
    FVG_MIN_SIZE_ATR_MULT = cfg.FVG_MIN_SIZE_ATR_MULT
    COMMISSION_RATE = 0.0005  # %0.05 Binance futures taker fee (each leg)

    # load_data @lru_cache sayesinde 2./3. session'da ayni coin icin
    # diskten tekrar okumaz, direkt memory'den doner.
    b1 = load_data(data_path)
    if not quiet:
        print(f"    [{session_name}] {len(b1)} bar, ", end="", flush=True)
    b15 = resample_15m(b1)
    if not b15:
        return None

    # Canli SessionState — her session kendi saatleriyle izole (IctRangeState kopyasi kaldirildi)
    sh = session_hours["start"]
    eh = session_hours["end"]
    spans_midnight = sh > eh
    ss = SessionState(start_hour=sh, end_hour=eh)
    rsm = RetraceStateMachine(max_wick_ratio=cfg.FVG_WICK_RATIO_MAX)

    day_cbdr = {}
    day_trades = defaultdict(list)
    active: list = []
    wins = []
    losses = []
    trade_records = []  # overlap filtrelemesi icin her trade'in unique ID + pnl kaydi
    rejection_counts: dict = defaultdict(int)

    atr_val: float = 0.0
    prev_close: float = b15[0].open
    for bar in b15[1:500]:
        tr = calculate_true_range(bar, prev_close)
        if atr_val == 0.0:
            atr_val = tr
        else:
            atr_val = update_atr(atr_val, tr)
        prev_close = bar.close

    total_bars = len(b15)
    for sb in range(500, total_bars):
        if not quiet and (sb - 500) % 5000 == 0:
            pct = (sb - 500) / (total_bars - 500) * 100
            print(
                f"\r    [{session_name}] %{pct:.0f} ({sb}/{total_bars})",
                end="",
                flush=True,
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
            if (
                (sd == "bullish" and db == DailyBias.BEARISH)
                or (sd == "bearish" and db == DailyBias.BULLISH)
                or db == DailyBias.NEUTRAL
            ):
                rsm.reset()
                continue
            h = edt.hour
            if (h >= sh or h < eh) if spans_midnight else (sh <= h < eh):
                rsm.reset()
                continue

            # ── Next-bar-open entry (look-ahead bias giderildi) ──
            if sb + 1 >= total_bars:
                rsm.reset()
                continue
            next_bar = b15[sb + 1]
            side = "long" if sd == "bullish" else "short"
            ep = next_bar.open
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

            # ── FVG quality filter (analyzer_v5 ile ayni) ──
            quality_mult = 1.0
            if tf is not None:
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
                cbdr_w = (
                    (ss.cbdr_body_high - ss.cbdr_body_low) / ss.cbdr_body_low
                ) * 100
            cbdr_mult = (
                get_cbdr_multiplier(symbol, cbdr_w) if cbdr_w is not None else 1.0
            )
            if cbdr_mult == 0.0:
                quality_mult = 0.0
                rejection_counts["CBDR_MULT_ZERO"] += 1

            # ── Haftasonu çarpani (config'den) ──
            _wprofile = cfg.CBDR_RISK_MATRIX.get(symbol, {})
            if quality_mult > 0 and _wprofile.get("weekend_bonus", False):
                if edt.weekday() >= 5:
                    cbdr_mult *= _wprofile.get("weekend_mult", 1.5)

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
                    "trade_id": trade_id,
                }
            )
            rsm.reset()
            continue  # ayni-bar trailing/exit calistirma

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
                trade_records.append(
                    {
                        "trade_id": t.get("trade_id", ""),
                        "pnl": t["pnl"],
                        "result": t["result"],
                        "fee": t.get("fee", 0),
                    }
                )
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
                trade_records.append(
                    {
                        "trade_id": t.get("trade_id", ""),
                        "pnl": t["pnl"],
                        "result": t["result"],
                        "fee": t.get("fee", 0),
                    }
                )
                if t["pnl"] > 0:
                    wins.append(t)
                else:
                    losses.append(t)

    if not quiet:
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
        daily_rows.append(
            {
                "day_key": dk,
                "cbdr_pct": w,
                "trades": n_trades,
                "wins": n_wins,
                "pnl": total_pnl,
            }
        )
    return daily_rows, wins, losses, trade_records, rejection_counts


def compute_session_stats(trade_records, initial_balance):
    n = len(trade_records)
    if n == 0:
        return {
            "total_trades": 0,
            "tp_pct": 0,
            "profit_trail_pct": 0,
            "positive_exit_pct": 0,
            "profit_factor": 0,
            "max_dd_pct": 0,
            "total_pnl": 0,
            "total_fee": 0,
            "pnl_per_fee": 0,
            "score": 0,
        }
    tp = sum(1 for r in trade_records if r["result"] == "TP")
    profit_trail = sum(1 for r in trade_records if r["result"] == "PROFIT_TRAIL")
    tp_pct = tp / n * 100
    profit_trail_pct = profit_trail / n * 100
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
        "positive_exit_pct": positive_exit_pct,
        "profit_factor": profit_factor,
        "max_dd_pct": max_dd_pct,
        "total_pnl": total_pnl,
        "total_fee": total_fee,
        "pnl_per_fee": pnl_per_fee,
        "score": round(score),
    }


def run_session_analysis(sym: str, session_name: str, session_hours: dict):
    try:
        result = collect_daily_data(
            sym, session_name=session_name, session_hours=session_hours
        )
        if result is None:
            return None
        daily_rows, wins, losses, trade_records, rejection_counts = result
        if len(daily_rows) < 3:
            return None
        stats = compute_session_stats(trade_records, cfg.INITIAL_BALANCE)
        return {
            "symbol": sym,
            "session": session_name,
            "daily_rows": daily_rows,
            "trade_records": trade_records,
            "stats": stats,
            "rejection_counts": rejection_counts,
        }
    except Exception as e:
        print(f"    [{session_name}/{sym}] HATA: {e}", flush=True)
        import traceback

        traceback.print_exc()
        return None


def main():
    parser = argparse.ArgumentParser(description="Per-session FVG size backtest")
    parser.add_argument(
        "--symbols",
        nargs="*",
        default=None,
        help="Belirli semboller (default: cfg.SYMBOLS tamami)",
    )
    parser.add_argument(
        "--workers", type=int, default=1, help="Paralel worker sayisi (1=serial)"
    )
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    t0 = time.time()

    # Onceki raporu temizle (her calistirmada sifirdan basla)
    _old_md = os.path.join(
        os.path.dirname(__file__), "..", "reports", "session_analysis.md"
    )
    if os.path.isfile(_old_md):
        os.remove(_old_md)
        print(f"[TEMIZLIK] Eski rapor silindi: {_old_md}", flush=True)

    # Parse FVG size maps from .md files
    fvg_size_maps = {}
    for sname, md_path in FVG_SIZE_MAP_FILES.items():
        fvg_map = _parse_fvg_size_from_md(md_path)
        if fvg_map is None:
            print(f"[UYARI] {sname} FVG size map bulunamadi: {md_path}", flush=True)
            continue
        fvg_size_maps[sname] = fvg_map
        print(f"[FVG] {sname}: {len(fvg_map)} coin FVG size yuklendi", flush=True)

    if not fvg_size_maps:
        print("[HATA] Hicbir FVG size map yuklenemedi")
        return

    symbols = args.symbols if args.symbols else sorted(cfg.SYMBOLS)
    all_results = {}

    for sname in sorted(fvg_size_maps):
        sh = SESSION_CONFIGS.get(sname)
        if not sh:
            continue
        sh_str = f"{sh['start']:02d}:00-{sh['end']:02d}:00 UTC"
        print(f"\n{'=' * 100}")
        print(f"  SESSION: {sname} ({sh_str})")
        print(f"  Symbols: {len(symbols)}, Workers: {args.workers}")
        print(f"{'=' * 100}")

        _orig_fvg_map = getattr(cfg, "FVG_SIZE_MAP", {}).copy()
        cfg.FVG_SIZE_MAP = fvg_size_maps[sname].copy()

        report_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
        os.makedirs(report_dir, exist_ok=True)
        md_path = os.path.join(report_dir, "session_analysis.md")

        # Session header (her session basinda bir kere)
        header_lines = []
        if not os.path.isfile(md_path):
            header_lines.append("# Session Analysis — Per-Session FVG Size Backtest")
            header_lines.append("")
            header_lines.append(
                f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            header_lines.append(
                "**Strategy:** V5 — Sweep → RSM → Quality → FVG size → CBDR Mult → EL → Entry"
            )
            header_lines.append("")
        header_lines.append(f"## {sname} ({sh_str})")
        header_lines.append("")
        header_lines.append(
            "| Symbol | FVG Size | Trades | TP% | PTrail% | PE% | PF | DD% | PnL | Fee | PnL/Fee | Score |"
        )
        header_lines.append(
            "|--------|----------|-------|-----|---------|-----|----|-----|-----|-----|---------|-------|"
        )
        mode = "a" if os.path.isfile(md_path) else "w"
        with open(md_path, mode, encoding="utf-8") as f:
            f.write("\n".join(header_lines) + "\n")
        print(f"[RAPOR] {sname} header -> {md_path}", flush=True)

        session_results = []
        for sym in symbols:
            if sym not in cfg.FVG_SIZE_MAP:
                print(f"    [{sname}] {sym}: FVG size yok, atlaniyor", flush=True)
                continue
            fvg_size = cfg.FVG_SIZE_MAP[sym]
            res = run_session_analysis(sym, sname, sh)
            if res is None:
                print(f"    [{sname}] {sym}: VERI YOK veya YETERSIZ", flush=True)
                continue
            session_results.append(res)
            st = res["stats"]
            daily_rows = res["daily_rows"]
            line = (
                f"| {sym:<8} | {fvg_size:.3f} | {st['total_trades']:>5} | "
                f"{st['tp_pct']:>4.1f}% | {st['profit_trail_pct']:>5.1f}% | "
                f"{st['positive_exit_pct']:>4.1f}% | {st['profit_factor']:>4.2f} | "
                f"{st['max_dd_pct']:>4.1f}% | {st['total_pnl']:>+7.0f} | "
                f"{st['total_fee']:>+7.0f} | {st['pnl_per_fee']:>5.2f} | {st['score']:>5.0f} |"
            )

            # Per-coin bucket detayi (console + MD)
            thr = analyze_thresholds(daily_rows, sym)
            bs = analyze_bucket_scaling(daily_rows, sym)
            bucket_lines = [line]
            if thr:
                fl = thr.get("fail_limit")
                fl_str = f"{fl:.2f}%" if fl is not None else "—"
                bucket_lines.append("")
                bucket_lines.append("| Analiz | Deger |")
                bucket_lines.append("|--------|------|")
                bucket_lines.append(f"| Wilson WR | {thr['overall_wr']:.1f}% |")
                bucket_lines.append(f"| Fail Limit | {fl_str} |")
                bucket_lines.append(f"| Total Trades | {thr['total_trades']} |")
            if bs and bs["bucket_stats"]:
                bucket_lines.append("")
                bucket_lines.append("| Bucket | Trades | PE% | Wilson CI 95% |")
                bucket_lines.append("|--------|-------|-----|---------------|")
                for b in bs["bucket_stats"]:
                    if b["trades"] > 0:
                        bucket_lines.append(
                            f"| {b['label']:<7} | {b['trades']:>5} | {b['wr']:>4.1f}% | "
                            f"{b['wilson_lower']:.1f}%-{b['wilson_upper']:.1f}% |"
                        )
                if bs["comparisons"]:
                    print(f"    [{sname}] {sym:<8} Bucket: {bs['summary']}", flush=True)

            # Her coin biter bitmez dosyaya yaz
            with open(md_path, "a", encoding="utf-8") as f:
                f.write("\n".join(bucket_lines) + "\n")
            print(
                f"    [{sname}] {sym:<8} FVG={fvg_size:.3f} "
                f"{st['total_trades']:>6} islem | "
                f"TP%={st['tp_pct']:>5.1f} PTrail%={st['profit_trail_pct']:>5.1f} "
                f"PF={st['profit_factor']:>5.2f} DD%={st['max_dd_pct']:>4.1f} "
                f"PnL={st['total_pnl']:>+8.0f} Skor={st['score']:>6.0f}",
                flush=True,
            )

        cfg.FVG_SIZE_MAP = _orig_fvg_map
        all_results[sname] = session_results

        if not session_results:
            continue

        # Session summary + aggregated bucket tablosu
        total_trades = sum(r["stats"]["total_trades"] for r in session_results)
        total_pnl = sum(r["stats"]["total_pnl"] for r in session_results)
        total_fee = sum(r["stats"]["total_fee"] for r in session_results)
        avg_score = (
            sum(r["stats"]["score"] for r in session_results) / len(session_results)
            if session_results
            else 0
        )
        total_days = sum(len(r["daily_rows"]) for r in session_results)
        print(
            f"\n  [{sname}] SUMMARY: {len(session_results)} coin, "
            f"{total_trades} trade, PnL={total_pnl:+.0f}, "
            f"Fee={total_fee:+.0f}, AvgScore={avg_score:.0f}",
            flush=True,
        )

        tail_lines = []
        tail_lines.append(
            f"**Summary:** {total_days} days, {total_trades} trades, "
            f"net PnL={total_pnl:+.0f}, Fee={total_fee:+.0f}, "
            f"Avg Score={avg_score:.0f}"
        )
        tail_lines.append("")
        tail_lines.append("### CBDR Bucket Scaling — Session Summary")
        tail_lines.append("")
        agg: dict = defaultdict(lambda: {"trades": 0, "wins": 0})
        for r in session_results:
            bs = analyze_bucket_scaling(r["daily_rows"], r["symbol"])
            if bs and bs["bucket_stats"]:
                for b in bs["bucket_stats"]:
                    agg[b["label"]]["trades"] += b["trades"]
                    agg[b["label"]]["wins"] += b["wins"]
        if agg:
            tail_lines.append("| Bucket | Trades | PE% | Wilson CI 95% |")
            tail_lines.append("|--------|-------|-----|---------------|")
            for lbl in ["0-1%", "1-1.5%", "1.5-2%", "2-3%", "3-5%", ">5%"]:
                d = agg.get(lbl)
                if d and d["trades"] > 0:
                    wr = d["wins"] / d["trades"] * 100
                    wl = wilson_lower(d["wins"], d["trades"]) * 100
                    wu = wilson_upper(d["wins"], d["trades"]) * 100
                    tail_lines.append(
                        f"| {lbl:<7} | {d['trades']:>5} | {wr:>4.1f}% | {wl:>5.1f}%-{wu:>5.1f}% |"
                    )
        tail_lines.append("")
        tail_lines.append("---")
        tail_lines.append("")

        with open(md_path, "a", encoding="utf-8") as f:
            f.write("\n".join(tail_lines) + "\n")
        print(f"[RAPOR] {sname} -> {md_path}", flush=True)

    print(f"\n{'=' * 100}")
    print(f"  TOPLAM SURE: {time.time() - t0:.0f}s")
    print(f"{'=' * 100}")
    for sname in sorted(all_results):
        results = all_results[sname]
        total_trades = sum(r["stats"]["total_trades"] for r in results)
        total_pnl = sum(r["stats"]["total_pnl"] for r in results)
        total_fee = sum(r["stats"]["total_fee"] for r in results)
        avg_score = (
            sum(r["stats"]["score"] for r in results) / len(results) if results else 0
        )
        print(
            f"  {sname}: {len(results)} coin, {total_trades} trade, "
            f"PnL={total_pnl:+.0f}, Fee={total_fee:+.0f}, Avg Score={avg_score:.0f}"
        )
    print(f"  Rapor: {md_path}")


if __name__ == "__main__":
    main()
