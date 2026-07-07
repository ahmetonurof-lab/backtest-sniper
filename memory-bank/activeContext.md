# backtest-sniper — Active Context

## Current State
2026-07-07: FVG v4 bypass A/B test tamamlandı. n<100 normalizasyon regresyonu düzeltildi (sniper repo). Fixed versiyon backtest koşuluyor.

## Recently Completed
- FVG v4 bypass A/B test raporları (`fvg_profile_v4.md` + `fvg_profile_v4_bypass.md`)
- n<100 normalizasyonu geri getirildi (sniper: 2e29624, 5 coin / 8 bucket)
- MCACP ajanlar (Cline, Goose) söküldü — çalışmıyorlar
- `memory-bank/` oluşturuldu

## Active Decisions
- CBDR_RISK_MATRIX artık n<100 bucket'lar 1.0x (normalize)
- FVG bypass testi: kalite/validity filtreleri olmadan sistem %40 WR'ı koruyor
- Pending: fixed versiyon backtest sonucunun Section 12 analizi

## Next Actions
1. Fixed versiyon raporu terminalden al (kullanıcı koşuyor)
2. Section 12: CBDR/SHOULD_TRADE sütunundaki düşüşü teyit et
3. Gerekirse normalize_cbdr_matrix.py'yi tekrar çalıştır

## Open Questions
- bypass WR=%40.8 vs fixed WR=%38.0 — fark anlamlı mı?
- CBDR_MULT_ZERO'daki düşüş beklenen seviyede mi?
- EL 1.5x çarpanı ASIA_RANGE coin'lerde (APT, AVAX, LINK, BNB) doğru çalışıyor mu?
