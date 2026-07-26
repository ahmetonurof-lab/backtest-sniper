"""Tests for fvg_zone_analyzer.py."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"),
)

from fvg_zone_analyzer import (
    classify_zone,
    find_nearest_fib_level,
    compute_zone_fibo_stats,
)


def test_classify_zone_bullish():
    assert classify_zone("bullish") == "discount"


def test_classify_zone_bearish():
    assert classify_zone("bearish") == "premium"


def test_classify_zone_empty():
    assert classify_zone("") == "premium"


def test_find_nearest_fib_level_exact():
    level, confirmed = find_nearest_fib_level(50.0, 100.0, 0.0)
    assert level == 0.5
    assert confirmed is True


def test_find_nearest_fib_level_near_618():
    level, confirmed = find_nearest_fib_level(61.8, 100.0, 0.0)
    assert level == 0.618
    assert confirmed is True


def test_find_nearest_fib_level_unconfirmed():
    level, confirmed = find_nearest_fib_level(40.0, 100.0, 0.0)
    assert level == 0.382
    assert confirmed is False


def test_find_nearest_fib_level_invalid_range():
    level, confirmed = find_nearest_fib_level(50.0, 0.0, 100.0)
    assert level is None
    assert confirmed is False


def test_find_nearest_fib_level_zero_midpoint():
    level, confirmed = find_nearest_fib_level(0.0, 0.0, 100.0)
    assert level is None
    assert confirmed is False


def test_compute_zone_fibo_stats_empty():
    rows = compute_zone_fibo_stats([])
    assert rows == []


def test_compute_zone_fibo_stats_single_trade():
    records = [
        {
            "result": "TP",
            "pnl": 100.0,
            "risk_usd": 50.0,
            "fvg_direction": "bullish",
            "fvg_top": 51.0,
            "fvg_bottom": 49.0,
            "cbdr_body_high": 55.0,
            "cbdr_body_low": 45.0,
        }
    ]
    rows = compute_zone_fibo_stats(records)
    assert len(rows) == 1
    r = rows[0]
    assert r["zone"] == "discount"
    assert r["trades"] == 1
    assert r["tp_pct"] == 100.0
    assert r["pf"] == 999.0


def test_compute_zone_fibo_stats_mixed():
    records = [
        {
            "result": "TP",
            "pnl": 100.0,
            "risk_usd": 50.0,
            "fvg_direction": "bullish",
            "fvg_top": 51.0,
            "fvg_bottom": 49.0,
            "cbdr_body_high": 55.0,
            "cbdr_body_low": 45.0,
        },
        {
            "result": "LOSS",
            "pnl": -50.0,
            "risk_usd": 50.0,
            "fvg_direction": "bullish",
            "fvg_top": 51.0,
            "fvg_bottom": 49.0,
            "cbdr_body_high": 55.0,
            "cbdr_body_low": 45.0,
        },
        {
            "result": "TP",
            "pnl": 200.0,
            "risk_usd": 100.0,
            "fvg_direction": "bearish",
            "fvg_top": 101.0,
            "fvg_bottom": 99.0,
            "cbdr_body_high": 105.0,
            "cbdr_body_low": 95.0,
        },
    ]
    rows = compute_zone_fibo_stats(records)
    zones = {r["zone"] for r in rows}
    assert "discount" in zones
    assert "premium" in zones


def test_compute_zone_fibo_stats_pf_calculation():
    records = [
        {
            "result": "TP",
            "pnl": 150.0,
            "risk_usd": 50.0,
            "fvg_direction": "bullish",
            "fvg_top": 51.0,
            "fvg_bottom": 49.0,
            "cbdr_body_high": 55.0,
            "cbdr_body_low": 45.0,
        },
        {
            "result": "LOSS",
            "pnl": -50.0,
            "risk_usd": 50.0,
            "fvg_direction": "bullish",
            "fvg_top": 51.0,
            "fvg_bottom": 49.0,
            "cbdr_body_high": 55.0,
            "cbdr_body_low": 45.0,
        },
    ]
    rows = compute_zone_fibo_stats(records)
    r = rows[0]
    assert r["pf"] == 3.0


def test_compute_zone_fibo_stats_net_pnl():
    records = [
        {
            "result": "TP",
            "pnl": 100.0,
            "risk_usd": 50.0,
            "fvg_direction": "bullish",
            "fvg_top": 51.0,
            "fvg_bottom": 49.0,
            "cbdr_body_high": 55.0,
            "cbdr_body_low": 45.0,
        },
        {
            "result": "LOSS",
            "pnl": -30.0,
            "risk_usd": 50.0,
            "fvg_direction": "bullish",
            "fvg_top": 51.0,
            "fvg_bottom": 49.0,
            "cbdr_body_high": 55.0,
            "cbdr_body_low": 45.0,
        },
    ]
    rows = compute_zone_fibo_stats(records)
    r = rows[0]
    assert r["net_pnl"] == 70.0


def test_compute_zone_fibo_stats_by_confirmed():
    records = [
        {
            "result": "TP",
            "pnl": 100.0,
            "risk_usd": 50.0,
            "fvg_direction": "bullish",
            "fvg_top": 50.5,
            "fvg_bottom": 49.5,
            "cbdr_body_high": 55.0,
            "cbdr_body_low": 45.0,
        },
        {
            "result": "TP",
            "pnl": 80.0,
            "risk_usd": 50.0,
            "fvg_direction": "bullish",
            "fvg_top": 50.5,
            "fvg_bottom": 49.5,
            "cbdr_body_high": 55.0,
            "cbdr_body_low": 45.0,
        },
    ]
    rows = compute_zone_fibo_stats(records)
    for r in rows:
        assert r["confirmed"] in ("confirmed", "unconfirmed")


def test_generate_zone_fibo_report_writes_file(tmp_path):
    from fvg_zone_analyzer import generate_zone_fibo_report

    records = [
        {
            "result": "TP",
            "pnl": 100.0,
            "risk_usd": 50.0,
            "fvg_direction": "bullish",
            "fvg_top": 51.0,
            "fvg_bottom": 49.0,
            "cbdr_body_high": 55.0,
            "cbdr_body_low": 45.0,
        },
    ]
    generate_zone_fibo_report(records, str(tmp_path))
    report_file = tmp_path / "fvg_zone_fibo_analysis.md"
    assert report_file.exists()
    content = report_file.read_text(encoding="utf-8")
    assert "FVG Zone + Fibonacci Analizi" in content
    assert "discount" in content


def test_compute_max_dd_positive():
    from fvg_zone_analyzer import compute_max_dd

    records = [
        {"pnl": 100},
        {"pnl": 50},
        {"pnl": -30},
        {"pnl": 20},
        {"pnl": -80},
    ]
    result = compute_max_dd(records)
    assert result > 0
    assert result < 100


def test_compute_max_dd_all_profit():
    from fvg_zone_analyzer import compute_max_dd

    records = [{"pnl": 10}, {"pnl": 20}, {"pnl": 30}]
    assert compute_max_dd(records) == 0.0


def test_compute_max_dd_empty():
    from fvg_zone_analyzer import compute_max_dd

    assert compute_max_dd([]) == 0.0


def test_run_holdout_validation_writes_file():
    from fvg_zone_analyzer import run_holdout_validation

    records = []
    for i in range(100):
        records.append(
            {
                "result": "TP" if i % 3 == 0 else "LOSS",
                "pnl": 100.0 if i % 3 == 0 else -50.0,
                "risk_usd": 50.0,
                "fvg_direction": "bullish" if i % 2 == 0 else "bearish",
                "fvg_top": 51.0,
                "fvg_bottom": 49.0,
                "cbdr_body_high": 55.0,
                "cbdr_body_low": 45.0,
            }
        )

    run_holdout_validation(records, "/tmp/reports")
    import os

    docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")
    report_file = os.path.join(docs_dir, "fibo_zone_holdout_validation.md")
    assert os.path.exists(report_file)
    content = open(report_file, encoding="utf-8").read()
    assert "Holdout Doğrulaması" in content
    assert "Train" in content
    assert "Holdout" in content
    assert "Karar" in content


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
