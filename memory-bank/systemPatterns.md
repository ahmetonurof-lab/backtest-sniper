# backtest-sniper — System Patterns

## Architecture
```
backtest-sniper/src/ → imports → sniper/src/
                                    ├── config.py        (semboller, CBDR_RISK_MATRIX, parametreler)
                                    ├── fvg.py           (detect_fvgs)
                                    ├── indicators.py    (ATR)
                                    ├── models.py        (Bar, ATR_PERIOD)
                                    ├── session.py       (DailyBias, SessionState, detect_phase)
                                    ├── session_router.py (get_cbdr_multiplier, should_trade, is_high_quality_fvg, is_fvg_valid, get_session_hours)
                                    ├── quant_logger.py  (Parquet logger)
                                    └── risk_manager.py  (DD circuit breaker, EL mult)
```

## Core Engines

### analyzer_v4.py — V4 Backtest Engine (764 satır)
- `collect_daily_data(symbol)` → veri yükle, session başlat
- Main loop: CBDR track → Sweep → RSM → FVG → Entry → Trail → Retrade
- `SessionState`: CBDR takip, sweep confirmation
- `RetraceStateMachine`: IDLE → SWEEP_DETECTED → TRIGGER_READY
- `RiskManager`: DD devre kesici, EL risk çarpanı
- `quant_logger`: trade kaydı, buffer → Parquet

### fvg_profile_v4.py — V4 Profil Engine (1889 satır)
- Aynı filtreler + 12 analiz katmanı
- `collect_fvg_profile(symbol)`: coin bazlı profil
- `main()`: 13 coin, MD rapor
- 12 katman: C2 anatomy, BOS/MSS, depth/wick-body, gap/ATR, vol rejimi, coin istatistik, DOW, bootstrap CI, continuation windows, FVG outcome, R-multiple, V4 rejection breakdown

## Data Flow
```
1m CSV → 15m Resample → Daily Loop:
  ├── CBDR Tracking (22-02 / 19-01 / 01-05)
  ├── CBDR Locked @ session.end
  ├── Sweep Detection (cbdr_body_high/low +/- tol)
  ├── RSM.on_sweep() → IDLE → SWEEP_DETECTED
  ├── FVG Scan (lookback=100)
  │   ├── Wick Rejection (wick dokundu, body kırmadı)
  │   ├── FVG Quality (HTF context, is_high_quality_fvg)
  │   ├── FVG Validity (gap/ATR ratio, is_fvg_valid)
  │   └── Should Trade (RR > 1.5, min_risk_dist)
  ├── CBDR Multiplier (get_cbdr_multiplier)
  ├── Entry (SL/TP hesapla, qty)
  ├── Trailing (FVG buffer, ATR mult)
  ├── Exit (SL/BE/SL2/TP)
  └── Retrade (max 2/gün)
```

## Design Patterns
- **State Machine**: RSM (3 state), SessionState (CBDR lifecycle)
- **Strategy**: Her coin ayrı session + bucket konfigürasyonu
- **Singleton**: config.py (tek kaynak)
- **Observer**: Session → RSM → FVG → Entry pipeline
- **Buffer/Flush**: quant_logger (trade buffer → Parquet)

## Rejection Breakdown (V4)
```
Toplam FVG
  ├── FVG_QUALITY: HTF teyit yoksa elendi
  ├── FVG_VALIDITY: gap/ATR oranı yetersizse elendi
  ├── MIN_RISK: risk mesafesi çok küçükse elendi
  ├── CBDR/SHOULD_TRADE: CBDR multiplier 0.0x veya RR<1.5
  └── ENTERED: trade açıldı
```
