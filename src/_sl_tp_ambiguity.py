#!/usr/bin/env python3
"""_sl_tp_ambiguity.py — SL/TP Ambiguity Analyzer

Motoru degistirmeden, 1m veri ile SL/TP gercek sirasini belirler.

Backtest motoru (analyzer_v5 / analyze_cbdr_thresholds) 15m bar'larda
SL'yi once kontrol eder. Ayni bar'da her iki seviye de erisildiginde
SL her zaman kazanir. Bu script 1m veri ile gercek siralamayi tespit eder.

Kullanim: python _sl_tp_ambiguity.py
"""

# ruff: noqa: E402 — path manipulation requires late imports
import os
import sys
import time
from datetime import datetime, timezone

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)
_SNIPER_SRC = os.path.join(_THIS_DIR, "..", "..", "sniper", "src")
if _SNIPER_SRC not in sys.path:
    sys.path.insert(0, _SNIPER_SRC)

from analyze_cbdr_thresholds import (
    load_data,
    resample_15m,
    collect_daily_data,
    SESSION_CONFIGS,
)

SYMBOLS = [
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

COMMISSION_RATE = 0.0005
_15M_MS = 15 * 60 * 1000


# ─── Core analysis functions ───────────────────────────────────────


def find_ambiguous(trades, b15):
    """Check if both SL and TP could have been hit in the exit 15m bar.

    For LOSS / PROFIT_TRAIL trades only (result != 'TP').
    LONG:  bar.low <= sl  AND  bar.high >= tp
    SHORT: bar.high >= sl AND  bar.low  <= tp
    """
    out = []
    for t in trades:
        if t.get("result") == "TP":
            continue
        idx = t.get("exit_bar")
        if idx is None or idx < 0 or idx >= len(b15):
            continue
        bar = b15[idx]
        sl, tp = t["sl"], t["tp"]
        if t["side"] == "long":
            if bar.low <= sl and bar.high >= tp:
                out.append(t)
        else:
            if bar.high >= sl and bar.low <= tp:
                out.append(t)
    return out


def true_order_1m(t, b1, b15):
    """Walk 1m bars inside the exit 15m window chronologically.

    Returns one of:
        TP_FIRST      — TP was hit before SL  → engine misclassified
        SL_FIRST      — SL was hit before TP  → engine correct
        SAME_1M_BAR   — both levels hit in the same 1m bar → inconclusive
        NEITHER       — neither level hit in any 1m bar (data anomaly)
        NO_DATA       — no 1m bars found for the window
    """
    idx = t["exit_bar"]
    bar = b15[idx]
    ts_lo = bar.timestamp
    ts_hi = ts_lo + _15M_MS
    side, sl, tp = t["side"], t["sl"], t["tp"]

    m1_window = [b for b in b1 if ts_lo <= b.timestamp < ts_hi]
    if not m1_window:
        return "NO_DATA"

    for b in m1_window:
        if side == "long":
            sl_hit = b.low <= sl
            tp_hit = b.high >= tp
        else:
            sl_hit = b.high >= sl
            tp_hit = b.low <= tp

        if sl_hit and tp_hit:
            return "SAME_1M_BAR"
        if sl_hit:
            return "SL_FIRST"
        if tp_hit:
            return "TP_FIRST"

    return "NEITHER"


def alt_pnl(t):
    """Compute PnL if TP was hit instead of the recorded SL exit."""
    entry = t["entry_price"]
    tp = t["tp"]
    qty = t.get("qty", 0)
    if t["side"] == "long":
        diff = tp - entry
    else:
        diff = entry - tp
    fees = (entry + tp) * qty * COMMISSION_RATE
    return round(diff * qty - fees, 2)


def fmt_ts(ts_ms):
    """Format millisecond timestamp to readable UTC string."""
    try:
        return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M"
        )
    except Exception:
        return "?"


# ─── Main ──────────────────────────────────────────────────────────


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    t0 = time.time()

    print("=" * 105)
    print("  SL/TP AMBIGUITY ANALYZER — 1m True Order Detection")
    print("  Backtest: analyze_cbdr_thresholds.collect_daily_data()")
    print("  Yontem: Ayni 15m barda SL+TP erisimi varsa, 1m veri ile gercek siralama")
    print("=" * 105)

    results = {}
    b15_map = {}
    grand = dict(
        total=0,
        ambiguous=0,
        tp_first=0,
        same_1m=0,
        sl_first=0,
        neither=0,
        no_data=0,
        pnl_impact=0.0,
    )

    for si, sym in enumerate(SYMBOLS):
        print(f"\n  [{si + 1}/{len(SYMBOLS)} {sym}]", flush=True)
        feather = os.path.join(_THIS_DIR, "data", "daily", f"{sym}_1m_raw.feather")
        if not os.path.isfile(feather):
            print(f"    VERI YOK: {feather}", flush=True)
            continue

        b1 = load_data(feather)
        b15 = resample_15m(b1)
        if not b15:
            print("    15m veri yok", flush=True)
            continue
        b15_map[sym] = b15
        print(f"    1m={len(b1)} bar, 15m={len(b15)} bar", flush=True)

        sessions = {}
        all_ambig = []

        for sname, shours in SESSION_CONFIGS.items():
            try:
                ret = collect_daily_data(
                    sym,
                    session_name=sname,
                    session_hours=shours,
                    quiet=True,
                )
                if ret is None:
                    print(f"    [{sname}] Veri dosyasi yok", flush=True)
                    continue
                daily_rows, wins, losses, trade_records, rejection_counts = ret
            except Exception as e:
                print(f"    [{sname}] HATA: {e}", flush=True)
                continue

            all_trades = wins + losses
            sl_trades = [t for t in all_trades if t.get("result") != "TP"]
            ambig = find_ambiguous(sl_trades, b15)

            print(
                f"    [{sname}] {len(all_trades)} trade, "
                f"{len(sl_trades)} SL-type, {len(ambig)} ambiguous",
                flush=True,
            )

            for t in ambig:
                t["_session"] = sname
                t["_sym"] = sym
                t["_order"] = true_order_1m(t, b1, b15)
                all_ambig.append(t)

            sessions[sname] = dict(total=len(all_trades), ambiguous=len(ambig))

        # ── Per-symbol aggregation ──
        tp_first = [t for t in all_ambig if t["_order"] == "TP_FIRST"]
        same_1m = [t for t in all_ambig if t["_order"] == "SAME_1M_BAR"]
        sl_first = [t for t in all_ambig if t["_order"] == "SL_FIRST"]
        neither_list = [t for t in all_ambig if t["_order"] == "NEITHER"]
        no_data_list = [t for t in all_ambig if t["_order"] == "NO_DATA"]

        # PnL impact: only from trades that were in losses (pnl <= 0)
        # These are the ones that would flip from loss to win
        tp_first_losses = [t for t in tp_first if t["pnl"] <= 0]
        tp_first_wins = [t for t in tp_first if t["pnl"] > 0]
        pnl_delta_loss_flips = sum(alt_pnl(t) - t["pnl"] for t in tp_first_losses)
        pnl_delta_win_boost = sum(alt_pnl(t) - t["pnl"] for t in tp_first_wins)
        pnl_delta = pnl_delta_loss_flips + pnl_delta_win_boost

        sym_total = sum(d["total"] for d in sessions.values())
        grand["total"] += sym_total
        grand["ambiguous"] += len(all_ambig)
        grand["tp_first"] += len(tp_first)
        grand["same_1m"] += len(same_1m)
        grand["sl_first"] += len(sl_first)
        grand["neither"] += len(neither_list)
        grand["no_data"] += len(no_data_list)
        grand["pnl_impact"] += pnl_delta

        results[sym] = dict(
            sessions=sessions,
            total=sym_total,
            ambiguous=len(all_ambig),
            tp_first=len(tp_first),
            same_1m=len(same_1m),
            sl_first=len(sl_first),
            neither=len(neither_list),
            no_data=len(no_data_list),
            pnl_impact=pnl_delta,
            pnl_loss_flips=len(tp_first_losses),
            pnl_win_boost=len(tp_first_wins),
            ambig_trades=all_ambig,
        )

        print(
            f"    => {len(all_ambig)} ambig | "
            f"TP first={len(tp_first)} (loss-flip={len(tp_first_losses)}, "
            f"win-boost={len(tp_first_wins)}) | "
            f"SL first={len(sl_first)} | Same 1m={len(same_1m)} | "
            f"PnL delta={pnl_delta:+.2f}",
            flush=True,
        )

    elapsed = time.time() - t0

    # ────────────────────────────────────────────────────────────────
    # Build Markdown report
    # ────────────────────────────────────────────────────────────────
    lines = []
    lines.append("# SL/TP Ambiguity Report")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("**Engine:** analyze_cbdr_thresholds (SL before TP in 15m bars)")
    lines.append("**Method:** 1m data true order detection within exit bar window")
    lines.append(f"**Sessions:** {', '.join(SESSION_CONFIGS.keys())}")
    lines.append(f"**Symbols:** {', '.join(SYMBOLS)}")
    lines.append(f"**Runtime:** {elapsed:.0f}s")
    lines.append("")

    # ── Global summary ──
    lines.append("## Global Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|------:|")
    lines.append(f"| Total trades analyzed | {grand['total']} |")
    lines.append(f"| Ambiguous (SL+TP in same 15m bar) | {grand['ambiguous']} |")
    lines.append(f"| **TP first (misclassified)** | **{grand['tp_first']}** |")
    lines.append(f"| SL first (engine correct) | {grand['sl_first']} |")
    lines.append(f"| Same 1m bar (inconclusive) | {grand['same_1m']} |")
    lines.append(f"| Neither hit | {grand['neither']} |")
    lines.append(f"| No 1m data | {grand['no_data']} |")
    lines.append(
        f"| **Total PnL impact (correction)** | **{grand['pnl_impact']:+.2f}** |"
    )
    if grand["total"] > 0:
        rate = grand["tp_first"] / grand["total"] * 100
        lines.append(f"| Misclassification rate | {rate:.2f}% of all trades |")
    if grand["ambiguous"] > 0:
        ambig_rate = grand["tp_first"] / grand["ambiguous"] * 100
        lines.append(
            f"| TP-first among ambiguous | {ambig_rate:.1f}% of ambiguous trades |"
        )
    lines.append("")

    # ── Score impact estimate ──
    total_flips = sum(r["pnl_loss_flips"] for r in results.values())
    total_boosts = sum(r["pnl_win_boost"] for r in results.values())
    total_pnl_before = 0.0
    total_pnl_after = 0.0
    for sym in results:
        for t in results[sym]["ambig_trades"]:
            total_pnl_before += t["pnl"]
            if t["_order"] == "TP_FIRST":
                total_pnl_after += alt_pnl(t)
            else:
                total_pnl_after += t["pnl"]

    lines.append("## Score Impact Estimate")
    lines.append("")
    lines.append("If misclassified trades were TP instead of SL/LOSS:")
    lines.append("")
    lines.append(f"- **Losses flipped to wins:** {total_flips} trades")
    lines.append(f"- **Existing wins with higher PnL:** {total_boosts} trades")
    lines.append(
        f"- **Ambiguous trades PnL before correction:** {total_pnl_before:+.2f}"
    )
    lines.append(f"- **Ambiguous trades PnL after correction:** {total_pnl_after:+.2f}")
    lines.append(
        f"- **Net PnL change in ambiguous subset:** {total_pnl_after - total_pnl_before:+.2f}"
    )
    lines.append(f"- **Global PnL impact:** {grand['pnl_impact']:+.2f}")
    lines.append("")
    lines.append("> Full score recalculation (BE+%, PF, DD%) requires re-running the ")
    lines.append(
        "> backtest with corrected SL/TP logic. The above shows the raw PnL delta."
    )
    lines.append("")

    # ── Coin breakdown ──
    lines.append("## Coin Breakdown")
    lines.append("")
    lines.append(
        "| Coin | Total | Ambig | TP First | SL First | Same 1m | "
        "Loss→Win | Win+PnL | PnL Impact |"
    )
    lines.append(
        "|"
        + "|".join(
            [
                "-" * 10,
                "-" * 6,
                "-" * 7,
                "-" * 9,
                "-" * 9,
                "-" * 8,
                "-" * 9,
                "-" * 8,
                "-" * 11,
            ]
        )
        + "|"
    )
    for sym in sorted(results.keys()):
        r = results[sym]
        lines.append(
            f"| {sym:<10} | {r['total']:>4} | {r['ambiguous']:>5} | "
            f"{r['tp_first']:>7} | {r['sl_first']:>7} | "
            f"{r['same_1m']:>6} | {r['pnl_loss_flips']:>7} | "
            f"{r['pnl_win_boost']:>6} | {r['pnl_impact']:>+9.2f} |"
        )
    lines.append("")

    # ── Misclassified trades detail ──
    all_tp_first = []
    for sym in results:
        for t in results[sym]["ambig_trades"]:
            if t["_order"] == "TP_FIRST":
                all_tp_first.append(t)

    if all_tp_first:
        lines.append("## Misclassified Trades (TP Hit First in 1m)")
        lines.append("")
        lines.append(
            "| Coin | Session | Side | Entry | SL | TP | "
            "Engine PnL | True PnL | Delta | Exit Bar |"
        )
        lines.append(
            "|"
            + "|".join(
                [
                    "-" * 10,
                    "-" * 12,
                    "-" * 6,
                    "-" * 10,
                    "-" * 10,
                    "-" * 10,
                    "-" * 10,
                    "-" * 10,
                    "-" * 9,
                    "-" * 16,
                ]
            )
            + "|"
        )
        for t in sorted(
            all_tp_first, key=lambda x: (x.get("_sym", ""), x.get("pnl", 0))
        ):
            true = alt_pnl(t)
            delta = true - t["pnl"]
            bar_ts = "?"
            sym = t.get("_sym", "?")
            if sym in b15_map and t["exit_bar"] < len(b15_map[sym]):
                bar_ts = fmt_ts(b15_map[sym][t["exit_bar"]].timestamp)
            trail_mark = " *" if t.get("trailing_count", 0) > 0 else ""
            lines.append(
                f"| {sym:<10} | {t.get('_session', '?'):<12} | "
                f"{t['side']:<6} | {t['entry_price']:>8.4f} | "
                f"{t['sl']:>8.4f} | {t['tp']:>8.4f} | "
                f"{t['pnl']:>+8.2f} | {true:>+8.2f} | "
                f"{delta:>+7.2f} | {bar_ts}{trail_mark} |"
            )
        lines.append("")
        lines.append("*\\* = trade had trailing SL adjustments before exit*")
        lines.append("")

    # ── All ambiguous trades detail ──
    all_ambig_sorted = []
    for sym in results:
        for t in results[sym]["ambig_trades"]:
            all_ambig_sorted.append(t)

    if all_ambig_sorted:
        lines.append("## All Ambiguous Trades")
        lines.append("")
        lines.append(
            "| Coin | Session | Side | Result | Exit Price | SL | TP | "
            "PnL | 1m Order | Trail | Exit Bar |"
        )
        lines.append(
            "|"
            + "|".join(
                [
                    "-" * 10,
                    "-" * 12,
                    "-" * 6,
                    "-" * 8,
                    "-" * 10,
                    "-" * 10,
                    "-" * 10,
                    "-" * 9,
                    "-" * 12,
                    "-" * 5,
                    "-" * 16,
                ]
            )
            + "|"
        )
        for t in sorted(
            all_ambig_sorted,
            key=lambda x: (
                x.get("_sym", ""),
                0 if x["_order"] == "TP_FIRST" else 1,
            ),
        ):
            sym = t.get("_sym", "?")
            bar_ts = "?"
            if sym in b15_map and t["exit_bar"] < len(b15_map[sym]):
                bar_ts = fmt_ts(b15_map[sym][t["exit_bar"]].timestamp)
            order_label = t["_order"]
            if order_label == "TP_FIRST":
                order_label = "**TP_FIRST**"
            trail_ct = t.get("trailing_count", 0)
            lines.append(
                f"| {sym:<10} | {t.get('_session', '?'):<12} | "
                f"{t['side']:<6} | {t.get('result', '?'):<8} | "
                f"{t.get('exit_price', 0):>8.4f} | "
                f"{t['sl']:>8.4f} | {t['tp']:>8.4f} | "
                f"{t['pnl']:>+7.2f} | {order_label:<12} | "
                f"{trail_ct:>3} | {bar_ts} |"
            )
        lines.append("")

    # ── Session breakdown ──
    lines.append("## Session Breakdown")
    lines.append("")
    lines.append("| Coin | Session | Total | Ambiguous | Ambig % | TP First |")
    lines.append(
        "|" + "|".join(["-" * 10, "-" * 12, "-" * 6, "-" * 10, "-" * 8, "-" * 9]) + "|"
    )
    for sym in sorted(results.keys()):
        for sname in SESSION_CONFIGS:
            if sname not in results[sym]["sessions"]:
                continue
            sd = results[sym]["sessions"][sname]
            amb_pct = sd["ambiguous"] / sd["total"] * 100 if sd["total"] > 0 else 0
            # Count TP_FIRST per session
            tp_count = sum(
                1
                for t in results[sym]["ambig_trades"]
                if t.get("_session") == sname and t["_order"] == "TP_FIRST"
            )
            lines.append(
                f"| {sym:<10} | {sname:<12} | {sd['total']:>4} | "
                f"{sd['ambiguous']:>8} | {amb_pct:>5.1f}% | "
                f"{tp_count:>7} |"
            )
    lines.append("")

    # ── Engine behavior note ──
    lines.append("## Engine Behavior Note")
    lines.append("")
    lines.append(
        "The backtest engine (`analyze_cbdr_thresholds.py` / `analyzer_v5.py`)"
    )
    lines.append("checks SL before TP within each 15m bar (lines 593-618):")
    lines.append("")
    lines.append("```python")
    lines.append('if t["side"] == "long":')
    lines.append('    if cur.low <= t["sl"]:     # SL checked FIRST')
    lines.append('        t["result"] = "SL"')
    lines.append('    elif cur.high >= t["tp"]:  # TP checked SECOND')
    lines.append('        t["result"] = "TP"')
    lines.append("```")
    lines.append("")
    lines.append("This means that when both levels are breached in the same 15m bar,")
    lines.append("SL always wins — even if TP was actually hit first within that bar.")
    lines.append("This script resolves that ambiguity using 1-minute resolution data.")
    lines.append("")

    lines.append("---")
    lines.append("*Report auto-generated by `_sl_tp_ambiguity.py`*")

    # ────────────────────────────────────────────────────────────────
    # Print to stdout
    # ────────────────────────────────────────────────────────────────
    report_text = "\n".join(lines)
    print("\n" + report_text)

    # ────────────────────────────────────────────────────────────────
    # Write markdown file
    # ────────────────────────────────────────────────────────────────
    report_dir = os.path.join(_THIS_DIR, "..", "reports")
    os.makedirs(report_dir, exist_ok=True)
    md_path = os.path.join(report_dir, "sl_tp_ambiguity.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report_text)
    print(f"\n  Rapor yazildi: {md_path}")
    print(f"  Toplam sure: {elapsed:.0f}s")


if __name__ == "__main__":
    main()
