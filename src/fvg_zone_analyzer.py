"""fvg_zone_analyzer.py — FVG zone + Fibonacci analiz raporu.

backtest-sniper/src/analyzer_v5.py tarafindan cagirilir.
trade_records uzerinden discount/premium bolge ve Fibonacci onay
istatistiklerini hesaplar.
"""

from __future__ import annotations

import os
import sys
from collections import defaultdict

_SNIPER_SRC = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "sniper", "src"
)
if _SNIPER_SRC not in sys.path:
    sys.path.insert(0, _SNIPER_SRC)

FIBO_LEVELS = [0.236, 0.382, 0.5, 0.618, 0.786]
FIBO_TOLERANCE = 0.005


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


def _filter_fib_levels(
    trade_records: list[dict],
    allowed_levels: set[float],
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
        if best_level in allowed_levels:
            filtered.append(t)
    return filtered


def run_holdout_validation(trade_records: list[dict], output_dir: str) -> None:
    if not trade_records:
        return

    n = len(trade_records)
    split_idx = int(n * 0.70)
    train = trade_records[:split_idx]
    holdout = trade_records[split_idx:]

    allowed = {0.236, 0.786}

    rows = []
    for label, records in [("Train", train), ("Holdout", holdout)]:
        for fibo_level in [0.236, 0.786]:
            for zone in ("discount", "premium"):
                group = [
                    t
                    for t in records
                    if classify_zone(t.get("fvg_direction", "")) == zone
                ]
                group = _filter_fib_levels(group, allowed)
                n_t = len(group)
                if n_t == 0:
                    continue
                wins = sum(
                    1 for t in group if t.get("result") in ("TP", "PROFIT_TRAIL")
                )
                winrate = (wins / n_t) * 100
                gross_profit = sum(t["pnl"] for t in group if t.get("pnl", 0) > 0) or 0
                gross_loss = abs(sum(t["pnl"] for t in group if t.get("pnl", 0) < 0))
                pf = gross_profit / gross_loss if gross_loss > 0 else 999.0
                net_pnl = sum(t.get("pnl", 0) for t in group)
                max_dd = compute_max_dd(group)
                rows.append(
                    {
                        "split": label,
                        "fibo_level": fibo_level,
                        "zone": zone,
                        "trades": n_t,
                        "winrate": winrate,
                        "pf": pf,
                        "net_pnl": net_pnl,
                        "max_dd_pct": max_dd,
                    }
                )

    lines = []
    lines.append("")
    lines.append("## Fibonacci Zone Holdout Doğrulaması (0.236 / 0.786)")
    lines.append("")
    lines.append("*Veri bölme: İlk %70 = Train, Son %30 = Holdout (kronolojik).*")
    lines.append("*Kural: Fibo seviyeleri {0.236, 0.786}, tüm onay durumları dahil.*")
    lines.append("")

    hdr = "| Split    | Fibo Level | Zone      | Trades | Winrate | PF    | Net PnL    | MaxDD%  |"
    sep = "|" + "|".join(["---"] * 8) + "|"
    lines.append(hdr)
    lines.append(sep)

    for r in rows:
        lines.append(
            f"| {r['split']:<9} | {r['fibo_level']:<10.3f} | "
            f"{r['zone']:<10} | {r['trades']:>6} | "
            f"{r['winrate']:>7.1f}% | {r['pf']:>5.2f} | "
            f"{r['net_pnl']:>+10.0f} | {r['max_dd_pct']:>7.1f}% |"
        )

    lines.append("")

    holdout_rows = [r for r in rows if r["split"] == "Holdout"]
    train_rows = [r for r in rows if r["split"] == "Train"]

    holdout_pf_vals = [r["pf"] for r in holdout_rows if r["pf"] < 999.0]
    holdout_wr_vals = [r["winrate"] for r in holdout_rows]
    avg_holdout_pf = (
        sum(holdout_pf_vals) / len(holdout_pf_vals) if holdout_pf_vals else 0
    )
    avg_holdout_wr = (
        sum(holdout_wr_vals) / len(holdout_wr_vals) if holdout_wr_vals else 0
    )

    train_pf_vals = [r["pf"] for r in train_rows if r["pf"] < 999.0]
    avg_train_pf = sum(train_pf_vals) / len(train_pf_vals) if train_pf_vals else 0

    lines.append("### Karar")
    lines.append("")
    if avg_holdout_pf >= 3.0 and avg_holdout_wr >= 55:
        lines.append(
            "**Doğrulandı.** Holdout ortalama PF = {:.2f} "
            "(train: {:.2f}), winrate = {:.1f}%. "
            "Kural kontrollü sermaye ile canlıya alınabilir.".format(
                avg_holdout_pf, avg_train_pf, avg_holdout_wr
            )
        )
    elif avg_holdout_pf < 2.5 or avg_holdout_wr < 55:
        lines.append(
            "**Doğrulanmadı — in-sample'a özgü.** Holdout ortalama PF = "
            "{:.2f} (train: {:.2f}), "
            "winrate = {:.1f}%. "
            "Kural terk edilir, mevcut (tüm seviyeler dahil) sistemle devam edilir.".format(
                avg_holdout_pf, avg_train_pf, avg_holdout_wr
            )
        )
    else:
        lines.append(
            "**Belirsiz.** Holdout PF = {:.2f}, "
            "winrate = {:.1f}%. "
            "Daha fazla veri ve/veya farklı parametrelerle tekrar değerlendirilmesi önerilir.".format(
                avg_holdout_pf, avg_holdout_wr
            )
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
        f"*Onay eşiği: FVG midpoint ile Fibonacci seviyesi arasındaki fark "
        f"{FIBO_TOLERANCE * 100:.1f}% altı.*"
    )

    report_path = os.path.join(output_dir, "fvg_zone_fibo_analysis.md")
    os.makedirs(output_dir, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"  [FVG Zone] Rapor: {report_path}")
    for line in lines:
        print(line)
