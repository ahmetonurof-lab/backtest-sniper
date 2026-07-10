"""
_analyze_all_20.py — 20 coin futures analizi (docs/config_reference kullanir).
Adim 1: Session fit testi (3 session karsilastirmasi)
Adim 2: CBDR bucket + Wilson CI analizi
Adim 3: Config ciktisi (SYMBOLS + CBDR_RISK_MATRIX)

Kullanim:  python _analyze_all_20.py
Config:    docs/config_reference.py (canli config'e dokunmaz)

Paralel mod: coin'leri ayri sureclerde isler. Varsayilan: worker=4.
  python _analyze_all_20.py --workers 4
  python _analyze_all_20.py --serial   (paralelsiz, eski davranis)
"""
import os, sys, math, time
from collections import defaultdict

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── 20 coin ──
ALL_SYMBOLS = [
    "BTCUSDT", "BNBUSDT", "SOLUSDT", "AVAXUSDT", "LINKUSDT",
    "XRPUSDT", "ATOMUSDT", "ADAUSDT", "APTUSDT", "DOTUSDT",
    "NEARUSDT", "ETHUSDT", "SUIUSDT",
    "OPUSDT", "ARBUSDT", "INJUSDT", "ALGOUSDT",
    "AAVEUSDT", "UNIUSDT", "DOGEUSDT",
]

DEFAULT_BUCKET_BOUNDS = [
    (0.0, 1.0), (1.0, 1.5), (1.5, 2.0), (2.0, 3.0), (3.0, 5.0), (5.0, 999.0)
]


# ─── Worker: tek coin analizi (ayri surecte calisir) ──────────
def _analyze_one_symbol(sym: str, workers: int = 1) -> dict | None:
    """Bir sembol icin Adim 1 (session fit) + Adim 2 (bucket) calistirir.
    Ayri bir ProcessPoolExecutor worker'inda calisacagi icin
    tum import/config kendi icinde kurar."""
    import os, sys, math, time
    from collections import defaultdict

    _dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, _dir)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    class _cfg:
        INITIAL_BALANCE = 10000.0
        RISK_PER_TRADE = 0.003
        SL_ATR_MULT = 1.5
        TP_RR = 2.0
        FVG_BUFFER_MULT = 0.50
        EARLY_LONDON_RISK_MULT = 1.5
        MIN_REL_FVG_THRESHOLD = 0.50
        FVG_WICK_RATIO_MAX = 0.75
        FVG_BUFFER_MIN_FACTOR = 0.10
        ATR_TRAIL_MULT = 0.25
        TRAIL_MIN_MOVE_MULT = 0.2
        BE_RISK_MULT = 1.0
        BE_SPREAD_PTS = 0.0
        FVG_MIN_SIZE_ATR_MULT = 0.06
        GLOBAL_FVG_EXPIRY_BARS = 45
        MIN_RISK_DIST_ATR_MULT = 0.1
        CBDR_DEAD_THRESHOLD_PCT = 0.5
        ASIA_DEAD_THRESHOLD_PCT = 0.3
        CBDR_SWEEP_ATR_TOLERANCE_MULT = 0.5
        CBDR_SWEEP_DEFAULT_TOLERANCE = 10.0
        CBDR_RISK_MATRIX = {}
    sys.modules["config"] = _cfg

    from analyze_cbdr_thresholds import (
        collect_daily_data, compute_session_stats,
        analyze_bucket_scaling, wilson_lower, wilson_upper,
        SESSION_CONFIGS
    )

    csv_path = os.path.join(os.path.dirname(__file__), "data", "daily", f"{sym}_1m_raw.csv")
    if not os.path.isfile(csv_path):
        return None

    # ── Adim 1: Session fit ──
    session_results = {}
    collect_cache = {}
    for sname, shours in SESSION_CONFIGS.items():
        r = collect_daily_data(sym, session_name=sname, session_hours=shours)
        if r is None:
            continue
        collect_cache[(sym, sname)] = r
        daily_rows, wins, losses, trade_records, rejection_counts = r
        stats = compute_session_stats(
            [(t["trade_id"], sname, t["pnl"], t["result"]) for t in trade_records],
            _cfg.INITIAL_BALANCE
        )
        stats["trades"] = len(trade_records)
        stats["rejections"] = dict(rejection_counts)
        session_results[sname] = stats

    if not session_results:
        return None

    # En iyi session
    ranked = []
    for sname, st in session_results.items():
        bep = st.get("be_plus_pct", 0)
        pf = st.get("profit_factor", 0)
        pnl = abs(st.get("total_pnl", 0))
        dd = st.get("max_dd_pct", 1)
        score = (bep * pf * pnl) / dd
        ranked.append((score, sname, st))
    ranked.sort(key=lambda x: x[0], reverse=True)
    best_score, best_sname, best_st = ranked[0]

    # ── Adim 2: CBDR bucket (cache'den) ──
    bucket_result = None
    cached = collect_cache.get((sym, best_sname))
    if cached is not None:
        daily_rows, wins, losses, trade_records, _ = cached
        # bucket scaling
        valid = [d for d in daily_rows if d["cbdr_pct"] is not None]
        if valid:
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
                mult = 1.0
                if n >= 100:
                    if wr * 100 >= 45 and wl >= 40:
                        mult = 1.5
                    elif wr * 100 >= 40 and wl >= 35:
                        mult = 1.25
                    elif wr * 100 >= 35:
                        mult = 1.0
                    elif wr * 100 >= 30:
                        mult = 0.75
                    elif wr * 100 >= 25:
                        mult = 0.5
                    else:
                        mult = 0.0
                bucket_stats.append({
                    "lo": lo, "hi": hi, "mult": mult,
                    "label": f"({lo:.1f}, {hi:.1f}, {mult:.1f})",
                    "trades": n, "wins": w,
                    "wr": round(wr * 100, 1),
                    "wilson_lower": round(wl, 1),
                    "wilson_upper": round(wh, 1),
                })
            bucket_result = bucket_stats

    return {
        "sym": sym,
        "best_sname": best_sname,
        "best_score": best_score,
        "best_stats": best_st,
        "session_results": session_results,
        "bucket_stats": bucket_result,
    }


# ─── Serial isleme (paralelsiz) ──────────────────────────────
def _run_serial(workers: int):
    """Coin'leri sirayla isle (eski davranis)."""
    from analyze_cbdr_thresholds import (
        collect_daily_data, compute_session_stats,
        analyze_bucket_scaling, wilson_lower, wilson_upper,
        SESSION_CONFIGS
    )
    session_best = {}
    bucket_results = {}
    all_session_stats = {}

    for sym in ALL_SYMBOLS:
        csv_path = os.path.join(os.path.dirname(__file__), "data", "daily", f"{sym}_1m_raw.csv")
        if not os.path.isfile(csv_path):
            print(f"  {sym}: VERI YOK, atlaniyor", flush=True)
            continue
        print(f"\n  {sym}:", flush=True)
        results = {}
        collect_cache = {}
        for sname, shours in SESSION_CONFIGS.items():
            r = collect_daily_data(sym, session_name=sname, session_hours=shours)
            if r is None:
                print(f"    {sname}: VERI YOK", flush=True)
                continue
            collect_cache[(sym, sname)] = r
            daily_rows, wins, losses, trade_records, rejection_counts = r
            stats = compute_session_stats(
                [(t["trade_id"], sname, t["pnl"], t["result"]) for t in trade_records],
                10000.0
            )
            stats["trades"] = len(trade_records)
            stats["rejections"] = dict(rejection_counts)
            results[sname] = stats
            bep = stats.get("be_plus_pct", 0)
            pf = stats["profit_factor"]
            pnl = abs(stats["total_pnl"])
            dd = stats["max_dd_pct"] if stats["max_dd_pct"] > 0 else 1
            skor = (bep * pf * pnl) / dd
            print(f"    {sname}: {stats['total_trades']} trade | "
                  f"WR={stats['win_pct']:.1f}% BE+={bep:.1f}% "
                  f"PF={pf:.2f} DD={stats['max_dd_pct']:.1f}% "
                  f"Skor={skor:.0f} PnL={stats['total_pnl']:+.0f}",
                  flush=True)

        if not results:
            continue
        all_session_stats[sym] = results

        ranked = []
        for sname, st in results.items():
            bep = st.get("be_plus_pct", 0)
            pf = st.get("profit_factor", 0)
            pnl = abs(st.get("total_pnl", 0))
            dd = st.get("max_dd_pct", 1)
            score = (bep * pf * pnl) / dd
            ranked.append((score, sname, st))
        ranked.sort(key=lambda x: x[0], reverse=True)
        best_score, best_sname, best_st = ranked[0]

        note = " (YENI)" if sym not in ["DEFAULT"] else " (AYNI)"
        print(f"  => {sym}: BEST={best_sname} "
              f"BE+={best_st.get('be_plus_pct',0):.1f}% PF={best_st['profit_factor']:.2f} "
              f"DD={best_st['max_dd_pct']:.1f}% PnL={best_st['total_pnl']:+.0f} "
              f"Skor={best_score:.0f}{note}", flush=True)
        session_best[sym] = best_sname

        # Adim 2 (cache'den)
        cached = collect_cache.get((sym, best_sname))
        if cached:
            daily_rows, wins, losses, trade_records, _ = cached
            valid = [d for d in daily_rows if d["cbdr_pct"] is not None]
            if valid:
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
                    mult = 1.0
                    if n >= 100:
                        if wr * 100 >= 45 and wl >= 40:
                            mult = 1.5
                        elif wr * 100 >= 40 and wl >= 35:
                            mult = 1.25
                        elif wr * 100 >= 35:
                            mult = 1.0
                        elif wr * 100 >= 30:
                            mult = 0.75
                        elif wr * 100 >= 25:
                            mult = 0.5
                        else:
                            mult = 0.0
                    bucket_stats.append({
                        "lo": lo, "hi": hi, "mult": mult,
                        "label": f"({lo:.1f}, {hi:.1f}, {mult:.1f})",
                        "trades": n, "wins": w,
                        "wr": round(wr * 100, 1),
                        "wilson_lower": round(wl, 1),
                        "wilson_upper": round(wh, 1),
                    })
                bucket_results[sym] = bucket_stats
                print(f"  {sym} ({best_sname}): {len(bucket_stats)} bucket", flush=True)
                for b in bucket_stats:
                    mult_str = f"{b['mult']:.1f}x" if b['mult'] > 0 else "ZEHIRLI"
                    print(f"    {b['label']:<25} n={b['trades']:>4} WR={b['wr']:>5.1f}% "
                          f"CI=[{b['wilson_lower']:>5.1f}%,{b['wilson_upper']:>5.1f}%] -> {mult_str}", flush=True)

    return session_best, bucket_results, all_session_stats


# ─── Config ciktisi (Adim 3) ────────────────────────────────
def _print_config(session_best: dict, bucket_results: dict, all_session_stats: dict, elapsed: float):
    """Adim 3: Konsola config ciktisini basar."""
    print("\n[ADIM 3] Config ciktisi", flush=True)
    print("=" * 100)

    print("\n# SYMBOLS")
    print("SYMBOLS = [")
    for sym in ALL_SYMBOLS:
        print(f'    "{sym}",')
    print("]")

    print(f"\n# SESSION DAGILIMI")
    for sym, sname in sorted(session_best.items(), key=lambda x: x[1]):
        print(f"# {sym}: {sname}")

    print(f"\n# CBDR_RISK_MATRIX")
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
            for b in bs:
                print(f'            {b["label"]},  # n={b["trades"]} WR={b["wr"]:.1f}% CI=[{b["wilson_lower"]:.1f}%,{b["wilson_upper"]:.1f}%]')
        else:
            print(f'            (0.0, 1.0, 1.0),')
            print(f'            (1.0, 999.0, 1.0),')
        print(f'        ],')
        print(f'    }},')
    print("}")

    print(f"\n# FVG_SIZE_MAP")
    print("FVG_SIZE_MAP: dict[str, float] = {")
    for sym in ALL_SYMBOLS:
        print(f'    "{sym}": 0.0,  # TODO: futures ATR bazli hesapla')
    print("}")

    print(f"\nDone. ({elapsed:.0f}s)", flush=True)


# ─── Main ────────────────────────────────────────────────────
def main():
    import argparse

    parser = argparse.ArgumentParser(description="20 coin futures analizi")
    parser.add_argument("--workers", type=int, default=4,
                        help="Paralel worker sayisi (0=serial, default=4)")
    parser.add_argument("--serial", action="store_true",
                        help="Serial mod (paralelsiz)")
    args = parser.parse_args()

    use_serial = args.serial or args.workers == 0
    n_workers = args.workers if not use_serial else 1

    t_start = time.time()
    print("=" * 100)
    print("  20 COIN FUTURES ANALIZI")
    print("  Adim 1: Session fit testi (3 session)")
    print("  Adim 2: CBDR Bucket + Wilson CI")
    print("  Adim 3: Config ciktisi")
    if not use_serial:
        print(f"  Mod: PARALEL ({n_workers} worker)")
    else:
        print(f"  Mod: SERIAL")
    print("=" * 100)

    if use_serial:
        session_best, bucket_results, _ = _run_serial(n_workers)
        _print_config(session_best, bucket_results, None, time.time() - t_start)
        return

    # ─── Paralel mod ──────────────────────────────────────────
    import concurrent.futures

    print(f"\n{len(ALL_SYMBOLS)} coin {n_workers} worker ile isleniyor...\n", flush=True)

    session_best = {}
    bucket_results = {}
    completed = 0
    errors = 0

    with concurrent.futures.ProcessPoolExecutor(max_workers=n_workers) as executor:
        fut_map = {executor.submit(_analyze_one_symbol, sym, n_workers): sym for sym in ALL_SYMBOLS}
        for future in concurrent.futures.as_completed(fut_map):
            sym = fut_map[future]
            try:
                result = future.result()
            except Exception as e:
                print(f"  [!] {sym}: HATA - {e}", flush=True)
                errors += 1
                completed += 1
                continue

            if result is None:
                print(f"  {sym}: VERI YOK veya BASARISIZ", flush=True)
                completed += 1
                continue

            best_sname = result["best_sname"]
            best_st = result["best_stats"]
            best_score = result["best_score"]
            session_best[sym] = best_sname
            if result["bucket_stats"]:
                bucket_results[sym] = result["bucket_stats"]

            # Session detaylari
            for sname, st in result["session_results"].items():
                bep = st.get("be_plus_pct", 0)
                pf = st["profit_factor"]
                pnl = abs(st["total_pnl"])
                dd = st["max_dd_pct"] if st["max_dd_pct"] > 0 else 1
                skor = (bep * pf * pnl) / dd
                print(f"  {sym:>8} {sname:<12} {st['total_trades']:>5} trade | "
                      f"WR={st['win_pct']:>4.1f}% BE+={bep:.1f}% "
                      f"PF={pf:.2f} DD={st['max_dd_pct']:.1f}% "
                      f"Skor={skor:.0f} PnL={st['total_pnl']:+.0f}",
                      flush=True)

            print(f"  => {sym}: BEST={best_sname} "
                  f"BE+={best_st.get('be_plus_pct',0):.1f}% PF={best_st['profit_factor']:.2f} "
                  f"DD={best_st['max_dd_pct']:.1f}% PnL={best_st['total_pnl']:+.0f} "
                  f"Skor={best_score:.0f}", flush=True)

            # Bucket detaylari
            bs = result.get("bucket_stats")
            if bs:
                for b in bs:
                    mult_str = f"{b['mult']:.1f}x" if b['mult'] > 0 else "ZEHIRLI"
                    print(f"         {b['label']:<25} n={b['trades']:>4} WR={b['wr']:>5.1f}% "
                          f"CI=[{b['wilson_lower']:>5.1f}%,{b['wilson_upper']:>5.1f}%] -> {mult_str}", flush=True)

            completed += 1
            done_ok = completed - errors
            print(f"  --- {done_ok}/{len(ALL_SYMBOLS)} basarili ({errors} hata) ---\n", flush=True)

    _print_config(session_best, bucket_results, None, time.time() - t_start)


if __name__ == "__main__":
    main()
