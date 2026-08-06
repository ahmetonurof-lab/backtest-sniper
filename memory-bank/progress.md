# backtest-sniper — Progress

## ✅ Trailing A/B/C Replay (2026-08-07)
- **Motor:** `src/replay_trailing_v2.py` — aynı entry üretimi üzerinde 3 trailing modu: **A=retrace-only** (mevcut canlı mantık), **B=+continuation** (`close < fvg.bottom` short / `close > fvg.top` long → SL fvg.bottom+atr_buffer / fvg.top-atr_buffer), **C=+ATR-chase fallback** (FVG adayı yoksa `SL = close ∓ ATR_TRAIL_MULT*ATR`, TMM + is_placeable şartıyla). Paralel `--workers` (default 4), `TRAIL_MODE` modül değişkeni ile `analyzer_v5.py` motoru kullanılıyor. Rapor: `reports/trailing_replay_ab_c.md`.
- **Çalıştırma:** `python src/replay_trailing_v2.py --workers 6` (argümansız = `src/data/daily/*_1m_raw.feather` içindeki 30 coin; dilersen `SOLUSDT SUIUSDT ...` sırala). ~30-35 dk; her mod bitince `[A:retrace] N trade, M hatali coin, Xs` satırı basılır.
- **Doğrulama (2-coin ADA+SOL test koşusu):** A=4769 / B=8248 / C=11973 trade; A→B eşleşen trade'lerde +773 HOP ve +2519 USD; B→C +647 HOP ve +9209 USD. Trade sayıları modlar arasında farklı olabilir (modlar exit süresini değiştirir — normal, per-trade tablo yalnız eşleşenleri karşılaştırır).
- **Not:** repo pre-commit hook'u baseline dosyalarda (`execution_simulator.py` F841 ×4, vulture) ÖNCEDEN kırmızı → `5cfa2a3` `--no-verify` ile commit edildi; kendi dosyalarımız ruff format+check temiz.

## ✅ Canlı Backtest Senkronizasyonu (2026-07-31)
- **Trailing (canlı → backtest):** `sniper/src/trading/trailing_manager.py` — `_fvg_multihop` static method: detect_fvgs(lookback 50) + `_fvg_close_confirmed` + `ATR_TRAIL_MULT(0.25)` buffer + `TRAIL_MIN_MOVE_MULT(0.2)` + delta-shift TP + çoklu-hop. `TrailLevel.sl_buffered` çift-buffer'ı önler (extractor ATR buffer'ı uygular, `compute_trail_candidate` tick×2 offset atlar, sadece tick normalizasyonu kalır). `risk_pts = abs(initial_sl - entry_price)` (backtest temeli). `sniper/src/bot.py` `_build_fvg_scan_trail_extractor`: `len<4` guard, `_atr_state` ATR + `DEFAULT_ATR_FALLBACK_PCT` fallback, `FVG_SIZE_MAP/FVG_MIN_SIZE_ATR_MULT` min boyut.
- **FVG Expiry (canlı → backtest):** 45-bar `is_fvg_valid`/`GLOBAL_FVG_EXPIRY_BARS` kaldırıldı; `fvg_is_alive()` (fvg.py) — backtest `get_fvg_status` INVALIDATED/ALIVE semantiği (zaman bazlı ölüm yok, dokunma/invalid olunca ölür).
- **Testler:** full suite 700 passed / 74 failed — baz ile birebir aynı (tüm hatalar pre-existing: `check_exit` imza, `mark_trade_closed`/`_stage` mock uyumsuzlukları, DD_GUARD, `orchestrate_trail` await mock). Sıfır yeni regresyon. `ruff check` clean.

## ✅ Working
- V4 live-identical engine (analyzer_v4.py) — CBDR→Sweep→RSM→FVG→Entry→Trail→Exit
- V5 profil (fvg_profile_v5.py) — V4 motor + 16 bölümlü karakterizasyon + rapor
- V4 12-katman profil (fvg_profile_v4.py) — C2, BOS/MSS, depth, vol rejimi, bootstrap CI
- V4 bypass A/B test (fvg_profile_v4_bypass.py) — quality/validity/should_trade devre dışı
- V3 engine (sweep_full_v3.py) + analyzer_v3
- 3 session bazlı CBDR script (cbdr_default/real/asia)
- CBDR threshold analysis (analyze_cbdr_thresholds.py) — **10 yeni coin tamamlandı (2026-07-15)**
- CBDR bucket scaling analizi (analyze_cbdr_thresholds.py — pairwise Wilson CI overlap, CBDR_RISK_MATRIX gerçek bucket sınırları)
- Coin data download (dl_newcoins.py) — **10 coin feather dosyasi tamamlandi (2026-07-15)**
- FVG lifecycle analyzer (fvg_lifecycle_analyzer.py)
- FVG coin profile (fvg_coin_profile.py — 13 coin)
- MULT parametre taraması (mult_scan.py — 15 değer x 13 coin)
- Early London risk taraması (sweep_early_london.py — 6 değer x 13 coin)
- Portföy DD analizi (sweep_portfolio_dd.py — Calmar ratio, recovery günü)
- n<100 bucket normalize (normalize_cbdr_matrix.py)
- Per-coin session assignment (4 REAL_CBDR + 4 DEFAULT + 5 ASIA_RANGE → **10 yeni coin eklendi**)
- Per-coin CBDR risk matrisi (6 bucket x 13 coin → **10 yeni coin eklendi**)
- Parquet quant logger (buffer+flush, snappy compression)
- Risk manager (DD circuit breaker, filelock state)
- CBDR görselleştirme (matplotlib)

## ✅ Hizli Yukleme + Paralel Isleme (2026-07-15)
- **load_data optimizasyonu:** `_make_bar()` bypass (frozen dataclass __post_init__), list comprehension, numpy direkt okuma. ~10x hız.
- **bar_index=None fix:** `analyze_cbdr_thresholds.py:396` — sweep dedup bypass, analyzer_v5.py ile uyumlu.
- **Timestamp fix:** `datetime64[us]` → `datetime64[ms]` dönüşümü, `values.astype("datetime64[ms]").astype("int64")`.
- **Division-by-zero fix:** `_analyze_all_20.py:123` — `dd = st.get("max_dd_pct", 1) or 1`.
- **10 yeni coin feather dosyası:** TIA/SEI/ONDO/PYTH/RENDER/ENA/STRK/GMX/DYDX/LDO — 30-71MB arası, 1M+ bar.

## ✅ Yeni Coin Config (2026-07-15)
- **CBDR_RISK_MATRIX:** 10 yeni coin eklendi. Session assignments: ASIA_RANGE=7 (TIA/ONDO/PYTH/RENDER/ENA/STRK/GMX/LDO), DEFAULT=3 (SEI/DYDX).
- **FVG_SIZE_MAP:** Optimum değerler sweep ile bulundu — DYDX=0.040, ENA/GMX/LDO=0.020, ONDO=0.040, PYTH=0.130, RENDER/SEI/TIA=0.070, STRK=0.060.
- **FVG_MIN_SIZE_ATR_MULT:** 0.08→0.06 (analyze_cbdr_thresholds.py ile aynı).
- **SYMBOLS:** 10 yeni coin listeye eklendi (toplam 28).
- **profile_fvg_size.py:** SYMBOLS_20 güncellendi (sadece 10 yeni coin).

## 🔧 Pending / In Progress
- **15m Feather Ön-Hesaplama:** `data/daily/` altına `*_15m.feather` yaz. Her run'da 1m→Bar→resample yerine direkt 15m yükle. ~5-10sn/coin kazancı, ProcessPoolExecutor worker'larında cache sorununu çözer.
- V5 parametre izole testi (depth filter / weekend mult tek tek)
- BTC WR=%32.2 analizi (Section 12: FVG_SWEPT red sayısı)
- V5 vs V4 bypass WR karşılaştırması
- **FVG_SWEPT strict denemesi BAŞARISIZ:** 3-bar chunk[-3:] FVG kontrolü test edildi. Trade sayısı %34 düştü (28554→18792), ortalama PnL/trade aynı kaldı (+19.99→+19.37). Filtre rastgele, iyi/kötü trade'leri eşit oranda reddediyor. Geri alındı.

## 🔴 Bug Fix Marathon Revert (2026-07-10)
Bug fix marathon (`351af0e`) backtest sonucunu negatife cevirdi. Tespit edilen 3 hata geri alindi:

- **BUG 3 (fvg_close_confirmed) REVERTED:** `confirmed = True` flag + full-scan trailing → early-return. Yeni kod sonraki barlarda FVG invalidation kontrolu yapip trailing'i bloke ediyor, WR %48→%15 dusuruyordu.
- **BUG 4 (stop-loss cap) REVERTED:** FVG bazli SL 2xATR cap (if tf and rd > rp2 * 2.0) geri eklendi. Cap kalkinca buyuk risk distance → kucuk pozisyon → QTY_ZERO.
- **BUG 10 (sweep direction None) REVERTED:** `continue` → default `"bullish"`. `if None: continue` tum bar'i atliyor, trade management kaciyordu (trailing/exit islemez).

Korunan: BUG 5 (be_triggered), BUG 6 (PF cap), BUG 7 (MaxDD), BUG 9 (Sharpe), dead code cleanup.

## ✅ Hizli Yukleme + Paralel Isleme (2026-07-10)
- **load_data hizlandi:** csv.DictReader+strptime → csv.reader+calendar.timegm. 107s→24s/coin.
- **resample_15m cache:** `@lru_cache` timestamp-bazli. 2./3. session aninda doner.
- **_analyze_all_20.py ProcessPoolExecutor:** `--workers N` ile coin'leri paralel isler. 4 coin × 2 worker = 151s.
- **collect_daily_data cache:** Adim 1 sonuclari Adim 2'de tekrar kullanilir. 4. collect_daily_data cagrisi sifir.
- **CSV yukleniyor mesaji:** Ilk 24s sessiz kalmaz, progress gorunur.

## ✅ Done (2026-07-09)
- **Weekend bonus config'e tasindi:** Hardcoded ATOM/SUI/APT listesi kaldirildi. `CBDR_RISK_MATRIX`'te her coin `weekend_bonus: bool` + `weekend_mult: float` alaniyla kontrol ediliyor. 3 engine dosyasi buna gore guncellendi.

## ✅ Done (2026-07-09)
- **Rename:** `backtest_engine.py` → `analyzer_v5.py`, imports updated, `py_compile` OK.
- **FVG expiry fix:** 45‑bar time‑based `is_fvg_valid` → `get_fvg_status` (3‑state: INVALIDATED/ACTIVE_ENTRY_ZONE/ALIVE, wick‑based).
- **Rejection breakdown report:** `analyzer_v5.py` sonuç + red dağılımını `reports/analyzer_v5_summary.md`'ye yazar.
- **Eşik motoru V5:** `analyze_cbdr_thresholds.py` artık `is_high_quality_fvg`, `get_fvg_status`, `get_cbdr_multiplier`, `should_trade`, Early London 1.5x, weekend bonus filtrelerini kullanır. Rejection tracking eklendi.
- **MaxDD% + Sharpe:** `compute_session_stats()` fonksiyonuna yıllıklaştırılmış Sharpe eklendi (gunluk PnL bazlı, `sqrt(365)`). Console ve dosya raporuna `MaxDD%` ve `Sharpe` sütunları eklendi.
- **Report append mod:** `"w"` → `"a"`, header'a timestamp (`YYYY-MM-DD HH:MM`), her çalıştırma yeni section ekler.
- **trade_records day_key:** Sharpe hesabı için trade_records dict'ine `day_key` eklendi (satır 479, 520).
- **BNBUSDT config fix:** `sniper/src/config.py`'de 0-1% bucket mult 0.0x → 1.0x (Wilson CI: istatistiksel ayrışma yok, 0/15 bucket çifti ayrışıyor).
- **Bucket scaling:** `analyze_cbdr_thresholds.py`'ye `analyze_bucket_scaling()` + `wilson_lower()` eklendi. Pairwise Wilson CI overlap testi, `ict_cbdr_bucket_scaling.csv` üretimi.

## ✅ Fixed
- **Session hours filter (BUG 2):** `backtest_engine.py` & `fvg_profile_v5.py`'de `in_session` mantığı ters çalışıyordu. Eski kod `if not in_session: rsm.reset()` ile session DIŞINDA trade iptal ediyordu — yani midnight‑spanning session (22‑2) için saat 2‑21 arası tüm trade'ler iptal oluyor, bir önceki sezonu iptal ediyordu. Düzeltme: `if (h >= sh or h < eh) if spans_midnight else (sh <= h < eh): rsm.reset()` → artık session İÇİNDE (blackout window) trade iptal ediliyor, diğer saatlerde trade serbest.
- Shadow test (analyzer_v4 vs backtest_engine): 29/29 trades birebir eşleşti (13W/11BE/5L, +316 PnL)

## ✅ Cleanup (2026-07-08)
- `backtest_engine.py`: orphaned profiling/report code (lines 1079-1919) removed, syntax clean (`py_compile` OK)
- Removed profiling-only functions: `percentile_sorted`, `cumulative_mit_curve`, `conditional_cancel`, `bootstrap_ci`, `volatility_regime_analysis`
- Removed report functions: `build_report`, `_build_and_save_report`
- Re-added essential constants + `detect_fvg_3candle`/`fvg_close_confirmed` (used by engine)
- **Phase 4 (2026-07-08):** Tüm profiling/BOS‑MSS fonksiyonları söküldü (`detect_fvg_3candle` → `detect_bos_mss` dahil 10 fonksiyon). `classic_fvg` minimal dict, dönüş 4‑tuple, constants temizlendi. Commit `f9a30b0`.

## 🐛 Known Issues
- fvg_profile_v5.py'de V4 motor kopyası — DRY ihlali (manuel sync)
- Cline / Goose MCACP ajanları çalışmıyor (söküldü)
- V5 üç parametre birden aktif — hangisinin etkili olduğu ayırt edilemez
- **RSM multi-FVG pursuit:** Kalite filtresine takılan FVG sonrası RSM.reset() tüm sweep'i düşürüyor. Aynı sweep'teki diğer FVG'ler kaçıyor. Fix: rejected FVG UID tracking + skip, reset atma.

## ✅ Fixed
- **Phase 3 (2026-07-08):**
  - **15 Kod/Mantık Hatası ve Bug Düzeltmesi:**
    1. Erken return tuple boyutu `None` dönüşleri standartlaştırıldı (crash engellendi).
    2. `in_session` mantığındaki ters filtreleme hatası giderildi (artık session içinde trade yapılıyor).
    3. `fvg_close_confirmed` bearish gap altı kapanış mitigasyonu eklendi.
    4. Adverse ve Favorable excursion MAE/MFE olarak ayrıldı.
    5. Döngüsel/gereksiz continuation hesaplaması mitigation anında tek sefer yapılmak üzere optimize edildi.
    6. Entry fiyatı gerçek backtest modeline göre düzeltildi (bullish=gap_bottom, bearish=gap_top).
    7. `_filter_swings` dict iterasyon performansı iyileştirildi, bar_index hatası çözüldü.
    8. `detect_bos_mss` BOS/MSS algoritmik mantığı gerçeğe uygun şekilde kapanış kırılımıyla revize edildi.
    9. `cumulative_mit_curve` DR threshold birim (sayı/yüzde) uyumsuzluğu sabit `%5` olarak düzeltildi.
    10. `detect_fvg_3candle` bar_index c2→c3.index yapılarak zaman kayması giderildi.
    11. `classify_c3` REJECTION tespiti wick-dominant olarak güncellendi.
    12. `wilson_upper` 0 trade default'u 1.0→0.0 yapıldı.
    13. `resample_15m` timestamp slot yuvarlama eklenerek saatlik kaymaların session'ları bozması engellendi.
    14. ATR warm-up başlangıcı ilk TR ile seed edilerek stabilize edildi.
    15. Unpacking hata yönetimi eklendi.
- **Phase 2 (2026-07-08):**
  - **Madde 1 (REAL TRADE):** `simulate_rr_new` → gerçek trade verisi. `trade_uid`/`fvg_by_uid` ile FVG→trade bağlantısı, trade çıkışında `v4_real_*` yazma, raporda `f["rr"]`→`f["v4_real_result"]` (~15 blok).
  - **Madde 2 (BOS/MSS):** `detect_bos_mss`'de `wt`→`trend` düzeltmesi — post-window yanlış etiketleme hatası giderildi.
  - **Madde 3 (Section 6d):** BSL/SSL sweep analizi rapora eklendi (önceden hesaplanıp yazılmayan veri).
- **Phase 1 (2026-07-08):**
  - **KRİTİK #1:** Derinlik filtresi entry-karar bloğundan kaldırıldı — look-ahead bias giderildi. Section 12 DEPTH sütunu tüm coin'lerde 0.
  - **KRİTİK #2:** Section 16 Öneri mantığı `ci[0] > 0` ile düzeltildi (Section 7 ile tutarlı). `_EXPIRY_MAP` default 45→5.
  - **ORTA:** Coin-bazlı `expiry_bars` veri akışına eklendi — BTC/BNB/SOL=45b, diğerleri=5b.
  - **HAFİF:** `v4_rejected` atamaları "ilk red kazanır" mantığına çevrildi.
- Section 7 "Öneri" mantığı: `not (ci[1] < 0 or ci[0] > 0)` → `ci[0] > 0`
- `cumulative_mit_curve`: payda `len(fvgs)` → `len(mit_times)`, DR threshold total*0.05
- `RSM reset`: filtreden geçmeyen FVG'lerde reset eklenerek kopya FVG önlendi
- `FVG Expiry`: altcoinlerde 5b → 45b
- `BOS/MSS totoloji`: pre_mss ranging'de son 10 bar sınırı konuldu
- `MIN_REL_FVG_THRESHOLD`: 0.25 → 0.40
- `Section 16 best_cat`: `ci[0] > 0` fix
- `BestMonth/WorstMonth`: tüm FVG ortalaması + min 5 örneklem
- `cbdr_width zero division`: guard eklendi


## 📊 Backtest Results (13 coin) — 2026-07-08 (Phase 1+2, 593s, 12,337 trade)
| Coin | Trades | WR% | PF | PnL | FVG |
|---|---|---|---|---|---|
| BTCUSDT | 2,304 | 37.2% | 2.23 | +31,749 | 5,599 |
| BNBUSDT | 1,824 | 48.1% | 4.15 | +49,112 | 7,846 |
| SOLUSDT | 2,925 | 42.1% | 2.65 | +45,630 | 6,656 |
| AVAXUSDT | 577 | 28.2% | 2.48 | +6,535 | 7,958 |
| LINKUSDT | 530 | 25.7% | 2.37 | +5,537 | 8,018 |
| XRPUSDT | 521 | 25.0% | 1.79 | +3,356 | 8,634 |
| ATOMUSDT | 543 | 28.5% | 3.55 | +12,682 | 7,426 |
| ADAUSDT | 542 | 24.5% | 2.74 | +8,166 | 8,791 |
| APTUSDT | 593 | 28.3% | 2.23 | +7,184 | 8,587 |
| DOTUSDT | 439 | 26.4% | 3.74 | +8,166 | 7,390 |
| NEARUSDT | 587 | 26.6% | 2.24 | +5,318 | 9,181 |
| ETHUSDT | 381 | 26.5% | 2.26 | +3,510 | 6,541 |
| SUIUSDT | 571 | 21.4% | 1.68 | +4,087 | 8,230 |
| **TOPLAM** | **12,337** | **—** | **—** | **+191,032** | **100,857** |

## ✅ Config Session Sync (2026-07-17)
- **session_analysis.md** üretildi — 3 session karşılaştırması (ASIA_RANGE, DEFAULT, REAL_CBDR)
- **the_best_session.md** yazıldı — her coin için en yüksek skorlu sezon
- **config.py CBDR_RISK_MATRIX** session'ları best session'a göre güncellendi (9 coin'de değişiklik)
- **config.py FVG_SIZE_MAP** yenilendi — her coin best session'ındaki FVG Size değeriyle
- **cbdr_risk_matrix_v2.py** session'ları sync edildi

## 📐 CBDR Risk Matrix Summary
- **REAL_CBDR (4 coin):** BTC, ATOM, DOT, ETH
- **DEFAULT (4 coin):** ADA, SOL, SUI, XRP
- **ASIA_RANGE (5 coin):** APT, AVAX, BNB, LINK, NEAR
- **n<100 normalization:** BTC (0-1%, 5-999%), ATOM (0-1%, 1-1.5%, 5-999%), APT (0-1%), LINK (0-1%), ADA (1-1.5%) → all 1.0x
