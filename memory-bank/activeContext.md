# backtest-sniper — Active Context

## Current State
2026-07-10: Bug fix marathon revert — 3 degisiklik backtest sonucunu negatife cevirdigi tespit edildi ve geri alindi. Hizli load_data + resample_15m cache + ProcessPoolExecutor paralel isleme eklendi. 20 coin analizi ~6-8dk'ya dustu.

## Recently Completed
- **BUG 3 (fvg_close_confirmed) REVERT:** Full-scan trailing → early-return. Bug fix marathon'da `confirmed = True` flag + sonraki barlarda invalidation kontrolu yanlis calisiyordu, trailing stoplar tetiklenmiyor, WR %48→%15 dustu.
- **BUG 4 (stop-loss cap) REVERT:** FVG bazli SL 2xATR cap geri eklendi. Cap kalkinca risk distance buyuyor, pozisyon kuculuyor, QTY_ZERO artiyordu.
- **BUG 10 (sweep direction None) REVERT:** `continue` → `direction="bullish"` default. `None` yonunde tum bar atlaniyor, trade management kaciyordu.
- **BUG 5 (be_triggered flag):** KORUNDU — `trailing_count` → `be_triggered`, ayni is.
- **BUG 6 (PF cap 999.0):** KORUNDU — division-by-zero korumasi.
- **BUG 7 (MaxDD peak_balance):** KORUNDU — dogru hesaplama.
- **BUG 9 (Sharpe all-days):** KORUNDU — trade olmayan gun 0 PnL.
- **Hizli load_data:** csv.DictReader+strptime → csv.reader+calendar.timegm (24s/coin, ~4.5x faster).
- **resample_15m cache:** `@lru_cache` timestamp-bazli resample (2./3. session aninda).
- **Paralel isleme:** `_analyze_all_20.py` `--workers N` ile ProcessPoolExecutor (default 4). 4 coin × 2 worker = 151s.
- **collect_daily_data cache:** Adim 1 sonuclari Adim 2'de tekrar kullanilir (4. collect_daily_data cagrisi giderildi).

## Next Actions
1. **20 coin analizi:** `python _analyze_all_20.py --workers 4`
2. **Sonuclari degerlendir:** analyze_cbdr_thresholds.py referansiyla karsilastir.
3. **`sniper/src/config.py` guncelle:** SYMBOLS + CBDR_RISK_MATRIX + FVG_SIZE_MAP + weekend_bonus.

## Notlar
- Tum veriler futures'tan indirildi (20 coin de hazir).
- `_analyze_all_20.py`, `analyze_cbdr_thresholds.py`, `analyzer_v5.py` — ayni motor. Bug fix marathon sonrasi 3 dosyada da ayni 3 hata vardi, hepsi duzeltildi.
- Gercek config `sniper/src/config.py`'de. `config_20.py` sadece test icin.
