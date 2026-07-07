# backtest-sniper — Product Context

## Why This Project Exists
- `sniper/` canlı botu ICT/SMC konseptlerini otonom uygular; backtest-sniper bu stratejinin geçmiş veride doğrulanmasını sağlar
- V4 engine filtrelerinin (FVG quality, validity, should_trade, CBDR multiplier) her birinin PnL/DD etkisini izole etmek
- 13 coin için per-coin optimal parametreleri bulmak (FVG_MIN_SIZE_ATR_MULT, CBDR bucket çarpanları, EL risk mult)
- İstatistiksel anlamlılık: Wilson score, bootstrap CI ile küçük örneklem bucket'larının normalize edilmesi

## Problems It Solves
- Canlı botda hangi FVG filtrelerinin gerçekten edge sağladığının kanıtlanması
- n<100 bucket'ların (istatistiksel olarak anlamlı olmayan) 0.0x zehirli etiketinden kurtarılması
- Session bazlı CBDR genişliklerinin trade sonucuna etkisinin ölçülmesi
- Early London 1.5x çarpanının diğer session bucket'larıyla etkileşiminin test edilmesi
- Parametre değişikliklerinin portföy genel DD etkisinin hesaplanması

## How It Works
1. 1m OHLCV CSV → 15m resample → CBDR tracking (günlük)
2. CBDR locked → Sweep detection → RSM state machine
3. FVG scan (lookback=100) → Wick rejection → TRIGGER_READY
4. FVG quality (HTF teyit) + Validity (gap/ATR) + Should trade (RR, risk dist)
5. CBDR multiplier (0.0-1.5x) + Early London mult (1.5x) → entry
6. Trailing SL/TP (FVG buffer bazlı) → exit → retrade (max 2/gün)
7. 12 katmanlı analiz + Parquet trade log + MD rapor

## Key Design Decisions
- `analyzer_v4.py` canlı-özdeş engine (SessionState + RSM + RiskManager)
- `fvg_profile_v4.py` ek 12 analiz katmanı ekler (engine'i sarmaz, filtreleri aynen kullanır)
- `fvg_profile_v4_bypass.py` A/B test: FVG_QUALITY/FVG_VALIDITY/SHOULD_TRADE devre dışı
- `normalize_cbdr_matrix.py` n<100 bucket'ları 1.0x'e çeker, config.py'yi otomatik günceller
- `sniper/src/config.py` tek kaynak (DRY); backtest-sniper'ın kendi config'i yok
