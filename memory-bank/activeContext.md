# backtest-sniper — Active Context

## Current State
2026-07-09: `analyzer_v5.py` V5 engine (quality+fvg_sweep+cbdr_mult+el+weekend). MaxDD% ve Sharpe sütunları eklendi. Report append moduna geçirildi (timestamp ile).

## Recently Completed
- **V5 engine live:** `analyzer_v5.py` çalışıyor; rejection breakdown raporu eklendi (`reports/analyzer_v5_summary.md`).
- **MaxDD% + Sharpe:** `compute_session_stats()` fonksiyonuna yıllıklaştırılmış Sharpe eklendi (gunluk PnL bazlı, `sqrt(365)`). Console ve dosya raporuna `MaxDD%` ve `Sharpe` sütunları eklendi.
- **Report append mod:** `"w"` → `"a"`, header'a timestamp (`YYYY-MM-DD HH:MM`), her çalıştırma yeni section ekler.
- **trade_records day_key:** Sharpe hesabı için trade_records dict'ine `day_key` eklendi (satır 479, 520).
- **Eşik motoru V5'e geçti:** `analyze_cbdr_thresholds.py`'nin `collect_daily_data()`'sı artık `is_high_quality_fvg`, `get_fvg_status` (sweep-based expiry), `get_cbdr_multiplier`, `should_trade`, Early London, weekend bonus kullanıyor. Rejection tracking eklendi.
- **analyze_bucket_scaling():** `analyze_cbdr_thresholds.py`'ye eklendi. CBDR_RISK_MATRIX'teki gerçek bucket sınırlarını kullanarak pairwise Wilson CI overlap testi yapıyor. `wilson_lower()` fonksiyonu da eklendi. `ict_cbdr_bucket_scaling.csv` ve MD bölümü üretiliyor. Mevcut `analyze_thresholds()` dokunulmadı.
- **BNBUSDT config fix:** `sniper/src/config.py`'de 0-1% bucket mult 0.0x → 1.0x (Wilson CI: istatistiksel ayrışma yok).

## Active Decisions
- `analyzer_v5.py` artık `analyzer_v4.py`'den farklı: FVG expiry fitil‑based, time‑based değil.
- BNB'nin 0-1% bucket'ı 1.0x ile çalışıyor (0.0x kısıtlaması kaldırıldı).
- Bucket scaling: Hiçbir bucket çifti istatistiksel olarak ayrışmıyor (Wilson CI overlap).
- **FVG_SWEPT strict test edildi ve REDDEDİLDİ:** 3-bar FVG kontrolü (chunk[-3:]) test edildi. Trade sayısı %34 düştü, WR artması rağmen ortalama PnL/trade aynı kaldı (-0.62). Filtre rastgele çalışıyor, iyi ve kötü trade'leri eşit oranda reddediyor. Geri alındı.

## Next Actions
1. Koştur, sonuçları kontrol et.

## Open Questions
- (none)


