# backtest-sniper — Active Context

## Current State
2026-07-07 14:09: V5 profil raporu (`fvg_profile_v5.md`) 13 coin × 16 bölüm tamamlandı — 64KB, 1064 satır.

## Recently Completed
- `fvg_profile_v5.py` — V4 motor + 16 bölümlü profil raporu (script hazır)
- 2 bug fix: `volatility_regime_analysis(cf, b15)` → `(cf, atr_vals)`; `return "\n".join(lines)` → `_lines_for_size`
- Pickle emergency dump mekanizması (`_v5_dump.pkl`, 222MB) + `--report-only` flag
- Full sim 315s'te 13 coin koştu, rapor başarıyla yazıldı

## Active Decisions
- V5 üç parametreyi aynı anda açar (_EXPIRY_MAP, depth filter, weekend mult) — izole test yok
- NameError (`lines` → `_lines_for_size`) build_report'u yarım bırakıyordu, düzeltildi

## Next Actions
1. V5 parametrelerini tek tek izole test et (CBDR/MULT taramaları gibi)
2. BTC WR=%32.2 analizi — Section 12'de FVG_VALIDITY red=9048 en büyük eleyen
3. Gerekirse V5 ayarlarını tweak et

## Open Questions
- WR=%32.2 kabul edilebilir mi, yoksa bir bug mı?
- V5'in üç parametresinden hangisi işe yarıyor?
- N_BOOTSTRAP=100, Section 13-16 bootstrap yavaş mı?

