"""
fvg_zone_analyzer.py

FVG Discount/Premium + Fibonacci zone analysis.

Fixes applied vs. the earlier ad-hoc analysis:
  1. Fibonacci price is computed from an actual swing range
     (swing_low + (swing_high - swing_low) * level), NOT from
     current_price * level (which was mathematically meaningless).
  2. fib_level filtering is done per-trade (each trade gets its own
     nearest fib level from its own FVG midpoint / swing), so two
     different fib levels can never silently collapse into identical
     stats — that was the bug that produced identical rows for
     0.236 and 0.786 in the first holdout attempt.
  3. Any (zone, fib_level, confirmed) bucket with n < MIN_RELIABLE_N
     is flagged unreliable and excluded from decision-making (mirrors
     the CBDR bucket engine's n<100 safety lock).
  4. Holdout validation evaluates MATCHED zone-fib pairs
     (discount+0.236, premium+0.786) as one combined strategy and
     MISMATCHED pairs (discount+0.786, premium+0.236) as a separate
     excluded group — it does NOT average all four into one PF, which
     was the error that produced a falsely "validated" result before.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Iterable, Literal

FIB_LEVELS = (0.236, 0.382, 0.5, 0.618, 0.786)
DEFAULT_FIB_TOLERANCE = 0.005  # ±0.5%
MIN_RELIABLE_N = 100

Zone = Literal["discount", "premium"]

# Matched pairs = FVG direction and fib retracement depth agree
# (bullish/discount FVG near a shallow retrace, bearish/premium FVG
# near a deep retrace). Mismatched pairs = the opposite combination.
MATCHED_PAIRS = frozenset({("discount", 0.236), ("premium", 0.786)})
MISMATCHED_PAIRS = frozenset({("discount", 0.786), ("premium", 0.236)})


@dataclass
class Trade:
    """Minimal fields this module needs from a trade record."""

    timestamp: float  # unix ts or monotonically increasing sort key
    fvg_direction: Literal["bullish", "bearish"]
    fvg_top: float
    fvg_bottom: float
    swing_high: float
    swing_low: float
    result: Literal["TP", "PTrail", "Loss"]
    r_multiple: float  # realized R for this trade (win: >0, loss: <0)
    pnl: float
    # Fields populated after classification (not required as input):
    zone: Zone | None = None
    fib_level: float | None = None
    fib_confirmed: bool | None = None


def classify_zone(fvg_direction: str) -> Zone:
    """Bullish FVG -> discount (buy-side imbalance), bearish -> premium."""
    return "discount" if fvg_direction == "bullish" else "premium"


def find_nearest_fib_level(
    fvg_top: float,
    fvg_bottom: float,
    swing_high: float,
    swing_low: float,
    tolerance: float = DEFAULT_FIB_TOLERANCE,
    levels: Iterable[float] = FIB_LEVELS,
) -> tuple[float | None, bool]:
    """
    Return (nearest_fib_level, confirmed) for a single FVG.

    Fibonacci price for `level` is swing_low + (swing_high - swing_low) * level
    -- NOT current_price * level. Confirmed means the FVG midpoint sits
    within `tolerance` (relative) of that fib price.
    """
    midpoint = (fvg_top + fvg_bottom) / 2
    rng = swing_high - swing_low
    if rng <= 0 or midpoint == 0:
        return None, False

    best_level = None
    best_dist = None
    for level in levels:
        fibo_price = swing_low + rng * level
        dist = abs(midpoint - fibo_price) / midpoint
        if best_dist is None or dist < best_dist:
            best_dist = dist
            best_level = level

    confirmed = best_dist is not None and best_dist < tolerance
    return best_level, confirmed


def classify_trades(trades: list[Trade]) -> list[Trade]:
    """In-place classification of zone / fib_level / fib_confirmed per trade."""
    for t in trades:
        t.zone = classify_zone(t.fvg_direction)
        t.fib_level, t.fib_confirmed = find_nearest_fib_level(
            t.fvg_top, t.fvg_bottom, t.swing_high, t.swing_low
        )
    return trades


def compute_max_dd(pnl_series: list[float]) -> float:
    """Max drawdown (%) on a cumulative-PnL equity curve built from a list
    of per-trade PnL values, in chronological order."""
    if not pnl_series:
        return 0.0
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for pnl in pnl_series:
        equity += pnl
        peak = max(peak, equity)
        if peak > 0:
            dd = (peak - equity) / peak
            max_dd = max(max_dd, dd)
    return max_dd * 100


@dataclass
class BucketStats:
    zone: Zone
    fib_level: float | None
    confirmed: bool | None
    trades: int
    winrate: float  # (TP + PTrail) / trades, in %
    pf: float
    net_pnl: float
    avg_r_win: float
    avg_r_loss: float
    max_dd_pct: float
    reliable: bool  # False if trades < MIN_RELIABLE_N


def _pf(wins: list[float], losses: list[float]) -> float:
    gross_win = sum(w for w in wins if w > 0)
    gross_loss = abs(sum(l for l in losses if l < 0))
    if gross_loss == 0:
        return float("inf") if gross_win > 0 else 0.0
    return gross_win / gross_loss


def _bucket_stats(
    zone, fib_level, confirmed, bucket_trades: list[Trade]
) -> BucketStats:
    n = len(bucket_trades)
    wins = [t.pnl for t in bucket_trades if t.result in ("TP", "PTrail")]
    losses = [t.pnl for t in bucket_trades if t.result == "Loss"]
    win_count = len(wins)
    winrate = (win_count / n * 100) if n else 0.0
    pf = _pf(wins, losses)
    net_pnl = sum(t.pnl for t in bucket_trades)
    r_wins = [t.r_multiple for t in bucket_trades if t.result in ("TP", "PTrail")]
    r_losses = [t.r_multiple for t in bucket_trades if t.result == "Loss"]
    avg_r_win = statistics.mean(r_wins) if r_wins else 0.0
    avg_r_loss = statistics.mean(r_losses) if r_losses else 0.0
    pnl_series = [t.pnl for t in sorted(bucket_trades, key=lambda t: t.timestamp)]
    max_dd = compute_max_dd(pnl_series)
    return BucketStats(
        zone=zone,
        fib_level=fib_level,
        confirmed=confirmed,
        trades=n,
        winrate=round(winrate, 2),
        pf=round(pf, 2) if pf != float("inf") else pf,
        net_pnl=round(net_pnl, 2),
        avg_r_win=round(avg_r_win, 4),
        avg_r_loss=round(avg_r_loss, 4),
        max_dd_pct=round(max_dd, 2),
        reliable=n >= MIN_RELIABLE_N,
    )


def compute_zone_fibo_stats(trades: list[Trade]) -> list[BucketStats]:
    """
    Group already-classified trades by (zone, fib_level, confirmed) and
    compute stats per bucket. Buckets with n < MIN_RELIABLE_N are flagged
    reliable=False but still returned (caller decides whether to display
    or exclude them from decisions).
    """
    buckets: dict[tuple, list[Trade]] = {}
    for t in trades:
        if t.zone is None or t.fib_level is None:
            continue
        key = (t.zone, t.fib_level, t.fib_confirmed)
        buckets.setdefault(key, []).append(t)

    return [
        _bucket_stats(zone, fib_level, confirmed, bucket_trades)
        for (zone, fib_level, confirmed), bucket_trades in sorted(buckets.items())
    ]


def generate_zone_fibo_report(stats: list[BucketStats]) -> str:
    lines = [
        "| Zone | Fibo Level | Confirmed | Trades | Winrate | PF | Net PnL | MaxDD% | Reliable |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for s in stats:
        conf = "confirmed" if s.confirmed else "unconfirmed"
        reliable = "yes" if s.reliable else "NO (n<100)"
        lines.append(
            f"| {s.zone} | {s.fib_level} | {conf} | {s.trades} | {s.winrate}% | "
            f"{s.pf} | {s.net_pnl:+.0f} | {s.max_dd_pct}% | {reliable} |"
        )
    return "\n".join(lines)


@dataclass
class HoldoutResult:
    train_matched: BucketStats
    holdout_matched: BucketStats
    train_mismatched: BucketStats
    holdout_mismatched: BucketStats
    validated: bool
    reason: str


def _filter_pairs(
    trades: list[Trade], pairs: frozenset[tuple[Zone, float]]
) -> list[Trade]:
    return [t for t in trades if t.zone is not None and (t.zone, t.fib_level) in pairs]


def run_holdout_validation(
    trades: list[Trade],
    train_frac: float = 0.7,
    matched_pairs: frozenset = MATCHED_PAIRS,
    mismatched_pairs: frozenset = MISMATCHED_PAIRS,
    pf_ratio_threshold: float = 0.8,
    winrate_drop_threshold: float = 5.0,
) -> HoldoutResult:
    """
    Chronological train/holdout split. Evaluates the MATCHED zone-fib
    pair set (discount+0.236, premium+0.786) as one combined strategy,
    and the MISMATCHED pair set separately, for context — it does not
    average all four combinations into a single misleading PF.

    Decision: validated if holdout PF >= pf_ratio_threshold * train PF
    AND holdout winrate is within winrate_drop_threshold points of train.
    """
    classify_trades(trades)  # idempotent, safe to call again
    ordered = sorted(trades, key=lambda t: t.timestamp)
    split_idx = int(len(ordered) * train_frac)
    train, holdout = ordered[:split_idx], ordered[split_idx:]

    train_matched_trades = _filter_pairs(train, matched_pairs)
    holdout_matched_trades = _filter_pairs(holdout, matched_pairs)
    train_mismatched_trades = _filter_pairs(train, mismatched_pairs)
    holdout_mismatched_trades = _filter_pairs(holdout, mismatched_pairs)

    train_matched = _bucket_stats("matched", None, None, train_matched_trades)
    holdout_matched = _bucket_stats("matched", None, None, holdout_matched_trades)
    train_mismatched = _bucket_stats("mismatched", None, None, train_mismatched_trades)
    holdout_mismatched = _bucket_stats(
        "mismatched", None, None, holdout_mismatched_trades
    )

    if not train_matched.reliable or not holdout_matched.reliable:
        return HoldoutResult(
            train_matched,
            holdout_matched,
            train_mismatched,
            holdout_mismatched,
            validated=False,
            reason="Matched-pair bucket has n<100 in train or holdout — insufficient data.",
        )

    pf_ok = (
        train_matched.pf != 0
        and holdout_matched.pf >= pf_ratio_threshold * train_matched.pf
    )
    winrate_ok = holdout_matched.winrate >= (
        train_matched.winrate - winrate_drop_threshold
    )

    validated = pf_ok and winrate_ok
    reason = (
        f"Holdout PF {holdout_matched.pf} vs train PF {train_matched.pf} "
        f"(ratio={holdout_matched.pf / train_matched.pf:.2f} if train nonzero); "
        f"holdout winrate {holdout_matched.winrate}% vs train {train_matched.winrate}%. "
        f"{'PASSED' if validated else 'FAILED'} thresholds "
        f"(pf_ratio>={pf_ratio_threshold}, winrate_drop<={winrate_drop_threshold}pt)."
    )
    return HoldoutResult(
        train_matched,
        holdout_matched,
        train_mismatched,
        holdout_mismatched,
        validated=validated,
        reason=reason,
    )


def generate_holdout_report(result: HoldoutResult) -> str:
    lines = [
        "## Fibonacci Zone Holdout Validation — Matched vs Mismatched Pairs",
        "",
        "Matched pairs = discount+0.236, premium+0.786 (combined as ONE strategy).",
        "Mismatched pairs = discount+0.786, premium+0.236 (shown for contrast, excluded from strategy).",
        "",
        "| Group | Split | Trades | Winrate | PF | Net PnL | MaxDD% | Reliable |",
        "|---|---|---|---|---|---|---|---|",
    ]

    def row(label, split, s: BucketStats):
        reliable = "yes" if s.reliable else "NO (n<100)"
        return (
            f"| {label} | {split} | {s.trades} | {s.winrate}% | {s.pf} | "
            f"{s.net_pnl:+.0f} | {s.max_dd_pct}% | {reliable} |"
        )

    lines.append(row("Matched", "Train", result.train_matched))
    lines.append(row("Matched", "Holdout", result.holdout_matched))
    lines.append(row("Mismatched", "Train", result.train_mismatched))
    lines.append(row("Mismatched", "Holdout", result.holdout_mismatched))
    lines += [
        "",
        f"**Decision: {'VALIDATED' if result.validated else 'NOT VALIDATED'}**",
        "",
        result.reason,
    ]
    return "\n".join(lines)
