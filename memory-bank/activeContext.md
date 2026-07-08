# backtest-sniper — Active Context

## Current State
2026-07-08: V5 Phase 3 (15 Kod/Mantık Hatası ve Bug Düzeltmesi) başarıyla uygulandı.

**Phase 3 — 15 Kod/Mantık Hatası ve Bug Fix Serisi:**
1. **KRİTİK #1** — Erken return tuple boyutu (`_collect_fvg_profile_impl` ve wrapper'da) 2 yerine 7 None yapılarak unpack/crash hatası (BUG 1) giderildi.
2. **KRİTİK #2** — `in_session` filtre mantığı ters çalışıyordu, session içinde trade edilecek şekilde düzeltildi (BUG 2).
3. **ORTA** — `fvg_close_confirmed` bearish kapanış koşulu gap altı kapanışları da kapsayacak şekilde genişletildi (BUG 3).
4. **ORTA** — `track_fvg_outcome` adverse/favorable excursion MAE ve MFE olarak ayrıldı, geriye dönük uyumluluk korundu (BUG 4).
5. **HAFİF** — `track_fvg_outcome` continuation penceresinin her bar'da tekrar hesaplanması engellendi, mitigation anında tek sefer hesaplandı (BUG 5).
6. **ORTA** — `simulate_rr_new` entry fiyatı gerçek trade modeline uygun hale getirildi (bullish=gap_bottom, bearish=gap_top) (BUG 6).
7. **HAFİF** — `_filter_swings` dict iterasyonu `.items()` ile O(N) yükü ve bar index karmaşası giderilerek optimize edildi (BUG 7).
8. **ORTA** — `detect_bos_mss` BOS/MSS tanımı, swing point sonrasındaki barların kapanışıyla kırılması formunda gerçeğe uygun hale getirildi (BUG 8).
9. **HAFİF** — `cumulative_mit_curve` DR threshold'unun sayı/yüzde birim uyumsuzluğu giderildi, sabit `%5` threshold kullanıldı (BUG 9).
10. **ORTA** — `detect_fvg_3candle` bar_index c2 yerine c3.index yapıldı (zamanlama kayması düzeltildi) (BUG 10).
11. **HAFİF** — `classify_c3` REJECTION tespiti çelişkili body_range_ratio koşullarından arındırılıp wick-dominant yapıldı (BUG 11).
12. **HAFİF** — `wilson_upper` 0 trade durumunda 1.0 yerine 0.0 döndürecek şekilde güncellendi (BUG 12).
13. **ORTA** — `resample_15m` timestamp slot yuvarlama/hizalama (00-15-30-45) mantığıyla yeniden yazılarak veri başlangıcındaki kaymaların session saatlerini bozması engellendi (BUG 13).
14. **HAFİF** — ATR warm-up başlangıcında `None` verilmesi yerine ilk TR değeriyle seed edilerek stabilite sağlandı (BUG 14).
15. **HAFİF** — `main()`'de tuple unpacking hata yönetimi tuple check'i ile sağlamlaştırıldı (BUG 15).

## Recently Completed
- **Phase 3 — 15 Kod/Mantık Hatası ve Bug Fix Serisi** (2026-07-08)
- **Phase 1 & Phase 2 Düzeltmeleri** (Look-ahead bias kaldırılması, expiry_bars veri akışı, Real Trade Bağlantısı, Sweep analizi).

## Active Decisions
- Derinlik verisi Section 10 ve 13'te post-hoc analiz olarak kalmaya devam ediyor.
- `cfg.GLOBAL_FVG_EXPIRY_BARS` global config'te trade kararları için set ediliyor, rapor okuması ise artık coin-bazlı.

## Next Actions
1. Tüm 15 bug düzeltmesinden sonra A/B testi veya backtest'i yeniden koşturup sonuçları doğrulamak.
2. V5 parametre izole testi.

## Open Questions
- Yeni düzeltmelerden sonra Section 0 WR/PF/PnL rakamlarındaki değişimler nasıl etkilendi?


