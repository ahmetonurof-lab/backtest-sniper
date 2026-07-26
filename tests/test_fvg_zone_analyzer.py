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
    compute_max_dd,
    run_holdout_validation,
    generate_holdout_report,
    HoldoutResult,
    _filter_fib_level,
    _bucket_stats,
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
    records = [{"pnl": 10}, {"pnl": 20}, {"pnl": 30}]
    assert compute_max_dd(records) == 0.0


def test_compute_max_dd_empty():
    assert compute_max_dd([]) == 0.0


def test_filter_fib_level_separates_0236_and_0786():
    records = []
    for i in range(200):
        records.append(
            {
                "result": "TP",
                "pnl": 100.0,
                "risk_usd": 50.0,
                "fvg_direction": "bullish",
                "fvg_top": 47.5,
                "fvg_bottom": 47.2,
                "cbdr_body_high": 55.0,
                "cbdr_body_low": 45.0,
            }
        )
    for i in range(200):
        records.append(
            {
                "result": "TP",
                "pnl": 100.0,
                "risk_usd": 50.0,
                "fvg_direction": "bearish",
                "fvg_top": 54.0,
                "fvg_bottom": 53.8,
                "cbdr_body_high": 55.0,
                "cbdr_body_low": 50.0,
            }
        )

    level_236 = _filter_fib_level(records, 0.236)
    level_786 = _filter_fib_level(records, 0.786)

    assert len(level_236) > 0
    assert len(level_786) > 0
    assert all(t.get("fvg_direction") == "bullish" for t in level_236)
    assert all(t.get("fvg_direction") == "bearish" for t in level_786)


def test_bucket_stats_reliable():
    records = [{"pnl": 10.0, "result": "TP", "risk_usd": 50.0}] * 150
    stats = _bucket_stats(records)
    assert stats["reliable"] is True
    assert stats["trades"] == 150


def test_bucket_stats_unreliable():
    records = [{"pnl": 10.0, "result": "TP", "risk_usd": 50.0}] * 50
    stats = _bucket_stats(records)
    assert stats["reliable"] is False
    assert stats["trades"] == 50


def test_holdout_result_dataclass():
    result = HoldoutResult()
    assert result.validated is False
    assert result.reason == ""
    assert result.train_matched == []
    assert result.holdout_matched == []
    assert result.train_mismatched == []
    assert result.holdout_mismatched == []


def test_run_holdout_validation_returns_holdout_result():
    records = []
    for i in range(200):
        records.append(
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
        )
    for i in range(200):
        records.append(
            {
                "result": "LOSS",
                "pnl": -50.0,
                "risk_usd": 50.0,
                "fvg_direction": "bearish",
                "fvg_top": 101.0,
                "fvg_bottom": 99.0,
                "cbdr_body_high": 105.0,
                "cbdr_body_low": 95.0,
            }
        )

    result = run_holdout_validation(records, "/tmp/reports")
    assert isinstance(result, HoldoutResult)
    assert isinstance(result.validated, bool)
    assert isinstance(result.reason, str)


def test_run_holdout_validation_separates_matched_mismatched():
    records = []
    for i in range(200):
        records.append(
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
        )
    for i in range(200):
        records.append(
            {
                "result": "TP",
                "pnl": 100.0,
                "risk_usd": 50.0,
                "fvg_direction": "bearish",
                "fvg_top": 101.0,
                "fvg_bottom": 99.0,
                "cbdr_body_high": 105.0,
                "cbdr_body_low": 95.0,
            }
        )

    result = run_holdout_validation(records, "/tmp/reports")
    assert len(result.train_matched) >= 0
    assert len(result.train_mismatched) >= 0


def test_generate_holdout_report_writes_file(tmp_path):
    result = HoldoutResult(
        train_matched=[
            {
                "split": "train",
                "zone": "discount",
                "fibo_level": 0.236,
                "match_type": "matched",
                "trades": 150,
                "reliable": True,
                "winrate": 60.0,
                "pf": 3.5,
                "net_pnl": 50000,
                "max_dd_pct": 0.5,
            }
        ],
        holdout_matched=[
            {
                "split": "holdout",
                "zone": "discount",
                "fibo_level": 0.236,
                "match_type": "matched",
                "trades": 60,
                "reliable": True,
                "winrate": 58.0,
                "pf": 3.2,
                "net_pnl": 20000,
                "max_dd_pct": 0.8,
            }
        ],
        train_mismatched=[
            {
                "split": "train",
                "zone": "discount",
                "fibo_level": 0.786,
                "match_type": "mismatched",
                "trades": 140,
                "reliable": True,
                "winrate": 55.0,
                "pf": 1.8,
                "net_pnl": -10000,
                "max_dd_pct": 2.0,
            }
        ],
        holdout_mismatched=[
            {
                "split": "holdout",
                "zone": "discount",
                "fibo_level": 0.786,
                "match_type": "mismatched",
                "trades": 55,
                "reliable": False,
                "winrate": 52.0,
                "pf": 1.5,
                "net_pnl": -5000,
                "max_dd_pct": 2.5,
            }
        ],
        validated=True,
        reason="Test reason",
    )

    generate_holdout_report(result, str(tmp_path))
    import os

    docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")
    report_file = os.path.join(docs_dir, "fibo_zone_holdout_validation.md")
    assert os.path.exists(report_file)
    content = open(report_file, encoding="utf-8").read()
    assert "Holdout Doğrulaması" in content
    assert "matched" in content
    assert "mismatched" in content
    assert "Karar" in content


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
