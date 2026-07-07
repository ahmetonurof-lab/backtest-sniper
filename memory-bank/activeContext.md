# backtest-sniper — Active Context

## Current State
2026-07-08: V5 4 doğrulanmış bug fix uygulandı + simülasyon yeniden koşuldu:
1. **KRİTİK #1** — Derinlik look-ahead bias kaldırıldı (entry kararına karışmıyor)
2. **KRİTİK #2** — Section 16 Öneri mantığı `ci[0] > 0` ile düzeltildi (Section 7 ile tutarlı)
3. **ORTA** — Coin-bazlı `expiry_bars` veri akışına eklendi, Section 16'da coin'e göre doğru expiry gösteriliyor
4. **HAFİF** — `v4_rejected` atamaları "ilk red kazanır" mantığına çevrildi

## Recently Completed
- **V5 Bugfix serisi (4 madde):**
  1. **KRİTİK #1** — Derinlik filtresi (DEPTH_WICK/DEPTH_BODY) entry-karar bloğundan tamamen kaldırıldı. Artık look-ahead bias yok. Derinlik verisi sadece post-hoc profiling'de (Section 10, 13) kullanılıyor.
  2. **KRİTİK #2** — Section 16'daki `not (ci[1] < 0 or ci[0] > 0)` → `ci[0] > 0` (Section 7'deki düzeltmenin aynısı). `_EXPIRY_MAP` varsayılanı 45→5.
  3. **ORTA** — `expiry_used` değişkeni `_collect_fvg_profile_impl`'den dönen 7. değer olarak eklendi, `main()`'de `all_coin_data[sym]["expiry_bars"]` olarak saklanıyor, Section 16'da `cfg.GLOBAL_FVG_EXPIRY_BARS` yerine coin-bazlı değer okunuyor.
  4. **HAFİF** — MIN_RISK_DIST, CBDR_MULT_ZERO, SHOULD_TRADE_* atamaları `if classic_fvg.get("v4_rejected") is None:` koşuluna alındı.
- **Simülasyon:** `_v5_dump.pkl` silindi, 13 coin baştan koşuldu (1293sn), rapor yenilendi.

## Active Decisions
- Derinlik verisi Section 10 ve 13'te post-hoc analiz olarak kalmaya devam ediyor
- `cfg.GLOBAL_FVG_EXPIRY_BARS` hâlâ global config'te set ediliyor (trade kararları için), sadece rapor okuması coin-bazlı hale getirildi

## Next Actions
1. V5 parametre izole testi
2. Yeni Section 0 WR/PF/PnL rakamlarının öncekiyle karşılaştırması (derinlik filtresi kalkınca trade sayısı arttı mı?)

## Open Questions
- Derinlik filtresi kalkınca Section 0 rakamları değişti — bu beklenen ve doğru davranış
- V5'in üç parametresinden hangisi işe yarıyor?

