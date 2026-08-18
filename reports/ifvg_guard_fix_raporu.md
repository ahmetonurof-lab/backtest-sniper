# IFVG Guard-Semantik Fix — 28-Coin Yeniden Koşu Raporu

**Tarih:** 2026-08-18
**Koşu:** `python src\analyzer_v5.py --workers 6 --ifvg` (797s, paralel 6 worker)
**Rapor:** `reports/analyzer_v5_summary.md` (son blok) + bu dosya
**Direktif:** `sniper/reports/ifvg-guard-fix-direktif.md`

---

## 1. Özet — Fix içeriği

Guard semantik uyumsuzluğu giderildi: canlı `fvg_is_alive` (bot.py) FVG'yi
**formasyon+2'den** tararken, IFVG (inverted) adaylar bu taramada **kırılım
barının kendisini** de görüyordu — kırılım barı tanım gereği flipped yönün
far-side'ına kapandığı için her IFVG adayı doğduğu anda ölü sayılıyordu
(canlıda yapısal olarak hiç IFVG trade'i üretilemezken, backtest'in
cur-bar-only kontrolü bunu hiç görmüyor ve binlerce "hayalet" IFVG trade'i
üretiyordu).

Uygulanan değişiklikler:

1. **`retrace_state.py` — `_register_inverted(fvg, break_bar_index)`**: aday
   artık kırılımın gerçekleştiği barın index'ini taşır (`HTFFVG.break_bar_index`).
   Her iki çağrı noktası da güncellendi: `on_bias_fvg` (break_bar_index=current.index)
   ve `on_sweep_confirmed` (break_bar_index=last.index — önceki çalışmada eksikti).
2. **Canlılık taraması başlangıcı** (yalnızca IFVG kaynaklı trigger'lar):
   - Canlı `bot.py`: `fvg_is_alive(..., scan_from=tf.break_bar_index+1)`.
   - Backtest `analyzer_v5.py`: IFVG trigger'ları için aynı `fvg_is_alive`
     `scan_from=break_bar_index+1` ile `chunk` üzerinde koşulur (NORMAL path
     bit-bit korundu — `get_fvg_status(cur)` aynen).
   - `fvg.py` `fvg_is_alive`'a opsiyonel `scan_from` parametresi eklendi.
   - Hedef: **iki tarafta aynı semantik** — kırılım barı ölüm değil, kırılım
     sonrası far-side close hâlâ ölüm (tutarlılık, gevşetme değil).
3. **Parity contract** (`tests/parity/test_parity_regression.py`):
   - 2026-07-31 benchmark'i **tazelendi** (stale: sweep-tüketim fix'i +
     signal_engine refactor'ü sonrası trigger sayıları 10K+→~500, sweep-lock
     33K→0 — input veri/sha256 AYNI).
   - **IFVG-on senaryosu eklendi**: `test_parity_ifvg_on` (9 sembol) — flag
     açıkken canlı ve backtest'in aynı IFVG trigger/reddi ürettiğini doğrular
     (core_diff=0, ifvg bt==live, IFVG_ON_BENCHMARK_CONTRACT).
4. **Yeni testler:** `break_bar_index` kaydı (test_retrace_state),
   `fvg_is_alive` scan_from semantiği — kırılım barı ölüm değil / sonrası ölüm
   (test_fvg), backtest `test_ifvg_state_fix.py` mevcut.

## 2. Sonuçlar — Fix Öncesi / Sonrası

| Metrik | Önceki koşu (guard bug, state-fix) | **Bu koşu (guard fix)** | Δ |
|---|---|---|---|
| Toplam trade | 62,806 | **53,018** | **−9,788 (−15.6%)** |
| Net PnL | +2,345,188 | **+1,889,348** | −455,840 (−19.4%) |
| NORMAL trade | 47,907 (+1,562,636) | **43,146 (+1,482,756)** | −4,761 |
| **IFVG trade** | 14,899 (23.7%) | **9,872 (18.6%)** | **−5,027 (−33.7%)** |
| IFVG-only PnL | +782,552 (+52.5/trade) | **+406,592 (+41.2/trade)** | −375,960 |
| Exp$ | +37.34 | **+35.64** | −1.70 |
| IFVG-off baseline | — | 48,943 / +1,602,063 | — |

**Direktif beklentisi karşılandı:** IFVG trade sayısı **düştü** (14,899 → 9,872,
−33.7%) — bir kısmı artık kırılım sonrası far-side close taramasında doğru
şekilde eleniyor. **Asıl geçerli rakam bu koşudur** (eski rakamlar guard
farkının artefaktıydı).

NORMAL trade'lerindeki değişim (−4,761) beklenen state-dinamiği yan etkisidir:
IFVG entry'leri pozisyon pencereleri işgal edip BIAS_LOCKED yoluyla NORMAL
re-entry üretiyordu; IFVG adayları azalınca bu zincir de seyreldi. NORMAL
entry karar mantığına dokunulmadı (bit-bit korundu).

## 3. Coin Bazlı IFVG PnL Dağılımı — tek-coin bağımlılığı kontrolü

**28/28 coin IFVG$ POZİTİF** (min XRP +5,748 — max SEI +25,920). Tek-coin
bağımlılığı YOK; getiri geniş tabana yayılmış.

| Coin | IFVG# | IFVG$ | | Coin | IFVG# | IFVG$ |
|---|---|---|---|---|---|---|
| ALGO | 287 | +12,614 | | NEAR | 398 | +17,262 |
| ADA | 353 | +10,909 | | LINK | 435 | +12,403 |
| APT | 362 | +10,402 | | OP | 393 | +19,496 |
| ATOM | 437 | +12,498 | | SOL | 339 | +11,130 |
| AAVE | 328 | +13,294 | | PYTH | 375 | +21,293 |
| ARB | 353 | +13,060 | | RENDER | 290 | +11,396 |
| BNB | 314 | +14,266 | | SEI | 396 | +25,920 |
| DOGE | 364 | +10,695 | | STRK | 371 | +20,347 |
| ENA | 329 | +20,580 | | SUI | 352 | +10,664 |
| AVAX | 319 | +11,697 | | XRP | 233 | +5,748 |
| DOT | 382 | +9,507 | | UNI | 389 | +12,253 |
| DYDX | 379 | +20,037 | | TIA | 385 | +22,144 |
| ONDO | 205 | +6,372 | | GMX | 394 | +18,839 |
| LDO | 364 | +18,145 | | INJ | 346 | +13,620 |

Holdout: **VALIDATED** (PF 7.83 vs train 4.08, ratio 1.92).

## 4. Parity A/B — canlı vs backtest aynı semantikte

- **18/18 parity testi PASS** (`tests/parity`, 9 sembol × 2 mod):
  - NORMAL (IFVG kapalı): core_diff=0, TRIGGER bt==live, sweep-lock bt==live,
    tazelenmiş `BENCHMARK_CONTRACT` değerleriyle.
  - **IFVG-on**: core_diff=0, IFVG trigger bt==live (ör. SOLUSDT 76==76,
    BNBUSDT 79==79), toplam TRIGGER bt==live — `IFVG_ON_BENCHMARK_CONTRACT`.
- **Aynı guard fonksiyonu, aynı başlangıç:** canlı `bot.py` ve backtest
  `analyzer_v5.py` artık ikisi de paylaşılan `fvg_is_alive`'ı
  `scan_from=break_bar_index+1` ile çağırıyor → kırılım barı iki tarafta da
  ölüm koşulu değil, kırılım sonrası far-side close iki tarafta da ölüm.
- **IFVG_ENABLED=False regresyon garantisi:** flag kapalıyken `_last_trigger_source`
  hep "NORMAL" → IFVG branch'leri hiç çalışmıyor; NORMAL path ve unit testleri
  bit-bit (baseline failure seti 24/24 aynı, 0 yeni fail; 1050 pass).

## 5. Test Durumu

| Suite | Sonuç |
|---|---|
| sniper tests (test_bot hariç) | **1050 passed** (baseline 1039 → +11 yeni), 24 fail **birebir pre-existing** (stash A/B kanıtı) |
| sniper test_retrace_state + test_fvg + test_signal_engine | 132 passed |
| sniper parity (NORMAL + IFVG-on) | **18 passed** |
| backtest tests | 63 passed (test_analyze_cbdr_thresholds collection error pre-existing) |

## 6. Karar / Kırmızı Çizgi

- **IFVG_ENABLED=True canlıya deploy edilmedi ve edilmeyecek** — kırmızı çizgi
  korunuyor; canlı config'de flag tanımlı değil (default False).
- Fix + bu yeniden koşu tamamlandı; rapor baş mühendise sunuldu. IFVG yolu
  artık canlıda yapısal olarak trade üretebilir durumda (guard semantiği
  backtest ile birebir), net +406,592 IFVG-only PnL / 9,872 trade, 28/28 coin
  pozitif. Deploy kararı baş mühendiste.
