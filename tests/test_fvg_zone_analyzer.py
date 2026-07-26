from fvg_zone_analyzer import (
    Trade,
    classify_zone,
    find_nearest_fib_level,
    classify_trades,
    compute_max_dd,
    compute_zone_fibo_stats,
    run_holdout_validation,
)


def test_classify_zone():
    assert classify_zone("bullish") == "discount"
    assert classify_zone("bearish") == "premium"


def test_fib_uses_swing_range_not_current_price():
    # swing 100 -> 200, level 0.618 -> fib price = 100 + 100*0.618 = 161.8
    swing_low, swing_high = 100.0, 200.0
    fvg_top, fvg_bottom = 162.0, 161.6  # midpoint 161.8, exact hit
    level, confirmed = find_nearest_fib_level(
        fvg_top, fvg_bottom, swing_high, swing_low
    )
    assert level == 0.618
    assert confirmed is True


def test_fib_not_confirmed_when_far_from_any_level():
    swing_low, swing_high = 100.0, 200.0
    fvg_top, fvg_bottom = (
        150.5,
        150.3,
    )  # midpoint 150.4, far from 0.5 (150) -> within 0.5%? check
    level, confirmed = find_nearest_fib_level(
        fvg_top, fvg_bottom, swing_high, swing_low
    )
    # midpoint 150.4 vs fib(0.5)=150 -> dist = 0.4/150.4 = 0.0027 < 0.005 -> confirmed True actually
    assert level == 0.5


def test_fib_returns_none_for_degenerate_swing():
    level, confirmed = find_nearest_fib_level(100, 100, 100, 100)
    assert level is None
    assert confirmed is False


def test_max_dd_simple():
    # equity: 20, 30, 40, 30, 45 -> peak 40 dip to 30 = 25% dd
    dd = compute_max_dd([10, 10, -10, 15], starting_balance=20)
    assert round(dd, 1) == 25.0


def test_max_dd_large_balance_small_pnl():
    # With large initial balance, small PnL swings produce negligible DD
    dd = compute_max_dd([10, 10, -10, 15])
    assert dd < 0.1


def _make_trade(ts, direction, fib_level, confirmed, result, r, pnl):
    # construct swing/fvg such that find_nearest_fib_level reproduces fib_level/confirmed
    swing_low, swing_high = 0.0, 100.0
    fibo_price = swing_low + (swing_high - swing_low) * fib_level
    offset = 0.001 if confirmed else 0.05  # within/outside 0.5% tolerance
    mid = fibo_price * (1 + offset) if confirmed else fibo_price * (1 + offset)
    return Trade(
        timestamp=ts,
        fvg_direction=direction,
        fvg_top=mid + 0.01,
        fvg_bottom=mid - 0.01,
        swing_high=swing_high,
        swing_low=swing_low,
        result=result,
        r_multiple=r,
        pnl=pnl,
    )


def test_different_fib_levels_never_collapse_to_identical_stats():
    """Regression test for the bug where 0.236 and 0.786 rows were
    byte-identical because fib_level wasn't actually filtering."""
    trades = []
    ts = 0
    for _ in range(150):
        ts += 1
        trades.append(_make_trade(ts, "bullish", 0.236, True, "TP", 2.0, 100))
    for _ in range(150):
        ts += 1
        trades.append(_make_trade(ts, "bearish", 0.786, True, "TP", 2.0, 50))

    classify_trades(trades)
    stats = compute_zone_fibo_stats(trades)
    by_level = {(s.zone, s.fib_level): s for s in stats}

    discount_236 = by_level[("discount", 0.236)]
    premium_786 = by_level[("premium", 0.786)]

    # Different net pnl (100/trade vs 50/trade) proves these are NOT
    # the same underlying group being duplicated.
    assert discount_236.net_pnl != premium_786.net_pnl
    assert discount_236.trades == 150
    assert premium_786.trades == 150


def test_low_n_bucket_flagged_unreliable():
    trades = [_make_trade(i, "bullish", 0.382, True, "TP", 1.5, 10) for i in range(30)]
    classify_trades(trades)
    stats = compute_zone_fibo_stats(trades)
    assert all(not s.reliable for s in stats if s.trades < 100)


def test_holdout_does_not_average_matched_and_mismatched():
    """The core regression: matched (strong) and mismatched (weak) pairs
    must be reported/evaluated separately, never blended into one PF."""
    trades = []
    # Interleave all four groups chronologically so both train and
    # holdout slices contain a mix of matched/mismatched trades.
    for i in range(300):
        ts = i * 4
        trades.append(_make_trade(ts + 0, "bullish", 0.236, True, "TP", 2.5, 100))
        trades.append(_make_trade(ts + 1, "bearish", 0.786, True, "TP", 2.5, 100))
        trades.append(_make_trade(ts + 2, "bullish", 0.786, True, "Loss", -1.0, -80))
        trades.append(_make_trade(ts + 3, "bearish", 0.236, True, "Loss", -1.0, -80))

    result = run_holdout_validation(trades, train_frac=0.7)

    # Matched should be strongly profitable, mismatched should not.
    assert result.train_matched.pf > result.train_mismatched.pf
    assert result.holdout_matched.pf > result.holdout_mismatched.pf
    assert result.train_matched.net_pnl > 0
    assert result.train_mismatched.net_pnl < 0


def test_holdout_validated_when_holdout_pf_close_to_train():
    trades = []
    for i in range(400):
        ts = i * 2
        trades.append(_make_trade(ts + 0, "bullish", 0.236, True, "TP", 2.0, 100))
        trades.append(_make_trade(ts + 1, "bearish", 0.786, True, "TP", 2.0, 100))
    result = run_holdout_validation(trades, train_frac=0.7)
    assert result.validated is True


def test_holdout_not_validated_when_insufficient_n():
    trades = [_make_trade(i, "bullish", 0.236, True, "TP", 2.0, 100) for i in range(20)]
    result = run_holdout_validation(trades, train_frac=0.7)
    assert result.validated is False
    assert "n<100" in result.reason
