"""
profile_fvg_size.py — Coin bazinda optimum FVG_SIZE_MAP bulma.
Sweep 0.02 - 0.20 step 0.01, motor analyzer_v5.

Tek eşik: FVG_SIZE_MAP (FVG.size / ATR orani).
is_high_quality_fvg kaldirildi. FVG_MIN_MULT_MAP kaldirildi.
on_sweep_confirmed + trailing ayni eşigi kullaniyor.

Kullanim:
  python profile_fvg_size.py                     # paralel (default 4 worker)
  python profile_fvg_size.py --workers 4
  python profile_fvg_size.py --serial             # sirali
"""

import os
import sys
import time

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LOG_FILE = os.path.join(_THIS_DIR, "..", "reports", "profile_fvg_size.log")

SYMBOLS_20 = [
    "TIAUSDT",
    "SEIUSDT",
    "ONDOUSDT",
    "PYTHUSDT",
    "RENDERUSDT",
    "ENAUSDT",
    "STRKUSDT",
    "GMXUSDT",
    "DYDXUSDT",
    "LDOUSDT",
]
SWEEP_START = 0.02
SWEEP_END = 0.20
SWEEP_STEP = 0.01


def _log_line(msg: str):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
        f.flush()


def _compute_score(trade_records) -> tuple[float, int]:
    n = len(trade_records)
    if n == 0:
        return 0.0, 0
    tp = sum(1 for t in trade_records if t["result"] == "TP")
    ptrail = sum(1 for t in trade_records if t["result"] == "PROFIT_TRAIL")
    pe = tp + ptrail
    pe_pct = pe / n * 100

    gp = sum(t["pnl"] for t in trade_records if t["pnl"] > 0) or 0
    gl = abs(sum(t["pnl"] for t in trade_records if t["pnl"] < 0))
    pf = 999.0 if gl == 0 else gp / gl

    total_pnl = sum(t["pnl"] for t in trade_records)
    total_fee = sum(t.get("fee", 0) for t in trade_records)
    pnl_per_fee = total_pnl / total_fee if total_fee > 0 else 0

    cum = 0
    peak = 0
    mdd = 0
    for t in trade_records:
        cum += t["pnl"]
        if cum > peak:
            peak = cum
        dd = peak - cum
        if dd > mdd:
            mdd = dd

    import config as _c

    peak_bal = _c.INITIAL_BALANCE + peak
    mdd_pct = (mdd / peak_bal) * 100 if peak_bal > 0 else 0

    score = (pf * (pe_pct / 100) * pnl_per_fee) / (1 + mdd_pct / 100) * 100
    return round(score), n


# ─── Worker: tek coin profilleme ─────────────────────────────
def _profile_one(sym: str, session_override: str | None = None) -> dict | None:
    import os
    import sys

    _dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, _dir)
    sys.path.insert(0, os.path.join(_dir, "..", "..", "sniper", "src"))
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    import config as cfg
    from analyzer_v5 import collect_fvg_profile

    feather_path = os.path.join(_dir, "data", "daily", f"{sym}_1m_raw.feather")
    if not os.path.isfile(feather_path):
        return None

    # Session override: change coin's session in CBDR_RISK_MATRIX temporarily
    _original_session = None
    if session_override and sym in cfg.CBDR_RISK_MATRIX:
        _original_session = cfg.CBDR_RISK_MATRIX[sym].get("session")
        cfg.CBDR_RISK_MATRIX[sym]["session"] = session_override

    try:
        values = [
            round(SWEEP_START + i * SWEEP_STEP, 3)
            for i in range(int((SWEEP_END - SWEEP_START) / SWEEP_STEP) + 1)
        ]
        results = []

        for idx, size in enumerate(values):
            cfg.FVG_SIZE_MAP[sym] = size
            try:
                r = collect_fvg_profile(sym)
            except Exception as e:
                _log_line(f"  [{sym}] size={size:.3f} CRASH: {e}")
                continue

            if r is None or (isinstance(r, tuple) and r[0] is None):
                continue

            _, _, _, trade_records, rejection_counts = r
            if not trade_records:
                results.append((size, 0, 0))
                continue

            score, n = _compute_score(trade_records)
            entered = rejection_counts.get("ENTERED", 0)
            results.append((size, score, n))
            _log_line(
                f"  [{sym}] {idx + 1:>2}/{len(values)} size={size:.3f} "
                f"score={score} trades={n} entered={entered}"
            )

        if not results:
            return None
        best = max(results, key=lambda x: x[1])
        _log_line(f"  [{sym}] BEST: size={best[0]:.3f} score={best[1]} trades={best[2]}")
        return {"sym": sym, "best_size": best[0], "best_score": best[1]}
    finally:
        # Restore original session
        if _original_session is not None and sym in cfg.CBDR_RISK_MATRIX:
            cfg.CBDR_RISK_MATRIX[sym]["session"] = _original_session


def _print_map(results: dict):
    lines = []
    lines.append("")
    lines.append("=" * 80)
    lines.append("  BEST FVG_SIZE_MAP PER COIN")
    lines.append("=" * 80)
    lines.append(f"  {'Coin':<12} {'Best':>10} {'Score':>8}")
    lines.append(f"  {'-' * 34}")
    for sym in sorted(results):
        r = results[sym]
        lines.append(f"  {sym:<12} {r['best_size']:>10.3f} {r['best_score']:>8}")
    lines.append("")
    lines.append("# Config'de guncellemek icin:")
    lines.append("FVG_SIZE_MAP: dict[str, float] = {")
    for sym in sorted(results):
        r = results[sym]
        lines.append(f'    "{sym}": {r["best_size"]:.3f},  # score={r["best_score"]}')
    lines.append("}")

    result = "\n".join(lines)
    for line in lines:
        _log_line(line)
    print(result, flush=True)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="FVG_SIZE_MAP profiler")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--serial", action="store_true")
    parser.add_argument(
        "--session",
        type=str,
        default=None,
        help="Override session for all coins (e.g., DEFAULT, ASIA_RANGE, REAL_CBDR)",
    )
    args = parser.parse_args()

    use_serial = args.serial or args.workers <= 1
    n_workers = 1 if use_serial else args.workers
    session_override = args.session

    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("  FVG SIZE PROFILER — TEK ASAMA (FVG_SIZE_MAP)\n")
        f.write(f"  Sweep: {SWEEP_START}-{SWEEP_END} step {SWEEP_STEP}\n")
        f.write(
            f"  Coins: {len(SYMBOLS_20)}, values/coin: {int((SWEEP_END - SWEEP_START) / SWEEP_STEP) + 1}\n"
        )
        f.write(
            f"  Mod: {'PARALEL' if not use_serial else 'SERIAL'} ({n_workers} worker)\n"
        )
        if session_override:
            f.write(f"  Session Override: {session_override}\n")
        f.write("=" * 80 + "\n")
        f.flush()

    t0 = time.time()
    print(f"[LOG] Detaylar -> {LOG_FILE}", flush=True)
    if session_override:
        print(f"[SESSION] Override: {session_override}", flush=True)
    print(
        f"[BASLADI] {len(SYMBOLS_20)} coin, {int((SWEEP_END - SWEEP_START) / SWEEP_STEP) + 1} deger/coin, {n_workers} worker",
        flush=True,
    )

    results = {}

    if use_serial:
        for sym in sorted(SYMBOLS_20):
            _log_line(f"\n[{sym}] basliyor...")
            r = _profile_one(sym, session_override=session_override)
            if r is None:
                _log_line(f"[{sym}] BASARISIZ")
                continue
            results[sym] = r
            _log_line(
                f"[{sym}] BEST: size={r['best_size']:.2f} score={r['best_score']}"
            )
    else:
        import concurrent.futures

        syms = sorted(SYMBOLS_20)
        _log_line(f"\n{syms} paralel isleniyor...\n")
        with concurrent.futures.ProcessPoolExecutor(max_workers=n_workers) as executor:
            fut_map = {
                executor.submit(_profile_one, sym, session_override): sym
                for sym in syms
            }
            for future in concurrent.futures.as_completed(fut_map):
                sym = fut_map[future]
                try:
                    r = future.result()
                except Exception as e:
                    import traceback

                    err = traceback.format_exc()
                    _log_line(f"[!] {sym}: {e}\n{err}")
                    continue
                if r is None:
                    _log_line(f"[{sym}] BASARISIZ")
                    continue
                results[sym] = r
                _log_line(
                    f"[{sym}] BEST: size={r['best_size']:.2f} score={r['best_score']}"
                )

    _log_line(f"\nToplam sure: {time.time() - t0:.0f}s")

    if results:
        _print_map(results)

    print(f"[BITTI] {time.time() - t0:.0f}s — Log: {LOG_FILE}", flush=True)


if __name__ == "__main__":
    main()
