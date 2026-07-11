# backtest-sniper — Active Context

## Current State
2026-07-11: Production reporting upgrade completed. Exit tracking: SL→LOSS/PROFIT_TRAIL. Sharpe: trade-return based (non-annualized). New summary columns: TP%, PTrail%, Loss%, Score, PnL/Fee, FVGCr. Score = (Sharpe × PF × PositiveExit%) / (1 + MaxDD%). Removed obsolete: WIN/BE/LOSS/WR%/BE+%.

## Recently Completed
- **Production Reporting (2026-07-11):** `analyzer_v5.py` reporting system updated per NEXUS specs:
  - Exit tracking: `SL` → `LOSS` / `PROFIT_TRAIL` (trailing_count > 0 & SL past entry = profitable trail)
  - Sharpe: daily-PnL annualized → trade-return based (`pnl / risk_usd`), non-annualized, RFR=0
  - New columns: `TP%`, `PTrail%`, `Loss%`, `PF`, `Sharpe`, `MaxDD%`, `Fee`, `NetPnL`, `PnL/Fee`, `FVGCr`, `FVGEnt`, `MinRisk`, `Score`
  - Removed: `WIN`, `BE`, `LOSS`, `WR%`, `BE+%`, individual rejection columns
  - Score = (Sharpe × PF × PositiveExit%) / (1 + MaxDD%) — No PnL in score, only ratios
  - `risk_usd` added to `trade_records` for Sharpe computation
- **2x2 Config Matrix Analysis (2026-07-11):** `reports/config_vs_analysis.md` — 3 runs compared (config2+0.40, config3+0.40, config3+0.50). config2+0.50 run pending.
- **Logic Drift Fixes (2026-07-11):** bar_index=sb, MIN_REL_FVG_THRESHOLD=0.50 her yerde, CBDR_RISK_MATRIX canliya aktarildi, BE canlidan kaldirildi.

## Next Actions
1. **config2+0.50 run** (Run D) — 2x2 matrisi tamamla
2. **Canli bot testi:** guncel config + BE'siz trailing ile paper trade baslat
3. **ETH duzelt:** ya tamamen cikar ya FVG tetikleme sartlarini zorlastir
4. **VIP List build:** Score/Sharpe bazli coin siralamasi
5. **FVG_SIZE_MAP:** futures ATR bazli hesapla

## Notlar
- Config.py su anda config2 (muhafazakar) degerlerinde (git commit hali). config3 matrix commitlenmedi.
- Dynamic scoring artık PnL içermiyor, sadece oran bazlı (Sharpe × PF × PositiveExit% / (1+MaxDD%)).
- Rapor dosyasi append modunda yaziyor, tum gecmis run'lar saklaniyor.
