import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

files = [
    os.path.join(BASE_DIR, "reports", "exec_sim_UNIUSDT_deterministic.json"),
    os.path.join(BASE_DIR, "reports", "exec_sim_SEIUSDT_deterministic.json"),
]

for path in files:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        print(f"\n{'='*80}")
        print(f"  {data['symbol']} — Execution Simulator Raporu")
        print(f"{'='*80}")
        
        orig = data["original_stats"]
        mod = data["modified_stats"]
        
        print(f"\n  Orijinal Backtest:")
        print(f"    Toplam Trade:    {orig['total_trades']}")
        print(f"    Win Rate:        {orig['positive_exit_pct']:.1f}%")
        print(f"    TP:              {orig['tp_pct']:.1f}%")
        print(f"    Profit Trail:    {orig['profit_trail_pct']:.1f}%")
        print(f"    Loss:            {orig['loss_pct']:.1f}%")
        print(f"    Profit Factor:   {orig['profit_factor']:.2f}")
        print(f"    Max DD%:         {orig['max_dd_pct']:.1f}%")
        print(f"    Sharpe:          {orig['sharpe']:.3f}")
        print(f"    Total PnL:       {orig['total_pnl']:+,.0f}")
        print(f"    Total Fee:       {orig['total_fee']:+,.0f}")
        print(f"    PnL/Fee:         {orig['pnl_per_fee']:.2f}")
        
        print(f"\n  Execution Simulator (Deterministic):")
        print(f"    Toplam Trade:    {mod['total_trades']}")
        print(f"    Win Rate:        {mod['positive_exit_pct']:.1f}%")
        print(f"    TP:              {mod['tp_pct']:.1f}%")
        print(f"    Profit Trail:    {mod['profit_trail_pct']:.1f}%")
        print(f"    Loss:            {mod['loss_pct']:.1f}%")
        print(f"    Profit Factor:   {mod['profit_factor']:.2f}")
        print(f"    Max DD%:         {mod['max_dd_pct']:.1f}%")
        print(f"    Sharpe:          {mod['sharpe']:.3f}")
        print(f"    Total PnL:       {mod['total_pnl']:+,.0f}")
        print(f"    Total Fee:       {mod['total_fee']:+,.0f}")
        print(f"    PnL/Fee:         {mod['pnl_per_fee']:.2f}")
        
        print(f"\n  Fark:")
        pnl_diff = mod['total_pnl'] - orig['total_pnl']
        pf_diff = mod['profit_factor'] - orig['profit_factor']
        mdd_diff = mod['max_dd_pct'] - orig['max_dd_pct']
        print(f"    PnL Farki:       {pnl_diff:+,.0f}")
        print(f"    PF Farki:        {pf_diff:+.2f}")
        print(f"    MaxDD Farki:     {mdd_diff:+.1f}%")
        
        print(f"\n  Execution Metrikleri:")
        em = data["exec_metrics"]
        print(f"    Entry Rejected:  {em['entry_rejected']}")
        print(f"    Entry Partial:   {em['entry_partial']}")
        
        # Trade detaylarından istatistik
        trades = data.get("modified_trades", [])
        if trades:
            wins = sum(1 for t in trades if t["pnl"] > 0)
            losses = sum(1 for t in trades if t["pnl"] < 0)
            avg_slippage = sum(t.get("slippage_bps", 0) for t in trades) / len(trades)
            print(f"    Avg Slippage:    {avg_slippage:.2f} bps")
            print(f"    Wins:            {wins}")
            print(f"    Losses:          {losses}")
        
    except Exception as e:
        print(f"Hata ({path}): {e}")

print(f"\n{'='*80}")
