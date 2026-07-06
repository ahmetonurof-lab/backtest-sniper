"""
fvg_profile_v4.py — V4 engine ile kapsamli FVG profili.
V4'ün canli-özdes filtrelerinden geçen FVG popülasyonu üzerinde
12 analiz katmani: C2 anatomisi, BOS/MSS, derinlik/wick-body,
gap/ATR quartile, volatilite rejimi, coin bazli istatistik.
"""
# ruff: noqa: E402, E702
import csv
import functools
import math
import os
import random
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

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
from session_router import get_cbdr_multiplier, should_trade, is_high_quality_fvg, is_fvg_valid
from quant_logger import QuantLogger

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ─── Profil Parametreleri ───────────────────────────────────
SESSION_NAME = "DEFAULT"
SESSION_HOURS = {'start': 22, 'end': 2}
DD_TRIP = 15.0
DD_RESET = 10.0

LOOKBACK_BARS = 200
SWEEP_LOOKBACK = 20
N_BOOTSTRAP = 1000
BOOTSTRAP_SEED = 42
FEE_TAKER = 0.0004
CONT_WINDOWS = [10, 20, 40]
DEPTH_BUCKETS = [(0, 25, "0-25%"), (25, 50, "25-50%"), (50, 75, "50-75%"),
                 (75, 100, "75-100%"), (100, 150, "100-150%"), (150, 9999, ">150%")]

SYMBOLS_TO_TEST = [
    "BTCUSDT", "BNBUSDT", "SOLUSDT", "AVAXUSDT", "LINKUSDT",
    "XRPUSDT", "ATOMUSDT", "ADAUSDT", "APTUSDT", "DOTUSDT",
    "NEARUSDT", "ETHUSDT", "SUIUSDT",
]

# ─── Helpers ─────────────────────────────────────────────────
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


# ─── Klasik 3-Mum FVG Tespiti (profil analizi için) ───────
def detect_fvg_3candle(c1, c2, c3, atr):
    if c3.low > c1.high:
        gap = c3.low - c1.high
        return {"direction": "bullish", "top": c3.low, "bottom": c1.high,
                "size": gap, "c1": c1, "c2": c2, "c3": c3,
                "bar_index": c2.index, "atr": atr}
    if c1.low > c3.high:
        gap = c1.low - c3.high
        return {"direction": "bearish", "top": c1.low, "bottom": c3.high,
                "size": gap, "c1": c1, "c2": c2, "c3": c3,
                "bar_index": c2.index, "atr": atr}
    return None


def classify_c3(fvg):
    c3 = fvg["c3"]
    c2 = fvg["c2"]
    atr = fvg["atr"]
    direction = fvg["direction"]
    body_c3 = abs(c3.close - c3.open)
    total_range_c3 = c3.high - c3.low
    body_range_ratio = body_c3 / total_range_c3 if total_range_c3 > 0 else 0
    if direction == "bullish":
        rejection_body = c3.open - c3.low if c3.close < c3.open else c3.close - c3.low
        expansion_body = max(c3.close - c3.open, c3.high - c3.open)
        broke_c2_high = c3.high > c2.high
        if c3.close < c3.open and rejection_body >= atr and body_range_ratio >= 0.70:
            return "REJECTION"
        if expansion_body >= atr * 1.5 and body_range_ratio >= 0.70 and broke_c2_high:
            return "EXPANSION"
    else:
        rejection_body = c3.high - c3.close if c3.close > c3.open else c3.high - c3.open
        expansion_body = max(c3.open - c3.close, c3.open - c3.low)
        broke_c2_low = c3.low < c2.low
        if c3.close > c3.open and rejection_body >= atr and body_range_ratio >= 0.70:
            return "REJECTION"
        if expansion_body >= atr * 1.5 and body_range_ratio >= 0.70 and broke_c2_low:
            return "EXPANSION"
    return "CONSOLIDATION"


def calc_c2_anatomy(c2):
    body = abs(c2.close - c2.open)
    rng = c2.high - c2.low
    if rng == 0:
        return {"body_ratio": 0.0, "upper_wick_ratio": 0.0, "lower_wick_ratio": 0.0, "clv": 0.0}
    return {
        "body_ratio": round(body / rng, 4),
        "upper_wick_ratio": round((c2.high - max(c2.open, c2.close)) / rng, 4),
        "lower_wick_ratio": round((min(c2.open, c2.close) - c2.low) / rng, 4),
        "clv": round(((c2.close - c2.low) - (c2.high - c2.close)) / rng, 4),
    }


def detect_sweep(b15, c3_pos, lookback=20):
    lo = max(0, c3_pos - lookback - 30)
    pre_bars = b15[lo:c3_pos]
    if len(pre_bars) < 6:
        return {"swept_high": False, "swept_low": False}
    swings_h, swings_l = [], []
    for i in range(2, len(pre_bars) - 2):
        h, l = pre_bars[i].high, pre_bars[i].low
        if h > pre_bars[i - 2].high and h > pre_bars[i - 1].high and h > pre_bars[i + 1].high and h > pre_bars[i + 2].high:
            swings_h.append((lo + i, h))
        if l < pre_bars[i - 2].low and l < pre_bars[i - 1].low and l < pre_bars[i + 1].low and l < pre_bars[i + 2].low:
            swings_l.append((lo + i, l))
    swept_h, swept_l = False, False
    recent = b15[max(0, c3_pos - lookback):c3_pos]
    for idx, pr in swings_h:
        for b in recent:
            if b.index > idx and b.high > pr and b.close < pr:
                swept_h = True; break
        if swept_h:
            break
    for idx, pr in swings_l:
        for b in recent:
            if b.index > idx and b.low < pr and b.close > pr:
                swept_l = True; break
        if swept_l:
            break
    return {"swept_high": swept_h, "swept_low": swept_l}


# ─── FVG Outcome / RR ───────────────────────────────────────
def track_fvg_outcome(fvg, bars_after):
    direction = fvg["direction"]
    fvg_top, fvg_bottom = fvg["top"], fvg["bottom"]
    fvg_index = fvg["bar_index"]
    atr = fvg["atr"]
    result = {"mitigated": False, "mitigate_bar": None, "mitigate_price": None,
              "bars_to_mitigate": None, "continuation_10": None, "continuation_20": None,
              "continuation_40": None, "continuation": None, "invalidated": False,
              "invalidate_bar": None, "max_excursion": 0.0, "max_excursion_dir": None,
              "bars_tracked": 0, "close_price_at_end": None}
    invalidate_dist = atr
    mitigated = False
    for offset, b in enumerate(bars_after):
        if b.index <= fvg_index:
            continue
        if offset >= LOOKBACK_BARS:
            break
        result["bars_tracked"] = offset + 1
        touched_fvg = False
        if direction == "bullish":
            if b.low <= fvg_top and b.high >= fvg_bottom:
                touched_fvg = True
            if b.close < fvg_bottom - invalidate_dist:
                result["invalidated"] = True
                result["invalidate_bar"] = offset
                if not mitigated:
                    break
        else:
            if b.high >= fvg_bottom and b.low <= fvg_top:
                touched_fvg = True
            if b.close > fvg_top + invalidate_dist:
                result["invalidated"] = True
                result["invalidate_bar"] = offset
                if not mitigated:
                    break
        if direction == "bullish":
            exc = max(0, b.high - fvg_top, fvg_bottom - b.low)
        else:
            exc = max(0, fvg_top - b.low, b.high - fvg_bottom)
        if exc > result["max_excursion"]:
            result["max_excursion"] = exc
            result["max_excursion_dir"] = "beyond" if (direction == "bullish" and b.high > fvg_top) or (direction == "bearish" and b.low < fvg_bottom) else "reverse"
        if not mitigated and touched_fvg:
            cond = (direction == "bullish" and fvg_bottom <= b.close <= fvg_top) or (direction == "bearish" and fvg_bottom <= b.close <= fvg_top)
            wick = (direction == "bullish" and b.close >= fvg_bottom and b.low <= fvg_top) or (direction == "bearish" and b.close <= fvg_top and b.high >= fvg_bottom)
            if cond or wick:
                mitigated = True
                result["mitigated"] = True
                result["mitigate_bar"] = offset
                result["mitigate_price"] = b.close
                result["bars_to_mitigate"] = offset
        if mitigated and result["continuation_10"] is None:
            for win_offset, win_key in [(10, "continuation_10"), (20, "continuation_20"), (40, "continuation_40")]:
                fo = offset + win_offset
                if fo < len(bars_after):
                    fb = bars_after[fo]
                    result[win_key] = fb.close > fvg_top if direction == "bullish" else fb.close < fvg_bottom
        if result["invalidated"] and mitigated:
            break
    for key in ["continuation_10", "continuation_20", "continuation_40"]:
        if mitigated and result[key] is None:
            result[key] = False
    result["continuation"] = result["continuation_10"]
    return result


def simulate_rr_new(fvg, bars_after):
    direction = fvg["direction"]
    gap_top, gap_bottom = fvg["top"], fvg["bottom"]
    gap_width = max(fvg["size"], 0.000001)
    if direction == "bullish":
        entry_price = gap_top
        target_price = entry_price + gap_width * 2.0
    else:
        entry_price = gap_bottom
        target_price = entry_price - gap_width * 2.0
    risk_pct = gap_width / max(entry_price, 0.000001)
    fee_leg_R = FEE_TAKER / max(risk_pct, 0.000001)

    r = {"touched": False, "entry_bar": None, "entry_price": entry_price,
         "hit_target": False, "hit_stop": False, "no_outcome": True,
         "net_profit_R": 0.0, "risk": gap_width,
         "max_depth_pct": 0.0, "max_depth_class": None,
         "first_touch_depth": None, "first_touch_class": None,
         "touches": [], "invalidation_bar": None, "outcome_bar": None,
         "continuation_10": False, "continuation_20": False, "continuation_40": False}
    entered = False
    for offset, b in enumerate(bars_after):
        if offset >= LOOKBACK_BARS:
            break
        touches = b.high >= gap_bottom and b.low <= gap_top
        if not entered:
            if touches:
                entered = True
                r["touched"] = True
                r["entry_bar"] = offset
            else:
                continue
        tinfo = None
        if touches:
            depth = max(0, (gap_top - b.low) / gap_width * 100) if direction == "bullish" else max(0, (b.high - gap_bottom) / gap_width * 100)
            ci = gap_bottom <= b.close <= gap_top
            tinfo = {"bar": offset, "depth_pct": round(depth, 1), "wick_only": not ci, "close_in_fvg": ci}
            r["touches"].append(tinfo)
            if depth > r["max_depth_pct"]:
                r["max_depth_pct"] = depth
                r["max_depth_class"] = "WICK_ONLY" if not ci else "BODY_CLOSE"
            if r["first_touch_depth"] is None:
                r["first_touch_depth"] = round(depth, 1)
                r["first_touch_class"] = "WICK_ONLY" if not ci else "BODY_CLOSE"
        inval = (direction == "bullish" and b.close < gap_bottom) or (direction == "bearish" and b.close > gap_top)
        if inval:
            r["hit_stop"] = True; r["no_outcome"] = False
            r["invalidation_bar"] = offset; r["outcome_bar"] = offset
            r["net_profit_R"] = -1.0 - 2.0 * fee_leg_R
            _check_continuation(r, bars_after, offset, direction, entry_price, gap_width)
            return r
        hit_t = (direction == "bullish" and b.high >= target_price) or (direction == "bearish" and b.low <= target_price)
        if hit_t:
            r["hit_target"] = True; r["no_outcome"] = False
            r["outcome_bar"] = offset
            r["net_profit_R"] = 2.0 - 2.0 * fee_leg_R
            _check_continuation(r, bars_after, offset, direction, entry_price, gap_width)
            return r
    if entered:
        r["no_outcome"] = True
        r["net_profit_R"] = -2.0 * fee_leg_R
        _check_continuation(r, bars_after, len(bars_after) - 1, direction, entry_price, gap_width)
    return r


def _check_continuation(r, bars_after, from_idx, direction, entry_price, gap_width):
    for win in CONT_WINDOWS:
        key = f"continuation_{win}"
        fo = from_idx + win
        if fo < len(bars_after):
            fb = bars_after[fo]
            r[key] = (direction == "bullish" and fb.high >= entry_price + gap_width) or \
                     (direction == "bearish" and fb.low <= entry_price - gap_width)


# ─── BOS/MSS ─────────────────────────────────────────────────
def find_all_swing_points(b15):
    hi_idx, hi_pr, lo_idx, lo_pr = [], [], [], []
    for i in range(2, len(b15) - 2):
        h, l = b15[i].high, b15[i].low
        if h > b15[i - 2].high and h > b15[i - 1].high and h > b15[i + 1].high and h > b15[i + 2].high:
            hi_idx.append(b15[i].index); hi_pr.append(h)
        if l < b15[i - 2].low and l < b15[i - 1].low and l < b15[i + 1].low and l < b15[i + 2].low:
            lo_idx.append(b15[i].index); lo_pr.append(l)
    return (hi_idx, hi_pr), (lo_idx, lo_pr)


def _filter_swings(c3_idx, hi, lo):
    sw_h = [(hi[0][i], hi[1][i]) for i in range(len(hi[0])) if c3_idx - 50 <= hi[0][i] < c3_idx]
    sw_l = [(lo[0][i], lo[1][i]) for i in range(len(lo[0])) if c3_idx - 50 <= lo[0][i] < c3_idx]
    return sw_h, sw_l


def detect_bos_mss(fvg, b15, hi, lo):
    c3_idx = fvg["c3"].index
    sw_h, sw_l = _filter_swings(c3_idx, hi, lo)
    trend = "ranging"
    if len(sw_h) >= 2 and len(sw_l) >= 2:
        if sw_h[-1][1] >= sw_h[-2][1] and sw_l[-1][1] >= sw_l[-2][1]:
            trend = "uptrend"
        elif sw_h[-1][1] < sw_h[-2][1] and sw_l[-1][1] < sw_l[-2][1]:
            trend = "downtrend"
    pre_start = max(0, c3_idx - 20)
    pre_closes = [b.close for b in b15[pre_start:c3_idx] if b.index < c3_idx] if c3_idx > pre_start else []
    pre_max_c = max(pre_closes, default=0)
    pre_min_c = min(pre_closes, default=0)
    pre_bos = any(idx < c3_idx and pre_max_c > pr for idx, pr in sw_h) if trend == "uptrend" else (
        any(idx < c3_idx and pre_min_c < pr for idx, pr in sw_l) if trend == "downtrend" else False)
    pre_mss = any(idx < c3_idx and pre_min_c < pr for idx, pr in sw_l) if trend == "uptrend" else (
        any(idx < c3_idx and pre_max_c > pr for idx, pr in sw_h) if trend == "downtrend" else
        any(idx < c3_idx and pre_max_c > pr for idx, pr in sw_h) or any(idx < c3_idx and pre_min_c < pr for idx, pr in sw_l))
    post_end = min(c3_idx + 21, len(b15))
    post_closes = [b.close for b in b15[c3_idx + 1:post_end] if b.index > c3_idx] if post_end > c3_idx + 1 else []
    post_max_c = max(post_closes, default=0)
    post_min_c = min(post_closes, default=0)
    wt = "downtrend" if trend == "uptrend" else ("uptrend" if trend == "downtrend" else "ranging")
    post_bos = any(idx < c3_idx and post_max_c > pr for idx, pr in sw_h) if wt == "uptrend" else (
        any(idx < c3_idx and post_min_c < pr for idx, pr in sw_l) if wt == "downtrend" else False)
    post_mss = any(idx < c3_idx and post_min_c < pr for idx, pr in sw_l) if wt == "uptrend" else (
        any(idx < c3_idx and post_max_c > pr for idx, pr in sw_h) if wt == "downtrend" else
        any(idx < c3_idx and post_max_c > pr for idx, pr in sw_h) or any(idx < c3_idx and post_min_c < pr for idx, pr in sw_l))
    pre_bos, pre_mss = bool(pre_bos), bool(pre_mss)
    post_bos, post_mss = bool(post_bos), bool(post_mss)
    group = "NONE"
    if pre_bos or pre_mss:
        group = "BOS_ONLY" if (pre_bos and not pre_mss) else ("MSS_ONLY" if (pre_mss and not pre_bos) else "BOTH")
    elif post_bos or post_mss:
        group = "BOS_ONLY" if (post_bos and not post_mss) else ("MSS_ONLY" if (post_mss and not post_bos) else "BOTH")
    return {"pre_bos": pre_bos, "pre_mss": pre_mss, "post_bos": post_bos, "post_mss": post_mss,
            "trend": trend, "group": group}


# ─── Istatistik ──────────────────────────────────────────────
def percentile_sorted(vals, p):
    if not vals:
        return 0
    idx = max(0, min(len(vals) - 1, int(len(vals) * p / 100)))
    return vals[idx]


def cumulative_mit_curve(fvgs, max_b=200):
    mit_times = sorted([f["outcome"]["bars_to_mitigate"] for f in fvgs
                        if f["outcome"]["mitigated"] and f["outcome"]["bars_to_mitigate"] is not None])
    total = len(fvgs)
    if total == 0:
        return [], 0
    curve = []
    dr = max_b
    prev_pct = 0
    for n in [1, 2, 3, 5, 10, 20, 30, 50, 75, 100, 150, 200]:
        cnt = sum(1 for t in mit_times if t < n) if mit_times else 0
        pct = cnt / total * 100
        curve.append((n, pct))
        if n > 1 and prev_pct > 0 and (pct - prev_pct) < 1.0 and dr == max_b:
            dr = n
        prev_pct = pct
    return curve, dr if dr != max_b else 200


def conditional_cancel(fvgs, max_b=200):
    mit = sorted([f["outcome"]["bars_to_mitigate"] for f in fvgs
                  if f["outcome"]["mitigated"] and f["outcome"]["bars_to_mitigate"] is not None])
    total = len(fvgs)
    if total == 0:
        return []
    res = []
    for n in [5, 10, 20, 30, 50, 75, 100, 150, 200]:
        still_open = sum(1 for f in fvgs if not f["outcome"]["mitigated"]
                         or (f["outcome"]["bars_to_mitigate"] is not None and f["outcome"]["bars_to_mitigate"] >= n))
        will_mit = sum(1 for t in mit if t >= n) if mit else 0
        prob = will_mit / still_open * 100 if still_open > 0 else 0
        res.append((n, prob, still_open))
    return res


def bootstrap_ci(vals, n_resamples=N_BOOTSTRAP, ci=95, seed=BOOTSTRAP_SEED):
    n = len(vals)
    if n < 3:
        return (None, None, sum(vals) / n if n else 0)
    rng = random.Random(seed)
    means = []
    for _ in range(n_resamples):
        s = 0.0
        for _ in range(n):
            s += vals[rng.randint(0, n - 1)]
        means.append(s / n)
    alpha = (100 - ci) / 2
    lo = sorted(means)[int(n_resamples * alpha / 100)]
    hi = sorted(means)[int(n_resamples * (100 - alpha) / 100)]
    return (lo, hi, sum(vals) / n)


# ─── Volatilite Rejimi ───────────────────────────────────────
def volatility_regime_analysis(fvgs, b15, window=50):
    atr_vals = [b15[i].high - b15[i].low for i in range(len(b15))]
    regime_results = defaultdict(lambda: {"count": 0, "mitigated": 0, "bars": [],
                                          "profits": [], "continuation_10": 0})
    for f in fvgs:
        idx = f["c3"].index
        lo_idx = max(0, idx - window)
        recent_atr = atr_vals[lo_idx:idx]
        if len(recent_atr) < 10:
            continue
        cur_atr = f["atr"]
        rank = sum(1 for v in recent_atr if v < cur_atr) / len(recent_atr)
        if rank < 0.33:
            regime = "LOW"
        elif rank < 0.67:
            regime = "MID"
        else:
            regime = "HIGH"
        r = regime_results[regime]
        r["count"] += 1
        if f["outcome"]["mitigated"]:
            r["mitigated"] += 1
            if f["outcome"]["bars_to_mitigate"] is not None:
                r["bars"].append(f["outcome"]["bars_to_mitigate"])
            if f["outcome"].get("continuation_10"):
                r["continuation_10"] += 1
        if f["rr"].get("hit_target") or f["rr"].get("hit_stop") or f["rr"].get("no_outcome"):
            r["profits"].append(f["rr"]["net_profit_R"])
    return dict(regime_results)


# ─── V4 Engine + FVG Capturing ─────────────────────────────
_LOGGER = None


def collect_fvg_profile(symbol: str):
    """V4 engine (live-identical) + captures every trigger-ready FVG with profiling data."""
    csv_path = os.path.join(os.path.dirname(__file__), "data", "daily", f"{symbol}_1m_raw.csv")
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

    b1 = load_data(csv_path)
    b15 = resample_15m(b1)
    if not b15:
        return None, None

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

    # Profiling: captured FVG population
    captured_fvgs = []

    running_pnl = 0.0
    peak_equity = float(ic)
    circuit_broken = False

    atr_val = 0.0
    prev_close = b15[0].open
    for bar in b15[1:500]:
        tr = calculate_true_range(bar, prev_close)
        atr_val = update_atr(atr_val if atr_val > 0 else None, tr)
        prev_close = bar.close

    # Pre-compute swing points for BOS/MSS
    swing_hi, swing_lo = find_all_swing_points(b15)

    total_bars = len(b15)
    for sb in range(500, total_bars):
        if (sb - 500) % 5000 == 0:
            pct = (sb - 500) / (total_bars - 500) * 100
            print(f"\r    [{SESSION_NAME}] %{pct:.0f} ({sb}/{total_bars})", end="", flush=True)
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
            bias_reject = (sd == "bullish" and db == DailyBias.BEARISH) or \
                          (sd == "bearish" and db == DailyBias.BULLISH) or \
                          db == DailyBias.NEUTRAL
            if bias_reject:
                rsm.reset()
                continue
            h = edt.hour
            if (h >= sh or h < eh) if spans_midnight else (sh <= h < eh):
                rsm.reset()
                continue

            # ── Capture FVG for profiling ──
            # Reconstruct 3-candle FVG from V4's trigger_fvg.real_index
            v4_fvg = rsm.trigger_fvg
            if v4_fvg is not None:
                ri = v4_fvg.bar_index
                c2_bar = chunk[ri] if 0 <= ri < len(chunk) else None
                c1_bar = chunk[ri - 1] if ri - 1 >= 0 else None
                c3_bar = chunk[ri + 1] if ri + 1 < len(chunk) else None
            else:
                c1_bar = c2_bar = c3_bar = None

            if c1_bar and c2_bar and c3_bar:
                classic_fvg = detect_fvg_3candle(c1_bar, c2_bar, c3_bar, atr)
            else:
                classic_fvg = None

            if classic_fvg is not None:
                classic_fvg["category"] = classify_c3(classic_fvg)
                classic_fvg["atr_used"] = atr
                classic_fvg["tr_of_c3"] = tr
                classic_fvg["atr_after_c3"] = atr_val
                classic_fvg["fvg_hour"] = h
                classic_fvg["timestamp"] = c3_bar.timestamp
                classic_fvg["day_of_week"] = edt.weekday()
                classic_fvg["c3_pos"] = sb
                classic_fvg["c2_anatomy"] = calc_c2_anatomy(c2_bar)
                classic_fvg["sweep"] = detect_sweep(b15, sb, SWEEP_LOOKBACK)
                bars_after = b15[sb + 1:min(sb + LOOKBACK_BARS, total_bars)]
                classic_fvg["outcome"] = track_fvg_outcome(classic_fvg, bars_after)
                classic_fvg["rr"] = simulate_rr_new(classic_fvg, bars_after)
                classic_fvg["v4_rejected"] = None  # marked later
            else:
                classic_fvg = {
                    "direction": v4_fvg.direction if v4_fvg else "bullish",
                    "top": v4_fvg.top if v4_fvg else 0,
                    "bottom": v4_fvg.bottom if v4_fvg else 0,
                    "size": (v4_fvg.top - v4_fvg.bottom) if v4_fvg else 0,
                    "bar_index": sb,
                    "atr": atr,
                    "category": "UNKNOWN",
                    "c1": c1_bar, "c2": c2_bar, "c3": c3_bar,
                    "c3_pos": sb,
                    "c2_anatomy": calc_c2_anatomy(c2_bar) if c2_bar else {},
                    "sweep": detect_sweep(b15, sb, SWEEP_LOOKBACK),
                    "v4_rejected": None,
                }
                bars_after = b15[sb + 1:min(sb + LOOKBACK_BARS, total_bars)]
                classic_fvg["outcome"] = track_fvg_outcome(classic_fvg, bars_after)
                classic_fvg["rr"] = simulate_rr_new(classic_fvg, bars_after)

            classic_fvg["v4_fvg_top"] = v4_fvg.top if v4_fvg else None
            classic_fvg["v4_fvg_bottom"] = v4_fvg.bottom if v4_fvg else None

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
            if tf is not None:
                if not is_high_quality_fvg(tf.top - tf.bottom, atr):
                    classic_fvg["v4_rejected"] = "FVG_QUALITY"
                    rsm.reset()
                    captured_fvgs.append(classic_fvg)
                    continue
                if not is_fvg_valid(tf.real_index, cur.index):
                    classic_fvg["v4_rejected"] = "FVG_VALIDITY"
                    rsm.reset()
                    captured_fvgs.append(classic_fvg)
                    continue

            # ── Min risk dist ──
            if rd < atr * cfg.MIN_RISK_DIST_ATR_MULT:
                classic_fvg["v4_rejected"] = "MIN_RISK_DIST"
                rsm.reset()
                captured_fvgs.append(classic_fvg)
                continue

            # ── CBDR + should_trade ──
            cbdr_w = None
            if ss.cbdr_body_low > 0 and not math.isinf(ss.cbdr_body_low):
                cbdr_w = ((ss.cbdr_body_high - ss.cbdr_body_low) / ss.cbdr_body_low) * 100
            cbdr_mult = get_cbdr_multiplier(symbol, cbdr_w) if cbdr_w is not None else 1.0
            if cbdr_mult == 0.0:
                classic_fvg["v4_rejected"] = "CBDR_MULT_ZERO"
                rsm.reset()
                captured_fvgs.append(classic_fvg)
                continue
            allowed, reason = should_trade(symbol, cbdr_width_pct=cbdr_w)
            if not allowed:
                classic_fvg["v4_rejected"] = f"SHOULD_TRADE_{reason}"
                rsm.reset()
                captured_fvgs.append(classic_fvg)
                continue

            # ── Circuit breaker + EL + CBDR ──
            current_equity = ic + running_pnl
            current_dd = ((peak_equity - current_equity) / peak_equity) * 100 if peak_equity > 0 else 0
            if circuit_broken and current_dd <= DD_RESET:
                circuit_broken = False
            elif not circuit_broken and current_dd >= DD_TRIP:
                circuit_broken = True
            h = edt.hour
            is_early_london = 2 <= h < 8
            if circuit_broken:
                final_mult = 1.0 * min(cbdr_mult, 1.0)
            else:
                el_mult = cfg.EARLY_LONDON_RISK_MULT if is_early_london else 1.0
                final_mult = el_mult * cbdr_mult

            qty = (ic * rpt * final_mult) / rd if rd > 0 else 0
            if qty <= 0:
                classic_fvg["v4_rejected"] = "QTY_ZERO"
                rsm.reset()
                captured_fvgs.append(classic_fvg)
                continue

            # ── ENTERED ──
            classic_fvg["v4_rejected"] = "ENTERED"
            classic_fvg["v4_entry_price"] = ep
            classic_fvg["v4_sl"] = sl
            classic_fvg["v4_tp"] = tp
            classic_fvg["v4_qty"] = qty
            classic_fvg["v4_side"] = side
            classic_fvg["v4_cbdr_mult"] = cbdr_mult
            classic_fvg["v4_final_mult"] = final_mult
            captured_fvgs.append(classic_fvg)

            entry_day = ss.cbdr_day
            active.append({"entry_bar": sb, "entry_price": ep, "sl": sl, "tp": tp,
                           "qty": qty, "side": side, "trigger_fvg": tf,
                           "initial_sl": sl, "initial_tp": tp, "trailing_count": 0,
                           "day_key": entry_day})
            rsm.reset()

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
                        if ns >= cur.close:
                            t["exit_price"] = cur.close
                            t["exit_bar"] = sb
                            t["result"] = "TRAIL_CLOSE"
                            t["closed"] = True
                            break
                        if ns > csl and (ns - csl) > rpt2 * TMM:
                            sd2 = ns - csl
                            csl = ns
                            ctp += sd2
                            ltc += 1
                            upd = True
                    else:
                        ns = fvg.top + ab2
                        if ns <= cur.close:
                            t["exit_price"] = cur.close
                            t["exit_bar"] = sb
                            t["result"] = "TRAIL_CLOSE"
                            t["closed"] = True
                            break
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

        for t in active:
            if t.get("closed") and t.get("result") == "TRAIL_CLOSE":
                diff = (t["exit_price"] - t["entry_price"]) if t["side"] == "long" else (t["entry_price"] - t["exit_price"])
                t["pnl"] = round(diff * t["qty"], 2)
                day_trades[t.get("day_key", "")].append(t["pnl"])
                trade_records.append({"result": "TRAIL_CLOSE", "pnl": t["pnl"]})
                if t["pnl"] > 0:
                    wins.append(t)
                else:
                    losses.append(t)
                running_pnl += t["pnl"]
                current_equity = ic + running_pnl
                if current_equity > peak_equity:
                    peak_equity = current_equity
                if _LOGGER is not None:
                    risk_usd = abs(t["initial_sl"] - t["entry_price"]) * t["qty"] if t["initial_sl"] else 0
                    fvg_sz = (t["trigger_fvg"].top - t["trigger_fvg"].bottom) if t.get("trigger_fvg") else None
                    _LOGGER.log_trade({"symbol": symbol, "session": SESSION_NAME, "side": t["side"].upper(),
                        "entry_time": edt, "entry_price": round(t["entry_price"], 6),
                        "exit_price": round(t["exit_price"], 6), "result": "TRAIL_CLOSE",
                        "final_pnl_usd": round(t["pnl"], 2), "risk_usd": round(risk_usd, 2),
                        "r_multiple": round(t["pnl"] / risk_usd, 4) if risk_usd > 0 else 0.0,
                        "trailing_count": t.get("trailing_count", 0),
                        "fvg_size_pips": round(fvg_sz, 6) if fvg_sz else None, "atr": round(atr, 6),})

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
                running_pnl += t["pnl"]
                current_equity = ic + running_pnl
                if current_equity > peak_equity:
                    peak_equity = current_equity
                if _LOGGER is not None:
                    risk_usd = abs(t["initial_sl"] - t["entry_price"]) * t["qty"] if t["initial_sl"] else 0
                    fvg_sz = (t["trigger_fvg"].top - t["trigger_fvg"].bottom) if t.get("trigger_fvg") else None
                    _LOGGER.log_trade({"symbol": symbol, "session": SESSION_NAME, "side": t["side"].upper(),
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
                running_pnl += t["pnl"]
                if _LOGGER is not None:
                    risk_usd = abs(t["initial_sl"] - t["entry_price"]) * t["qty"] if t["initial_sl"] else 0
                    fvg_sz = (t["trigger_fvg"].top - t["trigger_fvg"].bottom) if t.get("trigger_fvg") else None
                    _LOGGER.log_trade({"symbol": symbol, "session": SESSION_NAME, "side": t["side"].upper(),
                        "entry_time": edt, "entry_price": round(t["entry_price"], 6),
                        "exit_price": round(t["exit_price"], 6), "result": "OPEN",
                        "final_pnl_usd": round(t["pnl"], 2), "risk_usd": round(risk_usd, 2),
                        "r_multiple": round(t["pnl"] / risk_usd, 4) if risk_usd > 0 else 0.0,
                        "trailing_count": t.get("trailing_count", 0),
                        "fvg_size_pips": round(fvg_sz, 6) if fvg_sz else None, "atr": round(atr, 6),})

    print(f"\r    [{SESSION_NAME}] %100 ({total_bars}/{total_bars})", flush=True)

    # ── BOS/MSS for captured FVGs ──
    for f in captured_fvgs:
        if f.get("c3") is not None:
            f["bos_mss"] = detect_bos_mss(f, b15, swing_hi, swing_lo)
        else:
            f["bos_mss"] = {"pre_bos": False, "pre_mss": False, "post_bos": False,
                            "post_mss": False, "trend": "ranging", "group": "NONE"}

    # ── Daily rows ──
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
            "day_key": dk, "cbdr_pct": w, "trades": n_trades,
            "wins": n_wins, "be": n_be, "losses": n_trades - n_wins - n_be, "pnl": total_pnl,
        })

    return daily_rows, wins, losses, trade_records, captured_fvgs


# ─── Rapor Olusturma ─────────────────────────────────────────
def build_report(all_coin_data, results_data):
    lines = []

    def L(s=""):
        lines.append(s)

    L("# FVG Profile V4 — V4 Engine ile Kapsamli FVG Karakteristik Profili")
    L(f"**Session:** {SESSION_NAME} [{SESSION_HOURS['start']:02d}:00-{SESSION_HOURS['end']:02d}:00]")
    L(f"**Engine:** V4 (live-identical) — Sweep → RSM → Quality → Entry → Trailing")
    L(f"**Coinler:** {', '.join(SYMBOLS_TO_TEST)}")
    L(f"**Tarih:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    L("")
    L("---")
    L("")

    # ═══════════════════════════════════════════════════
    # BOLUM 0: Genel Performans
    # ═══════════════════════════════════════════════════
    L("## 0. Genel Performans (analyser_v4)")
    L("")
    L("| Coin | Trades | WIN | BE | LOSS | WR% | BE+% | PF | MaxDD% | PnL |")
    L("|" + "|".join(["-" * 8] * 10) + "|")
    for sym, stats, _, _, _ in results_data:
        L(f"| {sym:<8} | {stats['total_trades']:>6} | {stats['wins']:>4} | {stats['be']:>3} | {stats['losses']:>4} | "
          f"{stats['win_pct']:>4.1f}% | {stats['be_plus_pct']:>4.1f}% | {stats['profit_factor']:>3.2f} | "
          f"{stats['max_dd_pct']:>5.2f}% | {stats['total_pnl']:>+8.0f} |")
    L("")

    # ═══════════════════════════════════════════════════
    # BOLUM 1: Coin × Kategori Ana Tablo
    # ═══════════════════════════════════════════════════
    L("---")
    L("")
    L("## 1. Coin × Kategori Ana Tablo")
    L("")
    H = ["Coin", "Kat", "N", "Mit%", "Inv%", "p50Bar", "p90Bar",
         "Cont@10%", "Cont@40%", "RR_WR%", "NetExp", "n<30?"]
    L("| " + " | ".join(H) + " |")
    L("|" + "|".join(["-" * 6] * len(H)) + "|")

    for sym, coin_data in all_coin_data.items():
        fvgs = coin_data["fvgs"]
        cats = defaultdict(list)
        for f in fvgs:
            cats[f["category"]].append(f)
        for cat in ["CONSOLIDATION", "EXPANSION", "REJECTION"]:
            cf = cats.get(cat, [])
            n = len(cf)
            if n == 0:
                continue
            mit = sum(1 for f in cf if f["outcome"]["mitigated"])
            inv = sum(1 for f in cf if f["outcome"]["invalidated"])
            mit_pct = mit / n * 100
            inv_pct = inv / n * 100
            mtimes = sorted([f["outcome"]["bars_to_mitigate"] for f in cf
                             if f["outcome"]["mitigated"] and f["outcome"]["bars_to_mitigate"] is not None])
            p50 = percentile_sorted(mtimes, 50) if mtimes else 0
            p90 = percentile_sorted(mtimes, 90) if mtimes else 0
            cont10 = sum(1 for f in cf if f["outcome"].get("continuation_10")) / max(mit, 1) * 100
            cont40 = sum(1 for f in cf if f["outcome"].get("continuation_40")) / max(mit, 1) * 100
            wins = sum(1 for f in cf if f["rr"].get("hit_target"))
            losses_rr = sum(1 for f in cf if f["rr"].get("hit_stop"))
            rt = wins + losses_rr
            wr = wins / rt * 100 if rt > 0 else 0
            profits = [f["rr"]["net_profit_R"] for f in cf
                       if f["rr"].get("hit_target") or f["rr"].get("hit_stop")]
            net_exp = sum(profits) / len(profits) if profits else 0
            warn = "⚠️" if n < 30 else ""
            L(f"| {sym:<8s} | {cat:<13s} | {n:>4d} | {mit_pct:>5.1f} | {inv_pct:>5.1f} | "
              f"{p50:>4d} | {p90:>4d} | {cont10:>5.1f} | {cont40:>5.1f} | "
              f"{wr:>5.1f} | {net_exp:>+6.2f}R | {warn:>4s} |")
    L("")

    # ═══════════════════════════════════════════════════
    # BOLUM 2: Mitigasyon Zamanlamasi
    # ═══════════════════════════════════════════════════
    L("---")
    L("")
    L("## 2. Mitigasyon Zamanlamasi")
    L("")
    L("### 2a. Persentil Tablosu (bar-to-mitigate)")
    L("")
    H2 = ["Coin", "Kategori", "N_mit", "p25", "p50", "p75", "p90", "Ortalama"]
    L("| " + " | ".join(H2) + " |")
    L("|" + "|".join(["-" * 6] * len(H2)) + "|")
    for sym, coin_data in all_coin_data.items():
        fvgs = coin_data["fvgs"]
        cats = defaultdict(list)
        for f in fvgs:
            cats[f["category"]].append(f)
        for cat in ["CONSOLIDATION", "EXPANSION", "REJECTION"]:
            cf = cats.get(cat, [])
            mtimes = sorted([f["outcome"]["bars_to_mitigate"] for f in cf
                             if f["outcome"]["mitigated"] and f["outcome"]["bars_to_mitigate"] is not None])
            if not mtimes:
                continue
            L(f"| {sym:<8s} | {cat:<13s} | {len(mtimes):>5d} | "
              f"{percentile_sorted(mtimes,25):>4d} | {percentile_sorted(mtimes,50):>4d} | "
              f"{percentile_sorted(mtimes,75):>4d} | {percentile_sorted(mtimes,90):>4d} | "
              f"{sum(mtimes)/len(mtimes):>6.1f} |")
    L("")

    L("### 2b. Kumulatif Mitigasyon Egrisi & Diminishing Returns")
    L("")
    L("| Coin | Kategori | 1b | 2b | 3b | 5b | 10b | 20b | 30b | 50b | 75b | 100b | DR_nok |")
    L("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for sym, coin_data in all_coin_data.items():
        fvgs = coin_data["fvgs"]
        cats = defaultdict(list)
        for f in fvgs:
            cats[f["category"]].append(f)
        for cat in ["CONSOLIDATION", "EXPANSION", "REJECTION"]:
            cf = cats.get(cat, [])
            if len(cf) < 5:
                continue
            curve, dr = cumulative_mit_curve(cf)
            row = [f"{sym:<8s}", f"{cat:<13s}"]
            for n, pct in curve:
                row.append(f"{pct:.0f}")
            row.append(f"{dr}b")
            L("| " + " | ".join(row) + " |")
    L("")

    L("### 2c. Kosullu Iptal Esigi (Cancel Threshold)")
    L("")
    L("P(mitigate | henuz mitigate olmadi VE N bar gecti)")
    L("")
    L("| Coin | Kategori | 5b | 10b | 20b | 30b | 50b | 75b | 100b | 150b |")
    L("|---|---|---|---|---|---|---|---|---|---|")
    for sym, coin_data in all_coin_data.items():
        fvgs = coin_data["fvgs"]
        cats = defaultdict(list)
        for f in fvgs:
            cats[f["category"]].append(f)
        for cat in ["CONSOLIDATION", "EXPANSION", "REJECTION"]:
            cf = cats.get(cat, [])
            if len(cf) < 5:
                continue
            cc = conditional_cancel(cf)
            row = [f"{sym:<8s}", f"{cat:<13s}"]
            for n, prob, _ in cc:
                if n in [5, 10, 20, 30, 50, 75, 100, 150]:
                    row.append(f"{prob:.0f}%")
            L("| " + " | ".join(row) + " |")
    L("")

    L("### 2d. Onerilen Iptal Esigi (diminishing returns noktasi)")
    L("")
    L("| Coin | CONS | EXP | REJ |")
    L("|---|---|---|---|")
    for sym, coin_data in all_coin_data.items():
        fvgs = coin_data["fvgs"]
        cats = defaultdict(list)
        for f in fvgs:
            cats[f["category"]].append(f)
        drs = {}
        for cat in ["CONSOLIDATION", "EXPANSION", "REJECTION"]:
            cf = cats.get(cat, [])
            if len(cf) < 5:
                drs[cat] = "N/A"
            else:
                _, dr = cumulative_mit_curve(cf)
                drs[cat] = f"{dr}b"
        L(f"| {sym:<8s} | {drs.get('CONSOLIDATION','N/A'):>4s} | {drs.get('EXPANSION','N/A'):>4s} | {drs.get('REJECTION','N/A'):>4s} |")
    L("")

    # ═══════════════════════════════════════════════════
    # BOLUM 3: FVG Boyutu / ATR
    # ═══════════════════════════════════════════════════
    L("---")
    L("")
    L("## 3. FVG Boyutu / ATR Orani")
    L("")
    L("### 3a. gap/ATR dagilimi")
    L("")
    L("| Coin | Kons. medyan | Kons. p75 | Exp. medyan | Exp. p75 | Rej. medyan | Rej. p75 |")
    L("|---|---|---|---|---|---|---|")
    for sym, coin_data in all_coin_data.items():
        fvgs = coin_data["fvgs"]
        cats = defaultdict(list)
        for f in fvgs:
            cats[f["category"]].append(f)
        row = [f"{sym:<8s}"]
        for cat in ["CONSOLIDATION", "EXPANSION", "REJECTION"]:
            cf = cats.get(cat, [])
            ratios = sorted([f["size"] / max(f["atr"], 0.0001) for f in cf])
            if ratios:
                row.append(f"{percentile_sorted(ratios,50):.2f}")
                row.append(f"{percentile_sorted(ratios,75):.2f}")
            else:
                row.append("-")
                row.append("-")
        L("| " + " | ".join(row) + " |")
    L("")

    L("### 3b. gap/ATR × Kategori (2×3 tablosu — mitigasyon orani)")
    L("")
    L("| FVG Boyutu | CONS Mit% | EXP Mit% | REJ Mit% |")
    L("|---|---|---|---|")
    for size_label, lo, hi in [("Kucuk (<0.5xATR)", 0, 0.5),
                                ("Orta (0.5-1.5xATR)", 0.5, 1.5),
                                ("Buyuk (>1.5xATR)", 1.5, 999)]:
        row = [size_label]
        for cat in ["CONSOLIDATION", "EXPANSION", "REJECTION"]:
            all_f = []
            for coin_data in all_coin_data.values():
                for f in coin_data["fvgs"]:
                    if f["category"] == cat:
                        ratio = f["size"] / max(f["atr"], 0.0001)
                        if lo <= ratio < hi:
                            all_f.append(f)
            n = len(all_f)
            mit = sum(1 for f in all_f if f["outcome"]["mitigated"])
            row.append(f"{mit / max(n, 1) * 100:.1f}% (n={n})")
        L("| " + " | ".join(row) + " |")
    L("")

    # ═══════════════════════════════════════════════════
    # BOLUM 4: Volatilite Rejimi
    # ═══════════════════════════════════════════════════
    L("---")
    L("")
    L("## 4. Volatilite Rejimi Analizi")
    L("")
    L("Her FVG'nin olustugu donemdeki ATR'nin son 50 bar icindeki percentile'ina gore LOW/MID/HIGH rejim.")
    L("")
    L("| Coin | Kategori | Rejim | N | Mit% | MedBar | Cont@10% | NetExp |")
    L("|---|---|---|---|---|---|---|---|")
    for sym, coin_data in all_coin_data.items():
        fvgs = coin_data["fvgs"]
        b15 = coin_data["b15"]
        for cat in ["CONSOLIDATION", "EXPANSION", "REJECTION"]:
            cf = [f for f in fvgs if f["category"] == cat]
            if len(cf) < 5:
                continue
            regimes = volatility_regime_analysis(cf, b15)
            for regime_name in ["LOW", "MID", "HIGH"]:
                rr = regimes.get(regime_name, {})
                n = rr.get("count", 0)
                if n < 3:
                    continue
                mit = rr.get("mitigated", 0)
                mit_pct = mit / max(n, 1) * 100
                bars = rr.get("bars", [])
                med_bar = percentile_sorted(sorted(bars), 50) if bars else 0
                cont = rr.get("continuation_10", 0)
                cont_pct = cont / max(mit, 1) * 100
                profs = rr.get("profits", [])
                ne = sum(profs) / len(profs) if profs else 0
                L(f"| {sym:<8s} | {cat:<13s} | {regime_name:>4s} | {n:>4d} | {mit_pct:>5.1f} | "
                  f"{med_bar:>4d} | {cont_pct:>5.1f} | {ne:>+6.2f}R |")
    L("")

    # ═══════════════════════════════════════════════════
    # BOLUM 5: Hafta Ici / Hafta Sonu
    # ═══════════════════════════════════════════════════
    L("---")
    L("")
    L("## 5. Hafta Ici / Hafta Sonu Etkisi")
    L("")
    L("| Coin | Kategori | Haftaici N | Hftici Mit% | Hftici NetExp | Haftasonu N | Hftsonu Mit% | Hftsonu NetExp |")
    L("|---|---|---|---|---|---|---|---|")
    for sym, coin_data in all_coin_data.items():
        fvgs = coin_data["fvgs"]
        cats = defaultdict(list)
        for f in fvgs:
            cats[f["category"]].append(f)
        for cat in ["CONSOLIDATION", "EXPANSION", "REJECTION"]:
            cf = cats.get(cat, [])
            if not cf:
                continue
            wd = [f for f in cf if f["day_of_week"] < 5]
            we = [f for f in cf if f["day_of_week"] >= 5]

            def _stats(grp):
                n = len(grp)
                mit = sum(1 for f in grp if f["outcome"]["mitigated"]) / max(n, 1) * 100
                profs = [f["rr"]["net_profit_R"] for f in grp
                         if f["rr"].get("hit_target") or f["rr"].get("hit_stop")]
                ne = sum(profs) / len(profs) if profs else 0
                return n, mit, ne

            wn, wm, wexp = _stats(wd)
            wen, wem, weexp = _stats(we)
            L(f"| {sym:<8s} | {cat:<13s} | {wn:>5d} | {wm:>5.1f} | {wexp:>+7.2f}R | "
              f"{wen:>5d} | {wem:>5.1f} | {weexp:>+7.2f}R |")
    L("")

    # ═══════════════════════════════════════════════════
    # BOLUM 6: BOS/MSS Yapi Kirilimi
    # ═══════════════════════════════════════════════════
    L("---")
    L("")
    L("## 6. BOS / MSS Yapi Kirilimi Analizi")
    L("")
    L("| Kategori | Yapi | N | Mit% | Cont@10% | RR_WR% | NetExp | n<30? |")
    L("|---|---|---|---|---|---|---|---|")
    for cat in ["CONSOLIDATION", "EXPANSION", "REJECTION"]:
        groups = defaultdict(list)
        for coin_data in all_coin_data.values():
            for f in coin_data["fvgs"]:
                if f["category"] == cat:
                    groups[f.get("bos_mss", {}).get("group", "NONE")].append(f)
        for grp_name in ["NONE", "BOS_ONLY", "MSS_ONLY", "BOTH"]:
            grp = groups.get(grp_name, [])
            n = len(grp)
            if n == 0:
                continue
            mit = sum(1 for f in grp if f["outcome"]["mitigated"]) / max(n, 1) * 100
            mit_count = sum(1 for f in grp if f["outcome"]["mitigated"])
            cont10 = sum(1 for f in grp if f["outcome"].get("continuation_10")) / max(mit_count, 1) * 100
            wins = sum(1 for f in grp if f["rr"].get("hit_target"))
            losses_rr = sum(1 for f in grp if f["rr"].get("hit_stop"))
            rt = wins + losses_rr
            wr = wins / rt * 100 if rt > 0 else 0
            profs = [f["rr"]["net_profit_R"] for f in grp if f["rr"].get("hit_target") or f["rr"].get("hit_stop")]
            ne = sum(profs) / len(profs) if profs else 0
            warn = "⚠️" if n < 30 else ""
            L(f"| {cat:<13s} | {grp_name:<9s} | {n:>4d} | {mit:>5.1f} | {cont10:>5.1f} | "
              f"{wr:>5.1f} | {ne:>+6.2f}R | {warn:>4s} |")
    L("")

    L("### 6b. Hipotez Testi: Teyitli (BOS/MSS) vs Teyitsiz (NONE)")
    L("")
    for cat in ["CONSOLIDATION", "EXPANSION", "REJECTION"]:
        groups = defaultdict(list)
        for coin_data in all_coin_data.values():
            for f in coin_data["fvgs"]:
                if f["category"] == cat:
                    groups[f.get("bos_mss", {}).get("group", "NONE")].append(f)
        none_profs = [f["rr"]["net_profit_R"] for f in groups.get("NONE", [])
                      if f["rr"].get("hit_target") or f["rr"].get("hit_stop")]
        none_ci = bootstrap_ci(none_profs) if len(none_profs) >= 3 else (None, None, None)
        for grp_name in ["BOS_ONLY", "MSS_ONLY", "BOTH"]:
            grp = groups.get(grp_name, [])
            grp_profs = [f["rr"]["net_profit_R"] for f in grp
                         if f["rr"].get("hit_target") or f["rr"].get("hit_stop")]
            grp_ci = bootstrap_ci(grp_profs) if len(grp_profs) >= 3 else (None, None, None)
            if none_ci[0] is None or grp_ci[0] is None:
                L(f"| {cat:<13s} | {grp_name:<9s} | YETERSIZ ORNEKLEM |")
                continue
            overlap = not (grp_ci[1] < none_ci[0] or grp_ci[0] > none_ci[1])
            if overlap:
                verdict = "ANLAMLI FARK YOK"
            else:
                verdict = f"FARK VAR - {grp_name} {'daha iyi' if grp_ci[2] > none_ci[2] else 'daha kotu'}"
            L(f"| {cat:<13s} | {grp_name:<9s} | NONE(n={len(none_profs)}): {none_ci[2]:>+.2f}R "
              f"[{none_ci[0]:>+.2f}, {none_ci[1]:>+.2f}] | {grp_name}(n={len(grp_profs)}): "
              f"{grp_ci[2]:>+.2f}R [{grp_ci[0]:>+.2f}, {grp_ci[1]:>+.2f}] | {verdict} |")
    L("")

    # ═══════════════════════════════════════════════════
    # BOLUM 7: Coin Oneri
    # ═══════════════════════════════════════════════════
    L("---")
    L("")
    L("## 7. Coin -> Onerilen Kategori")
    L("")
    L("| Coin | CONS exp | CONS CI | EXP exp | EXP CI | REJ exp | REJ CI | Oneri |")
    L("|---|---|---|---|---|---|---|---|")
    for sym, coin_data in all_coin_data.items():
        fvgs = coin_data["fvgs"]
        cats = defaultdict(list)
        for f in fvgs:
            cats[f["category"]].append(f)
        best = None
        best_exp = -999
        row = [f"{sym:<8s}"]
        for cat in ["CONSOLIDATION", "EXPANSION", "REJECTION"]:
            cf = cats.get(cat, [])
            n = len(cf)
            profs = [f["rr"]["net_profit_R"] for f in cf if f["rr"].get("hit_target") or f["rr"].get("hit_stop")]
            ci = bootstrap_ci(profs) if len(profs) >= 3 else (None, None, None)
            if ci[0] is not None:
                row.append(f"{ci[2]:>+.2f}R")
                row.append(f"[{ci[0]:>+.2f},{ci[1]:>+.2f}]")
            else:
                row.append("N/A")
                row.append("N/A")
            if ci[2] is not None and ci[2] > best_exp and n >= 30 and not (ci[1] < 0 or ci[0] > 0):
                best_exp = ci[2]
                best = f"{cat} ({ci[2]:+.2f}R)"
        if best is None:
            best = "BELIRSIZ"
        row.append(best)
        L("| " + " | ".join(row) + " |")
    L("")

    # ═══════════════════════════════════════════════════
    # BOLUM 8: Nihai Degerlendirme
    # ═══════════════════════════════════════════════════
    L("---")
    L("")
    L("## 8. Nihai Degerlendirme")
    L("")
    for sym, coin_data in all_coin_data.items():
        fvgs = coin_data["fvgs"]
        cats = defaultdict(list)
        for f in fvgs:
            cats[f["category"]].append(f)
        L(f"### {sym}")
        L("")
        for cat in ["CONSOLIDATION", "EXPANSION", "REJECTION"]:
            cf = cats.get(cat, [])
            n = len(cf)
            profs = [f["rr"]["net_profit_R"] for f in cf if f["rr"].get("hit_target") or f["rr"].get("hit_stop")]
            ci = bootstrap_ci(profs) if len(profs) >= 3 else (None, None, None)
            if ci[0] is None:
                L(f"- **{cat}:** n={n}, yetersiz orneklem")
            elif ci[1] < 0:
                L(f"- **{cat}:** n={n}, exp={ci[2]:+.2f}R [{ci[0]:+.2f}, {ci[1]:+.2f}] — **negatif expectancy, kacinilmali**")
            elif ci[0] > 0:
                L(f"- **{cat}:** n={n}, exp={ci[2]:+.2f}R [{ci[0]:+.2f}, {ci[1]:+.2f}] — **olumlu edge**")
            else:
                L(f"- **{cat}:** n={n}, exp={ci[2]:+.2f}R [{ci[0]:+.2f}, {ci[1]:+.2f}] — sifiri kapsiyor, belirsiz")
        L("")
    L("")

    # ═══════════════════════════════════════════════════
    # BOLUM 9: C2 Mum Anatomisi
    # ═══════════════════════════════════════════════════
    L("---")
    L("")
    L("## 9. C2 Mum Anatomisi × Continuation")
    L("")
    L("### 9a. C2 Anatomi Metrikleri — Tanimlayici Istatistikler")
    L("")
    L("| Metrik | p25 | p50 | p75 | Ortalama |")
    L("|---|---|---|---|---|")
    for metrik in ["body_ratio", "upper_wick_ratio", "lower_wick_ratio", "clv", "gap_atr_ratio"]:
        vals = []
        for coin_data in all_coin_data.values():
            for f in coin_data["fvgs"]:
                if metrik == "gap_atr_ratio":
                    vals.append(f["size"] / max(f["atr"], 0.0001))
                else:
                    vals.append(f["c2_anatomy"].get(metrik, 0))
        if not vals:
            continue
        sv = sorted(vals)
        L(f"| {metrik:<20s} | {percentile_sorted(sv,25):>+.4f} | {percentile_sorted(sv,50):>+.4f} | "
          f"{percentile_sorted(sv,75):>+.4f} | {sum(vals)/len(vals):>+.4f} |")
    L("")

    L("### 9b. Spearman Korelasyonu: C2 Metrikleri × Continuation")
    L("")
    L("| Metrik | Cont@10 rho | Cont@20 rho | Cont@40 rho |")
    L("|---|---|---|---|")
    for metrik in ["body_ratio", "upper_wick_ratio", "lower_wick_ratio", "clv", "gap_atr_ratio"]:
        row = [f"{metrik:<20s}"]
        for win in CONT_WINDOWS:
            x, y = [], []
            for coin_data in all_coin_data.values():
                for f in coin_data["fvgs"]:
                    rn = f.get("rr", {})
                    if not rn.get("touched"):
                        continue
                    if metrik == "gap_atr_ratio":
                        x.append(f["size"] / max(f["atr"], 0.0001))
                    else:
                        x.append(f["c2_anatomy"].get(metrik, 0))
                    y.append(1 if rn.get(f"continuation_{win}") else 0)
            if len(set(y)) < 2 or len(x) < 5:
                row.append("N/A")
            else:
                n = len(x)
                rx = [sorted(x).index(v) + 1 for v in x]
                ry = [sorted(y).index(v) + 1 for v in y]
                d2 = sum((rx[i] - ry[i]) ** 2 for i in range(n))
                rho = 1 - 6 * d2 / (n * (n * n - 1)) if n > 1 else 0
                row.append(f"{rho:>+.4f}")
        L("| " + " | ".join(row) + " |")
    L("")

    L("### 9c. Body_Ratio Quartile × Continuation (Kategori Bagimsiz)")
    L("")
    L("| Kategori | Body_Q | N | Mit% | Cont@10% | NetExp (rr_new) |")
    L("|---|---|---|---|---|---|")
    for cat in ["CONSOLIDATION", "EXPANSION", "REJECTION"]:
        cf = []
        for coin_data in all_coin_data.values():
            for f in coin_data["fvgs"]:
                if f["category"] == cat and f.get("c2_anatomy"):
                    cf.append(f)
        if not cf:
            continue
        ratios = sorted([f["c2_anatomy"]["body_ratio"] for f in cf])
        qvals = [percentile_sorted(ratios, q) for q in [0, 25, 50, 75, 100]]
        for qi in range(4):
            lo, hi = qvals[qi], qvals[qi + 1]
            grp = [f for f in cf if lo <= f["c2_anatomy"]["body_ratio"] <= hi]
            n = len(grp)
            if n < 3:
                continue
            mit = sum(1 for f in grp if f.get("rr", {}).get("touched")) / n * 100
            touched = sum(1 for f in grp if f.get("rr", {}).get("touched"))
            cont = sum(1 for f in grp if f.get("rr", {}).get("continuation_10")) / max(touched, 1) * 100
            profs = [f["rr"]["net_profit_R"] for f in grp if f["rr"].get("hit_target") or f["rr"].get("hit_stop")]
            ne = sum(profs) / len(profs) if profs else 0
            L(f"| {cat:<13s} | Q{qi+1}({lo:.2f}-{hi:.2f}) | {n:>4d} | {mit:>5.1f} | {cont:>5.1f} | {ne:>+6.2f}R |")
    L("")

    # ═══════════════════════════════════════════════════
    # BOLUM 10: Retracement Derinligi
    # ═══════════════════════════════════════════════════
    L("---")
    L("")
    L("## 10. Retracement Derinligi × Continuation")
    L("")
    L("| Derinlik | WICK_ONLY N | WICK_ONLY Cont@10% | WICK_ONLY Cont@40% | "
      "WICK_ONLY NetExp | BODY_CLOSE N | BODY_CLOSE Cont@10% | "
      "BODY_CLOSE Cont@40% | BODY_CLOSE NetExp |")
    L("|---|---|---|---|---|---|---|---|---|")
    for dlo, dhi, dlabel in DEPTH_BUCKETS:
        row = [dlabel]
        for touch_class in ["WICK_ONLY", "BODY_CLOSE"]:
            grp = []
            for coin_data in all_coin_data.values():
                for f in coin_data["fvgs"]:
                    rn = f.get("rr", {})
                    if not rn.get("touched"):
                        continue
                    cls = rn.get("max_depth_class") or rn.get("first_touch_class", "WICK_ONLY")
                    dp = rn.get("max_depth_pct", 0)
                    if cls == touch_class and dlo <= dp < dhi:
                        grp.append(f)
            n = len(grp)
            if n < 3:
                row.extend(["0", "N/A", "N/A", "N/A"] if n == 0 else [f"{n}", "N/A", "N/A", "N/A"])
                continue
            cont10 = sum(1 for f in grp if f["rr"].get("continuation_10")) / n * 100
            cont40 = sum(1 for f in grp if f["rr"].get("continuation_40")) / n * 100
            profs = [f["rr"]["net_profit_R"] for f in grp if f["rr"].get("hit_target") or f["rr"].get("hit_stop")]
            ne = sum(profs) / len(profs) if profs else 0
            row.extend([f"{n}", f"{cont10:.1f}", f"{cont40:.1f}", f"{ne:+.2f}R"])
        L("| " + " | ".join(row) + " |")
    L("")

    # ═══════════════════════════════════════════════════
    # BOLUM 11: V4 Filtre Kirilimi
    # ═══════════════════════════════════════════════════
    L("---")
    L("")
    L("## 11. V4 Filtre Kirilimi")
    L("")
    L("V4 motorunda trigger-ready FVG'lerin hangi asamada elendigini gosterir.")
    L("")
    L("| Coin | Toplam FVG | ENTERED | FVG_QUALITY | FVG_VALIDITY | MIN_RISK | CBDR/SHOULD_TRADE | QTY_ZERO |")
    L("|---|---|---|---|---|---|---|---|")
    for sym, coin_data in all_coin_data.items():
        fvgs = coin_data["fvgs"]
        total = len(fvgs)
        entered = sum(1 for f in fvgs if f.get("v4_rejected") == "ENTERED")
        fvg_q = sum(1 for f in fvgs if f.get("v4_rejected") == "FVG_QUALITY")
        fvg_v = sum(1 for f in fvgs if f.get("v4_rejected") == "FVG_VALIDITY")
        min_r = sum(1 for f in fvgs if f.get("v4_rejected") == "MIN_RISK_DIST")
        cbdr_r = sum(1 for f in fvgs if f.get("v4_rejected", "").startswith("SHOULD_TRADE") or f.get("v4_rejected") == "CBDR_MULT_ZERO")
        qty_z = sum(1 for f in fvgs if f.get("v4_rejected") == "QTY_ZERO")
        L(f"| {sym:<8s} | {total:>6d} | {entered:>6d} | {fvg_q:>6d} | {fvg_v:>6d} | {min_r:>6d} | {cbdr_r:>6d} | {qty_z:>6d} |")
    L("")

    # ═══════════════════════════════════════════════════
    # BOLUM 12: Derinlik Hipotez Testi
    # ═══════════════════════════════════════════════════
    L("---")
    L("")
    L("## 12. Hipotez Testi: Derinlik × Continuation Iliskisi")
    L("")
    for cls_label, cls_filter in [("TUM FVG'ler", lambda f: True),
                                    ("WICK_ONLY", lambda f: f.get("rr", {}).get("max_depth_class") == "WICK_ONLY"),
                                    ("BODY_CLOSE", lambda f: f.get("rr", {}).get("max_depth_class") == "BODY_CLOSE")]:
        shallow, deep = [], []
        for coin_data in all_coin_data.values():
            for f in coin_data["fvgs"]:
                rn = f.get("rr", {})
                if not rn.get("touched") or not cls_filter(f):
                    continue
                dp = rn.get("max_depth_pct", 0)
                cont = 1 if rn.get("continuation_10") else 0
                if dp <= 50:
                    shallow.append(cont)
                else:
                    deep.append(cont)
        if len(shallow) >= 3 and len(deep) >= 3:
            sci = bootstrap_ci(shallow)
            dci = bootstrap_ci(deep)
            overlap_cont = not (dci[1] < sci[0] or dci[0] > sci[1])
            if overlap_cont:
                verdict = "ANLAMLI FARK YOK"
            else:
                verdict = f"{'Derin > Sig (yuksek depth daha iyi)' if dci[2] > sci[2] else 'Sig > Derin (dusuk depth daha iyi)'}"
            L(f"- **{cls_label}** — Sig(<=50%, n={len(shallow)}): {sci[2]:.3f} [{sci[0]:.3f},{sci[1]:.3f}] | "
              f"Derin(>50%, n={len(deep)}): {dci[2]:.3f} [{dci[0]:.3f},{dci[1]:.3f}] | {verdict}")
        else:
            L(f"- **{cls_label}** — YETERSIZ ORNEKLEM (sig={len(shallow)}, derin={len(deep)})")
    L("")
    L("---")
    L("*Auto-generated by fvg_profile_v4.py*")

    return "\n".join(lines)


# ─── Istatistik Hesaplama ────────────────────────────────────
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


# ─── Main ─────────────────────────────────────────────────────
def main():
    t0 = time.time()
    print("=" * 100)
    print("  FVG PROFILE V4 — V4 Engine ile Kapsamli FVG Karakteristik Profili")
    print(f"  Session: {SESSION_NAME} [{SESSION_HOURS['start']:02d}:00-{SESSION_HOURS['end']:02d}:00]")
    print("  Engine: V4 (live-identical) — Sweep -> RSM -> Quality -> Entry -> Trailing")
    print(f"  Coinler: {', '.join(SYMBOLS_TO_TEST)}")
    print("=" * 100)

    # QuantLogger (same as analyzer_v4)
    parquet_path = os.path.join(os.path.dirname(__file__), "..", "reports", f"trades_{SESSION_NAME.lower()}.parquet")
    global _LOGGER
    _LOGGER = QuantLogger(parquet_path)

    all_coin_data = {}
    results_data = []

    for sym in SYMBOLS_TO_TEST:
        print(f"\n  [{sym}] Profil analizi basliyor...", flush=True)
        result = collect_fvg_profile(sym)
        if result is None or result[0] is None:
            print(f"    [{sym}] VERI DOSYASI YOK", flush=True)
            continue
        daily_rows, wins, losses, trade_records, captured_fvgs = result
        if len(daily_rows) < 3:
            print(f"    [{sym}] YETERSIZ VERI", flush=True)
            continue

        stats = compute_session_stats(trade_records, cfg.INITIAL_BALANCE)
        results_data.append((sym, stats, None, daily_rows, captured_fvgs))
        all_coin_data[sym] = {"fvgs": captured_fvgs, "b15": None, "total": len(captured_fvgs)}

        print(f"    [{sym}] {stats['total_trades']} islem, {len(captured_fvgs)} FVG | "
              f"WIN:{stats['wins']} BE:{stats['be']} LOSS:{stats['losses']} | "
              f"WR={stats['win_pct']:.1f}%")

    # ── Parquet ──
    if _LOGGER is not None:
        _LOGGER.save_and_clear()
        _LOGGER = None

    # ── Summary ──
    print(f"\n{'='*100}")
    print(f"  SUMMARY — {SESSION_NAME}")
    print(f"{'='*100}")
    print(f"  {'Symbol':<10} {'Trades':>7} {'WIN':>6} {'BE':>5} {'LOSS':>6} {'WR%':>6} {'BE+%':>6} {'PF':>6} {'PnL':>10} {'FVG':>6}")
    print(f"  {'-'*70}")
    for sym, stats, _, _, fvgs in results_data:
        print(f"  {sym:<10} {stats['total_trades']:>7} {stats['wins']:>6} {stats['be']:>5} {stats['losses']:>6} "
              f"{stats['win_pct']:>5.1f}% {stats['be_plus_pct']:>5.1f}% {stats['profit_factor']:>5.2f} {stats['total_pnl']:>+9.0f} {len(fvgs):>6d}")
    print(f"\n  Total time: {time.time()-t0:.0f}s")

    # ── Load b15 for volatility analysis (re-load from cached data) ──
    for sym in all_coin_data:
        csv_path = os.path.join(os.path.dirname(__file__), "data", "daily", f"{sym}_1m_raw.csv")
        if os.path.isfile(csv_path):
            b1 = load_data(csv_path)
            b15 = resample_15m(b1)
            all_coin_data[sym]["b15"] = b15

    # ── MD Report ──
    report_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
    os.makedirs(report_dir, exist_ok=True)
    md_path = os.path.join(report_dir, "fvg_profile_v4.md")

    report = build_report(all_coin_data, results_data)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n  Rapor: {md_path}")
    print(f"  Total: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
