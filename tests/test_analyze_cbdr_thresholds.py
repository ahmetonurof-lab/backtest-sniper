"""
test_analyze_cbdr_thresholds.py — Birim ve regresyon testleri.

Kullanim:
  python test_analyze_cbdr_thresholds.py              # unit test
  python test_analyze_cbdr_thresholds.py --regression  # 1 coin × REAL_CBDR baseline
"""

import os
import sys
import json
import argparse
import tempfile

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import analyze_cbdr_thresholds as m  # noqa: E402

_P = 0
_F = 0
_SP = 0
_SF = 0


def _assert_eq(label, got, expected):
    global _P, _F, _SP, _SF
    if got == expected:
        _P += 1
        _SP += 1
        print(f"  OK  {label}: {got!r}")
    else:
        _F += 1
        _SF += 1
        print(f"  FAIL {label}: got {got!r}, expected {expected!r}")


def _assert_close(label, got, expected, tol=0.01):
    global _P, _F, _SP, _SF
    if abs(got - expected) <= tol:
        _P += 1
        _SP += 1
        print(f"  OK  {label}: {got}")
    else:
        _F += 1
        _SF += 1
        print(f"  FAIL {label}: got {got}, expected {expected} (tol={tol})")


def print_summary(section):
    global _SP, _SF
    total = _SP + _SF
    print(f"\n  [{section}] {_SP}/{total} passed, {_SF} failed\n")
    _SP = 0
    _SF = 0


# ── 1. _parse_fvg_size_from_md ─────────────────────────────────


def test_parse_fvg_size_from_md():
    md_content = """# FVG Size Profile
| Coin | Best FVG Size | Score | Trades |
|------|--------------|-------|--------|
| BTCUSDT | 0.050 | 100 | 500 |

```python
FVG_SIZE_MAP: dict[str, float] = {
    "BTCUSDT": 0.050,
    "ETHUSDT": 0.030,
}
```"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as f:
        f.write(md_content)
        tmp = f.name

    try:
        result = m._parse_fvg_size_from_md(tmp)
        _assert_eq("parse: BTCUSDT", result.get("BTCUSDT"), 0.050)
        _assert_eq("parse: ETHUSDT", result.get("ETHUSDT"), 0.030)
        _assert_eq("parse: count", len(result), 2)
    finally:
        os.unlink(tmp)

    # Dosya yoksa None
    none_result = m._parse_fvg_size_from_md("/nonexistent/path.md")
    _assert_eq("parse: missing file", none_result, None)


# ── 2. compute_session_stats ────────────────────────────────────


def test_compute_session_stats_empty():
    stats = m.compute_session_stats([], 10000)
    _assert_eq("empty: total_trades", stats["total_trades"], 0)
    _assert_eq("empty: score", stats["score"], 0)


def test_compute_session_stats_all_tp():
    records = [
        {"result": "TP", "pnl": 100, "fee": 5},
        {"result": "TP", "pnl": 150, "fee": 6},
    ]
    stats = m.compute_session_stats(records, 10000)
    _assert_eq("all_tp: trades", stats["total_trades"], 2)
    _assert_eq("all_tp: tp_pct", stats["tp_pct"], 100.0)
    _assert_eq("all_tp: ptrail_pct", stats["profit_trail_pct"], 0.0)
    _assert_eq("all_tp: pe_pct", stats["positive_exit_pct"], 100.0)
    _assert_close("all_tp: pf", stats["profit_factor"], 999.0)
    _assert_eq("all_tp: total_pnl", stats["total_pnl"], 250)
    _assert_eq("all_tp: total_fee", stats["total_fee"], 11)
    _assert_close("all_tp: pnl_per_fee", stats["pnl_per_fee"], 250 / 11)
    _assert_close("all_tp: max_dd_pct", stats["max_dd_pct"], 0.0)
    _assert_eq(
        "all_tp: score", stats["score"], round(999.0 * 1.0 * (250 / 11) / 1.0 * 100)
    )


def test_compute_session_stats_mixed():
    records = [
        {"result": "TP", "pnl": 200, "fee": 5},
        {"result": "PROFIT_TRAIL", "pnl": 80, "fee": 4},
        {"result": "LOSS", "pnl": -50, "fee": 3},
        {"result": "LOSS", "pnl": -30, "fee": 2},
    ]
    stats = m.compute_session_stats(records, 10000)
    _assert_eq("mixed: trades", stats["total_trades"], 4)
    _assert_eq("mixed: tp_pct", stats["tp_pct"], 25.0)
    _assert_eq("mixed: ptrail_pct", stats["profit_trail_pct"], 25.0)
    _assert_eq("mixed: pe_pct", stats["positive_exit_pct"], 50.0)

    gp = 200 + 80
    gl = 50 + 30
    _assert_close("mixed: pf", stats["profit_factor"], gp / gl)

    total_fee = 5 + 4 + 3 + 2
    total_pnl = 200 + 80 - 50 - 30
    _assert_eq("mixed: total_fee", stats["total_fee"], total_fee)
    _assert_eq("mixed: total_pnl", stats["total_pnl"], total_pnl)
    _assert_close("mixed: pnl_per_fee", stats["pnl_per_fee"], total_pnl / total_fee)

    # MaxDD: cum 200, peak 200, dd 0; cum 280, peak 280, dd 0; cum 230, peak 280, dd 50; cum 200, peak 280, dd 80
    max_dd = 80
    peak_bal = 10000 + 280
    dd_pct = max_dd / peak_bal * 100
    _assert_close("mixed: max_dd_pct", stats["max_dd_pct"], dd_pct)

    expected_score = (
        (
            stats["profit_factor"]
            * stats["positive_exit_pct"]
            / 100
            * stats["pnl_per_fee"]
        )
        / (1 + dd_pct / 100)
        * 100
    )
    _assert_close("mixed: score", stats["score"], round(expected_score))


def test_compute_session_stats_drawdown_high():
    # Same PF, PE%, total_pnl, total_fee — different DD → DD penalizes score
    records_low_dd = [
        {"result": "TP", "pnl": 200, "fee": 5},
        {"result": "LOSS", "pnl": -100, "fee": 5},
    ]
    records_high_dd = [
        {"result": "TP", "pnl": 200, "fee": 5},
        {"result": "LOSS", "pnl": -100, "fee": 5},
        {"result": "LOSS", "pnl": -100, "fee": 5},
        {"result": "TP", "pnl": 200, "fee": 5},
    ]
    # Same overall: PF=2.0, PE%=50%, total_pnl=100, total_fee=10 per pair
    s_low = m.compute_session_stats(records_low_dd, 10000)
    s_high = m.compute_session_stats(records_high_dd, 10000)
    _assert_close("dd: PF", s_low["profit_factor"], s_high["profit_factor"])
    _assert_eq("dd: PE%", s_low["positive_exit_pct"], s_high["positive_exit_pct"])
    # high_dd has alternating wins/losses → deeper drawdown
    assert s_high["max_dd_pct"] > s_low["max_dd_pct"], "high DD should be larger"
    print(
        f"  INFO dd: low_score={s_low['score']} high_score={s_high['score']} "
        f"low_dd={s_low['max_dd_pct']:.4f}% high_dd={s_high['max_dd_pct']:.4f}%"
    )
    _assert_eq("dd: high score lower", s_low["score"] > s_high["score"], True)


# ── 3. Score formula consistency with analyzer_v5 ────────────────


def test_score_formula_matches_v5():
    """Same trade_records should produce identical score from both engines."""
    sys.path.insert(0, _THIS_DIR)
    from analyzer_v5 import compute_session_stats as v5_stats

    records = [
        {"result": "TP", "pnl": 150, "fee": 5, "risk_usd": 20},
        {"result": "PROFIT_TRAIL", "pnl": 50, "fee": 3, "risk_usd": 20},
        {"result": "LOSS", "pnl": -30, "fee": 2, "risk_usd": 20},
        {"result": "LOSS", "pnl": -20, "fee": 2, "risk_usd": 20},
    ]
    balance = 10000
    s_v5 = v5_stats(records, balance)
    s_th = m.compute_session_stats(records, balance)

    keys = [
        "total_trades",
        "tp_pct",
        "profit_trail_pct",
        "positive_exit_pct",
        "profit_factor",
        "max_dd_pct",
        "total_pnl",
        "total_fee",
        "pnl_per_fee",
        "score",
    ]
    for key in keys:
        _assert_close(f"v5_match: {key}", s_th[key], s_v5[key], tol=0.01)


# ── 4. Wilson CI ────────────────────────────────────────────────


def test_wilson_upper_edge():
    _assert_eq("wilson_up: 0 trades", m.wilson_upper(0, 0), 1.0)


def test_wilson_lower_edge():
    _assert_eq("wilson_lo: 0 trades", m.wilson_lower(0, 0), 0.0)


def test_wilson_50pct_200():
    u = m.wilson_upper(100, 200)
    lo = m.wilson_lower(100, 200)
    _assert_close("wilson 100/200 upper", u, 0.569, tol=0.01)
    _assert_close("wilson 100/200 lower", lo, 0.431, tol=0.01)
    _assert_eq("wilson 100/200 symmetric", u > 0.5 and lo < 0.5, True)


def test_wilson_90pct_1000():
    u = m.wilson_upper(900, 1000)
    lo = m.wilson_lower(900, 1000)
    _assert_close("wilson 900/1000 upper", u, 0.919, tol=0.01)
    _assert_close("wilson 900/1000 lower", lo, 0.878, tol=0.01)


# ── 5. analyze_thresholds ───────────────────────────────────────


def test_analyze_thresholds_none():
    thr = m.analyze_thresholds([], "TESTUSDT")
    _assert_eq("thr: empty", thr, None)


def test_analyze_thresholds_few_days():
    rows = [{"cbdr_pct": 2.0, "trades": 10, "wins": 5, "pnl": 100}] * 3
    thr = m.analyze_thresholds(rows, "TESTUSDT")
    _assert_eq("thr: <5 days", thr, None)


def test_analyze_thresholds_basic():
    rows = [
        {"cbdr_pct": 1.0 + i * 0.5, "trades": 100, "wins": 55, "pnl": 500}
        for i in range(10)
    ]
    thr = m.analyze_thresholds(rows, "TESTUSDT", min_bucket_trades=10)
    _assert_eq("thr: symbol", thr["symbol"], "TESTUSDT")
    _assert_eq("thr: total_days", thr["total_days"], 10)
    _assert_eq("thr: total_pnl", thr["total_pnl"], 5000)
    _assert_close("thr: overall_wr", thr["overall_wr"], 55.0, tol=0.1)
    _assert_eq("thr: buckets exists", len(thr["buckets"]) > 0, True)


# ── 6. analyze_bucket_scaling ───────────────────────────────────


def test_analyze_bucket_scaling_no_profile():
    rows = [{"cbdr_pct": 2.0, "trades": 10, "wins": 5}]
    bs = m.analyze_bucket_scaling(rows, "NONEXISTENTUSDT")
    _assert_eq("bs: no profile", bs, None)


# ── 7. Regression test (1 coin × REAL_CBDR) ─────────────────────


BASELINE_PATH = os.path.join(
    _THIS_DIR, "..", "reports", "cbdr_thresholds_baseline.json"
)
REGRESSION_TOLERANCE = {
    "total_trades": 0.02,
    "tp_pct": 2.0,
    "profit_trail_pct": 2.0,
    "positive_exit_pct": 2.0,
    "profit_factor": 0.10,
    "max_dd_pct": 1.0,
    "total_pnl": 0.05,
    "total_fee": 0.05,
    "score": 5.0,
}


def _save_baseline(data):
    os.makedirs(os.path.dirname(BASELINE_PATH), exist_ok=True)
    with open(BASELINE_PATH, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Baseline: {BASELINE_PATH}")


def _load_baseline():
    if not os.path.isfile(BASELINE_PATH):
        return None
    with open(BASELINE_PATH) as f:
        return json.load(f)


def run_regression():
    sym = "SOLUSDT"
    session_hours = {"start": 19, "end": 1}
    result = m.run_session_analysis(sym, "REAL_CBDR", session_hours)
    if result is None:
        print(f"\n  [REGRESSION] {sym} VERI YOK veya YETERSIZ")
        return None

    st = result["stats"]
    print(
        f"\n  [{sym}] {st['total_trades']} islem | "
        f"TP={st['tp_pct']:.1f}% PTrail={st['profit_trail_pct']:.1f}% "
        f"PF={st['profit_factor']:.2f} DD={st['max_dd_pct']:.1f}% "
        f"Skor={st['score']} PnL={st['total_pnl']:+.0f}"
    )

    return {
        "symbol": sym,
        "session": "REAL_CBDR",
        "total_trades": st["total_trades"],
        "tp_pct": round(st["tp_pct"], 1),
        "profit_trail_pct": round(st["profit_trail_pct"], 1),
        "positive_exit_pct": round(st["positive_exit_pct"], 1),
        "profit_factor": round(st["profit_factor"], 2),
        "max_dd_pct": round(st["max_dd_pct"], 1),
        "total_pnl": round(st["total_pnl"], 0),
        "total_fee": round(st["total_fee"], 0),
        "score": round(st["score"], 0),
    }


def compare_regression(current, baseline):
    failures = 0
    for key in REGRESSION_TOLERANCE:
        cv = current[key]
        bv = baseline[key]
        tol = REGRESSION_TOLERANCE.get(key, 0)

        if key in ("total_trades", "total_pnl", "total_fee"):
            diff = abs(cv - bv) / max(abs(bv), 1) * 100
            ok = diff <= tol * 100
        elif key == "score":
            diff = abs(cv - bv)
            ok = diff <= tol
        else:
            diff = abs(cv - bv)
            ok = diff <= tol

        status = "OK" if ok else "FAIL"
        if not ok:
            failures += 1
        print(f"  {key:<20} baseline={bv} current={cv} diff={diff:.2f} [{status}]")
    return failures


# ── Runner ──────────────────────────────────────────────────────


def run_unit_tests():
    print("=" * 60)
    print("  UNIT TESTS — analyze_cbdr_thresholds.py")
    print("=" * 60)

    test_parse_fvg_size_from_md()
    print_summary("_parse_fvg_size_from_md")

    test_compute_session_stats_empty()
    test_compute_session_stats_all_tp()
    test_compute_session_stats_mixed()
    test_compute_session_stats_drawdown_high()
    print_summary("compute_session_stats")

    test_score_formula_matches_v5()
    print_summary("formula vs analyzer_v5")

    test_wilson_upper_edge()
    test_wilson_lower_edge()
    test_wilson_50pct_200()
    test_wilson_90pct_1000()
    print_summary("wilson CI")

    test_analyze_thresholds_none()
    test_analyze_thresholds_few_days()
    test_analyze_thresholds_basic()
    print_summary("analyze_thresholds")

    test_analyze_bucket_scaling_no_profile()
    print_summary("analyze_bucket_scaling")


def main():
    parser = argparse.ArgumentParser(
        description="analyze_cbdr_thresholds.py test suite"
    )
    parser.add_argument(
        "--regression", action="store_true", help="Regresyon testi (baseline)"
    )
    parser.add_argument("--update", action="store_true", help="Baseline guncelle")
    parser.add_argument("--check", action="store_true", help="Baseline ile karsilastir")
    args = parser.parse_args()

    if args.regression or args.update or args.check:
        print("=" * 60)
        print("  REGRESYON TESTI — analyze_cbdr_thresholds.py")
        print("  Coin: SOLUSDT, Session: REAL_CBDR")
        print("=" * 60)

        current = run_regression()
        if current is None:
            print("\n  TEST: VERI YOK (atlandi)")
            return

        baseline = _load_baseline()
        if args.update or baseline is None:
            _save_baseline(current)
            print("\n  Baseline kaydedildi.")
            if args.check:
                print("  --check ile kontrol edin.")
            return

        print("\n  Karsilastirma:")
        failures = compare_regression(current, baseline)
        print(f"\n  SONUC: {failures} hata")
    else:
        run_unit_tests()

    global _P, _F
    total = _P + _F
    print(f"\n  TOPLAM: {_P}/{total} passed, {_F} failed")
    sys.exit(0 if _F == 0 else 1)


if __name__ == "__main__":
    main()
