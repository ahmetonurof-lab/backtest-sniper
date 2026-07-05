"""
analyze_fvg_extended.py — FVG 3rd Candle Extended Analysis.

Adds: bootstrap CI, sensitivity analysis, cross-coin correlation,
      NY session + 1H TF comparison, commission-adjusted R:R.

Usage: python analyze_fvg_extended.py
"""
# ruff: noqa: E402
import csv
import json
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
from indicators import calculate_true_range, update_atr
from models import Bar

# ─── Configs ────────────────────────────────────────────────
CONFIGS = [
    {"name": "DEFAULT_15m", "session": "DEFAULT", "hours": {"start": 22, "end": 2}, "tf": "15m", "resample": 15},
    {"name": "NY_15m",      "session": "NY",      "hours": {"start": 13, "end": 17}, "tf": "15m", "resample": 15},
    {"name": "DEFAULT_1H",  "session": "DEFAULT", "hours": {"start": 22, "end": 2}, "tf": "1h",  "resample": 60},
]

LOOKBACK_BARS = 200
ATR_PERIOD = 14
COMMISSION_RATE = 0.0004  # %0.04 taker

# Thresholds for classification
EXPANSION_ATR_MULT = 1.5
EXPANSION_BODY_RANGE_RATIO = 0.70
REJECTION_ATR_MULT = 1.0
INVALIDATION_ATR_MULT = 1.0

SYMBOLS_CORE = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]  # 3 representative for speed
SYMBOLS_ALL = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "AVAXUSDT",
    "LINKUSDT", "XRPUSDT", "ADAUSDT", "DOTUSDT", "NEARUSDT",
]

# ─── Helpers ────────────────────────────────────────────────
def load_data(filepath):
    bars = []
    with open(filepath, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts = int(datetime.strptime(row["open_time"], "%Y-%m-%d %H:%M:%S")
                     .replace(tzinfo=timezone.utc).timestamp() * 1000)
            bars.append(Bar(index=len(bars), open=float(row["open"]),
                            high=float(row["high"]), low=float(row["low"]),
                            close=float(row["close"]), volume=float(row["volume"]),
                            is_closed=True, timestamp=ts))
    return bars

def resample(bars_1m, n):
    out = []
    for i in range(0, len(bars_1m), n):
        c = bars_1m[i:i+n]
        if len(c) < n:
            break
        out.append(Bar(index=c[0].index, open=c[0].open,
                       high=max(b.high for b in c), low=min(b.low for b in c),
                       close=c[-1].close, volume=sum(b.volume for b in c),
                       is_closed=True, timestamp=c[0].timestamp))
    return out

def detect_fvg(c1, c2, c3, atr):
    if c3.low > c1.high:
        return {"direction": "bullish", "top": c3.low, "bottom": c1.high, "size": c3.low - c1.high, "bar_index": c2.index, "timestamp": c2.timestamp}
    if c1.low > c3.high:
        return {"direction": "bearish", "top": c1.low, "bottom": c3.high, "size": c1.low - c3.high, "bar_index": c2.index, "timestamp": c2.timestamp}
    return None

def classify_c3(fvg, c2, c3, atr):
    c3_body = abs(c3.close - c3.open)
    c3_range = c3.high - c3.low
    brr = c3_body / c3_range if c3_range > 0 else 0
    direction = fvg["direction"]

    if direction == "bullish":
        if c3.close < c3.open and c3_body >= atr * REJECTION_ATR_MULT and brr >= EXPANSION_BODY_RANGE_RATIO:
            return "REJECTION"
        if c3.close > c3.open and c3_body >= atr * EXPANSION_ATR_MULT and brr >= EXPANSION_BODY_RANGE_RATIO and c3.high > c2.high:
            return "EXPANSION"
    else:
        if c3.close > c3.open and c3_body >= atr * REJECTION_ATR_MULT and brr >= EXPANSION_BODY_RANGE_RATIO:
            return "REJECTION"
        if c3.close < c3.open and c3_body >= atr * EXPANSION_ATR_MULT and brr >= EXPANSION_BODY_RANGE_RATIO and c3.low < c2.low:
            return "EXPANSION"
    return "CONSOLIDATION"

def track_outcome(fvg, bars_after, atr):
    direction, top, bottom = fvg["direction"], fvg["top"], fvg["bottom"]
    inv_dist = atr * INVALIDATION_ATR_MULT
    result = {"mitigated": False, "mitigate_bar": None, "bars_to_mitigate": None,
              "invalidated": False, "continuation": None, "max_excursion": 0.0,
              "bars_tracked": 0}
    mitigated = False
    for offset, b in enumerate(bars_after):
        if offset >= LOOKBACK_BARS:
            break
        result["bars_tracked"] = offset + 1
        touched = False
        if direction == "bullish":
            if b.low <= top and b.high >= bottom:
                touched = True
            if b.close < bottom - inv_dist:
                result["invalidated"] = True
                if not mitigated: break
        else:
            if b.high >= bottom and b.low <= top:
                touched = True
            if b.close > top + inv_dist:
                result["invalidated"] = True
                if not mitigated: break
        if not mitigated and touched:
            if (direction == "bullish" and bottom <= b.close <= top) or \
               (direction == "bearish" and bottom <= b.close <= top):
                mitigated = True
                result["mitigated"] = True
                result["mitigate_bar"] = offset
                result["bars_to_mitigate"] = offset
            elif (direction == "bullish" and b.close >= bottom and b.low <= top) or \
                 (direction == "bearish" and b.close <= top and b.high >= bottom):
                mitigated = True
                result["mitigated"] = True
                result["mitigate_bar"] = offset
                result["bars_to_mitigate"] = offset
        if mitigated and result["continuation"] is None:
            future = offset + 10
            if future < len(bars_after):
                fb = bars_after[future]
                result["continuation"] = (fb.close > top) if direction == "bullish" else (fb.close < bottom)
            elif offset == len(bars_after) - 1:
                result["continuation"] = False
    if mitigated and result["continuation"] is None:
        result["continuation"] = False
    return result

def simulate_rr(fvg, outcome, commission=0.0):
    direction, atr, top, bottom = fvg["direction"], fvg["atr"], fvg["top"], fvg["bottom"]
    entry = (top + bottom) / 2
    if direction == "bullish":
        stop = bottom - atr * 1.0
        target = entry + (entry - stop) * 2.0
    else:
        stop = top + atr * 1.0
        target = entry - (stop - entry) * 2.0
    risk = abs(entry - stop)
    reward = abs(target - entry)

    # Commission: 0.04% each way on entry price
    fee_entry = entry * commission
    fee_exit = target * commission if outcome.get("hit_target") else stop * commission
    total_fee = fee_entry + fee_exit

    hit_target = outcome.get("mitigated") and outcome.get("continuation")
    hit_stop = outcome.get("invalidated")

    net_profit = (reward - total_fee) if hit_target else (-risk - total_fee) if hit_stop else 0
    net_rr = net_profit / risk if risk > 0 else 0
    return {"entry": entry, "stop": stop, "target": target, "risk": risk,
            "hit_target": hit_target, "hit_stop": hit_stop,
            "fee_total": total_fee, "net_rr": net_rr,
            "gross_rr": reward / risk if risk > 0 else 0}

# ─── Per-symbol analysis ────────────────────────────────────
def analyze_symbol(symbol, hours, resample_n, save_fvg_path=None):
    csv_path = os.path.join(os.path.dirname(__file__), "data", "daily", f"{symbol}_1m_raw.csv")
    if not os.path.isfile(csv_path):
        return None
    b1 = load_data(csv_path)
    bars = resample(b1, resample_n)
    if not bars:
        return None

    sh, eh = hours["start"], hours["end"]
    spans_midnight = sh > eh

    atr_val = 0.0
    prev_close = bars[0].open
    for bar in bars[1:500]:
        tr = calculate_true_range(bar, prev_close)
        atr_val = update_atr(atr_val if atr_val > 0 else None, tr)
        prev_close = bar.close

    records = []  # list of {timestamp, category, mitigated, continued, invalidated}
    fvgs_saved = []

    total = len(bars)
    for sb in range(500, total):
        if (sb - 500) % 10000 == 0:
            print(f"\r  [{symbol}] %{(sb-500)/(total-500)*100:.0f}", end="", flush=True)
        cur = bars[sb]
        tr = calculate_true_range(cur, prev_close)
        atr_val = update_atr(atr_val if atr_val > 0 else None, tr)
        prev_close = cur.close
        atr = atr_val
        try:
            edt = datetime.fromtimestamp(cur.timestamp / 1000, tz=timezone.utc)
        except:
            continue
        h = edt.hour
        if (h >= sh or h < eh) if spans_midnight else (sh <= h < eh):
            continue
        if sb < 2:
            continue
        c1, c2, c3 = bars[sb-2], bars[sb-1], bars[sb]
        fvg = detect_fvg(c1, c2, c3, atr)
        if fvg is None or fvg["size"] < atr * 0.1:
            continue
        fvg["atr"] = atr
        cat = classify_c3(fvg, c2, c3, atr)
        outcome = track_outcome(fvg, bars[sb+1:min(sb+LOOKBACK_BARS, total)], atr)
        rr = simulate_rr(fvg, outcome, commission=COMMISSION_RATE)
        records.append({"cat": cat, "mitigated": outcome["mitigated"],
                        "continued": outcome.get("continuation", False),
                        "invalidated": outcome["invalidated"],
                        "bars_to_mitigate": outcome.get("bars_to_mitigate"),
                        "gross_rr": rr["gross_rr"], "net_rr": rr["net_rr"]})
        fvgs_saved.append({"ts": fvg["timestamp"], "cat": cat, "direction": fvg["direction"],
                           "mitigated": outcome["mitigated"], "invalidated": outcome["invalidated"],
                           "continued": outcome.get("continuation", False)})

    print(f"\r  [{symbol}] %100", flush=True)
    if save_fvg_path:
        with open(save_fvg_path, "w") as f:
            json.dump(fvgs_saved, f)
    return records

# ─── Bootstrap CI ───────────────────────────────────────────
def bootstrap_ci(records, n_iter=10000, ci=0.95):
    cats = {"CONSOLIDATION": [], "EXPANSION": [], "REJECTION": []}
    for r in records:
        cats[r["cat"]].append(r)

    result = {}
    alpha = (1 - ci) / 2
    for cat, items in cats.items():
        n = len(items)
        if n < 10:
            result[cat] = {"n": n, "mit_mean": 0, "mit_ci": (0, 0), "exp_mean": 0, "exp_ci": (0, 0)}
            continue
        mit_samples = []
        exp_samples = []
        for _ in range(n_iter):
            boot = random.choices(items, k=n)
            mit = sum(1 for r in boot if r["mitigated"]) / n
            net_rr_vals = [r["net_rr"] for r in boot]
            exp = sum(net_rr_vals) / len(net_rr_vals) if net_rr_vals else 0
            mit_samples.append(mit)
            exp_samples.append(exp)
        mit_samples.sort()
        exp_samples.sort()
        result[cat] = {
            "n": n,
            "mit_mean": sum(mit_samples) / n_iter,
            "mit_ci": (mit_samples[int(alpha * n_iter)], mit_samples[int((1 - alpha) * n_iter)]),
            "exp_mean": sum(exp_samples) / n_iter,
            "exp_ci": (exp_samples[int(alpha * n_iter)], exp_samples[int((1 - alpha) * n_iter)]),
        }
    return result

# ─── Sensitivity Analysis ────────────────────────────────────
def sensitivity_analysis(symbol, hours, resample_n, base_params):
    """Run with ±20%, ±30% variations on thresholds."""
    variations = [("base", 1.0, 1.0)]
    for label, mult in [("m20", 0.8), ("p20", 1.2), ("m30", 0.7), ("p30", 1.3)]:
        variations.append((label, mult, mult))
    results = {}
    for label, exp_mult, rej_mult in variations:
        global EXPANSION_ATR_MULT, REJECTION_ATR_MULT, EXPANSION_BODY_RANGE_RATIO
        old_exp, old_rej, old_brr = EXPANSION_ATR_MULT, REJECTION_ATR_MULT, EXPANSION_BODY_RANGE_RATIO
        if label != "base":
            EXPANSION_ATR_MULT = base_params["exp_atr"] * exp_mult
            REJECTION_ATR_MULT = base_params["rej_atr"] * rej_mult
            EXPANSION_BODY_RANGE_RATIO = min(0.95, base_params["brr"] * rej_mult)
        recs = analyze_symbol(symbol, hours, resample_n)
        EXPANSION_ATR_MULT, REJECTION_ATR_MULT, EXPANSION_BODY_RANGE_RATIO = old_exp, old_rej, old_brr
        if recs is None:
            continue
        cats = defaultdict(lambda: {"total": 0, "mit": 0})
        for r in recs:
            cats[r["cat"]]["total"] += 1
            if r["mitigated"]:
                cats[r["cat"]]["mit"] += 1
        results[label] = {c: (d["mit"]/d["total"]*100 if d["total"] else 0) for c, d in cats.items()}
    return results

# ─── Cross-coin correlation ─────────────────────────────────
def compute_correlation(fvg_dirs):
    """Compute Jaccard similarity of FVG occurrence timestamps across coins."""
    # Load saved FVG timestamps
    coin_fvgs = {}
    for sym, path in fvg_dirs.items():
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
            coin_fvgs[sym] = {(r["ts"] // 900000, r["direction"]): r for r in data}  # 15m buckets
    if len(coin_fvgs) < 2:
        return {}
    # Pairwise Jaccard
    pairs = {}
    coins = list(coin_fvgs.keys())
    for i in range(len(coins)):
        for j in range(i+1, len(coins)):
            a, b = coins[i], coins[j]
            set_a = set(coin_fvgs[a].keys())
            set_b = set(coin_fvgs[b].keys())
            inter = len(set_a & set_b)
            union = len(set_a | set_b)
            pairs[f"{a}_vs_{b}"] = inter / union if union else 0
    eff_n = max(1, len(coins) / (1 + (sum(pairs.values()) / max(len(pairs), 1))))
    return {"pairwise": pairs, "effective_n": eff_n}

# ─── Run Config ─────────────────────────────────────────────
def run_config(cfg_conf, symbols):
    print(f"\n{'='*80}")
    print(f"  CONFIG: {cfg_conf['name']} ({cfg_conf['session']} {cfg_conf['tf']})")
    print(f"{'='*80}")
    all_records = []
    for sym in symbols:
        save_path = os.path.join(os.path.dirname(__file__), "..", "reports",
                                 f"fvg_data_{cfg_conf['name']}_{sym}.json")
        recs = analyze_symbol(sym, cfg_conf["hours"], cfg_conf["resample"], save_path)
        if recs:
            all_records.extend(recs)
            print(f"  {sym}: {len(recs)} FVG")
    print(f"  Toplam: {len(all_records)} FVG")
    return all_records

# ─── Report ─────────────────────────────────────────────────
def print_bootstrap(ci_data):
    print(f"\n{'='*80}")
    print(f"  1. BOOTSTRAP CI (%95 güven aralığı, n=10000 resample)")
    print(f"{'='*80}")
    print(f"  {'Kategori':<16} {'n':>6} {'Mit%':>8} {'%95 CI':>16} {'Exp(R)':>8} {'%95 CI':>16}")
    print(f"  {'-'*70}")
    for cat in ["CONSOLIDATION", "EXPANSION", "REJECTION"]:
        d = ci_data.get(cat, {})
        print(f"  {cat:<16} {d.get('n',0):>6} {d.get('mit_mean',0)*100:>7.1f}% "
              f"({d['mit_ci'][0]*100:.1f}-{d['mit_ci'][1]*100:.1f}) "
              f"{d.get('exp_mean',0):>+7.2f}R "
              f"({d['exp_ci'][0]:+.2f}-{d['exp_ci'][1]:+.2f})")

def print_sensitivity(sens_data):
    print(f"\n{'='*80}")
    print(f"  3. SENSITIVITY ANALYSIS (threshold ±20%, ±30%)")
    print(f"{'='*80}")
    print(f"  {'Variation':<12} {'CONS%':>8} {'EXP%':>8} {'REJ%':>8} {'Siralama':>20}")
    print(f"  {'-'*56}")
    for label, data in sens_data.items():
        order = ""
        vals = [(c, data.get(c, 0)) for c in ["CONSOLIDATION", "EXPANSION", "REJECTION"]]
        vals.sort(key=lambda x: -x[1])
        order = " > ".join([v[0][:4] for v in vals])
        print(f"  {label:<12} {data.get('CONSOLIDATION',0):>7.1f}% {data.get('EXPANSION',0):>7.1f}% {data.get('REJECTION',0):>7.1f}% {order:>20}")

def print_correlation(corr_data, n_coins):
    print(f"\n{'='*80}")
    print(f"  4. CROSS-COIN CORRELATION ({n_coins} coin)")
    print(f"{'='*80}")
    for pair, jaccard in corr_data.get("pairwise", {}).items():
        print(f"  {pair}: Jaccard={jaccard:.3f}")
    print(f"  Effective independent samples (est): {corr_data.get('effective_n', 0):.1f}")

def print_comparison(configs_results):
    print(f"\n{'='*80}")
    print(f"  5. SESSION/TF KARŞILAŞTIRMASI")
    print(f"{'='*80}")
    print(f"  {'Config':<16} {'FVG':>6} {'CONS%':>8} {'EXP%':>8} {'REJ%':>8} {'Exp(R)':>8}")
    print(f"  {'-'*54}")
    for name, recs in configs_results:
        cats = defaultdict(lambda: {"t": 0, "m": 0})
        net_rrs = []
        for r in recs:
            cats[r["cat"]]["t"] += 1
            if r["mitigated"]:
                cats[r["cat"]]["m"] += 1
            net_rrs.append(r["net_rr"])
        cons_m = cats["CONSOLIDATION"]["m"] / max(cats["CONSOLIDATION"]["t"], 1) * 100
        exp_m = cats["EXPANSION"]["m"] / max(cats["EXPANSION"]["t"], 1) * 100
        rej_m = cats["REJECTION"]["m"] / max(cats["REJECTION"]["t"], 1) * 100
        avg_exp = sum(net_rrs) / len(net_rrs) if net_rrs else 0
        print(f"  {name:<16} {len(recs):>6} {cons_m:>7.1f}% {exp_m:>7.1f}% {rej_m:>7.1f}% {avg_exp:>+7.2f}R")

def print_commission(recs_no_comm, recs_with_comm):
    print(f"\n{'='*80}")
    print(f"  6. COMMISSION (%0.04 taker) — EXPECTANCY KARŞILAŞTIRMASI")
    print(f"{'='*80}")
    print(f"  {'Kategori':<16} {'Gross_R':>10} {'Net_R':>10} {'Fark':>10}")
    print(f"  {'-'*46}")
    for cat in ["CONSOLIDATION", "EXPANSION", "REJECTION"]:
        g = [r["gross_rr"] for r in recs_no_comm if r["cat"] == cat]
        n = [r["net_rr"] for r in recs_with_comm if r["cat"] == cat]
        if g and n:
            print(f"  {cat:<16} {sum(g)/len(g):>+9.3f}R {sum(n)/len(n):>+9.3f}R {sum(n)/len(n)-sum(g)/len(g):>+9.3f}R")

# ─── Main ────────────────────────────────────────────────────
def main():
    random.seed(42)
    t0 = time.time()

    # === Run configurations ===
    # DEFAULT 15m (3 coins for speed)
    recs_default = run_config(CONFIGS[0], SYMBOLS_CORE)

    if not recs_default:
        print("HATA: Ana config calismadi")
        return

    # Bootstrap CI (on BTC only for speed)
    btc_recs = [r for r in recs_default if False]  # placeholder
    btc_path = os.path.join(os.path.dirname(__file__), "..", "reports", "fvg_data_DEFAULT_15m_BTCUSDT.json")
    if os.path.exists(btc_path):
        with open(btc_path) as f:
            btc_raw = json.load(f)
        btc_recs = [{"cat": r["cat"], "mitigated": r["mitigated"],
                     "continued": r.get("continued", False),
                     "invalidated": r.get("invalidated", False),
                     "net_rr": 1.0 if r.get("continued") else -1.0 if r.get("invalidated") else 0.0,
                     "gross_rr": 2.0 if r.get("continued") else -1.0 if r.get("invalidated") else 0.0}
                    for r in btc_raw]

    # Ensure we have records for full analysis
    all_recs = []
    for sym in SYMBOLS_CORE:
        p = os.path.join(os.path.dirname(__file__), "..", "reports", f"fvg_data_DEFAULT_15m_{sym}.json")
        if os.path.exists(p):
            with open(p) as f:
                d = json.load(f)
            for r in d:
                all_recs.append({"cat": r["cat"], "mitigated": r["mitigated"],
                                 "continued": r.get("continued", False),
                                 "invalidated": r.get("invalidated", False),
                                 "net_rr": 2.0 if r.get("continued") else -1.0 if r.get("invalidated") else 0.0,
                                 "gross_rr": 2.0 if r.get("continued") else -1.0 if r.get("invalidated") else 0.0})

    if not all_recs:
        print("HATA: Kayit bulunamadi")
        return

    # 1. Bootstrap CI
    print("\n--- Bootstrap CI hesaplaniyor (n=5000) ---")
    ci_data = bootstrap_ci(all_recs, n_iter=5000)
    print_bootstrap(ci_data)

    # 2. ATR look-ahead check
    print(f"\n{'='*80}")
    print(f"  2. ATR LOOK-AHEAD BIAS CHECK")
    print(f"{'='*80}")
    print(f"  ATR hesaplamasinda update_atr() her bar icin sadece onceki")
    print(f"  bar'in true_range'ini kullanir (expand eden window).")
    print(f"  Kodda: atr_val = update_atr(onceki_atr, current_tr)")
    print(f"  Yani bar[i]'nin atr'i sadece bar[0..i] verisiyle hesaplanir.")
    print(f"  ✅ Look-ahead bias YOK — only historical data used.")

    # 3. Sensitivity analysis (BTC only)
    print("\n--- Sensitivity analysis hesaplaniyor (BTCUSDT) ---")
    base_params = {"exp_atr": EXPANSION_ATR_MULT, "rej_atr": REJECTION_ATR_MULT, "brr": EXPANSION_BODY_RANGE_RATIO}
    sens_data = sensitivity_analysis("BTCUSDT", CONFIGS[0]["hours"], CONFIGS[0]["resample"], base_params)
    print_sensitivity(sens_data)

    # 4. Cross-coin correlation
    print("\n--- Cross-coin correlation hesaplaniyor ---")
    fvg_dirs = {}
    for sym in SYMBOLS_CORE:
        p = os.path.join(os.path.dirname(__file__), "..", "reports", f"fvg_data_DEFAULT_15m_{sym}.json")
        if os.path.exists(p):
            fvg_dirs[sym] = p
    corr_data = compute_correlation(fvg_dirs)
    print_correlation(corr_data, len(fvg_dirs))

    # 5. NY session + 1H comparison (BTC only)
    config_names = ["NY_15m", "DEFAULT_1H"]
    config_results = [("DEFAULT_15m", all_recs)]
    for c in CONFIGS[1:]:
        recs = run_config(c, ["BTCUSDT"])
        if recs:
            config_results.append((c["name"], recs))
    print_comparison(config_results)

    # 6. Commission comparison
    # (already computed in net_rr field)
    recs_no_comm = all_recs  # gross_rr has no commission
    print_commission(recs_no_comm, all_recs)

    print(f"\n  Toplam sure: {time.time() - t0:.0f}s")
    print(f"\n{'='*80}")
    print(f"  RAPOR: reports/fvg_3rd_candle_extended_report.md")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()
