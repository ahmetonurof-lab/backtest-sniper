"""Fallback frekans analizi: checkpoint'ten A vs E farklarini cek, coin bazli dagilimi goster."""

import pickle
import os
import collections

CKPT = os.path.join(
    os.path.dirname(__file__), "..", "reports", "_replay_checkpoint.pkl"
)

with open(CKPT, "rb") as f:
    data = pickle.load(f)

results = data["results"]
base_key = ("A", 0.1, 1)
e_key = ("E", 2.0, 30)

if base_key not in results:
    print(f"Base key {base_key} bulunamadi. Mevcut key'ler: {list(results.keys())}")
    exit(1)
if e_key not in results:
    print(f"E key {e_key} bulunamadi. Mevcut key'ler: {list(results.keys())}")
    exit(1)

base = results[base_key]
variant = results[e_key]

# E vs A: farkli sonuclanan trade'ler
diff_trades = []
for k, v in variant.items():
    b = base.get(k)
    if b is None:
        continue
    if (b["trailing_count"], b["result"], b["final_pnl_usd"]) != (
        v["trailing_count"],
        v["result"],
        v["final_pnl_usd"],
    ):
        sym = k[0]  # (symbol, entry_time, side, entry_price)
        diff_trades.append(
            {
                "symbol": sym,
                "entry_time": k[1],
                "side": k[2],
                "entry_price": k[3],
                "A_result": b["result"],
                "E_result": v["result"],
                "A_pnl": b["final_pnl_usd"],
                "E_pnl": v["final_pnl_usd"],
                "A_hops": b["trailing_count"],
                "E_hops": v["trailing_count"],
            }
        )

print("=== A vs E (K=2.0, N=30) Fallback Analizi ===")
print(f"Toplam farkli trade: {len(diff_trades)}")
print()

# Coin bazli dagilim
coin_counts = collections.Counter(t["symbol"] for t in diff_trades)
print("--- Farkli Trade Saysi (Coin bazli, azalan) ---")
for sym, cnt in coin_counts.most_common():
    print(f"  {sym:15s}  {cnt}")

# Her coin'in toplam trade sayisi (A baseline)
coin_total = collections.Counter()
for k in base:
    coin_total[k[0]] += 1

print()
print("--- Coin Bazli Oran (Farkli / Toplam) ---")
print(f"{'Coin':15s} {'Farkli':>7s} {'Toplam':>7s} {'Oran%':>8s}")
print("-" * 42)
for sym, cnt in coin_counts.most_common():
    total = coin_total.get(sym, 0)
    ratio = cnt / total * 100 if total else 0
    print(f"{sym:15s} {cnt:7d} {total:7d} {ratio:7.2f}%")

# Hiç fallback tetiklenmeyen coin'ler
all_symbols = set(coin_total.keys())
triggered = set(coin_counts.keys())
never_triggered = all_symbols - triggered
print(f"\n--- Hiç fallback tetiklenmeyen coin'ler ({len(never_triggered)} adet) ---")
for sym in sorted(never_triggered):
    total = coin_total.get(sym, 0)
    print(f"  {sym:15s}  {total} trade")

# PnL etkisi
total_pnl_delta = sum(t["E_pnl"] - t["A_pnl"] for t in diff_trades)
print("\n--- PnL Etkisi ---")
print(f"Toplam PnL degisimi: {total_pnl_delta:+,.2f} USD")
print(
    f"Ortalama/degisim:    {total_pnl_delta/len(diff_trades):+,.2f} USD/trade"
    if diff_trades
    else ""
)

# Sonuc dagilimi
result_changes = collections.Counter(
    (t["A_result"], t["E_result"]) for t in diff_trades
)
print("\n--- Sonuc Degisim Dagilimi ---")
for (a_r, e_r), cnt in result_changes.most_common():
    print(f"  {a_r:15s} -> {e_r:15s}  {cnt}")
