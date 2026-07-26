"""fvg_zone_analyzer.py — FVG zone + Fibonacci analiz raporu.

backtest-sniper/src/analyzer_v5.py tarafindan cagirilir.
trade_records uzerinden discount/premium bolge ve Fibonacci
istatistiklerini hesaplar. Holdout dogrulama sonucu HoldoutResult
doner.
"""

from __future__ import annotations

import os
import sys
from collections import defaultdict
from dataclasses import dataclass, field

_SNIPER_SRC = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "sniper", "src"
)
if _SNIPER_SRC not in sys.path:
    sys.path.insert(0, _SNIPER_SRC)

FIBO_LEVELS = [0.236, 0.382, 0.5, 0.618, 0.786]
FIBO_TOLERANCE = 0.005
MIN_BUCKET_SIZE = 100


@dataclass
class HoldoutResult:
    train_matched: list[dict] = field(default_factory=list)
    holdout_matched: list[dict] = field(default_factory=list)
    train_mismatched: list[dict] = field(default_factory=list)
    holdout_mismatched: list[dict] = field(default_factory=list)
    validated: bool = False
    reason: str = ""


def classify_zone(fvg_direction: str) -> str:
    return "discount" if fvg_direction == "bullish" else "premium"


def find_nearest_fib_level(
    fvg_midpoint: float, swing_high: float, swing_low: float
) -> tuple[float | None, bool]:
    if swing_high <= swing_low or fvg_midpoint <= 0:
        return None, False
    rng = swing_high - swing_low
    best_level = None
    best_diff = float("inf")
    for level in FIBO_LEVELS:
        fibo_price = swing_low + rng * level
        diff = abs(fvg_midpoint - fibo_price) / fvg_midpoint
        if diff < best_diff:
            best_diff = diff
            best_level = level
    confirmed = best_diff < FIBO_TOLERANCE
    return best_level, confirmed


def compute_zone_fibo_stats(trade_records: list[dict]) -> list[dict]:
    groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)

    for trade in trade_records:
        zone = classify_zone(trade.get("fvg_direction", ""))
        fvg_top = trade.get("fvg_top", 0)
        fvg_bottom = trade.get("fvg_bottom", 0)
        midpoint = (fvg_top + fvg_bottom) / 2
        swing_high = trade.get("cbdr_body_high", 0)
        swing_low = trade.get("cbdr_body_low", 0)

        fibo_level, confirmed = find_nearest_fib_level(midpoint, swing_high, swing_low)
        fibo_key = f"{fibo_level:.3f}" if fibo_level is not None else "none"
        confirmed_key = "confirmed" if confirmed else "unconfirmed"

        key = (zone, fibo_key, confirmed_key)
        groups[key].append(trade)

    rows = []
    for (zone, fibo_key, confirmed_key), trades in sorted(groups.items()):
        n = len(trades)
        wins = sum(1 for t in trades if t.get("result") == "TP")
        profit_trail = sum(1 for t in trades if t.get("result") == "PROFIT_TRAIL")
        losses = sum(1 for t in trades if t.get("result") in ("LOSS", "OPEN"))
        tp_pct = wins / n * 100 if n > 0 else 0
        pt_pct = profit_trail / n * 100 if n > 0 else 0
        loss_pct = losses / n * 100 if n > 0 else 0
        positive_exit_pct = tp_pct + pt_pct

        gross_profit = sum(t["pnl"] for t in trades if t.get("pnl", 0) > 0) or 0
        gross_loss = abs(sum(t["pnl"] for t in trades if t.get("pnl", 0) < 0))
        pf = gross_profit / gross_loss if gross_loss > 0 else 999.0

        win_trades = [
            t for t in trades if t.get("pnl", 0) > 0 and t.get("risk_usd", 0) > 0
        ]
        loss_trades = [
            t for t in trades if t.get("pnl", 0) < 0 and t.get("risk_usd", 0) > 0
        ]

        avg_r_win = (
            sum(t["pnl"] / t["risk_usd"] for t in win_trades) / len(win_trades)
            if win_trades
            else 0.0
        )
        avg_r_loss = (
            sum(t["pnl"] / t["risk_usd"] for t in loss_trades) / len(loss_trades)
            if loss_trades
            else 0.0
        )

        net_pnl = sum(t.get("pnl", 0) for t in trades)

        rows.append(
            {
                "zone": zone,
                "fibo_level": fibo_key,
                "confirmed": confirmed_key,
                "trades": n,
                "tp_pct": tp_pct,
                "profit_trail_pct": pt_pct,
                "loss_pct": loss_pct,
                "positive_exit_pct": positive_exit_pct,
                "pf": pf,
                "avg_r_win": avg_r_win,
                "avg_r_loss": avg_r_loss,
                "net_pnl": net_pnl,
            }
        )

    return rows


def compute_max_dd(trade_records: list[dict]) -> float:
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    for t in trade_records:
        cumulative += t.get("pnl", 0)
        if cumulative > peak:
            peak = cumulative
        dd = peak - cumulative
        if dd > max_dd:
            max_dd = dd
    if peak <= 0:
        return 0.0
    return (max_dd / peak) * 100


def _filter_fib_level(
    trade_records: list[dict],
    target_level: float,
) -> list[dict]:
    filtered = []
    for t in trade_records:
        fvg_top = t.get("fvg_top", 0)
        fvg_bottom = t.get("fvg_bottom", 0)
        midpoint = (fvg_top + fvg_bottom) / 2
        swing_high = t.get("cbdr_body_high", 0)
        swing_low = t.get("cbdr_body_low", 0)
        if swing_high <= swing_low or midpoint <= 0:
            continue
        rng = swing_high - swing_low
        best_level = None
        best_diff = float("inf")
        for level in FIBO_LEVELS:
            fibo_price = swing_low + rng * level
            diff = abs(midpoint - fibo_price) / midpoint
            if diff < best_diff:
                best_diff = diff
                best_level = level
        if best_level == target_level:
            filtered.append(t)
    return filtered


def _bucket_stats(group: list[dict]) -> dict:
    n = len(group)
    reliable = n >= MIN_BUCKET_SIZE
    wins = sum(1 for t in group if t.get("result") in ("TP", "PROFIT_TRAIL"))
    winrate = (wins / n) * 100 if n > 0 else 0
    gross_profit = sum(t["pnl"] for t in group if t.get("pnl", 0) > 0) or 0
    gross_loss = abs(sum(t["pnl"] for t in group if t.get("pnl", 0) < 0))
    pf = gross_profit / gross_loss if gross_loss > 0 else 999.0
    net_pnl = sum(t.get("pnl", 0) for t in group)
    max_dd = compute_max_dd(group)
    return {
        "trades": n,
        "reliable": reliable,
        "winrate": winrate,
        "pf": pf,
        "net_pnl": net_pnl,
        "max_dd_pct": max_dd,
    }


def run_holdout_validation(trade_records: list[dict], output_dir: str) -> HoldoutResult:
    if not trade_records:
        return HoldoutResult(reason="Bos trade_records")

    n = len(trade_records)
    split_idx = int(n * 0.70)
    train = trade_records[:split_idx]
    holdout = trade_records[split_idx:]

    matched_keys = [("discount", 0.236), ("premium", 0.786)]
    mismatched_keys = [("discount", 0.786), ("premium", 0.236)]

    train_matched = []
    holdout_matched = []
    train_mismatched = []
    holdout_mismatched = []

    for label, records in [("train", train), ("holdout", holdout)]:
        for zone, fibo_level in matched_keys:
            group = [
                t for t in records if classify_zone(t.get("fvg_direction", "")) == zone
            ]
            group = _filter_fib_level(group, fibo_level)
            stats = _bucket_stats(group)
            stats["split"] = label
            stats["zone"] = zone
            stats["fibo_level"] = fibo_level
            stats["match_type"] = "matched"
            if label == "train":
                train_matched.append(stats)
            else:
                holdout_matched.append(stats)

        for zone, fibo_level in mismatched_keys:
            group = [
                t for t in records if classify_zone(t.get("fvg_direction", "")) == zone
            ]
            group = _filter_fib_level(group, fibo_level)
            stats = _bucket_stats(group)
            stats["split"] = label
            stats["zone"] = zone
            stats["fibo_level"] = fibo_level
            stats["match_type"] = "mismatched"
            if label == "train":
                train_mismatched.append(stats)
            else:
                holdout_mismatched.append(stats)

    holdout_matched_pf = (
        sum(r["pf"] for r in holdout_matched if r["reliable"] and r["pf"] < 999.0)
        / sum(1 for r in holdout_matched if r["reliable"] and r["pf"] < 999.0)
        if any(r["reliable"] and r["pf"] < 999.0 for r in holdout_matched)
        else 0
    )
    holdout_matched_wr = (
        sum(r["winrate"] for r in holdout_matched if r["reliable"])
        / sum(1 for r in holdout_matched if r["reliable"])
        if any(r["reliable"] for r in holdout_matched)
        else 0
    )

    validated = False
    reason = ""

    reliable_matched = [r for r in holdout_matched if r["reliable"]]

    if not reliable_matched:
        reason = "Holdout matched bucket'lari reliable degil (n<100). Veri yetersiz."
    elif holdout_matched_pf >= 3.0 and holdout_matched_wr >= 55:
        validated = True
        reason = (
            f"Holdout matched PF={holdout_matched_pf:.2f} "
            f"(train matched PF="
            f"{sum(r['pf'] for r in train_matched if r['pf'] < 999) / max(sum(1 for r in train_matched if r['pf'] < 999), 1):.2f}), "
            f"winrate={holdout_matched_wr:.1f}%. Kural dogrulandi."
        )
    elif holdout_matched_pf < 2.5 or holdout_matched_wr < 55:
        reason = (
            f"Holdout matched PF={holdout_matched_pf:.2f}, "
            f"winrate={holdout_matched_wr:.1f}%. In-sample'a ozgu, kural terk ediliyor."
        )
    else:
        reason = (
            f"Belirsiz. Holdout matched PF={holdout_matched_pf:.2f}, "
            f"winrate={holdout_matched_wr:.1f}%. Ek veri ile tekrar degerlendirilmesi oneriliyor."
        )

    result = HoldoutResult(
        train_matched=train_matched,
        holdout_matched=holdout_matched,
        train_mismatched=train_mismatched,
        holdout_mismatched=holdout_mismatched,
        validated=validated,
        reason=reason,
    )

    generate_holdout_report(result, output_dir)
    return result


def generate_holdout_report(result: HoldoutResult, output_dir: str) -> None:
    lines = []
    lines.append("")
    lines.append("## Fibonacci Zone Holdout Doğrulaması (0.236 / 0.786)")
    lines.append("")
    lines.append("*Veri bölme: İlk %70 = Train, Son %30 = Holdout (kronolojik).*")
    lines.append("*Kural: Fibo seviyeleri {0.236, 0.786}, tüm onay durumları dahil.*")
    lines.append(
        "*Matched = discount+0.236 / premium+0.786; Mismatched = discount+0.786 / premium+0.236.*"
    )
    lines.append("")

    for split_label, matched_list, mismatched_list in [
        ("Train", result.train_matched, result.train_mismatched),
        ("Holdout", result.holdout_matched, result.holdout_mismatched),
    ]:
        lines.append(f"### {split_label}")
        lines.append("")

        hdr = "| Zone      | Fibo Level | Match     | Trades | Reliable | Winrate | PF    | Net PnL    | MaxDD%  |"
        sep = "|" + "|".join(["---"] * 9) + "|"
        lines.append(hdr)
        lines.append(sep)

        for r in matched_list + mismatched_list:
            match_label = "matched" if r["match_type"] == "matched" else "mismatched"
            reliable_mark = "✓" if r["reliable"] else "✗"
            lines.append(
                f"| {r['zone']:<10} | {r['fibo_level']:<10.3f} | "
                f"{match_label:<9} | {r['trades']:>6} | {reliable_mark:>8} | "
                f"{r['winrate']:>7.1f}% | {r['pf']:>5.2f} | "
                f"{r['net_pnl']:>+10.0f} | {r['max_dd_pct']:>7.1f}% |"
            )

        lines.append("")

    lines.append("### Karar")
    lines.append("")
    lines.append(
        f"**{'Doğrulandı' if result.validated else 'Doğrulanmadı'}.** {result.reason}"
    )
    lines.append("")

    docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")
    os.makedirs(docs_dir, exist_ok=True)
    report_path = os.path.join(docs_dir, "fibo_zone_holdout_validation.md")
    with open(report_path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"  [Holdout] Rapor: {report_path}")
    for line in lines:
        print(line)


def generate_zone_fibo_report(trade_records: list[dict], output_dir: str) -> None:
    rows = compute_zone_fibo_stats(trade_records)

    hdr = (
        "| Zone      | Fibo Level | Confirmed   | Trades | TP%   | PTrail% | Loss%  | "
        "PF    | Avg R(win) | Avg R(loss) | Net PnL    |"
    )
    sep = "|" + "|".join(["---"] * 11) + "|"

    lines = []
    lines.append("")
    lines.append("## FVG Zone + Fibonacci Analizi")
    lines.append("")
    lines.append(hdr)
    lines.append(sep)

    for r in rows:
        line = (
            f"| {r['zone']:<10} | {r['fibo_level']:<10} | "
            f"{r['confirmed']:<11} | {r['trades']:>6} | "
            f"{r['tp_pct']:>5.1f}% | {r['profit_trail_pct']:>7.1f}% | "
            f"{r['loss_pct']:>6.1f}% | {r['pf']:>5.2f} | "
            f"{r['avg_r_win']:>10.4f} | {r['avg_r_loss']:>11.4f} | "
            f"{r['net_pnl']:>+10.0f} |"
        )
        lines.append(line)

    lines.append("")
    lines.append("*Fibo seviyeleri: swing_low + (swing_high - swing_low) * level.*")
    lines.append(
        "*Onay eşiği: FVG midpoint ile Fibonacci seviyesi arasındaki fark "
        f"{FIBO_TOLERANCE * 100:.1f}% altı.*"
    )

    report_path = os.path.join(output_dir, "fvg_zone_fibo_analysis.md")
    os.makedirs(output_dir, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"  [FVG Zone] Rapor: {report_path}")
    for line in lines:
        print(line)
