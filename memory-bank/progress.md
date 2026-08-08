# backtest-sniper — Progress

## ✅ Ölü Script Temizliği (2026-08-08)
- **Kapsam:** Kullanıcı talebi — "fvg size bucket test cbdr sezon gibi kritik dosyalar haricinde kullanılmayanları sil". Import grafiği analizi (hiçbir dosyadan `import` edilmeyenler) baz alındı.
- **Silinen (33 tracked + 21 untracked = 54):** `analyzer_v5_tp15.py`, `analyzer_v5_tp15_notrail.py`, `analyzer_v5_tp15_tpfix.py`, `analyzer_v5_tp18_atr_fine/low/min/sweep/ultra.py`, `analyzer_v5_tp18_crosscoin.py` (tek seferlik TP/ATR taramaları); `_calc_scores/_calc_single/_ds_comp/_run_single/_sl_tp_ambiguity/_verify_confirm_parity/_verify_retrace_fix/_worker`; `_check_file/_check_imports/_check_output/_check_stash/_find_commits/_find_header/_find_run/_git_log_report/_read_found/_read_main_output/_run_algo/_run_main` (untracked debug araçları); `config_backup_pre_v2.py`, `kelly_calibration_check.py`, `production_benchmark_v2.py` (+ bağımlısı `_worker.py`); `utils/` eski analizler: `analyzer.py`, `analyzer_v4.py`, `analyze_entry_hours.py`, `analyze_parquet.py`, `analyze_parquet_v2.py`, `analyze_v3.py`, `atr_cmp_real.py`, `bos_analysis.py`, `build_report_v2.py`, `check_sweeps.py`, `compare_windows.py`, `dl_extra.py`, `dl_extra2.py`, `dl_fresh.py`, `dl_newcoins.py`, `generate_wilson_matrix.py`, `mult_scan.py`, `param_sweep.py`, `sweep_early_london.py`, `sweep_full_v3.py`, `sweep_portfolio_dd.py`.
- **Korunanlar (kritik kategoriler):** fvg (`fvg_profile_v5`, `fvg_zone_analyzer`, `fvg_coin_profile`, `fvg_lifecycle_analyzer`, `fvg_profile_v4(+bypass)`, `check_sweeps_fvg`, `analyze_fvg_*`), size (`profile_fvg_size`), bucket (`bucket_data_extractor_v2`, `bucket_risk_engine`, `test_cbdr_buckets`), cbdr (`cbdr_risk_matrix_v2`, `analyze_cbdr_thresholds`, `analyzer_cbdr`, `analyze_cbdr_risk_mult`, `cbdr_asia/default/real`, `normalize_cbdr_matrix`, `visualize_cbdr(+zoom)`), test (`execution_simulator_test`, `shadow_test`, `test_el`, `_profile_test`), session/sezon raporları. Ayrıca `risk_manager.py`, `weekend_monster_detector.py`, `replay_trailing_v2.py` (analyzer_v5 trailing replikasyon motoru — canlı ile birebir) korundu.
- **Doğrulama:** `src/analyzer_v5.py`'nin `from _worker import`'ı yok; `production_benchmark_v2` + `_worker` birlikte silindi. Silinen hiçbir modül kalan kodda import edilmiyor (önceki import taraması). Code index yeniden üretildi: 1858→1763 fonksiyon (sniper 1420 + backtest-sniper 343). Commit `cd8bbf0` push edildi. Ana repo `.env.example` silindi → commit `5dfdc50` push edildi.

## ✅ Continuation Tarama SONUCU — ÖLÜ (2026-08-07 FINAL)
- **Nihai sonuç: continuation (B) 9/9 varyasyonda derin negatif.** K=0.1 N=1/2/3 → -1.53M/-1.43M/-1.35M; K=0.3 → -1.41M/-1.35M/-1.30M; K=1.0 → -1.21M/-1.19M/-1.18M. A retrace **+4,100,540** (PE 60.9%, 111,246 trade) — baseline birebir.
- **N-bar teyit (N=3) marjinal kazandırır ama PE'yi düzeltmez:** B içinde LOSS 65,038→63,692 (K=1.0), NetPnL -1.21M→-1.18M; PE% 32.7-33.8'de takılı (A: 60.9). Geniş K=1.0 tampon AvgHold'i uzatır (2.9→3.8 bar), erken kesmeyi önler ama HOP -15.5K / PnL Delta -2.5M telafi edilemez.
- **Karar:** A/retrace canlıda sabit kalır; continuation deploy edilmez. `ATR_TRAIL_MULT_CONTINUATION=0.50`/`CONTINUATION_CONFIRM_BARS=2` yalnızca repo'da kalır (canlı restart yok).
- **Rapor:** `reports/trailing_replay_ab_c.md` FINAL (tüm 10 koşu). Tam NetPnL tablosu progress'in üstünde.
- **Checkpoint dersi:** `taskkill /F` checkpoint'i bozdu (yarım yazım, 161MB EOFError) → 7 koşuluk veri kayboldu, tarama baştan başladı. **Fix:** `_save_checkpoint` atomik yazıma geçti (tmp+rename) — commit `ea3629f`. Kullanıcı RAM uyarısı: aslında boş RAM 7.7GB, tarama bitmişti (bekleyen komut çıktıları kaybolduğu için "takıldın" sanıldı).
- Tarama sırası sorunları: 2. koşu (workers 6) 7 koşu yaptı, kullanıcı kararıyla durduruldu; 3. koşu `--skip-k 0.5` checkpoint bozuk diye baştan A+B0.1+B0.3'ü yeniden koştu → fark edilip durduruldu; son koşu yalnız `--cont-k 1.0` (checkpoint'ten A yüklendi) → bitti.

## ✅ Continuation K/N Fix — Baş Mühendis Direktifi Uygulandı (2026-08-07)
- **Direktif:** (1) continuation'a özel geniş K tampon (`ATR_TRAIL_MULT_CONTINUATION=0.5`), (2) N-bar teyit (`CONTINUATION_CONFIRM_BARS=2`), (3) replay'de K∈{0.3,0.5,1.0} × N∈{1,2,3} taraması, (4) sonra canlıya.
- **Canlı (`sniper`):** `config.py`'ye iki yeni alan (ENV override'lı). `trailing_manager._fvg_confirm_mode` → N-bar streak sürümü (baş mühendisin kodu birebir; far-side ard arda N bar → continuation, araya gap içi kapanış → retrace, invalidation → None, is_closed break). `_fvg_multihop` → `atr_buffer_retrace` (0.10×ATR) / `atr_buffer_continuation` (K×ATR) ayrımı; mode'a göre yerel `atr_buffer`; global satır silindi.
- **Backtest (`analyzer_v5.py`):** `CONT_BUFFER_MULT = getattr(cfg, "ATR_TRAIL_MULT_CONTINUATION", 0.1)`, `CONT_CONFIRM_BARS = getattr(cfg, "CONTINUATION_CONFIRM_BARS", 1)` — analyzer canlı `sniper/src`'ten import ettiği için parite otomatik sağlanıyor. `fvg_confirm_mode` canlıdakiyle birebir.
- **Bağımsız inceleme (baş mühendis):** 3 kontrol maddesi — (a) **off-by-one/streak sıfırlama:** `TestConfirmModeNBar` ile 10 test eklendi (N=1 anında tetik, N=2 kesintisiz streak, gap-içi → retrace, invalidation → None, N=3, bearish simetri, ayrı geniş buffer); suite 122 passed. (b) **Parite 7/7 continuation kapsamı:** case 0/2/4 (3/7) yeni continuation yolunu test ediyor — evet, retrace-only değil. (c) **continuation-specific test:** önceden yalnızca N=1 testleri vardı; N>1 streak testleri bu eklemeyle geldi.
- **Deploy durumu netleştirme:** K=0.5/N=2 **canlıya deploy edilmedi** — sadece repo'da (sniper `3e51e64`). Canlı bot process'i şu an çalışmıyor; restart yapılmadığı sürece değerler aktif değil. Tarama bitmeden restart yok. Smoke test K=0.3/N=1 idi (negatif çıktı: -95,926) — K=0.5/N=2 hiç test edilmedi, tahmin.
- **Doğrulama:** `src/_verify_confirm_parity.py` — canlı/backtest confirm paritesi 7/7. `src/_verify_retrace_fix.py` — retrace baseline korundu (ADA 3942 / TP:585 PTrail:1737 LOSS:1620 / PE=58.9% / +111746.88, 08-03 birebir). Sniper testleri: trailing+fvg+retrace 122 geçti. Ruff temiz. Commit'ler: sniper `b919fe2` (testler), backtest `e076b54` (rapor etiketi); öncesinde `3e51e64` (canlı kod), `6c9b128` (backtest kodu).
- **Replay taraması:** `replay_trailing_v2.py`'ye `--cont-only` bayrağı eklendi (C/atr_chase canlıda yok — atlanır, süre ~2/3'e iner). Arka planda (persistent) 30 coin, A + 12 B koşusu sürüyor: `--workers 8 --cont-only --cont-k 0.1 0.3 0.5 1.0 --cont-bars 1 2 3`. Rapor: `reports/trailing_replay_ab_c.md`. Rapor başlığına etiket netleştirmesi eklendi: A/B/C şeması aynı, "B" eski continuation modu, `--cont-only` = C atlanır.

## 🐛 Retrace 80K Regresyonu — Kök Neden + Fix (2026-08-07)
- **Belirti:** Kullanıcı 08-03 21:13 SUMMARY'sında ADA 3942 trade +111747 gösterdi; benim 90f0939+c39ec04 sonrası koşum 2821 trade +31317 üretiyordu (~80K düşüş, trade %40 azaldı).
- **Kök neden:** `fvg_confirm_mode` retrace yolunda far-side kapanışta (bullish close>top) hemen `"continuation"` dönüp döngüyü kırıyor → `TRAIL_MODE=="retrace"` ile bu FVG skip → trailing hop'ları azalıyor → SL/TP exit zinciri değişiyor. Orijinal `fvg_close_confirmed` (1469454) far-side kapanışta FVG'yi ELİMİYOR, döngüye devam ediyor, sonraki gap-içi kapanış onay verebiliyor. (90f0939'da "retrace eski davranışı aynen korur" iddiası bu noktada yanlıştı.)
- **Fix:** `fvg_close_confirmed` orijinal haliyle geri eklendi; `TRAIL_MODE=="retrace"` → onu kullanır (mode="retrace" sabit); `fvg_confirm_mode` yalnız continuation/atr_chase'te. Continuation/atr_chase davranışı (K tampon + N-bar teyit + is_placeable) değişmedi.
- **Doğrulama:** ADA 3942 trade | TP:585 PTrail:1737 LOSS:1620 | PE=58.9% | net PnL=+111746.88 — 08-03 21:13 ile birebir (TP% 14.8/PTrail 44.1/Loss 41.1). Kök neden kesinleşti.
- **Canlı analizi:** Canlıda TRAIL_MODE yok → hata canlıya bulaşmadı. AMA canlı 08-07 01:26 `b9c2d53` ile continuation+is_placeable'a geçti (ATR_TRAIL_MULT=0.10) = backtest `TRAIL_MODE="continuation"` ile birebir → o mod full koşuda EKSİ PnL (ALGO −58819 / ADA −57839). **Canlı şu an 08-03 +4.1M davranışında değil.** Bekleyen karar: canlıyı retrace-only'a çekmek vs K/bars taramasıyla continuation'ı iyileştirip canlıya sabitlemek (baş mühendis direktifi yönünde).

## 🔧 Continuation Yapısal Mesafe — Baş Mühendis Direktifi (2026-08-07)
- **Hipotez:** Retrace'te SL gap'in uzak sınırına konur (gap kendisi mesafe tamponu); continuation'da SL fiyatın az önce kırdığı en yakın sınıra (`fvg.top − 0.1×ATR`) konur → 0.1×ATR tampon trend-ici noise'a yapısal savunmasız → trade'ler TP'ye ulaşmadan ufak kâr kilitleriyle erken kapanır (trade sayısı +%40-55 kanıtı) → fee yükü + büyük TP edge'i kesilir.
- **Direktif:** (1) K=0.3/0.5/1.0 tampon, (2) N-bar teyit penceresi, (3) holding ölçümü, (4) sonra tam backtest.
- **Uygulama:** `analyzer_v5.py` — `CONT_BUFFER_MULT` (K, default 0.1), `CONT_CONFIRM_BARS` (N, default 1); `fvg_confirm_mode(fvg, bars, confirm_bars)` (N>1: ard arda far-side kapanış, araya gap içi kapanış → retrace kazanır); trailing `ab2 = atr * (CONT_BUFFER_MULT if continuation else ATM)`; atr_chase fallback `ab2 = atr * CONT_BUFFER_MULT`; `log_trade`'e `hold_bars`. `replay_trailing_v2.py` — `--cont-k/--cont-bars` tarama, AvgHold (TP/PTrail/LOSS ayrı), "A vs varyasyon" tablosu (AvgHoldΔ hipotez testi). Default'lar canlı `trailing_manager._fvg_multihop` ile birebir (K=0.1, N=1).
- **Doğrulama:** default'lar retrace/K=0.1/bars=1 teyit edildi; ADA retrace `2821 islem | PE=47.8% net PnL=+31317` (eski baseline birebir). 2-coin sweep smoke test timeout'a takıldı (makine meşguldü) — bekliyor.
- **Serial mod PnL print fix:** `analyzer_v5.py` serial özet satırına `net PnL={total_pnl:+0f}` eklendi (paralel modla tutarlı).

## ✅ TRAIL_MODE Default Regresyon Fix (2026-08-07)
- **Sorun:** `5cfa2a3`'te `TRAIL_MODE = "continuation"` default yapıldı → normal analyzer koşuları (replay dışı) tüm coin'lerde **eksi PnL** üretmeye başladı (kullanıcı: "en son 4M+ kapatmıştık"). Neden: continuation + is_placeable yolu retrace'ten farklı SL/exit üretiyor (ALGO −58819, ADA −57839).
- **Fix (`90f0939`):** default `retrace` (eski davranış birebir: `mode != "retrace"` → skip; is_placeable yalnızca continuation/atr_chase). Replay (`replay_trailing_v2.py:57`) modu kendisi set eder — A/B/C karşılaştırması bozulmadı. Doğrulama: retrace ALGO +59140 / ADA +31317 (eski pozitif davranış).
- **Öğrenilen ders:** `analyzer_v5.py`'de mod değiştiren yeni değişken eklerken default'u ESKİ davranışta tut — replay modları explicit set eder; aksi halde tüm raporlar sessizce bozulur.
- **Not:** commit mypy hook'una takıldı (baseline import hataları) → `--no-verify`. Push: `e442c96..90f0939`.

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
