# backtest-sniper — Active Context

## Current State
2026-07-10: Bug fix marathon revert + hizli load_data + ProcessPoolExecutor paralel. Config sniper/src/config.py'ye yerlesti. Pre-commit hooks kuruldu. analyzer_v5.py da paralel calisiyor.

## Recently Completed
- **BUG 3 REVERT:** fvg_close_confirmed early-return. WR %48→%15 hatasi duzeldi.
- **BUG 4 REVERT:** Stop-loss cap (2xATR) geri. QTY_ZERO dustu.
- **BUG 10 REVERT:** sweep_direction None → "bullish" default.
- **Korunan:** be_triggered, PF cap 999.0, MaxDD peak_balance, Sharpe all-days.
- **auto_multiplier:** analizecbdr_thresholds.py'de tek merkez, _analyze_all_20.py onu cagiriyor.
- **Hizli load_data:** csv.DictReader→csv.reader+calendar.timegm (24s/coin).
- **resample_15m cache:** @lru_cache.
- **Paralel:** `_analyze_all_20.py --workers N` (default 4), `analyzer_v5.py --workers N`.
- **Config:** 20 coin SYMBOLS+CBDR_RISK_MATRIX+FVG_SIZE_MAP sniper/src/config.py'ye yerlesti.
- **Pre-commit:** ruff, vulture, mypy, whitespace kuruldu.
- **collect_daily_data cache:** Adim 1→Adim 2, 4. cagri yok.

## Next Actions
1. **FVG_SIZE_MAP:** futures ATR bazli hesapla (su an 0.0 placeholder)
2. **Canli bot testi:** guncel config ile paper trade baslat

## Notlar
- Tum veriler futures'tan indirildi (20 coin de hazir).
- `_analyze_all_20.py`, `analyze_cbdr_thresholds.py`, `analyzer_v5.py` — ayni motor. Bug fix marathon sonrasi 3 dosyada da ayni 3 hata vardi, hepsi duzeltildi.
- Gercek config `sniper/src/config.py`'de. `config_20.py` sadece test icin.
