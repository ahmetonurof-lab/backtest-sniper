"""
kelly_calibration_check.py
===========================
analyzer_v5.py (src/) ile AYNI klasore konulmali.

Amac: composite score staircase'inin (0.80/0.65/0.50/... esikleri, PF gate
1.3/1.8/2.5 esikleri) GERCEKTEN hak edilmis mi oldugunu, o esiklerden
BAGIMSIZ iki yontemle capraz kontrol etmek:

  1) KELLY KRITERI: her bucket'in kendi R-multiple (pnl/risk_usd) dagiliminden
     f* = p - (1-p)/b  (p=kazanma olasiligi, b=ort.kazanc/ort.kayip orani)
     hesaplanir. Bu, bizim sectigimiz esiklerden tamamen bagimsiz, sadece o
     bucket'in kendi trade sonuclarindan cikan objektif bir sayi.
     Bootstrap CI (gun bazinda resample, korelasyonu koruyarak) ile
     guvenilirligi olculur.

  2) WALK-FORWARD: veri zaman bazinda ilk %70 (train) / son %30 (test) olarak
     bolunur. Train'den hesaplanan Kelly/skor siralamasi, hic gorulmemis
     test doneminde de tutuyor mu (Spearman rank correlation) kontrol edilir.
     Tutmuyorsa, mevcut esikler o zamana ozel (overfit) demektir.

Cikti: kelly_calibration_report.md
  - Her bucket icin: mevcut multiplier, composite score, Kelly f* (+ %90 CI),
    onerilen kelly-bazli fraksiyon (celyrek-Kelly, guvenlik icin).
  - Genel Spearman correlation (mevcut multiplier vs Kelly f*).
  - Walk-forward sonucu: train vs test siralama korelasyonu.

Kullanim (src/ klasorunde):
    python3 kelly_calibration_check.py [-o kelly_calibration_report.md] [--bootstrap 1000]
"""

import sys
import os
import argparse
import random
from datetime import datetime
from statistics import mean

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_SNIPER_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "sniper", "src")
if _SNIPER_SRC not in sys.path:
    sys.path.insert(0, _SNIPER_SRC)

import config as cfg
from analyzer_v5 import collect_fvg_profile

KELLY_FRACTION_SAFETY = 0.25   # ceyrek-Kelly (tam Kelly cok agresif/parametre belirsizligine hassas)


def r_multiples(trades):
    """Her trade icin pnl/risk_usd -> R-multiple listesi."""
    out = []
    for t in trades:
        ru = t.get("risk_usd", 0)
        if ru and ru > 0:
            out.append(t["pnl"] / ru)
    return out


def kelly_fraction(r_list):
    """f* = p - (1-p)/b ; b = ort.kazanc_R / ort.kayip_R (abs)."""
    if not r_list:
        return None
    wins = [r for r in r_list if r > 0]
    losses = [r for r in r_list if r <= 0]
    if not wins or not losses:
        return None
    p = len(wins) / len(r_list)
    avg_win = mean(wins)
    avg_loss = abs(mean(losses))
    if avg_loss == 0:
        return None
    b = avg_win / avg_loss
    f_star = p - (1 - p) / b
    return f_star


def bootstrap_kelly_ci(trades_by_day: dict, n_boot=1000, seed=42):
    """Gun bazinda bootstrap (trade bazinda degil -- gun ici korelasyonu korur)."""
    rng = random.Random(seed)
    days = list(trades_by_day.keys())
    if len(days) < 5:
        return None, None, None
    point = kelly_fraction(r_multiples([t for d in days for t in trades_by_day[d]]))
    if point is None:
        return None, None, None

    samples = []
    for _ in range(n_boot):
        resampled_days = [rng.choice(days) for _ in days]
        pooled = [t for d in resampled_days for t in trades_by_day[d]]
        f = kelly_fraction(r_multiples(pooled))
        if f is not None:
            samples.append(f)
    if not samples:
        return point, None, None
    samples.sort()
    lo = samples[int(0.05 * len(samples))]
    hi = samples[int(0.95 * len(samples)) - 1]
    return point, lo, hi


def spearman_corr(x: list, y: list):
    """Basit Spearman rank korelasyonu (ek kutuphane gerektirmeden)."""
    n = len(x)
    if n < 3:
        return None

    def rank(vals):
        sorted_idx = sorted(range(len(vals)), key=lambda i: vals[i])
        ranks = [0.0] * len(vals)
        i = 0
        while i < len(sorted_idx):
            j = i
            while j + 1 < len(sorted_idx) and vals[sorted_idx[j + 1]] == vals[sorted_idx[i]]:
                j += 1
            avg_rank = (i + j) / 2 + 1
            for k in range(i, j + 1):
                ranks[sorted_idx[k]] = avg_rank
            i = j + 1
        return ranks

    rx, ry = rank(x), rank(y)
    d2 = sum((a - b) ** 2 for a, b in zip(rx, ry))
    return 1 - (6 * d2) / (n * (n ** 2 - 1))


def parse_day(day_key):
    """day_key formati session.py:367'de dogrulandi: '%Y-%m-%d'."""
    try:
        return datetime.strptime(day_key, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", default="kelly_calibration_report.md")
    parser.add_argument("--bootstrap", type=int, default=1000)
    args = parser.parse_args()

    symbols = sorted(cfg.SYMBOLS)
    all_current_mults = []
    all_kelly_points = []
    bucket_rows = []

    train_mults, train_kelly = [], []
    test_mults, test_kelly = [], []

    for sym in symbols:
        print(f"[{sym}] isleniyor...")
        try:
            result = collect_fvg_profile(sym)
        except Exception as e:
            print(f"  HATA: {e}")
            continue
        if result is None or result[0] is None:
            continue
        daily_rows, wins, losses, trade_records, rejection_counts = result
        if not trade_records:
            continue

        day_to_cbdr = {d["day_key"]: d.get("cbdr_pct") for d in daily_rows if d.get("cbdr_pct") is not None}
        profile = cfg.CBDR_RISK_MATRIX.get(sym, {})
        matrix_buckets = profile.get("buckets", [])

        # trade'leri gun+bucket'a gore grupla
        trades_by_bucket_day = {}
        for tr in trade_records:
            dk = tr.get("day_key")
            cbdr_w = day_to_cbdr.get(dk)
            if cbdr_w is None:
                continue
            for lo, hi, mult in matrix_buckets:
                if lo <= cbdr_w < hi:
                    key = (lo, hi, mult)
                    trades_by_bucket_day.setdefault(key, {}).setdefault(dk, []).append(tr)
                    break

        for (lo, hi, mult), by_day in trades_by_bucket_day.items():
            all_trades = [t for d in by_day.values() for t in d]
            if len(all_trades) < 30:
                continue
            point, ci_lo, ci_hi = bootstrap_kelly_ci(by_day, n_boot=args.bootstrap)
            if point is None:
                continue

            all_current_mults.append(mult)
            all_kelly_points.append(point)
            bucket_rows.append({
                "symbol": sym, "lo": lo, "hi": hi, "n": len(all_trades),
                "current_mult": mult, "kelly_f": point, "ci_lo": ci_lo, "ci_hi": ci_hi,
            })

            # walk-forward: gunleri tarihe gore sirala, ilk %70/son %30
            dated_days = [(d, parse_day(d)) for d in by_day.keys()]
            dated_days = [(d, dt) for d, dt in dated_days if dt is not None]
            dated_days.sort(key=lambda x: x[1])
            if len(dated_days) >= 10:
                split_idx = int(len(dated_days) * 0.7)
                train_days = [d for d, _ in dated_days[:split_idx]]
                test_days = [d for d, _ in dated_days[split_idx:]]
                train_trades = [t for d in train_days for t in by_day.get(d, [])]
                test_trades = [t for d in test_days for t in by_day.get(d, [])]
                f_train = kelly_fraction(r_multiples(train_trades))
                f_test = kelly_fraction(r_multiples(test_trades))
                if f_train is not None and f_test is not None:
                    train_mults.append(mult)
                    train_kelly.append(f_train)
                    test_mults.append(mult)
                    test_kelly.append(f_test)

    overall_corr = spearman_corr(all_current_mults, all_kelly_points)
    train_corr = spearman_corr(train_mults, train_kelly)
    test_corr = spearman_corr(test_mults, test_kelly)

    lines = ["# Kelly Kalibrasyon Kontrol Raporu", ""]
    lines.append(f"Bootstrap tekrar sayisi: {args.bootstrap} | Ceyrek-Kelly guvenlik carpani: {KELLY_FRACTION_SAFETY}")
    lines.append("")
    lines.append(f"**Genel Spearman korelasyonu (mevcut multiplier vs Kelly f*): {overall_corr:.3f}**"
                 if overall_corr is not None else "Genel korelasyon hesaplanamadi (yetersiz veri)")
    lines.append("")
    lines.append("## Walk-Forward Dogrulama (ilk %70 train / son %30 test)")
    lines.append(f"- Train donemi korelasyonu: {train_corr:.3f}" if train_corr is not None else "- Train: yetersiz veri")
    lines.append(f"- Test (gorulmemis) donemi korelasyonu: {test_corr:.3f}" if test_corr is not None else "- Test: yetersiz veri")
    if train_corr is not None and test_corr is not None:
        drop = train_corr - test_corr
        lines.append(f"- Korelasyon dususu (train->test): {drop:.3f} "
                     f"{'(BUYUK DUSUS - mevcut esikler donem-ozel/overfit olabilir)' if drop > 0.25 else '(makul, sistem zamana dayanikli gorunuyor)'}")
    lines.append("")
    lines.append("## Bucket Detaylari")
    lines.append("| Symbol | Bucket | n | Mevcut Mult | Kelly f* | %90 CI | Ceyrek-Kelly Onerisi | Uyum |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in sorted(bucket_rows, key=lambda x: (x["symbol"], x["lo"])):
        quarter_kelly = r["kelly_f"] * KELLY_FRACTION_SAFETY if r["kelly_f"] else None
        ci_str = f"[{r['ci_lo']:.3f}, {r['ci_hi']:.3f}]" if r["ci_lo"] is not None else "N/A"
        # kaba uyum kontrolu: mevcut mult standart-ustu (>=1.0) veriyorsa,
        # Kelly de pozitif edge (f*>0) mi gosteriyor -- yon uyumu
        agree = "✓" if (r["current_mult"] >= 1.0) == (r["kelly_f"] > 0) else "✗"
        lines.append(
            f"| {r['symbol']} | {r['lo']}-{r['hi']} | {r['n']} | {r['current_mult']}x | "
            f"{r['kelly_f']:.3f} | {ci_str} | {quarter_kelly:.3f} | {agree} |"
        )

    with open(args.output, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\nRapor yazildi: {args.output}")
    print(f"Genel korelasyon: {overall_corr}")
    print(f"Train/Test korelasyon: {train_corr} / {test_corr}")


if __name__ == "__main__":
    main()
