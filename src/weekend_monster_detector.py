"""
weekend_monster_detector.py
=============================
analyzer_v5.py (src/) ile AYNI klasore konulmali.

Her coin icin hafta ici vs hafta sonu (Cmt-Paz) performansini karsilastirir.
Sadece nokta-tahmine (PF farki var mi) bakmiyor -- GUN bazinda permutasyon
testiyle bunun rastgele gurultu mu yoksa gercek bir yapisal fark mi oldugunu
olcuyor, ve 28 coin arasinda coklu test duzeltmesi (Benjamini-Hochberg) uyguluyor.

Cikti: weekend_monster_report.md
  - Her coin icin: n_weekday, n_weekend, PF_weekday, PF_weekend, PF_orani,
    ham p-degeri, duzeltilmis p-degeri (BH-FDR), "CANAVAR" etiketi
    (sadece hem istatistiksel anlamli HEM ekonomik olarak buyukse).

Kullanim (src/ klasorunde):
    python3 weekend_monster_detector.py [-o weekend_monster_report.md] [--perms 2000]
"""

import sys
import os
import argparse
import random
from datetime import datetime

_BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BASE)
_SNIPER_SRC = os.environ.get("SNIPER_ROOT") or os.path.join(_BASE, "..", "..", "sniper", "src")
if _SNIPER_SRC not in sys.path:
    sys.path.insert(0, _SNIPER_SRC)

import config as cfg  # noqa: E402
from analyzer_v5 import collect_fvg_profile, compute_session_stats  # noqa: E402

MIN_N_PER_GROUP = 100          # bu esigin altinda hicbir sonuca guvenme
EFFECT_SIZE_MIN_PF_RATIO = 1.3  # ekonomik anlamlilik esigi
FDR_ALPHA = 0.05


def parse_day_key_weekday(day_key: str):
    """day_key'den haftanin gununu cikar. Format: %Y-%m-%d (session.py cbdr_key)."""
    try:
        return datetime.strptime(day_key, "%Y-%m-%d").weekday()  # 0=Pzt ... 5=Cmt,6=Paz
    except (ValueError, TypeError):
        return None


def split_by_weekday(trade_records):
    """trade_records icindeki her trade'i, o gunun hafta ici/sonu olmasina
    gore ikiye ayirir. day_key bazinda -> ayni gunun tum trade'leri ayni
    gruba dusuyor (korelasyonu koruyoruz)."""
    weekday_trades, weekend_trades = [], []
    day_is_weekend = {}
    unmatched = 0
    for tr in trade_records:
        dk = tr.get("day_key")
        if dk not in day_is_weekend:
            wd = parse_day_key_weekday(dk) if dk else None
            day_is_weekend[dk] = (wd is not None and wd >= 5)
            if wd is None:
                unmatched += 1
        if day_is_weekend[dk]:
            weekend_trades.append(tr)
        else:
            weekday_trades.append(tr)
    return weekday_trades, weekend_trades, unmatched, day_is_weekend


def pf_from_trades(trades):
    if not trades:
        return 0.0
    gp = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    gl = abs(sum(t["pnl"] for t in trades if t["pnl"] < 0))
    return 999.0 if gl == 0 else gp / gl


def permutation_test_pf_diff(all_trades, day_is_weekend, n_weekend_days, n_perms=2000, seed=42):
    """
    Gun bazinda permutasyon: gercek hafta sonu gun sayisi kadar GUNU rastgele
    'hafta sonu' olarak isaretleyip (ayni gundeki trade'ler birlikte kalir),
    her permutasyonda PF farkini hesapla. Gercek fark bu null dagilimin
    neresinde -> empirik p-degeri.
    """
    rng = random.Random(seed)
    all_days = list(day_is_weekend.keys())
    if len(all_days) <= n_weekend_days or n_weekend_days == 0:
        return None  # yetersiz gun cesitliligi

    # gercek PF farkini hesapla (referans)
    real_weekday = [t for t in all_trades if not day_is_weekend[t["day_key"]]]
    real_weekend = [t for t in all_trades if day_is_weekend[t["day_key"]]]
    real_diff = pf_from_trades(real_weekend) - pf_from_trades(real_weekday)

    null_diffs = []
    for _ in range(n_perms):
        shuffled_weekend_days = set(rng.sample(all_days, n_weekend_days))
        perm_weekend = [t for t in all_trades if t["day_key"] in shuffled_weekend_days]
        perm_weekday = [t for t in all_trades if t["day_key"] not in shuffled_weekend_days]
        null_diffs.append(pf_from_trades(perm_weekend) - pf_from_trades(perm_weekday))

    # iki-yonlu empirik p-degeri
    extreme = sum(1 for d in null_diffs if abs(d) >= abs(real_diff))
    p_value = (extreme + 1) / (n_perms + 1)  # +1 duzeltmesi (asla p=0 cikmasin)
    return real_diff, p_value


def benjamini_hochberg(p_values: dict, alpha=0.05):
    """symbol -> p_value sozlugu alir, symbol -> (adjusted_p, significant) dondurur."""
    items = sorted(p_values.items(), key=lambda kv: kv[1])
    m = len(items)
    adjusted = {}
    prev_adj = 1.0
    for rank, (sym, p) in enumerate(reversed(items), start=1):
        i = m - rank + 1
        adj = min(prev_adj, p * m / i)
        adjusted[sym] = adj
        prev_adj = adj
    significant = {sym: (adjusted[sym], adjusted[sym] <= alpha) for sym in adjusted}
    return significant


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", default="weekend_monster_report.md")
    parser.add_argument("--perms", type=int, default=2000)
    args = parser.parse_args()

    symbols = sorted(cfg.SYMBOLS)
    print(f"{len(symbols)} sembol icin hafta sonu analizi...\n")

    results = {}
    raw_p_values = {}

    for sym in symbols:
        print(f"[{sym}] isleniyor...")
        try:
            result = collect_fvg_profile(sym)
        except Exception as e:
            print(f"  HATA: {e}")
            continue
        if result is None or result[0] is None:
            print("  veri yok, atlaniyor")
            continue
        daily_rows, wins, losses, trade_records, rejection_counts = result
        if not trade_records:
            print("  trade yok, atlaniyor")
            continue

        weekday_trades, weekend_trades, unmatched, day_is_weekend = split_by_weekday(trade_records)
        n_weekend_days = sum(1 for v in day_is_weekend.values() if v)

        if unmatched > 0:
            print(f"  UYARI: {unmatched} gun day_key formatindan parse edilemedi")

        n_wd, n_we = len(weekday_trades), len(weekend_trades)
        if n_wd < MIN_N_PER_GROUP or n_we < MIN_N_PER_GROUP:
            print(f"  n yetersiz (hafta_ici={n_wd}, hafta_sonu={n_we}) -> guvenilir degil, atlaniyor")
            results[sym] = {
                "n_weekday": n_wd, "n_weekend": n_we,
                "pf_weekday": None, "pf_weekend": None,
                "insufficient_n": True,
            }
            continue

        stats_wd = compute_session_stats(weekday_trades, cfg.INITIAL_BALANCE)
        stats_we = compute_session_stats(weekend_trades, cfg.INITIAL_BALANCE)

        perm_result = permutation_test_pf_diff(
            trade_records, day_is_weekend, n_weekend_days, n_perms=args.perms
        )
        if perm_result is None:
            print("  permutasyon icin yetersiz gun cesitliligi, atlaniyor")
            continue
        real_diff, p_value = perm_result

        results[sym] = {
            "n_weekday": n_wd, "n_weekend": n_we,
            "pf_weekday": stats_wd["profit_factor"], "pf_weekend": stats_we["profit_factor"],
            "sharpe_weekday": stats_wd["sharpe"], "sharpe_weekend": stats_we["sharpe"],
            "maxdd_weekday": stats_wd["max_dd_pct"], "maxdd_weekend": stats_we["max_dd_pct"],
            "pf_ratio": (stats_we["profit_factor"] / stats_wd["profit_factor"]) if stats_wd["profit_factor"] > 0 else None,
            "p_value": p_value,
            "insufficient_n": False,
        }
        raw_p_values[sym] = p_value
        print(f"  hafta_ici PF={stats_wd['profit_factor']:.2f} (n={n_wd}) | "
              f"hafta_sonu PF={stats_we['profit_factor']:.2f} (n={n_we}) | ham_p={p_value:.4f}")

    # Coklu test duzeltmesi
    fdr_results = benjamini_hochberg(raw_p_values, alpha=FDR_ALPHA) if raw_p_values else {}

    # Rapor
    lines = ["# Weekend Monster Detection Report", ""]
    lines.append(f"Permutasyon sayisi: {args.perms} | Min n/grup: {MIN_N_PER_GROUP} | "
                 f"Min PF orani (ekonomik esik): {EFFECT_SIZE_MIN_PF_RATIO} | FDR alpha: {FDR_ALPHA}")
    lines.append("")
    lines.append("| Symbol | n_hafta_ici | n_hafta_sonu | PF_hafta_ici | PF_hafta_sonu | PF_orani | ham_p | duzeltilmis_p | CANAVAR MI |")
    lines.append("|---|---|---|---|---|---|---|---|---|")

    monsters = []
    for sym, r in sorted(results.items()):
        if r.get("insufficient_n"):
            lines.append(f"| {sym} | {r['n_weekday']} | {r['n_weekend']} | - | - | - | - | - | YETERSIZ VERI |")
            continue
        adj_p, is_sig_stat = fdr_results.get(sym, (None, False))
        is_sig_effect = r["pf_ratio"] is not None and r["pf_ratio"] >= EFFECT_SIZE_MIN_PF_RATIO
        is_monster = is_sig_stat and is_sig_effect
        if is_monster:
            monsters.append(sym)
        lines.append(
            f"| {sym} | {r['n_weekday']} | {r['n_weekend']} | {r['pf_weekday']:.2f} | "
            f"{r['pf_weekend']:.2f} | {r['pf_ratio']:.2f}x | {r['p_value']:.4f} | "
            f"{adj_p:.4f} | {'✓ CANAVAR' if is_monster else '-'} |"
        )

    lines.append("")
    lines.append(f"## Sonuc: {len(monsters)} 'hafta sonu canavari' tespit edildi: {monsters}")
    lines.append("")
    lines.append(
        "Not: 'CANAVAR' etiketi hem istatistiksel anlamlilik (BH-FDR duzeltilmis p<=0.05) "
        "HEM ekonomik buyukluk (PF orani >= 1.3x) gerektirir. Sadece biri yetmez."
    )

    with open(args.output, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\nRapor yazildi: {args.output}")
    print(f"Tespit edilen canavarlar: {monsters}")


if __name__ == "__main__":
    main()
