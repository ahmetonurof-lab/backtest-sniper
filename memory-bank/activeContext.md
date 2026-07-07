# backtest-sniper — Active Context

## Current State
2026-07-07: V5 Section 7 Öneri bug fix — `not (ci[1] < 0 or ci[0] > 0)` → `ci[0] > 0`. Raporda Section 7 artık Section 8 ile tutarlı: sadece tüm CI sıfırın üstündeyken kategori öneriyor.

## Recently Completed
- Bug fix: `fvg_profile_v5.py:1407` — Section 7 "Öneri" mantığı tersti (sıfır CI içindeyken seçiyordu, anlamlı pozitif/negatif edge'leri atlıyordu → tüm coinler BELIRSIZ çıkıyordu)

## Active Decisions
- `ci[0] > 0` ile düzeltme: sadece alt CI sınırı sıfırın üstündeyse (anlamlı pozitif) kategori öner

## Next Actions
1. Raporu terminalden yeniden koşup doğrula
2. V5 parametre izole testi
3. BTC WR=%32.2 analizi

## Open Questions
- WR=%32.2 kabul edilebilir mi, yoksa bir bug mı?
- V5'in üç parametresinden hangisi işe yarıyor?

