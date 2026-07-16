"""
bucket_data_extractor_v2.py
============================
analyzer_v5.py (trailing-dahil, "live-identical" motor) ile AYNI klasöre
(src/) konulmalı — config.py, fvg.py, indicators.py, session.py, session_router.py
gibi bağımlılıkları oradan import eder.

Ne yapar:
  1. Her sembol için collect_fvg_profile(symbol) çağırır (analyzer_v5.py'den) ->
     daily_rows (day_key -> cbdr_pct) ve trade_records (day_key, pnl, result,
     risk_usd dahil — PROFIT_TRAIL'i de kapsıyor, trailing dahil).
  2. Her trade'i, ait olduğu günün cbdr_pct'ine göre CBDR_RISK_MATRIX'teki
     GERÇEK bucket sınırlarına atar (analyze_cbdr_thresholds.py'deki
     analyze_bucket_scaling() ile AYNI atama mantığı).
  3. Her (symbol, bucket) alt kümesi için compute_session_stats()'i
     (analyzer_v5.py'den, DEĞİŞTİRİLMEDEN) çağırır -> n, PF, Sharpe, MaxDD%, PE%.
  4. bucket_data.json yazar (bucket_risk_engine.py'nin beklediği format).

NOT: Önceki bucket_extractor.py (fvg_size/atr oranına dayanan) YANLIŞTI,
kullanma / sil. Bucket anahtarı CBDR range genişliği yüzdesidir, FVG/ATR
oranı değil.

Kullanım (src/ klasöründe):
    python3 bucket_data_extractor_v2.py [-o bucket_data.json]
"""

import sys
import os
import json
import argparse

_BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BASE)
_SNIPER_SRC = os.environ.get("SNIPER_ROOT") or os.path.join(
    _BASE, "..", "..", "sniper", "src"
)
if _SNIPER_SRC not in sys.path:
    sys.path.insert(0, _SNIPER_SRC)

import config as cfg  # noqa: E402
from analyzer_v5 import collect_fvg_profile, compute_session_stats  # noqa: E402

DEFAULT_BUCKETS = [
    (0.0, 1.0),
    (1.0, 1.5),
    (1.5, 2.0),
    (2.0, 3.0),
    (3.0, 5.0),
    (5.0, 999.0),
]


def bucket_stats_for_symbol(symbol: str) -> list:
    result = collect_fvg_profile(symbol)
    if result is None or (isinstance(result, tuple) and result[0] is None):
        print(f"  [{symbol}] VERI YOK, atlaniyor")
        return []

    daily_rows, wins, losses, trade_records, rejection_counts = result
    if not daily_rows or not trade_records:
        print(f"  [{symbol}] daily_rows veya trade_records bos, atlaniyor")
        return []

    # day_key -> cbdr_pct sozlugu (analyze_bucket_scaling ile ayni mantik)
    day_to_cbdr = {
        d["day_key"]: d["cbdr_pct"] for d in daily_rows if d.get("cbdr_pct") is not None
    }

    profile = cfg.CBDR_RISK_MATRIX.get(symbol, {})
    session = profile.get("session", "DEFAULT")
    matrix_buckets = profile.get("buckets", [])
    bucket_bounds = (
        [(lo, hi) for lo, hi, _mult in matrix_buckets]
        if matrix_buckets
        else DEFAULT_BUCKETS
    )

    # Her trade'i gunun cbdr_pct'ine gore bucket'a ata
    bucket_trades: dict = {b: [] for b in bucket_bounds}
    unmatched = 0
    for tr in trade_records:
        dk = tr.get("day_key")
        cbdr_w = day_to_cbdr.get(dk)
        if cbdr_w is None:
            unmatched += 1
            continue
        placed = False
        for lo, hi in bucket_bounds:
            if lo <= cbdr_w < hi:
                bucket_trades[(lo, hi)].append(tr)
                placed = True
                break
        if not placed:
            unmatched += 1

    if unmatched:
        print(
            f"  [{symbol}] {unmatched} trade hicbir bucket'a eslenemedi (cbdr_pct eksik/disinda)"
        )

    out = []
    for (lo, hi), trades in bucket_trades.items():
        if not trades:
            out.append(
                {
                    "symbol": symbol,
                    "session": session,
                    "bucket_low": lo,
                    "bucket_high": hi,
                    "n": 0,
                    "pf": 0.0,
                    "sharpe": 0.0,
                    "max_dd_pct": 0.0,
                    "pe_pct": 0.0,
                }
            )
            continue
        stats = compute_session_stats(trades, cfg.INITIAL_BALANCE)
        if stats["total_trades"] == 0:
            continue
        out.append(
            {
                "symbol": symbol,
                "session": session,
                "bucket_low": lo,
                "bucket_high": hi,
                "n": stats["total_trades"],
                "pf": round(stats["profit_factor"], 3),
                "sharpe": round(stats["sharpe"], 4),
                "max_dd_pct": round(stats["max_dd_pct"], 3),
                "pe_pct": round(stats["positive_exit_pct"], 2),
            }
        )
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", default="bucket_data.json")
    parser.add_argument(
        "--symbols",
        nargs="*",
        default=None,
        help="Belirli semboller (default: config.py SYMBOLS listesinin tamami)",
    )
    args = parser.parse_args()

    symbols = args.symbols if args.symbols else sorted(cfg.SYMBOLS)
    print(
        f"{len(symbols)} sembol icin bucket cikartiliyor (trailing-dahil, analyzer_v5 motoru)...\n"
    )

    all_records = []
    for sym in symbols:
        print(f"[{sym}] isleniyor...")
        try:
            recs = bucket_stats_for_symbol(sym)
            all_records.extend(recs)
            print(f"  [{sym}] {len(recs)} bucket uretildi")
        except Exception as e:
            import traceback

            print(f"  [{sym}] HATA: {e}")
            traceback.print_exc()
            continue

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(all_records, f, indent=2, ensure_ascii=False)

    print(f"\nTOPLAM: {len(all_records)} bucket -> {args.output}")
    print("\nSonraki adim:")
    print(f"  python3 bucket_risk_engine.py {args.output} config.py")


if __name__ == "__main__":
    main()
