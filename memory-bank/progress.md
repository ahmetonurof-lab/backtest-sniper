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
- V5 parametre izole testi (_EXPIRY_MAP / depth filter / weekend mult tek tek)
- BTC WR=%32.2 analizi (Section 12: FVG_VALIDITY red=9048)
- V5 vs V4 bypass WR karşılaştırması

## 🐛 Known Issues
- BTC WR=%32.2 (V5) — düşük, Section 12'de FVG_VALIDITY red=9048 en büyük eleyen
- fvg_profile_v5.py'de V4 motor kopyası — DRY ihlali (manuel sync)
- Cline / Goose MCACP ajanları çalışmıyor (söküldü)
- V5 üç parametre birden aktif — hangisinin etkili olduğu ayırt edilemez

## 📊 Backtest Results (13 coin, ~30 gün)
| Metric | V4 Orijinal (broken) | V4 Bypass | V5 (13 coin) |
|---|---|---|---|
| BTC Trades | 419 | 2,678 | 698 |
| BTC WR | 40.3% | 40.8% | 32.2% |
| BTC PnL | +12,895 | +75,639 | +9,842 |
| BTC FVG | — | — | 20,179 (FVG_VALIDITY red=9,048)
| BNB WR | — | — | 46.6% |
| SOL WR | — | — | 38.6% |
| ETH WR | — | — | 40.8% |
| Toplam Trade | — | — | 2,658 (13 coin) |

## 📐 CBDR Risk Matrix Summary
- **REAL_CBDR (4 coin):** BTC, ATOM, DOT, ETH
- **DEFAULT (4 coin):** ADA, SOL, SUI, XRP
- **ASIA_RANGE (5 coin):** APT, AVAX, BNB, LINK, NEAR
- **n<100 normalization:** BTC (0-1%, 5-999%), ATOM (0-1%, 1-1.5%, 5-999%), APT (0-1%), LINK (0-1%), ADA (1-1.5%) → all 1.0x
