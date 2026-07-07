# backtest-sniper — Tech Context

## Technologies
- **Python** 3.12+
- **ccxt** — Binance veri indirme (1m OHLCV CSV)
- **pandas** — veri işleme, resample
- **numpy** — hesaplamalar
- **matplotlib** — CBDR görselleştirme
- **pyarrow / parquet** — quant_logger çıktı formatı
- **scipy** — bootstrap CI, Wilson score
- **ruff** — lint + format (pre-commit)
- **vulture** — dead code detection (pre-commit)
- **mypy** — type check (pre-commit)

## Project Structure
```
backtest-sniper/
├── src/
│   ├── analyzer_v4.py           # V4 live-identical engine
│   ├── fvg_profile_v4.py        # V4 12-katman profil (orijinal)
│   ├── fvg_profile_v4_bypass.py # V4 bypass (A/B test)
│   ├── analyzer_v3.py           # V3 engine
│   ├── sweep_full_v3.py         # V3 tum katmanlar
│   ├── fvg_coin_profile.py      # Per-coin FVG profil
│   ├── fvg_lifecycle_analyzer.py# FVG decay/sweep recovery
│   ├── analyze_cbdr_thresholds.py # CBDR genişlik analizi
│   ├── cbdr_default.py / cbdr_real.py / cbdr_asia.py  # Session bazlı CBDR
│   ├── risk_manager.py          # DD circuit breaker
│   ├── quant_logger.py          # Parquet logger
│   ├── mult_scan.py             # MULT parametre taraması
│   ├── normalize_cbdr_matrix.py # n<100 bucket normalize
│   ├── sweep_early_london.py    # EL risk çarpanı taraması
│   ├── sweep_portfolio_dd.py    # Portföy DD analizi
│   ├── generate_wilson_matrix.py# Wilson score matrisi
│   ├── utils/
│   │   ├── dl_fresh.py          # Veri indirme
│   │   ├── param_sweep.py       # min_fvg_size optimizasyonu
│   │   ├── check_sweeps.py      # Sweep doğrulama
│   │   ├── check_sweeps_fvg.py  # Sweep+FVG doğrulama
│   │   └── visualize_cbdr.py / visualize_cbdr_zoom.py  # Görselleştirme
│   ├── _run_btc.py / _run_btc2.py / _run_btc3.py # BTC test scriptleri
│   ├── _run_all.py              # 13 coin toplu koşu
│   └── _run_fvg_coin.py         # Coin profil koşusu
├── reports/                     # MD rapor, JSON, Parquet, CSV, PNG
├── docs/                        # strategy_flow.md, test_report.md
├── output/                      # trade_state.json
└── data/                        # 1m CSV veri dosyaları (git'te yok)
```

## Dependencies
`backtest-sniper`'ın kendi `requirements.txt`'si yok. Tüm bağımlılıklar `sniper/`'dan gelir:
- `sniper/src/` altındaki tüm modüller (config, fvg, indicators, models, session, session_router, quant_logger, risk_manager)
- Harici: ccxt, pandas, numpy, matplotlib, pyarrow, scipy, python-dotenv

## Environment
- `TESTNET_API_KEY` / `TESTNET_API_SECRET` — Binance Testnet (backtest için gerekli değil)
- `SNIPER_OUTPUT_DIR` — `backtest-sniper/output/` (env'de set edilir)
- Platform: Windows (cmd.exe), Python 3.12+

## Key Config Parameters (sniper/src/config.py)
| Param | Value | Açıklama |
|---|---|---|
| INITIAL_BALANCE | 10000.0 | Başlangıç bakiyesi |
| RISK_PER_TRADE | 0.003 | Risk/trade oranı |
| LEVERAGE | 5 | Kaldıraç |
| SL_ATR_MULT | 1.5 | Stop ATR çarpanı |
| TP_RR | 2.0 | Risk/Reward oranı |
| FVG_MIN_SIZE_ATR_MULT | 0.06 | Min FVG boyutu (ATR bazlı) |
| EARLY_LONDON_RISK_MULT | 1.5 | EL risk çarpanı |
| GLOBAL_FVG_EXPIRY_BARS | 45 | FVG zaman aşımı |
| CBDR_DEAD_THRESHOLD_PCT | 0.5 | CBDR dead zone |
| ATR_TRAIL_MULT | 0.25 | Trailing ATR çarpanı |
| MIN_RISK_DIST_ATR_MULT | 0.1 | Min risk mesafesi |
| FVG_WICK_RATIO_MAX | 0.75 | Max wick/body oranı |
