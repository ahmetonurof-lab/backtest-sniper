"""
compare_windows.py — V3 pencereler arasi karsilastirma (multi-session).
3 CBDR penceresini ayri ayri calistirir, overlap filtreli karsilastirma tablosu basar.
"""
# ruff: noqa: E402, E704, E701, E702 — path manipulation + legacy style
import csv
import os
import sys
import time
from datetime import datetime, timezone

os.environ["SNIPER_OUTPUT_DIR"] = os.path.join(os.path.dirname(__file__), "..", "output")
sys.path.insert(0, os.path.dirname(__file__))
_SNIPER_SRC = os.path.join(os.path.dirname(__file__), "..", "..", "sniper", "src")
if _SNIPER_SRC not in sys.path:
    sys.path.insert(0, _SNIPER_SRC)

import config as cfg
import analyzer_v3

REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
os.makedirs(REPORT_DIR, exist_ok=True)

# ─── Session configs (analyze_cbdr_thresholds.py ile uyumlu) ───
SESSION_CONFIGS = {
    'REAL_CBDR':   {'start': 19, 'end': 1},
    'DEFAULT':     {'start': 22, 'end': 2},
    'ASIA_RANGE':  {'start': 1,  'end': 5},
}


def compute_stats(trade_list, initial_balance):
    """(session_name, pnl, result) listesinden istatistik hesapla."""
    n = len(trade_list)
    if n == 0:
        return {'trades': 0, 'wr': 0, 'pf': 0, 'mdd': 0, 'avg_mae': 0, 'pnl': 0}
    pnls = [t[1] for t in trade_list]
    total_pnl = sum(pnls)
    wins = sum(1 for p in pnls if p > 0)
    wr = wins / n * 100 if n > 0 else 0
    gross_profit = sum(p for p in pnls if p > 0) or 0
    gross_loss = abs(sum(p for p in pnls if p < 0)) or 1e-9
    pf = gross_profit / gross_loss
    cum = 0; peak = 0; mdd = 0
    for p in pnls:
        cum += p
        if cum > peak: peak = cum
        dd = peak - cum
        if dd > mdd: mdd = dd
    mdd_pct = (mdd / initial_balance) * 100 if initial_balance > 0 else 0
    losses_list = [p for p in pnls if p < 0]
    avg_mae = abs(sum(losses_list) / len(losses_list)) if losses_list else 0
    return {'trades': n, 'wr': wr, 'pf': pf, 'mdd': mdd_pct, 'avg_mae': avg_mae, 'pnl': total_pnl}


def main():
    t0 = time.time()

    print("=" * 110)
    print("  V3 PENCERE KARSILASTIRMA — Multi-Session")
    print(f"  Session'lar: {', '.join(SESSION_CONFIGS.keys())}")
    print("=" * 110)

    all_symbol_results = {}  # {sym: {sname: {...}}}
    all_trade_records = []   # (trade_id, sname, pnl, result, sym)

    for sym in sorted(cfg.SYMBOLS):
        sym_start = time.time()
        print(f"\n  [{sym}] Calisiyor...", flush=True)
        sym_results = {}

        for sname, shours in SESSION_CONFIGS.items():
            try:
                result = analyzer_v3.run_for_symbol(sym, session_hours=shours)
                if result is None:
                    print(f"    [{sname}] VERI YOK / HATA", flush=True)
                    continue
                sym_results[sname] = result
                # Trade record'larini topla (analyzer_v3 trades listesinden)
                for t in result.get('trades', []):
                    entry_day = t.get('day_key', '')
                    bar_idx = t.get('entry_bar', 0)
                    trade_id = f"{sname}_{entry_day}_{bar_idx}"
                    all_trade_records.append((trade_id, sname, t.get('pnl', 0), t.get('result', ''), sym))
                print(f"    [{sname}] {result.get('total_trades', 0)} islem, WR={result.get('wr', 0):.1f}%", flush=True)
            except Exception as e:
                print(f"    [{sname}] HATA: {e}", flush=True)
                continue

        if sym_results:
            all_symbol_results[sym] = sym_results
            print(f"  [{sym}] {time.time()-sym_start:.0f}s", flush=True)

    # ── Overlap filtrele ──
    unique_records = []
    seen_keys = set()
    for tid, sname, pnl, result, sym in all_trade_records:
        ok = tid.split('_', 1)[1] if '_' in tid else tid  # entry_day_sb
        if ok not in seen_keys:
            seen_keys.add(ok)
            unique_records.append((tid, sname, pnl, result, sym))

    total_raw = len(all_trade_records)
    total_unique = len(unique_records)

    # ── Session bazinda istatistikler ──
    csv_rows = []
    for sym in sorted(cfg.SYMBOLS):
        if sym not in all_symbol_results:
            continue
        print(f"\n  ┌─ [{sym}] V3 Pencere Karsilastirma ───────────────────────────────┐")
        print(f"  │ {'Session':<14} {'Trade':>7} {'WR%':>7} {'PF':>7} {'MaxDD%':>8} {'AvgMAE':>8} {'PnL':>10} │")
        print(f"  ├{'─'*14}┼{'─'*7}┼{'─'*7}┼{'─'*7}┼{'─'*8}┼{'─'*8}┼{'─'*10}┤")
        for sname in SESSION_CONFIGS:
            if sname not in all_symbol_results[sym]:
                continue
            raw_trades = all_symbol_results[sym][sname].get('trades', [])
            # Unique trade'leri filtrele
            session_unique = [r for r in unique_records if r[1] == sname and r[4] == sym]
            stats = compute_stats(session_unique, cfg.INITIAL_BALANCE)
            print(f"  │ {sname:<14} {len(raw_trades):>7} {stats['wr']:>5.1f}% {stats['pf']:>5.2f} "
                  f"{stats['mdd']:>6.2f}% {stats['avg_mae']:>7.2f} {stats['pnl']:>+8.0f} │")
            csv_rows.append({
                'Coin': sym, 'Session': sname,
                'Trades_Raw': len(raw_trades), 'Trades_Unique': stats['trades'],
                'WR': round(stats['wr'], 1), 'PF': round(stats['pf'], 2),
                'MaxDD': round(stats['mdd'], 2), 'AvgMAE': round(stats['avg_mae'], 2),
                'PnL': round(stats['pnl'], 0),
            })
        print(f"  └{'─'*14}┴{'─'*7}┴{'─'*7}┴{'─'*7}┴{'─'*8}┴{'─'*8}┴{'─'*10}┘")

    print(f"\n  Overlap: {total_unique}/{total_raw} unique trade ({total_raw - total_unique} filtered)")

    # ── CSV rapor ──
    csv_path = os.path.join(REPORT_DIR, "v3_window_comparison.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=['Coin', 'Session', 'Trades_Raw', 'Trades_Unique',
                                           'WR', 'PF', 'MaxDD', 'AvgMAE', 'PnL'])
        w.writeheader()
        w.writerows(csv_rows)
    print(f"  CSV: {csv_path}")

    # ── MD rapor ──
    md_path = os.path.join(REPORT_DIR, "v3_window_comparison.md")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# V3 Pencere Karsilastirmasi — Multi-Session\n\n")
        f.write(f"**Generated:** {now}\n")
        f.write("**Strategy:** V3 — Sweep → FVG → Entry → Trailing → Exit\n")
        f.write(f"**Session Configs:** {', '.join(SESSION_CONFIGS.keys())}\n")
        f.write(f"**Overlap Filter:** Active — {total_unique}/{total_raw} unique\n\n")
        f.write("## Comparison Table\n\n")
        f.write("| Coin | Session | Raw | Unique | WR% | PF | MaxDD% | AvgMAE | PnL |\n")
        f.write("|------|---------|----:|-------:|----:|----:|------:|------:|----:|\n")
        for row in csv_rows:
            f.write(f"| {row['Coin']:<8} | {row['Session']:<10} | {row['Trades_Raw']:>4} | {row['Trades_Unique']:>4} | "
                    f"{row['WR']:>4.1f}% | {row['PF']:>3.2f} | {row['MaxDD']:>5.2f}% | {row['AvgMAE']:>5.2f} | {row['PnL']:>+8.0f} |\n")
        f.write("\n---\n")
        f.write("*Report auto-generated by `compare_windows.py`*\n")

    print(f"  MD:  {md_path}")
    print(f"\n  Toplam sure: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
