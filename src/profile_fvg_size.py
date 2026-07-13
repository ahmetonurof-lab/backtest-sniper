"""
profile_fvg_size.py — Coin bazinda optimum FVG_MIN_SIZE_ATR_MULT bulma.
Sweep 0.02 - 0.20 step 0.01, motor analyzer_v5.

Degisiklik (2026-07-13):
- fvg_close_confirmed = OFF (retrace_state.py'de devre disi)
- MIN_REL_FVG_THRESHOLD = 0.40 (sabit)
- Sadece FVG_MIN_SIZE_ATR_MULT taranir

Tum detay log'u reports/profile_fvg_size.log dosyasina yazilir.
Sonucta sadece ozet terminale basilir.

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
    "ALGOUSDT",
    "APTUSDT",
    "ARBUSDT",
    "ATOMUSDT",
    "AAVEUSDT",
    "ADAUSDT",
    "AVAXUSDT",
    "BNBUSDT",
    "DOGEUSDT",
    "BTCUSDT",
    "ETHUSDT",
    "DOTUSDT",
    "INJUSDT",
    "LINKUSDT",
    "NEARUSDT",
    "OPUSDT",
    "SOLUSDT",
    "SUIUSDT",
    "XRPUSDT",
    "UNIUSDT",
]
SWEEP_START = 0.02
SWEEP_END = 0.20
SWEEP_STEP = 0.01
FIXED_CBDR_THRESHOLD = 0.40


def _log_line(msg: str):
    """Append to log file."""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
        f.flush()


# ─── Worker: tek coin profilleme ─────────────────────────────
def _profile_one(sym: str) -> dict | None:
    """Tek coin icin tum FVG_MIN_SIZE_ATR_MULT degerlerini dene, en iyisini bul.
    Ayri ProcessPoolExecutor worker'inda calisir."""
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
        _log_line(f"[{sym}] VERI YOK: {feather_path}")
        return None

    values = [
        round(SWEEP_START + i * SWEEP_STEP, 3)
        for i in range(int((SWEEP_END - SWEEP_START) / SWEEP_STEP) + 1)
    ]
    results = []

    # Sabit: CBDR threshold
    cfg.MIN_REL_FVG_THRESHOLD = FIXED_CBDR_THRESHOLD

    for idx, size in enumerate(values):
        cfg.FVG_MIN_SIZE_ATR_MULT = size
        try:
            r = collect_fvg_profile(sym)
        except Exception as e:
            _log_line(f"  [{sym}] mult={size:.3f} CRASH: {e}")
            continue

        if r is None or (isinstance(r, tuple) and r[0] is None):
            _log_line(f"  [{sym}] mult={size:.3f} VERI YOK")
            continue

        daily_rows, wins, losses, trade_records, rejection_counts = r
        if not trade_records:
            results.append((size, 0))
            continue

        n = len(trade_records)
        tp = sum(1 for t in trade_records if t["result"] == "TP")
        ptrail = sum(1 for t in trade_records if t["result"] == "PROFIT_TRAIL")
        tp_pct = tp / n * 100
        ptrail_pct = ptrail / n * 100
        positive_exit_pct = tp_pct + ptrail_pct

        gross_profit = sum(t["pnl"] for t in trade_records if t["pnl"] > 0) or 0
        gross_loss = abs(sum(t["pnl"] for t in trade_records if t["pnl"] < 0))
        pf = 999.0 if gross_loss == 0 else gross_profit / gross_loss

        total_pnl = sum(t["pnl"] for t in trade_records)
        total_fee = sum(t.get("fee", 0) for t in trade_records)
        pnl_per_fee = total_pnl / total_fee if total_fee > 0 else 0

        cumulative = 0
        peak = 0
        max_dd = 0
        for t in trade_records:
            cumulative += t["pnl"]
            if cumulative > peak:
                peak = cumulative
            dd = peak - cumulative
            if dd > max_dd:
                max_dd = dd
        peak_balance = cfg.INITIAL_BALANCE + peak
        max_dd_pct = (max_dd / peak_balance) * 100 if peak_balance > 0 else 0

        pe_dec = positive_exit_pct / 100.0
        score = (pf * pe_dec * pnl_per_fee) / (1 + max_dd_pct / 100) * 100
        results.append((size, round(score)))

        entered = rejection_counts.get("ENTERED", 0)
        _log_line(
            f"  [{sym}] {idx + 1:>2}/{len(values)} mult={size:.3f} score={round(score)} trades={n} entered={entered}"
        )

    if not results:
        _log_line(f"  [{sym}] HICBIR SONUC YOK")
        return None
    best = max(results, key=lambda x: x[1])
    _log_line(f"  [{sym}] BEST: mult={best[0]:.3f} score={best[1]}")
    return {
        "sym": sym,
        "best_size": best[0],
        "best_score": best[1],
        "total_values": len(results),
    }


def _print_fvg_map(results: dict):
    lines = []
    lines.append("")
    lines.append("=" * 80)
    lines.append("  BEST FVG_MIN_SIZE_ATR_MULT PER COIN")
    lines.append(f"  (MIN_REL_FVG_THRESHOLD={FIXED_CBDR_THRESHOLD} sabit)")
    lines.append("=" * 80)
    lines.append(f"  {'Coin':<12} {'Best Mult':>10} {'Score':>8}")
    lines.append(f"  {'-' * 34}")
    for sym in sorted(results):
        r = results[sym]
        lines.append(f"  {sym:<12} {r['best_size']:>10.3f} {r['best_score']:>8}")
    lines.append("")
    lines.append("# Config'de guncellemek icin:")
    lines.append(
        f"FVG_MIN_SIZE_ATR_MULT = {results[sorted(results)[0]]['best_size']:.3f}  # ortalama"
    )
    lines.append("")
    lines.append("# Coin bazli cozum (opsiyonel):")
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

    parser = argparse.ArgumentParser(description="FVG_SIZE profiler")
    parser.add_argument("--workers", type=int, default=4, help="Worker sayisi")
    parser.add_argument("--serial", action="store_true", help="Sirali mod")
    args = parser.parse_args()

    use_serial = args.serial or args.workers <= 1
    n_workers = 1 if use_serial else args.workers

    # Log dosyasini temizle
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("FVG SIZE PROFILER\n")
        f.write(f"Sweep: {SWEEP_START}-{SWEEP_END} step {SWEEP_STEP}\n")
        f.write(
            f"Coins: {len(SYMBOLS_20)}, values/coin: {int((SWEEP_END - SWEEP_START) / SWEEP_STEP) + 1}\n"
        )
        f.write(
            f"Mod: {'PARALEL' if not use_serial else 'SERIAL'} ({n_workers} worker)\n"
        )
        f.write("=" * 80 + "\n")
        f.flush()

    t0 = time.time()
    print(f"[LOG] Detaylar -> {LOG_FILE}", flush=True)
    print(
        f"[BASLADI] {len(SYMBOLS_20)} coin, {int((SWEEP_END - SWEEP_START) / SWEEP_STEP) + 1} deger/coin, {n_workers} worker",
        flush=True,
    )

    results = {}

    if use_serial:
        for sym in sorted(SYMBOLS_20):
            _log_line(f"\n[{sym}] basliyor...")
            r = _profile_one(sym)
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
            fut_map = {executor.submit(_profile_one, sym): sym for sym in syms}
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
        _print_fvg_map(results)

    print(f"[BITTI] {time.time() - t0:.0f}s — Log: {LOG_FILE}", flush=True)


if __name__ == "__main__":
    main()
