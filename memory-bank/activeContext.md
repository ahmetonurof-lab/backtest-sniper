# backtest-sniper — Active Context

## Current State
2026-07-10: Bug fix marathon revert + hizli load_data + ProcessPoolExecutor paralel. Config sniper/src/config.py'ye yerlesti. Pre-commit hooks kuruldu. analyze_cbdr_thresholds.py stratejisi analyzer_v5.py ile birebir ayni hale getirildi (next-bar entry, komisyon, BE, same-bar guard). Sezon/bucket wilson analizine hazir.

## Recently Completed
- **analyze_cbdr_thresholds.py V5 hizalamasi (2026-07-10):** threshold motoru V5 ile birebir ayni stratejiye oturtuldu. Degisenler: `MIN_REL_FVG_THRESHOLD` 0.50→0.40, next-bar-open entry (+ bounds guard), `entry_bar: sb+1`, SL cap `rd > rp2*2` kaldirildi, commission-based BE, komisyon PnL'den düsüldü, same-bar exit guard (continue), just_locked low>0 check.
- **get_fvg_status fix (2026-07-10):** `analyzer_v5.py` + `analyze_cbdr_thresholds.py` — INVALIDATED artık wick (high/low) değil **close** bazlı. Bearish: `close > top` → invalidate; Bullish: `close < bottom` → invalidate. ACTIVE_ENTRY_ZONE çift yönlü overlap: `bar.high >= bottom AND bar.low <= top`. BSL wick'i gap üstündeyken entry'nin INVALIDATED olması hatası düzeldi. Trade sayısı %48 arttı (34,366→51,034), net PnL 2.8x (+$248K→+$695K).
- **Komisyon modeli (2026-07-10):** analyzer_v5.py — SLIPPAGE kaldırıldı, %0.05 entry + %0.05 exit komisyon ayrı ayrı hesaplanıyor. Raporda Fee sütunu eklendi, PnL → net PnL olarak yeniden adlandırıldı. `COMMISSION_RATE=0.0005`, her leg ayrı hesaplanır.
- **BE komisyon bazlı (2026-07-10):** analyzer_v5.py — BE seviyesi BESP (fixed point) yerine `entry × (1 ± COMMISSION_RATE) / (1 ∓ COMMISSION_RATE)` formülüne çevrildi. BE tetiklendiğinde net PnL ≈ 0 olur.
- **FIX #1 (same-bar exit):** entry bloğunda `rsm.reset()` sonrası `continue` — entry barında trailing/exit engellendi.
- **FIX #3 (next-bar-open entry):** giriş `cur.close` yerine `next_bar.open`, `entry_bar = sb + 1`, bar boundary guard.
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
1. **ETH duzelt:** ya tamamen cikar ya FVG tetikleme sartlarini zorlastir
2. **VIP List:** Sharpe > 4.5 & MaxDD < %1 coin havuzu (OP, BNB, AAVE, ALGO, ADA, ARB)
3. **DD-bazli pozisyon:** dusuk DD coine daha buyuk pozisyon (BNB 3x ETH)
4. **FVG_SWEPT filtresi:** sadece sweep onay mumundan sonra isleme gir (WR/PF tavani)
5. **Pipeline:** ETH ayikla -> pozisyonu Sharpe'a gore optimize et
6. **FVG_SIZE_MAP:** futures ATR bazli hesapla (su an 0.0 placeholder)
7. **Canli bot testi:** guncel config ile paper trade baslat

## Notlar
- Tum veriler futures'tan indirildi (20 coin de hazir).
- `_analyze_all_20.py`, `analyze_cbdr_thresholds.py`, `analyzer_v5.py` — ayni motor + ayni strateji. Bug fix marathon sonrasi 3 dosyada da ayni 3 hata vardi, hepsi duzeltildi. Threshholds V5'e hizalandi (11b71f2).
- Gercek config `sniper/src/config.py`'de. `config_20.py` sadece test icin.
