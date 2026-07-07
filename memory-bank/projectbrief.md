# backtest-sniper — Project Brief

## Core Mission
ICT/SMC tabanlı FVG + CBDR sweep stratejisinin, `sniper/` canlı botuyla birebir aynı V4 engine filtrelerini kullanarak geçmiş veri üzerinde backtest, analiz ve optimizasyonunu yapmak.

## Key Requirements
- 13 sembol: BTC, ETH, BNB, SOL, AVAX, LINK, XRP, ATOM, ADA, APT, DOT, NEAR, SUI
- 3 session: DEFAULT (22-02), REAL_CBDR (19-01), ASIA_RANGE (01-05)
- V4 live-identical engine: CBDR → Sweep → RSM → FVG Quality → Entry → Trailing → Exit → Retrade
- Coin bazlı CBDR risk matrisi (6 bucket x 3 session)
- Early London (02-08) risk çarpanı (1.5x)
- Parquet tabanlı quant logger
- 12 katmanlı FVG profili (C2, BOS/MSS, depth, vol rejimi, vb.)
- A/B test: bypass modu ile filtre etkisi karşılaştırması

## Scope
- **In:** Backtest motoru, FVG profili, CBDR risk matrisi, parametre taraması, portföy DD analizi, FVG lifecycle, görselleştirme
- **Out:** Canlı trade, order gönderme, paper trading, gerçek cüzdan yönetimi

## Architecture
`backtest-sniper/src/` → imports → `sniper/src/` (config, fvg, indicators, models, session, session_router, quant_logger, risk_manager)
