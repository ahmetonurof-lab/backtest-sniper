# backtest-sniper — Active Context

## Current State
2026-07-09: `analyzer_v5.py` V5 engine (quality+fvg_sweep+cbdr_mult+el+weekend). `analyze_cbdr_thresholds.py` aynı motoru kullanacak şekilde güncellendi.

## Recently Completed
- **V5 engine live:** `analyzer_v5.py` çalışıyor; rejection breakdown raporu eklendi (`reports/analyzer_v5_summary.md`).
- **Eşik motoru V5'e geçti:** `analyze_cbdr_thresholds.py`'nin `collect_daily_data()`'sı artık `is_high_quality_fvg`, `get_fvg_status` (sweep-based expiry), `get_cbdr_multiplier`, `should_trade`, Early London, weekend bonus kullanıyor. Rejection tracking eklendi.
- **analyze_bucket_scaling():** `analyze_cbdr_thresholds.py`'ye eklendi. CBDR_RISK_MATRIX'teki gerçek bucket sınırlarını kullanarak pairwise Wilson CI overlap testi yapıyor. `wilson_lower()` fonksiyonu da eklendi. `ict_cbdr_bucket_scaling.csv` ve MD bölümü üretiliyor. Mevcut `analyze_thresholds()` dokunulmadı.

## Active Decisions
- `analyzer_v5.py` artık `analyzer_v4.py`'den farklı: FVG expiry fitil‑based, time‑based değil.

## Next Actions
1. Koştur, sonuçları kontrol et.

## Open Questions
- (none)


