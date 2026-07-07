# backtest-sniper — Active Context

## Current State
2026-07-08: V5 Phase 1 (4 bug fix) + Phase 2 (3 yeni fix) uygulandı.

**Phase 1 — 4 Doğrulanmış Bug Fix:**
1. **KRİTİK #1** — Derinlik look-ahead bias kaldırıldı (entry kararına karışmıyor)
2. **KRİTİK #2** — Section 16 Öneri mantığı `ci[0] > 0` ile düzeltildi (Section 7 ile tutarlı)
3. **ORTA** — Coin-bazlı `expiry_bars` veri akışına eklendi, Section 16'da coin'e göre doğru expiry gösteriliyor
4. **HAFİF** — `v4_rejected` atamaları "ilk red kazanır" mantığına çevrildi

**Phase 2 — 3 Yeni Fix:**
1. **Madde 1** — `simulate_rr_new` → gerçek trade sonuçları: `trade_uid` ile FVG→trade bağlantısı, `fvg_by_uid` dict, trade çıkışında `v4_real_result/v4_real_pnl_usd/v4_real_pnl_R/v4_real_hit_target/v4_real_hit_stop` yazma, raporda `f["rr"]` yerine `v4_real_*` kullanımı (~15 kod bloğu)
2. **Madde 2** — `detect_bos_mss`'de post-window yanlış etiketlenme hatası: `wt` (inverted trend) yerine `trend` kullanıldı
3. **Madde 3** — Section 6d: BSL/SSL sweep analizi eklendi (önceden hesaplanan `swept_high`/`swept_low` verisi rapora yazılmıyordu)

## Recently Completed
- **Phase 1 — V5 Bugfix serisi (4 madde):**
  1. **KRİTİK #1** — Derinlik filtresi (DEPTH_WICK/DEPTH_BODY) entry-karar bloğundan tamamen kaldırıldı. Artık look-ahead bias yok. Derinlik verisi sadece post-hoc profiling'de (Section 10, 13) kullanılıyor.
  2. **KRİTİK #2** — Section 16'daki `not (ci[1] < 0 or ci[0] > 0)` → `ci[0] > 0` (Section 7'deki düzeltmenin aynısı). `_EXPIRY_MAP` varsayılanı 45→5.
  3. **ORTA** — `expiry_used` değişkeni `_collect_fvg_profile_impl`'den dönen 7. değer olarak eklendi, `main()`'de `all_coin_data[sym]["expiry_bars"]` olarak saklanıyor, Section 16'da `cfg.GLOBAL_FVG_EXPIRY_BARS` yerine coin-bazlı değer okunuyor.
  4. **HAFİF** — MIN_RISK_DIST, CBDR_MULT_ZERO, SHOULD_TRADE_* atamaları `if classic_fvg.get("v4_rejected") is None:` koşuluna alındı.
- **Simülasyon (Phase 1):** `_v5_dump.pkl` silindi, 13 coin baştan koşuldu (1293sn), rapor yenilendi.
- **Phase 2 — 3 Yeni Fix:**
  1. **Madde 1 (REAL TRADE BAĞLANTISI):** `captured_fvgs` sözlüğüne `fvg_by_uid = {}` eklendi. Entry'de `trade_uid = f"{symbol}_{sb}_{side}"` ile FVG→trade bağlantısı kuruldu. Trade çıkışında `v4_real_result/v4_real_pnl_usd/v4_real_pnl_R/v4_real_hit_target/v4_real_hit_stop` alanları `fvg_by_uid[trade_uid]` üzerinden güncellendi. Raporun ~15 farklı bloğunda (Section 1,5,6,6c,7,8,9c,10,14,15a,15b,16, volatility_regime_analysis) `f["rr"]` yerine `f["v4_real_result"]` kullanıldı.
  2. **Madde 2 (BOS/MSS FIX):** `detect_bos_mss` fonksiyonunda post-window etiketlemesi `wt` (inverted trend) yerine `trend` kullanılarak düzeltildi — expansion FVG'ler MSS_ONLY yerine doğru etiketleniyor.
  3. **Madde 3 (Section 6d SWEEP):** `_collect_fvg_profile_impl`'de hesaplanan `swept_high`/`swept_low` verisi artık `build_report`'ta Section 6d olarak raporlanıyor (SWEPT_HIGH/SWEPT_LOW/NO_SWEEP × kategori analizi).
- **Simülasyon (Phase 2):** `_v5_dump.pkl` silindi, 13 coin baştan koşuldu (593sn), rapor yenilendi.

## Active Decisions
- Derinlik verisi Section 10 ve 13'te post-hoc analiz olarak kalmaya devam ediyor
- `cfg.GLOBAL_FVG_EXPIRY_BARS` hâlâ global config'te set ediliyor (trade kararları için), sadece rapor okuması coin-bazlı hale getirildi

## Next Actions
1. V5 parametre izole testi
2. Yeni Section 0 WR/PF/PnL rakamlarının öncekiyle karşılaştırması (derinlik filtresi kalkınca trade sayısı arttı mı?)

## Open Questions
- Derinlik filtresi kalkınca Section 0 rakamları değişti — bu beklenen ve doğru davranış
- V5'in üç parametresinden hangisi işe yarıyor?

