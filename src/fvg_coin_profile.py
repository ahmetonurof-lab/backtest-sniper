"""
fvg_coin_profile.py — Coin-Özel FVG Karakteristik Profili.

13 coin, 15m DEFAULT (22:00-02:00), 2.5 yıl veri üzerinde
her coin için ayrı ayrı mitigasyon zamanlaması, iptal eşiği,
BOS/MSS teyidi, volatilite rejimi analizi.
"""
import os, sys, random, math, time
from collections import defaultdict
from datetime import datetime, timezone

os.environ["SNIPER_OUTPUT_DIR"] = os.path.join(os.path.dirname(__file__), "..", "output")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_SRC = os.path.join(os.path.dirname(__file__), "..", "..", "sniper", "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
import config as cfg
from indicators import calculate_true_range, update_atr
from models import Bar

# ─── Parametreler ────────────────────────────────────────────
SESSION_NAME = "DEFAULT"
SESSION_HOURS = {"start": 22, "end": 2}
TIMEFRAME = "15m"
LOOKBACK_BARS = 200
ATR_PERIOD = 14
EXPANSION_ATR_MULT = 1.5
EXPANSION_BODY_RANGE_RATIO = 0.70
REJECTION_ATR_MULT = 1.0
INVALIDATION_ATR_MULT = 1.0
FEE_TAKER = 0.0004
N_BOOTSTRAP = 1000
BOOTSTRAP_SEED = 42

SYMBOLS_TO_TEST = [
    "BTCUSDT", "BNBUSDT", "SOLUSDT", "AVAXUSDT", "LINKUSDT",
    "XRPUSDT", "ATOMUSDT", "ADAUSDT", "APTUSDT", "DOTUSDT",
    "NEARUSDT", "ETHUSDT", "SUIUSDT",
]

# ─── Veri / FVG ──────────────────────────────────────────────
def load_data(filepath):
    bars = []
    with open(filepath, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            ts = int(datetime.strptime(row["open_time"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp() * 1000)
            bars.append(Bar(index=i, open=float(row["open"]), high=float(row["high"]), low=float(row["low"]), close=float(row["close"]), volume=float(row["volume"]), is_closed=True, timestamp=ts))
    return bars

def resample_15m(bars_1m):
    m15 = []
    for i in range(0, len(bars_1m), 15):
        c = bars_1m[i:i+15]
        if len(c) < 15:
            break
        m15.append(Bar(index=c[0].index, open=c[0].open, high=max(b.high for b in c), low=min(b.low for b in c), close=c[-1].close, volume=sum(b.volume for b in c), is_closed=True, timestamp=c[0].timestamp))
    return m15

import csv  # noqa: E402

def detect_fvg_3candle(c1, c2, c3, atr):
    if c3.low > c1.high:
        gap = c3.low - c1.high
        return {"direction": "bullish", "top": c3.low, "bottom": c1.high, "size": gap, "c1": c1, "c2": c2, "c3": c3, "bar_index": c2.index, "atr": atr}
    if c1.low > c3.high:
        gap = c1.low - c3.high
        return {"direction": "bearish", "top": c1.low, "bottom": c3.high, "size": gap, "c1": c1, "c2": c2, "c3": c3, "bar_index": c2.index, "atr": atr}
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
        expansion_body = c3.close - c3.open if c3.close >= c3.open else c3.high - c3.open
        expansion_body = max(c3.close - c3.open, c3.high - c3.open)
        broke_c2_high = c3.high > c2.high
        if c3.close < c3.open and rejection_body >= atr * REJECTION_ATR_MULT and body_range_ratio >= EXPANSION_BODY_RANGE_RATIO:
            return "REJECTION"
        if expansion_body >= atr * EXPANSION_ATR_MULT and body_range_ratio >= EXPANSION_BODY_RANGE_RATIO and broke_c2_high:
            return "EXPANSION"
    else:
        rejection_body = c3.high - c3.close if c3.close > c3.open else c3.high - c3.open
        expansion_body = c3.open - c3.close if c3.close <= c3.open else c3.open - c3.low
        expansion_body = max(c3.open - c3.close, c3.open - c3.low)
        broke_c2_low = c3.low < c2.low
        if c3.close > c3.open and rejection_body >= atr * REJECTION_ATR_MULT and body_range_ratio >= EXPANSION_BODY_RANGE_RATIO:
            return "REJECTION"
        if expansion_body >= atr * EXPANSION_ATR_MULT and body_range_ratio >= EXPANSION_BODY_RANGE_RATIO and broke_c2_low:
            return "EXPANSION"
    return "CONSOLIDATION"

def track_fvg_outcome(fvg, bars_after):
    direction = fvg["direction"]
    fvg_top, fvg_bottom = fvg["top"], fvg["bottom"]
    fvg_index = fvg["bar_index"]
    atr = fvg["atr"]
    result = {"mitigated": False, "mitigate_bar": None, "mitigate_price": None, "bars_to_mitigate": None, "continuation_10": None, "continuation_20": None, "continuation_40": None, "continuation": None, "invalidated": False, "invalidate_bar": None, "max_excursion": 0.0, "max_excursion_dir": None, "bars_tracked": 0, "close_price_at_end": None}
    invalidate_dist = atr * INVALIDATION_ATR_MULT
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

def simulate_rr(fvg, bars_after):
    direction = fvg["direction"]
    atr = fvg["atr"]
    fvg_top, fvg_bottom = fvg["top"], fvg["bottom"]
    entry = (fvg_top + fvg_bottom) / 2
    if direction == "bullish":
        stop = fvg_bottom - atr * 1.0
        target = entry + (entry - stop) * 2.0
    else:
        stop = fvg_top + atr * 1.0
        target = entry - (stop - entry) * 2.0
    risk = abs(entry - stop)
    risk_pct = risk / entry if entry > 0 else 0.001
    fee_per_leg_R = FEE_TAKER / risk_pct
    result = {"entry": entry, "stop": stop, "target": target, "risk": risk, "reward": abs(target - entry), "rr": abs(target - entry)/risk if risk > 0 else 0, "hit_target": False, "hit_stop": False, "no_fill": False, "no_outcome": False, "fee_per_leg_R": fee_per_leg_R, "net_profit_R": 0.0}
    entered, entry_offset = False, 0
    for offset, b in enumerate(bars_after[:LOOKBACK_BARS]):
        if b.low <= entry <= b.high:
            entered, entry_offset = True, offset
            break
    if not entered:
        result["no_fill"] = True
        return result
    for b in bars_after[entry_offset:entry_offset + LOOKBACK_BARS]:
        hit_stop = b.low <= stop if direction == "bullish" else b.high >= stop
        hit_target = b.high >= target if direction == "bullish" else b.low <= target
        if hit_stop:
            result["hit_stop"] = True; result["net_profit_R"] = -1.0 - 2.0*fee_per_leg_R; return result
        if hit_target:
            result["hit_target"] = True; result["net_profit_R"] = 2.0 - 2.0*fee_per_leg_R; return result
    result["no_outcome"] = True; result["net_profit_R"] = -2.0*fee_per_leg_R; return result

# ─── Analiz ──────────────────────────────────────────────────
def analyze_coin(symbol):
    csv_path = os.path.join(os.path.dirname(__file__), "data", "daily", f"{symbol}_1m_raw.csv")
    if not os.path.isfile(csv_path):
        return None, None
    b1 = load_data(csv_path)
    b15 = resample_15m(b1)
    if not b15:
        return None, None
    sh, eh = SESSION_HOURS["start"], SESSION_HOURS["end"]
    spans_midnight = sh > eh
    atr_val = 0.0
    prev_close = b15[0].open
    for bar in b15[1:500]:
        tr = calculate_true_range(bar, prev_close)
        atr_val = update_atr(atr_val if atr_val > 0 else None, tr)
        prev_close = bar.close
    fvgs, total_bars = [], len(b15)
    for sb in range(500, total_bars):
        cur = b15[sb]
        atr = atr_val
        tr = calculate_true_range(cur, prev_close)
        atr_val = update_atr(atr_val if atr_val > 0 else None, tr)
        prev_close = cur.close
        try:
            edt = datetime.fromtimestamp(cur.timestamp / 1000, tz=timezone.utc)
        except Exception:
            continue
        h = edt.hour
        in_session = (h >= sh or h < eh) if spans_midnight else (sh <= h < eh)
        if not in_session:
            continue
        if sb < 2:
            continue
        c1, c2, c3 = b15[sb-2], b15[sb-1], b15[sb]
        fvg_data = detect_fvg_3candle(c1, c2, c3, atr)
        if fvg_data is None:
            continue
        if fvg_data["size"] < atr * 0.1:
            continue
        fvg_data["category"] = classify_c3(fvg_data)
        fvg_data["atr_used"] = atr
        fvg_data["tr_of_c3"] = tr
        fvg_data["atr_after_c3"] = atr_val
        fvg_data["fvg_hour"] = h
        fvg_data["timestamp"] = c3.timestamp
        fvg_data["day_of_week"] = edt.weekday()
        bars_after = b15[sb+1:min(sb+LOOKBACK_BARS, total_bars)]
        fvg_data["outcome"] = track_fvg_outcome(fvg_data, bars_after)
        fvg_data["rr"] = simulate_rr(fvg_data, bars_after)
        fvg_data["bar_slice_start"] = max(0, sb-50)
        fvg_data["bar_slice_end"] = min(total_bars, sb+LOOKBACK_BARS)
        fvgs.append(fvg_data)
    return fvgs, b15

# ─── BOS/MSS ─────────────────────────────────────────────────
def find_all_swing_points(b15):
    """Pre-compute ALL fractal swing points once per coin."""
    hi_idx, hi_pr, lo_idx, lo_pr = [], [], [], []
    for i in range(2, len(b15)-2):
        h, l = b15[i].high, b15[i].low
        if (h > b15[i-2].high and h > b15[i-1].high and h > b15[i+1].high and h > b15[i+2].high):
            hi_idx.append(b15[i].index); hi_pr.append(h)
        if (l < b15[i-2].low and l < b15[i-1].low and l < b15[i+1].low and l < b15[i+2].low):
            lo_idx.append(b15[i].index); lo_pr.append(l)
    return (hi_idx, hi_pr), (lo_idx, lo_pr)

def _filter_swings(c3_idx, hi, lo):
    sw_h = [(hi[0][i], hi[1][i]) for i in range(len(hi[0])) if c3_idx-50 <= hi[0][i] < c3_idx]
    sw_l = [(lo[0][i], lo[1][i]) for i in range(len(lo[0])) if c3_idx-50 <= lo[0][i] < c3_idx]
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
    # Pre window (20 bars before C3) — max/min close shortcut
    pre_start = max(0, c3_idx-20)
    pre_closes = [b.close for b in b15[pre_start:c3_idx] if b.index < c3_idx] if c3_idx > pre_start else []
    pre_max_c = max(pre_closes, default=0)
    pre_min_c = min(pre_closes, default=0)
    pre_bos = any(idx < c3_idx and pre_max_c > pr for idx, pr in sw_h) if trend == "uptrend" else (
               any(idx < c3_idx and pre_min_c < pr for idx, pr in sw_l) if trend == "downtrend" else False)
    pre_mss = any(idx < c3_idx and pre_min_c < pr for idx, pr in sw_l) if trend == "uptrend" else (
               any(idx < c3_idx and pre_max_c > pr for idx, pr in sw_h) if trend == "downtrend" else
               any(idx < c3_idx and pre_max_c > pr for idx, pr in sw_h) or any(idx < c3_idx and pre_min_c < pr for idx, pr in sw_l))
    post_end = min(c3_idx+21, len(b15))
    post_closes = [b.close for b in b15[c3_idx+1:post_end] if b.index > c3_idx] if post_end > c3_idx+1 else []
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
    return {"pre_bos": pre_bos, "pre_mss": pre_mss, "post_bos": post_bos, "post_mss": post_mss, "trend": trend, "group": group}

# ─── İstatistik ──────────────────────────────────────────────
def percentile_sorted(vals, p):
    if not vals:
        return 0
    idx = max(0, min(len(vals)-1, int(len(vals)*p/100)))
    return vals[idx]

def cumulative_mit_curve(fvgs, max_b=200):
    mit_times = sorted([f["outcome"]["bars_to_mitigate"] for f in fvgs if f["outcome"]["mitigated"] and f["outcome"]["bars_to_mitigate"] is not None])
    total = len(fvgs)
    if total == 0:
        return [], 0
    curve = []
    dr = max_b
    prev_pct = 0
    for n in [1,2,3,5,10,20,30,50,75,100,150,200]:
        cnt = sum(1 for t in mit_times if t < n) if mit_times else 0
        pct = cnt/total*100
        curve.append((n, pct))
        if n > 1 and prev_pct > 0 and (pct-prev_pct) < 1.0 and dr == max_b:
            dr = n
        prev_pct = pct
    return curve, dr if dr != max_b else 200

def conditional_cancel(fvgs, max_b=200):
    mit = sorted([f["outcome"]["bars_to_mitigate"] for f in fvgs if f["outcome"]["mitigated"] and f["outcome"]["bars_to_mitigate"] is not None])
    total = len(fvgs)
    if total == 0:
        return []
    res = []
    for n in [5,10,20,30,50,75,100,150,200]:
        still_open = sum(1 for f in fvgs if not f["outcome"]["mitigated"] or (f["outcome"]["bars_to_mitigate"] is not None and f["outcome"]["bars_to_mitigate"] >= n))
        will_mit = sum(1 for t in mit if t >= n) if mit else 0
        prob = will_mit/still_open*100 if still_open > 0 else 0
        res.append((n, prob, still_open))
    return res

def bootstrap_ci(vals, n_resamples=N_BOOTSTRAP, ci=95, seed=BOOTSTRAP_SEED):
    n = len(vals)
    if n < 3:
        return (None, None, sum(vals)/n if n else 0)
    rng = random.Random(seed)
    means = []
    for _ in range(n_resamples):
        s = 0.0
        for _ in range(n):
            s += vals[rng.randint(0, n-1)]
        means.append(s/n)
    alpha = (100-ci)/2
    lo = sorted(means)[int(n_resamples*alpha/100)]
    hi = sorted(means)[int(n_resamples*(100-alpha)/100)]
    return (lo, hi, sum(vals)/n)

# ─── Volatilite Rejimi ───────────────────────────────────────
def volatility_regime_analysis(fvgs, b15, window=50):
    """Classify each FVG's regime based on rolling ATR percentile."""
    atr_vals = [b15[i].high-b15[i].low for i in range(len(b15))]
    regime_results = defaultdict(lambda: {"count": 0, "mitigated": 0, "bars": [], "profits": [], "continuation_10": 0})
    for f in fvgs:
        idx = f["c3"].index
        lo = max(0, idx-window)
        recent_atr = atr_vals[lo:idx]
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
        if f["rr"].get("hit_target") or f["rr"].get("hit_stop"):
            r["profits"].append(f["rr"]["net_profit_R"])
        elif f["rr"].get("no_outcome"):
            r["profits"].append(f["rr"]["net_profit_R"])
    return dict(regime_results)

# ─── Ana Rapor ───────────────────────────────────────────────
def build_report(all_coin_data):
    lines = []
    def L(s=""):
        lines.append(s)
    L("# Coin-Özel FVG Karakteristik Profili")
    L(f"**Session:** {SESSION_NAME} [{SESSION_HOURS['start']:02d}:00-{SESSION_HOURS['end']:02d}:00]  **TF:** {TIMEFRAME}")
    L(f"**Coinler:** {', '.join(SYMBOLS_TO_TEST)}")
    L(f"**Tarih:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    L("")
    L("---")
    L("")
    L("## 1. Coin × Kategori Ana Tablo")
    L("")
    H = ["Coin", "Kat", "N", "Mit%", "Inv%", "p50Bar", "p90Bar", "Cont@10", "Cont@40", "RR_WR", "NetExp", "n<30?"]
    L("| " + " | ".join(H) + " |")
    L("|" + "|".join(["-"*6]*len(H)) + "|")

    coin_best = {}
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
            mit_pct = mit/n*100
            inv_pct = inv/n*100
            mtimes = sorted([f["outcome"]["bars_to_mitigate"] for f in cf if f["outcome"]["mitigated"] and f["outcome"]["bars_to_mitigate"] is not None])
            p50 = percentile_sorted(mtimes, 50) if mtimes else 0
            p90 = percentile_sorted(mtimes, 90) if mtimes else 0
            cont10 = sum(1 for f in cf if f["outcome"].get("continuation_10"))/max(mit,1)*100
            cont40 = sum(1 for f in cf if f["outcome"].get("continuation_40"))/max(mit,1)*100
            wins = sum(1 for f in cf if f["rr"].get("hit_target"))
            losses = sum(1 for f in cf if f["rr"].get("hit_stop"))
            rt = wins+losses
            wr = wins/rt*100 if rt > 0 else 0
            profits = [f["rr"]["net_profit_R"] for f in cf if f["rr"].get("hit_target") or f["rr"].get("hit_stop")]
            net_exp = sum(profits)/len(profits) if profits else 0
            warn = "⚠️" if n < 30 else ""
            L(f"| {sym:<8s} | {cat:<13s} | {n:>4d} | {mit_pct:>5.1f} | {inv_pct:>5.1f} | {p50:>4d} | {p90:>4d} | {cont10:>5.1f} | {cont40:>5.1f} | {wr:>5.1f} | {net_exp:>+6.2f}R | {warn:>4s} |")
            ci = bootstrap_ci(profits) if len(profits) >= 3 else (None, None, None)
            if cat not in coin_best or (ci[2] is not None and (coin_best[cat].get("exp") is None or ci[2] > coin_best[cat]["exp"])):
                coin_best[cat] = {"coin": sym, "exp": ci[2], "ci_lo": ci[0], "ci_hi": ci[1], "n": n}

    L("")
    L("---")
    L("")

    # ─── Mitigasyon Zamanlaması ───────────────────────────
    L("## 2. Mitigasyon Zamanlaması")
    L("")
    L("### 2a. Persentil Tablosu (bar-to-mitigate)")
    L("")
    H2 = ["Coin", "Kategori", "N_mit", "p25", "p50", "p75", "p90", "Ortalama"]
    L("| " + " | ".join(H2) + " |")
    L("|" + "|".join(["-"*6]*len(H2)) + "|")
    for sym, coin_data in all_coin_data.items():
        fvgs = coin_data["fvgs"]
        cats = defaultdict(list)
        for f in fvgs:
            cats[f["category"]].append(f)
        for cat in ["CONSOLIDATION", "EXPANSION", "REJECTION"]:
            cf = cats.get(cat, [])
            mtimes = sorted([f["outcome"]["bars_to_mitigate"] for f in cf if f["outcome"]["mitigated"] and f["outcome"]["bars_to_mitigate"] is not None])
            if not mtimes:
                continue
            m25 = percentile_sorted(mtimes, 25)
            m50 = percentile_sorted(mtimes, 50)
            m75 = percentile_sorted(mtimes, 75)
            m90 = percentile_sorted(mtimes, 90)
            avg = sum(mtimes)/len(mtimes)
            L(f"| {sym:<8s} | {cat:<13s} | {len(mtimes):>5d} | {m25:>4d} | {m50:>4d} | {m75:>4d} | {m90:>4d} | {avg:>6.1f} |")

    L("")
    L("### 2b. Kümülatif Mitigasyon Eğrisi & Diminishing Returns")
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
    L("### 2c. Koşullu İptal Eşiği (Cancel Threshold)")
    L("")
    L("P(mitigate | henüz mitigate olmadı VE N bar geçti)")
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
            for n, prob, still in cc:
                if n in [5,10,20,30,50,75,100,150]:
                    row.append(f"{prob:.0f}%")
            L("| " + " | ".join(row) + " |")

    L("")
    L("### 2d. Önerilen İptal Eşiği (diminishing returns noktası)")
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
    L("---")
    L("")

    # ─── FVG Boyutu / ATR ────────────────────────────────
    L("## 3. FVG Boyutu / ATR Oranı")
    L("")
    L("### 3a. gap/ATR dağılımı")
    L("")
    L("| Coin | Kons. medyan | Kons. p75 | Exp. medyan | Exp. p75 | Rej. medyan | Rej. p75 |")
    L("|---|---|---|---|---|---|---|---|")
    for sym, coin_data in all_coin_data.items():
        fvgs = coin_data["fvgs"]
        cats = defaultdict(list)
        for f in fvgs:
            cats[f["category"]].append(f)
        row = [f"{sym:<8s}"]
        for cat in ["CONSOLIDATION", "EXPANSION", "REJECTION"]:
            cf = cats.get(cat, [])
            ratios = sorted([f["size"]/max(f["atr"],0.0001) for f in cf])
            if ratios:
                row.append(f"{percentile_sorted(ratios,50):.2f}")
                row.append(f"{percentile_sorted(ratios,75):.2f}")
            else:
                row.append("-")
                row.append("-")
        L("| " + " | ".join(row) + " |")

    L("")
    L("### 3b. gap/ATR × Kategori (2×3 tablosu — mitigasyon oranı)")
    L("")
    L("| FVG Boyutu | CONS Mit% | EXP Mit% | REJ Mit% |")
    L("|---|---|---|---|")
    for size_label, lo, hi in [("Küçük (<0.5xATR)", 0, 0.5), ("Orta (0.5-1.5xATR)", 0.5, 1.5), ("Büyük (>1.5xATR)", 1.5, 999)]:
        row = [size_label]
        for cat in ["CONSOLIDATION", "EXPANSION", "REJECTION"]:
            all_f = []
            for coin_data in all_coin_data.values():
                for f in coin_data["fvgs"]:
                    if f["category"] == cat:
                        ratio = f["size"]/max(f["atr"],0.0001)
                        if lo <= ratio < hi:
                            all_f.append(f)
            n = len(all_f)
            mit = sum(1 for f in all_f if f["outcome"]["mitigated"])
            row.append(f"{mit/max(n,1)*100:.1f}% (n={n})")
        L("| " + " | ".join(row) + " |")

    L("")
    L("---")
    L("")

    # ─── Volatilite Rejimi ────────────────────────────────
    L("## 4. Volatilite Rejimi Analizi")
    L("")
    L("Her FVG'nin oluştuğu dönemdeki ATR'nin son 50 bar içindeki percentile'ına göre LOV/MID/HIGH rejim.")
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
                mit_pct = mit/max(n,1)*100
                bars = rr.get("bars", [])
                med_bar = percentile_sorted(sorted(bars), 50) if bars else 0
                cont = rr.get("continuation_10", 0)
                cont_pct = cont/max(mit,1)*100
                profs = rr.get("profits", [])
                ne = sum(profs)/len(profs) if profs else 0
                L(f"| {sym:<8s} | {cat:<13s} | {regime_name:>4s} | {n:>4d} | {mit_pct:>5.1f} | {med_bar:>4d} | {cont_pct:>5.1f} | {ne:>+6.2f}R |")

    L("")
    L("---")
    L("")

    # ─── Hafta İçi Etkisi ─────────────────────────────────
    L("## 5. Hafta İçi / Hafta Sonu Etkisi")
    L("")
    L("| Coin | Kategori | Haftaiçi N | Hftiçi Mit% | Hftiçi NetExp | Haftasonu N | Hftsonu Mit% | Hftsonu NetExp |")
    L("|---|---|---|---|---|---|---|---|")
    dow_names = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
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
            def stats(grp):
                n = len(grp)
                mit = sum(1 for f in grp if f["outcome"]["mitigated"])/max(n,1)*100
                profs = []
                for f in grp:
                    if f["rr"].get("hit_target") or f["rr"].get("hit_stop"):
                        profs.append(f["rr"]["net_profit_R"])
                ne = sum(profs)/len(profs) if profs else 0
                return n, mit, ne
            wn, wm, wexp = stats(wd)
            wen, wem, weexp = stats(we)
            L(f"| {sym:<8s} | {cat:<13s} | {wn:>5d} | {wm:>5.1f} | {wexp:>+7.2f}R | {wen:>5d} | {wem:>5.1f} | {weexp:>+7.2f}R |")

    L("")
    L("---")
    L("")

    # ─── BOS/MSS Analizi ──────────────────────────────────
    L("## 6. BOS / MSS Yapı Kırılımı Analizi")
    L("")
    L("**Uyarı:** BOS/MSS alt grupları örneklemi böldüğü için çoğu hücrede n çok küçük kalabilir. n<30 olan hücreler bilgi amaçlıdır, yorumlanmamalıdır.")
    L("")
    L("### 6a. Kategori × Yapı Grubu Tablosu")
    L("")
    H6 = ["Kategori", "Yapı", "N", "Mit%", "Cont@10%", "RR_WR%", "NetExp", "n<30?"]
    L("| " + " | ".join(H6) + " |")
    L("|" + "|".join(["-"*6]*len(H6)) + "|")
    for cat in ["CONSOLIDATION", "EXPANSION", "REJECTION"]:
        groups = defaultdict(list)
        for coin_data in all_coin_data.values():
            for f in coin_data["fvgs"]:
                if f["category"] == cat:
                    bos = f.get("bos_mss", {})
                    groups[bos.get("group", "NONE")].append(f)
        for grp_name in ["NONE", "BOS_ONLY", "MSS_ONLY", "BOTH"]:
            grp = groups.get(grp_name, [])
            n = len(grp)
            if n == 0:
                continue
            mit = sum(1 for f in grp if f["outcome"]["mitigated"])/max(n,1)*100
            mit_count = sum(1 for f in grp if f["outcome"]["mitigated"])
            cont10 = sum(1 for f in grp if f["outcome"].get("continuation_10"))/max(mit_count,1)*100
            wins = sum(1 for f in grp if f["rr"].get("hit_target"))
            losses = sum(1 for f in grp if f["rr"].get("hit_stop"))
            rt = wins+losses
            wr = wins/rt*100 if rt > 0 else 0
            profs = [f["rr"]["net_profit_R"] for f in grp if f["rr"].get("hit_target") or f["rr"].get("hit_stop")]
            ne = sum(profs)/len(profs) if profs else 0
            warn = "⚠️" if n < 30 else ""
            L(f"| {cat:<13s} | {grp_name:<9s} | {n:>4d} | {mit:>5.1f} | {cont10:>5.1f} | {wr:>5.1f} | {ne:>+6.2f}R | {warn:>4s} |")

    L("")
    L("### 6b. Hipotez Testi: Teyitli (BOS/MSS) vs Teyitsiz (NONE)")
    L("")
    for cat in ["CONSOLIDATION", "EXPANSION", "REJECTION"]:
        groups = defaultdict(list)
        for coin_data in all_coin_data.values():
            for f in coin_data["fvgs"]:
                if f["category"] == cat:
                    groups[f.get("bos_mss", {}).get("group", "NONE")].append(f)
        none_profs = [f["rr"]["net_profit_R"] for f in groups.get("NONE", []) if f["rr"].get("hit_target") or f["rr"].get("hit_stop")]
        none_ci = bootstrap_ci(none_profs) if len(none_profs) >= 3 else (None, None, None)
        for grp_name in ["BOS_ONLY", "MSS_ONLY", "BOTH"]:
            grp = groups.get(grp_name, [])
            grp_profs = [f["rr"]["net_profit_R"] for f in grp if f["rr"].get("hit_target") or f["rr"].get("hit_stop")]
            grp_ci = bootstrap_ci(grp_profs) if len(grp_profs) >= 3 else (None, None, None)
            if none_ci[0] is None or grp_ci[0] is None:
                L(f"| {cat:<13s} | {grp_name:<9s} | YETERSIZ ÖRNEKLEM |")
                continue
            overlap = not (grp_ci[1] < none_ci[0] or grp_ci[0] > none_ci[1])
            verdict = "ANLAMLI FARK YOK" if overlap else f"✅ FARK VAR - {grp_name} {'daha iyi' if grp_ci[2] > none_ci[2] else 'daha kötü'}"
            L(f"| {cat:<13s} | {grp_name:<9s} | NONE(n={len(none_profs)}): {none_ci[2]:>+.2f}R [{none_ci[0]:>+.2f}, {none_ci[1]:>+.2f}] | {grp_name}(n={len(grp_profs)}): {grp_ci[2]:>+.2f}R [{grp_ci[0]:>+.2f}, {grp_ci[1]:>+.2f}] | {verdict} |")

    L("")
    L("---")
    L("")

    # ─── Coin Bazlı Öneri ─────────────────────────────────
    L("## 7. Coin → Önerilen Kategori")
    L("")
    L("Her coin için en yüksek net expectancy veren kategori (sadece n>=30, bootstrap CI sıfırı kapsamıyorsa)")
    L("")
    L("| Coin | CONS exp | CONS CI | EXP exp | EXP CI | REJ exp | REJ CI | Öneri |")
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
            best = "BELİRSİZ"
        row.append(best)
        L("| " + " | ".join(row) + " |")

    L("")
    L("---")
    L("")

    # ─── Nihai Değerlendirme ──────────────────────────────
    L("## 8. Nihai Değerlendirme: ICT FVG Modeli Coin Bazında Anlamlı mı?")
    L("")
    for sym, coin_data in all_coin_data.items():
        fvgs = coin_data["fvgs"]
        cats = defaultdict(list)
        for f in fvgs:
            cats[f["category"]].append(f)
        L(f"### {sym}")
        L("")
        assessments = []
        for cat in ["CONSOLIDATION", "EXPANSION", "REJECTION"]:
            cf = cats.get(cat, [])
            n = len(cf)
            profs = [f["rr"]["net_profit_R"] for f in cf if f["rr"].get("hit_target") or f["rr"].get("hit_stop")]
            ci = bootstrap_ci(profs) if len(profs) >= 3 else (None, None, None)
            if ci[0] is None:
                assessments.append(f"- **{cat}:** n={n}, yetersiz örneklem")
            elif ci[1] < 0:
                assessments.append(f"- **{cat}:** n={n}, exp={ci[2]:+.2f}R [{ci[0]:+.2f}, {ci[1]:+.2f}] — **negatif expectancy, kaçınılmalı**")
            elif ci[0] > 0:
                assessments.append(f"- **{cat}:** n={n}, exp={ci[2]:+.2f}R [{ci[0]:+.2f}, {ci[1]:+.2f}] — **✅ anlamlı edge**")
            else:
                assessments.append(f"- **{cat}:** n={n}, exp={ci[2]:+.2f}R [{ci[0]:+.2f}, {ci[1]:+.2f}] — sıfırı kapsıyor, belirsiz")
        for a in assessments:
            L(a)
        L("")

    L("---")
    L("*Auto-generated by fvg_coin_profile.py*")
    return "\n".join(lines)

def main():
    t0 = time.time()
    print("="*80)
    print("  COIN-ÖZEL FVG KARAKTERİSTİK PROFİLİ")
    print(f"  Session: {SESSION_NAME}  TF: {TIMEFRAME}")
    print(f"  Coinler: {', '.join(SYMBOLS_TO_TEST)}")
    print("="*80)

    all_coin_data = {}
    for sym in SYMBOLS_TO_TEST:
        print(f"\n  [{sym}] Analiz ediliyor...", flush=True)
        fvgs, b15 = analyze_coin(sym)
        if not fvgs:
            print(f"    [{sym}] VERI YOK")
            continue
        print(f"    [{sym}] {len(fvgs)} FVG, swing noktalari hesaplaniyor...", flush=True)
        hi, lo = find_all_swing_points(b15)
        print(f"    [{sym}] BOS/MSS hesaplaniyor ({len(fvgs)} FVG)...", flush=True)
        for idx, f in enumerate(fvgs):
            bos_mss = detect_bos_mss(f, b15, hi, lo)
            f["bos_mss"] = bos_mss
        all_coin_data[sym] = {"fvgs": fvgs, "b15": b15, "total": len(fvgs)}
        print(f"    [{sym}] {len(fvgs)} FVG tamam")

    print(f"\n  Toplam süre: {time.time()-t0:.0f}s")

    if not all_coin_data:
        print("  Hiç veri yok!")
        return

    print("\n  Rapor oluşturuluyor...")
    report = build_report(all_coin_data)

    report_path = os.path.join(os.path.dirname(__file__), "..", "reports", "fvg_coin_profile.md")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"  Rapor: {report_path}")
    print(f"  Toplam: {time.time()-t0:.0f}s")

if __name__ == "__main__":
    main()
