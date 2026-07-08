# backtest-sniper — Active Context

## Current State
2026-07-09: `backtest_engine.py` → `analyzer_v5.py` rename. FVG expiry time‑based → sweep‑based (`is_fvg_alive`).

## Recently Completed
- **Rename (2026-07-09):** `backtest_engine.py` → `analyzer_v5.py` (git mv), imports in `bos_analysis.py` & `shadow_test.py` updated.
- **FVG expiry rule (2026-07-09):** Eski `is_fvg_valid(bar_index, cur_index)` — 45 bar time‑based expiry kalktı. Yerine `is_fvg_alive(top, bottom, b15, fvg_b15_idx, cur_b15_idx)` — fiyatın high/low ile FVG gap'ine girip girmediğini kontrol eder. `cfg.GLOBAL_FVG_EXPIRY_BARS` satırı da kaldırıldı.

## Active Decisions
- `analyzer_v5.py` artık `analyzer_v4.py`'den farklı: FVG expiry fitil‑based, time‑based değil.

## Next Actions
1. Koştur, sonuçları kontrol et.

## Open Questions
- (none)


