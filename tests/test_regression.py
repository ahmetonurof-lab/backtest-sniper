"""
regression_test.py — analyzer_v5.py regresyon testi.
1 coin × 1 session calistir, output'u baseline ile karsilastir.

Kullanim:
  python test_regression.py              # ilk calistirma -> baseline kaydet
  python test_regression.py --check      # baseline ile karsilastir
  python test_regression.py --update     # baseline'i guncelle
"""
import sys, os, json, math, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from analyzer_v5 import collect_fvg_profile, compute_session_stats
from session_router import get_session_hours
import config as cfg

SYM = "BTCUSDT"
BASELINE_PATH = os.path.join(os.path.dirname(__file__), "..", "reports", "regression_baseline.json")
TOLERANCE = {
    "total_trades": 0.02,    # %2
    "tp_pct": 2.0,           # mutlak yuzde
    "profit_factor": 0.10,    # mutlak
    "max_dd_pct": 1.0,        # mutlak yuzde
    "sharpe": 0.3,            # mutlak
    "total_pnl": 0.05,        # %5
}


def run_test():
    """BTC + REAL_CBDR calistir, sonuclari don."""
    csv_path = os.path.join(os.path.dirname(__file__), "data", "daily", f"{SYM}_1m_raw.csv")
    if not os.path.isfile(csv_path):
        print(f"  VERI YOK: {csv_path}")
        return None

    profile = cfg.CBDR_RISK_MATRIX.get(SYM, {})
    sname = profile.get("session", "REAL_CBDR")
    sh_info = get_session_hours(SYM)
    print(f"  [{SYM}] Session={sname} [{sh_info['start']:02d}:00-{sh_info['end']:02d}:00]", flush=True)

    result = collect_fvg_profile(SYM)
    if result is None or result[0] is None:
        print(f"  [{SYM}] ENGINE BASARISIZ")
        return None

    daily_rows, wins, losses, trade_records, rejection_counts = result
    stats = compute_session_stats(trade_records, cfg.INITIAL_BALANCE, daily_rows)

    print(f"  Trades={stats['total_trades']} TP={stats['tp_pct']:.1f}% "
          f"PF={stats['profit_factor']:.2f} DD={stats['max_dd_pct']:.1f}% "
          f"Sharpe={stats['sharpe']:.2f} PnL={stats['total_pnl']:+.0f}", flush=True)

    return {
        "symbol": SYM,
        "session": sname,
        "total_trades": stats["total_trades"],
        "tp_pct": round(stats["tp_pct"], 1),
        "profit_factor": round(stats["profit_factor"], 2),
        "max_dd_pct": round(stats["max_dd_pct"], 1),
        "sharpe": round(stats["sharpe"], 2),
        "total_pnl": round(stats["total_pnl"], 0),
        "wins": stats["wins"],
        "be": stats["be"],
        "losses": stats["losses"],
        "entered": rejection_counts.get("ENTERED", 0),
    }


def save_baseline(data):
    with open(BASELINE_PATH, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Baseline kaydedildi: {BASELINE_PATH}")


def load_baseline():
    if not os.path.isfile(BASELINE_PATH):
        return None
    with open(BASELINE_PATH) as f:
        return json.load(f)


def compare(current, baseline):
    failures = 0
    for key in ["total_trades", "tp_pct", "profit_factor", "max_dd_pct", "sharpe", "total_pnl"]:
        cv = current[key]
        bv = baseline[key]
        tol = TOLERANCE.get(key, 0)

        if key in ("total_trades", "total_pnl"):
            diff = abs(cv - bv) / max(abs(bv), 1) * 100
            ok = diff <= tol * 100
        else:
            diff = abs(cv - bv)
            ok = diff <= tol

        status = "OK" if ok else "FAIL"
        if not ok:
            failures += 1
        print(f"  {key:<16} baseline={bv} current={cv} diff={diff:.2f} [{status}]")

    return failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Baseline ile karsilastir")
    parser.add_argument("--update", action="store_true", help="Baseline'i guncelle")
    args = parser.parse_args()

    print("=" * 60)
    print("  REGRESYON TESTI — analyzer_v5.py")
    print(f"  Coin: {SYM}")
    print("=" * 60)

    current = run_test()
    if current is None:
        print("\n  TEST: VERI YOK (atlandi)")
        return

    if args.check or os.path.isfile(BASELINE_PATH):
        baseline = load_baseline()
        if baseline is None:
            print("\n  Baseline bulunamadi. --update ile kaydedin.")
            save_baseline(current)
            return

        print("\n  Karsilastirma:")
        failures = compare(current, baseline)
        print(f"\n  SONUC: {failures} hata")
    else:
        save_baseline(current)
        print("\n  Baseline kaydedildi. Kontrol icin --check ile tekrar calistirin.")

    print("=" * 60)


if __name__ == "__main__":
    main()
