"""
execution_simulator_test.py — Execution simulator entegrasyon testi.

Bu dosya analyzer_v5'i degistirmeden, onun ciktiları uzerinde
execution simulation uygular. Orjinal backtest motorunu bozmaz.

Kullanim:
    python execution_simulator_test.py --symbol UNIUSDT
    python execution_simulator_test.py --symbol SEIUSDT --mode monte_carlo
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

# Backtest motorunu import et
_SNIPER_SRC = os.path.join(os.path.dirname(__file__), "..", "..", "sniper", "src")
sys.path.insert(0, _SNIPER_SRC)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import importlib.util
config_path = os.path.join(_SNIPER_SRC, "config.py")
spec = importlib.util.spec_from_file_location("config", config_path)
cfg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cfg)

from analyzer_v5 import collect_fvg_profile, compute_session_stats

# Execution simulator'ı import et
from execution_simulator import create_execution_simulator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("execution_simulator_test")


def run_with_execution_sim(
    symbol: str,
    mode: str = "deterministic",
    seed: int = 42,
) -> dict[str, Any]:
    """Tek sembol icin backtest + execution simulation calistir."""
    print(f"\n{'='*80}")
    print(f"  {symbol} — Execution Simulator Test (mode={mode}, seed={seed})")
    print(f"{'='*80}")

    # 1. Orjinal backtest calistir
    print(f"\n[1/3] Orjinal backtest calistiriliyor...")
    result = collect_fvg_profile(symbol)
    if result is None or (isinstance(result, tuple) and result[0] is None):
        return {"error": "VERI YOK"}
    daily_rows, wins, losses, trade_records, rejection_counts = result
    if len(daily_rows) < 1:
        return {"error": "YETERSIZ VERI"}

    # trade_records'da entry_price ve qty yok, wins+losses kullan
    all_trades = wins + losses
    original_stats = compute_session_stats(trade_records, cfg.INITIAL_BALANCE, daily_rows)
    print(f"  Orjinal: {original_stats['total_trades']} trade, "
          f"PnL={original_stats['total_pnl']:+.0f}, "
          f"Fee={original_stats['total_fee']:+.0f}")

    # 2. Execution simulator olustur
    print(f"\n[2/3] Execution simulator hazirlaniyor...")
    exec_sim = create_execution_simulator(
        profiles_path=None,  # execution_profiles.json'dan yukler
        mode=mode,
        seed=seed,
    )
    print(f"  Profiller yuklendi: {len(exec_sim.profiles)} sembol")

    # 3. Trade'lere execution simulation uygula
    print(f"\n[3/3] Trade'lere execution simulation uygulaniyor...")
    modified_trades = []
    exec_metrics = defaultdict(int)
    exec_slippages = []

    for trade in all_trades:
        # Entry simulation
        entry_result = exec_sim.submit_entry(
            symbol=symbol,
            side=trade.get("side", "long").lower(),
            signal_price=trade.get("entry_price", 0),
            requested_qty=trade.get("qty", 0),
            sl=trade.get("initial_sl"),
            tp=trade.get("initial_tp"),
            bar_timestamp=0,
            atr=0,
            mode=mode,
        )

        if entry_result.status.value == "REJECTED":
            exec_metrics["entry_rejected"] += 1
            continue

        if entry_result.status.value == "PARTIAL":
            exec_metrics["entry_partial"] += 1

        actual_entry_price = entry_result.average_fill_price or trade.get("entry_price", 0)
        actual_qty = entry_result.filled_qty
        exec_slippages.append(entry_result.slippage_bps)

        # Exit simulation
        exit_price = trade.get("exit_price", 0)
        exit_type = "TP" if trade.get("result") == "TP" else "SL"
        adjusted_exit_price, fee_rate = exec_sim.get_execution_adjusted_exit(
            symbol=symbol,
            side=trade.get("side", "long").lower(),
            exit_price=exit_price,
            exit_type=exit_type,
            bar=None,
        )

        # Yeni PnL hesapla
        if trade.get("side", "long").lower() == "long":
            diff = adjusted_exit_price - actual_entry_price
        else:
            diff = actual_entry_price - adjusted_exit_price

        entry_fee = actual_entry_price * actual_qty * fee_rate
        exit_fee = adjusted_exit_price * actual_qty * fee_rate
        total_fee = entry_fee + exit_fee
        pnl = diff * actual_qty - total_fee

        modified_trade = trade.copy()
        modified_trade["entry_price"] = actual_entry_price
        modified_trade["qty"] = actual_qty
        modified_trade["exit_price"] = adjusted_exit_price
        modified_trade["pnl"] = round(pnl, 2)
        modified_trade["fee"] = round(total_fee, 2)
        modified_trade["slippage_bps"] = entry_result.slippage_bps
        modified_trades.append(modified_trade)

    # 4. Yeni istatistikler
    modified_stats = compute_session_stats(modified_trades, cfg.INITIAL_BALANCE, daily_rows)

    # 5. Karsilastirma
    print(f"\n{'='*80}")
    print(f"  KARSILASTIRMA")
    print(f"{'='*80}")
    print(f"  {'Metrik':<30} {'Orjinal':>12} {'Modified':>12} {'Fark':>12}")
    print(f"  {'-'*66}")

    metrics = [
        ("Total Trades", "total_trades", "d"),
        ("PnL", "total_pnl", "+.0f"),
        ("Fee", "total_fee", "+.0f"),
        ("PnL/Fee", "pnl_per_fee", ".2f"),
        ("Profit Factor", "profit_factor", ".2f"),
        ("Max DD%", "max_dd_pct", ".1f"),
        ("TP%", "tp_pct", ".1f"),
        ("Loss%", "loss_pct", ".1f"),
    ]

    for name, key, fmt in metrics:
        orig_val = original_stats.get(key, 0)
        mod_val = modified_stats.get(key, 0)
        diff_val = mod_val - orig_val
        if fmt == "+.0f":
            print(f"  {name:<30} {orig_val:>+12.0f} {mod_val:>+12.0f} {diff_val:>+12.0f}")
        elif fmt == ".2f":
            print(f"  {name:<30} {orig_val:>12.2f} {mod_val:>12.2f} {diff_val:>12.2f}")
        elif fmt == ".1f":
            print(f"  {name:<30} {orig_val:>12.1f} {mod_val:>12.1f} {diff_val:>12.1f}")
        else:
            print(f"  {name:<30} {orig_val:>12} {mod_val:>12} {diff_val:>12}")

    print(f"\n  Execution Metrics:")
    print(f"    Entry rejected: {exec_metrics['entry_rejected']}")
    print(f"    Entry partial: {exec_metrics['entry_partial']}")
    if exec_slippages:
        avg_slip = sum(exec_slippages) / len(exec_slippages)
        print(f"    Avg slippage: {avg_slip:.2f} bps")

    return {
        "symbol": symbol,
        "original_stats": original_stats,
        "modified_stats": modified_stats,
        "exec_metrics": dict(exec_metrics),
        "modified_trades": modified_trades,
    }


def main():
    parser = argparse.ArgumentParser(description="Execution simulator test")
    parser.add_argument("--symbol", type=str, required=True, help="Test edilecek sembol")
    parser.add_argument("--mode", type=str, default="deterministic", choices=["deterministic", "monte_carlo"])
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    result = run_with_execution_sim(args.symbol, args.mode, args.seed)
    
    # Sonuclari kaydet
    output_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "reports",
        f"exec_sim_{args.symbol}_{args.mode}.json"
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n  Rapor kaydedildi: {output_path}")


if __name__ == "__main__":
    main()
