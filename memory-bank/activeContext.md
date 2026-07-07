# backtest-sniper — Active Context

## Current State
2026-07-07: V5 profiling script (`fvg_profile_v5.py`) yazıldı ve koşuluyor. V4'ün üstüne MIN_REL=0.25, depth filter, weekend mult, coin bazlı expiry, RSM reset iyileştirmesi eklendi. CBDR timestamp bug'ı `datetime64[ms]` cast ile düzeltildi.

## Recently Completed
- `fvg_profile_v5.py` oluşturuldu — V4 motor mantığı + 16 bölümlü profil raporu
- MIN_REL_FVG_THRESHOLD 0.50 → 0.25 indirildi (daha fazla FVG)
- Depth filtresi eklendi: WICK >%100, BODY >%150 RED
- Weekend mult: ATOM/SUI/APT için CBDR ×1.5 (Cmt-Paz)
- Coin bazlı FVG expiry: BTC/BNB/SOL 45b, diğerleri 5b
- RSM reset iyileştirmesi: kalite filtresinden geçmeyen FVG'lerde RSM resetlenmez
- Timestamp bug düzeltildi: `datetime64[ns] // 10**6` → `datetime64[ms]`
- V4 eski raporları temizlendi

## Active Decisions
- V5 = V4 motoru + karakterizasyon katmanı (import yok, kendi içinde kopya)
- CBDR debug çıktısı kaldırıldı (günler doğru akıyor)
- BTC WR=%32.2 — düşük, araştırılacak

## Next Actions
1. V5 raporu (`fvg_profile_v5.md`) incele — tüm coinler bitsin
2. BTC WR=%32.2 sebebini analiz et (FVG_VALIDITY 55K red?)
3. Gerekirse V5 ayarlarını tweak et

## Open Questions
- WR=%32.2 kabul edilebilir mi, yoksa bir bug mı?
- CBDR 906 gün doğru tespit ediliyor mu?
- RSM reset iyileştirmesi WR'ı yukarı mı çekecek?
