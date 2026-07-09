"""
_analyze_all_20.py — 20 coin futures analizi (config_20 kullanir).
Adim 1: Session fit testi (3 session karsilastirmasi)
Adim 2: CBDR bucket + Wilson CI analizi
Adim 3: Config ciktisi (SYMBOLS + CBDR_RISK_MATRIX)

Kullanim:  python _analyze_all_20.py
Config:    src/config_20.py (canli config'e dokunmaz)
"""
import os, sys, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── 20-coin test config'ini yukle, canli config yerine tak ──
import config_20
sys.modules["config"] = config_20

# ── Engine fonksiyonlari (sys.modules['config'] uzerinden config_20'yi gorur) ──
from analyze_cbdr_thresholds import (
    collect_daily_data, compute_session_stats,
    analyze_bucket_scaling, wilson_lower, wilson_upper,
    SESSION_CONFIGS
)

# ─── 20 coin ───────────────────────────────────────────────────
ALL_SYMBOLS = [
    "BTCUSDT", "BNBUSDT", "SOLUSDT", "AVAXUSDT", "LINKUSDT",
    "XRPUSDT", "ATOMUSDT", "ADAUSDT", "APTUSDT", "DOTUSDT",
    "NEARUSDT", "ETHUSDT", "SUIUSDT",
    "OPUSDT", "ARBUSDT", "INJUSDT", "ALGOUSDT",
    "AAVEUSDT", "UNIUSDT", "DOGEUSDT",
]

# Mevcut session atamalari (config_20'den)
CURRENT_SESSION_MAP = {}
for sym in config_20.CBDR_RISK_MATRIX:
    CURRENT_SESSION_MAP[sym] = config_20.CBDR_RISK_MATRIX[sym].get("session", "DEFAULT")


def best_session(stats_dict):
    """En iyi session'u sec: PF*10 + WR (Sharpe yoksa PF+WR bazli)."""
    ranked = []
    for sname, st in stats_dict.items():
        pf = st.get("profit_factor", 0)
        wr = st.get("win_pct", 0)
        pnl = st.get("total_pnl", 0)
        dd = st.get("max_dd_pct", 100)
        score = pf * 10 + wr + (pnl / 1000) - dd
        ranked.append((score, sname, st))
    ranked.sort(key=lambda x: x[0], reverse=True)
    return ranked[0]


DEFAULT_BUCKET_BOUNDS = [
    (0.0, 1.0), (1.0, 1.5), (1.5, 2.0), (2.0, 3.0), (3.0, 5.0), (5.0, 999.0)
]


def auto_multiplier(wr: float, wilson_lower: float, trades: int) -> float:
    """WR + Wilson CI alt sinirina gore otomatik multiplier.
    Mantik:
      1.5x = WR > 44 veya Wilson_Lower > 38 (guvenli ustun)
      1.2x = WR > 40 veya Wilson_Lower > 34 (hafif ustun)
      1.0x = WR > 34 (standart)
      0.8x = WR > 28 (defansif)
      0.5x = WR > 22 (zayif)
      0.0x = WR <= 22 veya trades < 10 (ZEHIRLI)
    """
    if trades < 10:
        return 0.0
    if wr > 44 or wilson_lower > 38:
        return 1.5
    if wr > 40 or wilson_lower > 34:
        return 1.2
    if wr > 34:
        return 1.0
    if wr > 28:
        return 0.8
    if wr > 22:
        return 0.5
    return 0.0


def compute_bucket_scaling(daily_rows: list, symbol: str):
    """CBDR bucket sinirlarini WR + Wilson CI'ya gore hesapla,
    mevcut config varsa onu kullan, yoksa DEFAULT_BUCKET_BOUNDS kullan."""
    # Mevcut config'te var mi?
    profile = config_20.CBDR_RISK_MATRIX.get(symbol)
    if profile and profile.get("buckets"):
        return analyze_bucket_scaling(daily_rows, symbol)

    # Yoksa default sinirlarla calis
    valid = [d for d in daily_rows if d["cbdr_pct"] is not None]
    if not valid:
        return None

    bucket_data = defaultdict(lambda: {"trades": 0, "wins": 0})
    for d in valid:
        cbdr_w = d["cbdr_pct"]
        for lo, hi in DEFAULT_BUCKET_BOUNDS:
            if lo <= cbdr_w < hi:
                bucket_data[(lo, hi)]["trades"] += d.get("trades", 0)
                bucket_data[(lo, hi)]["wins"] += d.get("wins", 0)
                break

    bucket_stats = []
    for lo, hi in DEFAULT_BUCKET_BOUNDS:
        bd = bucket_data.get((lo, hi), {"trades": 0, "wins": 0})
        n = bd["trades"]
        w = bd["wins"]
        wr = w / n if n > 0 else 0.0
        wl = wilson_lower(w, n) * 100
        wh = wilson_upper(w, n) * 100
        mult = auto_multiplier(wr * 100, wl, n)
        bucket_stats.append({
            "lo": lo, "hi": hi, "mult": mult,
            "label": f"({lo:.1f}, {hi:.1f}, {mult:.1f})",
            "trades": n, "wins": w,
            "wr": round(wr * 100, 1),
            "wilson_lower": round(wl, 1),
            "wilson_upper": round(wh, 1),
        })

    return {
        "bucket_stats": bucket_stats,
        "comparisons": [],
        "divergent_pairs": 0,
        "total_qualifying_buckets": 0,
    }


def generate_config_entry(sym, sname, bucket_stats):
    """CBDR_RISK_MATRIX entry uret (auto multiplier)."""
    buckets = [(b["lo"], b["hi"], b["mult"]) for b in bucket_stats]
    return {
        "session": sname,
        "weekend_bonus": False,
        "weekend_mult": 1.0,
        "buckets": buckets,
    }


def main():
    print("=" * 100)
    print("  20 COIN FUTURES ANALIZI")
    print("  Adim 1: Session fit testi (3 session)")
    print("  Adim 2: CBDR Bucket + Wilson CI")
    print("  Adim 3: Config ciktisi")
    print("=" * 100)

    # ─── Adim 1: Session fit ──────────────────────────────────
    print("\n[ADIM 1] Session fit testi...", flush=True)
    session_best = {}
    all_stats = {}

    for sym in ALL_SYMBOLS:
        csv_path = os.path.join(os.path.dirname(__file__), "data", "daily", f"{sym}_1m_raw.csv")
        if not os.path.isfile(csv_path):
            print(f"  {sym}: VERI YOK, atlaniyor", flush=True)
            continue

        print(f"\n  {sym}:", flush=True)
        results = {}
        for sname, shours in SESSION_CONFIGS.items():
            r = collect_daily_data(sym, session_name=sname, session_hours=shours)
            if r is None:
                print(f"    {sname}: VERI YOK", flush=True)
                continue
            daily_rows, wins, losses, trade_records, rejection_counts = r
            stats = compute_session_stats(
                [(t["trade_id"], sname, t["pnl"], t["result"]) for t in trade_records],
                config_20.INITIAL_BALANCE
            )
            stats["trades"] = len(trade_records)
            stats["rejections"] = dict(rejection_counts)
            results[sname] = stats

            print(f"    {sname}: {stats['total_trades']} trade | "
                  f"WR={stats['win_pct']:.1f}% PF={stats['profit_factor']:.2f} "
                  f"DD={stats['max_dd_pct']:.1f}% PnL={stats['total_pnl']:+.0f}",
                  flush=True)

        if not results:
            continue

        all_stats[sym] = results

        # En iyi session
        score, best_sname, best_st = best_session(results)
        current_sname = CURRENT_SESSION_MAP.get(sym)
        note = " (YENI)" if sym not in CURRENT_SESSION_MAP else \
               f" (MEVCUT: {current_sname}, SECILEN: {best_sname})" \
               if best_sname != current_sname else " (AYNI)"
        print(f"  => {sym}: BEST={best_sname} "
              f"WR={best_st['win_pct']:.1f}% PF={best_st['profit_factor']:.2f} "
              f"Sharpe={best_st.get('sharpe',0):.2f}{note}", flush=True)
        session_best[sym] = best_sname

    # ─── Adim 2: CBDR bucket ──────────────────────────────────
    print("\n[ADIM 2] CBDR Bucket + Wilson CI...", flush=True)
    bucket_results = {}
    for sym in ALL_SYMBOLS:
        if sym not in session_best:
            continue
        sname = session_best[sym]
        shours = SESSION_CONFIGS[sname]
        r = collect_daily_data(sym, session_name=sname, session_hours=shours)
        if r is None:
            continue
        daily_rows, wins, losses, trade_records, _ = r

        bs = compute_bucket_scaling(daily_rows, sym)
        if bs is None:
            continue
        bucket_results[sym] = bs
        bstats = bs["bucket_stats"]
        print(f"  {sym} ({sname}): {len(bstats)} bucket", flush=True)
        for b in bstats:
            mult_str = f"{b['mult']:.1f}x" if b['mult'] > 0 else "ZEHIRLI"
            print(f"    {b['label']:<25} n={b['trades']:>4} WR={b['wr']:>5.1f}% "
                  f"CI=[{b['wilson_lower']:>5.1f}%,{b['wilson_upper']:>5.1f}%] -> {mult_str}", flush=True)

    # ─── Adim 3: Config ciktisi ───────────────────────────────
    print("\n[ADIM 3] Config ciktisi", flush=True)
    print("=" * 100)

    # SYMBOLS
    print("\n# SYMBOLS")
    print("SYMBOLS = [")
    for sym in ALL_SYMBOLS:
        print(f'    "{sym}",')
    print("]")

    # Session ozeti
    print(f"\n# SESSION DAGILIMI")
    for sym, sname in sorted(session_best.items(), key=lambda x: x[1]):
        note = ""
        old = CURRENT_SESSION_MAP.get(sym)
        if old and old != sname:
            note = f" (ESKI: {old})"
        print(f"# {sym}: {sname}{note}")

    # CBDR_RISK_MATRIX
    print(f"\n# CBDR_RISK_MATRIX (50% x 100 trade esik)")
    print("CBDR_RISK_MATRIX: dict[str, dict] = {")
    for sym in ALL_SYMBOLS:
        if sym not in session_best:
            continue
        sname = session_best[sym]
        bs = bucket_results.get(sym)
        print(f'    "{sym}": {{')
        print(f'        "session": "{sname}",')
        print(f'        "weekend_bonus": False,')
        print(f'        "weekend_mult": 1.0,')
        print(f'        "buckets": [')
        if bs:
            for bbs in bs["bucket_stats"]:
                label = bbs["label"]
                mult = bbs["mult"]
                trades = bbs["trades"]
                wr = bbs["wr"]
                wl = bbs["wilson_lower"]
                wh = bbs["wilson_upper"]
                print(f'            {label},  # n={trades} WR={wr:.1f}% CI=[{wl:.1f}%,{wh:.1f}%]')
        else:
            print(f'            (0.0, 1.0, 1.0),')
            print(f'            (1.0, 999.0, 1.0),')
        print(f'        ],')
        print(f'    }},')
    print("}")

    # FVG_SIZE_MAP (bos)
    print(f"\n# FVG_SIZE_MAP")
    print("FVG_SIZE_MAP: dict[str, float] = {")
    for sym in ALL_SYMBOLS:
        print(f'    "{sym}": 0.0,  # TODO: futures ATR bazli hesapla')
    print("}")

    print("\nDone.", flush=True)


if __name__ == "__main__":
    main()
