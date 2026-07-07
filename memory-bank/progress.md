# backtest-sniper — Progress

## ✅ Working
- V4 live-identical engine (analyzer_v4.py) — CBDR→Sweep→RSM→FVG→Entry→Trail→Exit
- V5 profil (fvg_profile_v5.py) — V4 motor + 16 bölümlü karakterizasyon + rapor
- V4 12-katman profil (fvg_profile_v4.py) — C2, BOS/MSS, depth, vol rejimi, bootstrap CI
- V4 bypass A/B test (fvg_profile_v4_bypass.py) — quality/validity/should_trade devre dışı
- V3 engine (sweep_full_v3.py) + analyzer_v3
- 3 session bazlı CBDR script (cbdr_default/real/asia)
- CBDR threshold analysis (analyze_cbdr_thresholds.py)
- FVG lifecycle analyzer (fvg_lifecycle_analyzer.py)
- FVG coin profile (fvg_coin_profile.py — 13 coin)
- MULT parametre taraması (mult_scan.py — 15 değer x 13 coin)
- Early London risk taraması (sweep_early_london.py — 6 değer x 13 coin)
- Portföy DD analizi (sweep_portfolio_dd.py — Calmar ratio, recovery günü)
- n<100 bucket normalize (normalize_cbdr_matrix.py)
- Per-coin session assignment (4 REAL_CBDR + 4 DEFAULT + 5 ASIA_RANGE)
- Per-coin CBDR risk matrisi (6 bucket x 13 coin, Wilson score bazlı)
- Parquet quant logger (buffer+flush, snappy compression)
- Risk manager (DD circuit breaker, filelock state)
- CBDR görselleştirme (matplotlib)

## 🔧 Pending / In Progress
- V5 tüm coinlerin bitmesi + rapor incelemesi
- BTC WR=%32.2 düşüklüğünün analizi (FVG_VALIDITY 55K red sebebi)
- V5 vs V4 bypass WR karşılaştırması

## 🐛 Known Issues
- BTC WR=%32.2 (V5) — düşük, FVG_VALIDITY 55K reddi araştırılmalı
- fvg_profile_v5.py de V4 motor kopyasını içeriyor — DRY ihlali (manuel sync)
- Cline / Goose MCACP ajanları çalışmıyor (söküldü)
- ASIA_RANGE coin'lerde EL 02-08 overlap: APT, AVAX, LINK, BNB, NEAR

## 📊 Backtest Results (13 coin, ~30 gün)
| Metric | V4 Orijinal (broken) | V4 Bypass | V5 (BTC preliminary) |
|---|---|---|---|
| BTC Trades | 419 | 2,678 | 698 |
| BTC WR | 40.3% | 40.8% | 32.2% |
| BTC PF | 3.39 | 3.51 | TBD |
| BTC PnL | +12,895 | +75,639 | TBD |
| BTC CBDR elenen | 3,214 (%81) | 11,357 | 906 gün |
| BTC FVG | — | — | 20,179 |

## 📐 CBDR Risk Matrix Summary
- **REAL_CBDR (4 coin):** BTC, ATOM, DOT, ETH
- **DEFAULT (4 coin):** ADA, SOL, SUI, XRP
- **ASIA_RANGE (5 coin):** APT, AVAX, BNB, LINK, NEAR
- **n<100 normalization:** BTC (0-1%, 5-999%), ATOM (0-1%, 1-1.5%, 5-999%), APT (0-1%), LINK (0-1%), ADA (1-1.5%) → all 1.0x
