# LUNA — Kısmi Kâr Alma (Partial TP) Serisi Karar Raporu

**Tarih:** 2026-08-15 · **Hazırlayan:** yerel ajan · **Amaç:** LUNA direktifindeki 4 görevin durumu + kısmi TP deneylerinin sonuçları; canlıya deploy önerisi için LUNA'nın akıl/kararı isteniyor.

---

## 1. LUNA Direktifinin 4 Görevi — Durum

| # | Görev | Durum | Kanıt |
|---|---|---|---|
| 1 | **Sweep tetikleme fix'ini koru** (A6-01: `sweep_confirmed` tüketimi, `bar_index=cur.index`, bayrak temizleme) | ✅ TAMAM | `sweep_sync.py` + `tests/test_cbdr_sweep.py` (4 test PASS) — commit `55a15fa` |
| 2 | **BIAS_LOCKED parity dalı** (canlı `signal_engine.py:78-114` ile birebir) | ✅ TAMAM | `sweep_sync.py` BIAS_LOCKED dalı, `tests/test_bias_locked.py` (10 test PASS) — commit `55a15fa`/`07e3816` |
| 3 | **State & persistence parity** (her koşu temiz state; tekrar koşulabilirlik) | ✅ TAMAM | `_clean_backtest_state` + iki bağımsız baseline koşusu **bit-bit aynı** (48,943 / +1,602,063) |
| 4 | **Entry/trailing iyileştirmelerini baseline'dan ayır** (ayrı commit, ayrı mod etiketi) | ✅ TAMAM | baseline `55a15fa` ↔ trailing deneyleri `c4edf98` (ayrı commit); `--trail-exp` etiketi |

**Test planı:** 14/14 PASS (bias_locked 10 + cbdr_sweep 4). Reddedilen sonuçlardan kaçınıldı (eski sweep bug'ı 22,650/+4M yok; state kirli koşu yok; yalnız PnL gösteren rapor yok; trailing+entry karışımı yok).

---

## 2. Plan C — Trailing İyileştirme Koşuları (28 sembol, LUNA direktifinin 4. görevinin uygulaması)

| Koşu | Trade | NetPnL | PF | Exp$/trade | Exit TP/PTrail/Loss |
|---|---|---|---|---|---|
| **BASELINE_RETRACE_LIVE_PARITY** | 48,943 | **+1,602,063** | 3.18 | +32.73 | 17.0 / 40.1 / 42.9 |
| PROFIT_GATE_0_8R | 43,793 | +113,523 | 1.09 | +2.59 | 20.0 / 18.6 / 61.4 |
| PROFIT_GATE_1_0R | 42,694 | +59,833 | 1.05 | +1.40 | 21.0 / 16.3 / 62.7 |
| ATR_TRAIL_0_5 | 56,116 | −829,117 | 0.24 | −14.78 | 0.8 / 31.1 / 68.1 |
| ATR_TRAIL_0_75 | 55,140 | −862,938 | 0.25 | −15.65 | 1.6 / 29.2 / 69.2 |
| HYBRID_FVG_PLUS_PROFIT_GATE | 44,009 | −115,700 | 0.90 | −2.63 | 15.8 / 13.3 / 70.9 |

**Sonuç:** 5/5 deney baseline'ı geçemedi (28/28 sembolde altında). Trailing'e erken müdahale eden her varyant kârı kesiyor veya stop'u erken vuruyor. **Baseline retrace trailing korunuyor; canlıya trailing değişikliği önerilmez.**

---

## 2b. PROFIT_PROTECT — Swing High/Low ± ATR + FVG Retrace Birleşimi (28 sembol)

**Bu, kullanıcının önerdiği "swing high/low ± ATR + FVG trail" birleşimidir ve implemente edilip koşulmuştur** (4 parametre, 28 sembol, 2026-08-15 12:02-12:48). Mekanizma (`analyzer_v5.py` `PROFIT_PROTECT_*`):
- **Kapı (latch):** trade intrabar `+Gate·risk_pts` unrealized kârı gördüğünde koruma KALICI olarak devreye girer (`PROFIT_PROTECT_GATE_R`).
- **İlk koruma:** `SL = entry ± fees ± 0.1R` (round-trip komisyonu dahil).
- **Swing ratchet:** son onaylı swing low/high ∓ `SWING_ATR_MULT`·ATR (long max / short min).
- **FVG retrace DEVAM eder** — çarpışma yok; max/min birleşimi ortak kuraldır.

| Koşu | Gate | Swing ATR | Trade | NetPnL | Exp$/trade | TP/PTrail/Loss% | AvgHold |
|---|---|---|---|---|---|---|---|
| BASELINE_RETRACE_LIVE_PARITY | — | — | 48,943 | **+1,602,063** | +32.73 | 17.0 / 40.1 / 42.9 | — |
| PROFIT_PROTECT_0_8R_SW0_5 | 0.8R | 0.5 | 51,854 | +1,424,298 | +27.47 | 3.0 / 65.6 / 31.4 | 2.4 |
| PROFIT_PROTECT_0_8R_SW0_75 | 0.8R | 0.75 | 51,848 | +1,424,462 | +27.47 | 3.0 / 65.6 / 31.4 | 2.4 |
| PROFIT_PROTECT_1_0R_SW0_5 | 1.0R | 0.5 | 50,665 | +1,436,431 | +28.35 | 5.1 / 60.4 / 34.5 | 2.8 |
| PROFIT_PROTECT_1_0R_SW0_75 | 1.0R | 0.75 | 50,650 | +1,436,301 | +28.36 | 5.1 / 60.4 / 34.5 | 2.8 |

**Sonuç:** 4 parametre de net-negatif. Kapı arttıkça (0.8→1.0R) kuyruk daha az kesiliyor ve baseline'a yaklaşıyor ama geçmiyor (Exp −16%→−13%). **Swing ATR tamponu 0.5 vs 0.75 etkisiz** (Δ≈+164$ / 51.8K trade). PE artışı (57→65.6) istatistik oyunu: kayıplar BE+fees+0.1R ufak kâra çevriliyor, cebe inen rakam kaybediyor. (Daha geç gate 2.0R de denendi, 8 sembolde −3.4% — bkz. §3 referans satırı.)

---

## 3. Kısmi Kâr Alma (Partial TP) Serisi — 8 Sembol Evreni

Trailing'e müdahale etmek yerine **pozisyonun bir kısmını erken kârda realize etme** hipotezi test edildi. Tetikleyici tasarımı: R bazlı (entry + R·risk_pts) vs **fiyat bazlı** (entry·(1±PCT/100)).

| Varyant | Tetikleyici | Kapanış oranı | NetPnL (8 sembol) | vs baseline 8-sembol (438,966) | MaxDD ort |
|---|---|---|---|---|---|
| BASELINE (8 sembol) | — | — | **438,966** | — | ~0.57% |
| PARTIAL_TP_1_2R_70PCT | 1.2R | %70 | 437,373 | **−0.4%** | ~0.51% |
| PARTIAL_TP_1_8R_50PCT | 1.8R | %50 | 440,010 | **+0.24%** | ~0.55% |
| PARTIAL_TP_2R_70PCT (eski) | **%3 fiyat** | %70 | **444,318** | **+1.2%** | ~0.54% |
| PROFIT_PROTECT_2_0R_SW0_5/75 (referans) | — | — | 424,107/424,252 | −3.4% | — |

**Desen:** Tetikleyici "geç" (yüksek fiyat kârı) olursa az trade tetikleniyor ama tetiklenenler kârlı; erken olursa çok trade tetikleniyor ama her biri küçük. **Fiyat bazlı %3 + %70 kapanış (2R_70PCT) şu ana kadarki en iyi sonuç: baseline üzeri +1.2%.**

### Kritik bulgu — %3 tetikleyiciye ulaşan trade oranı çok düşük

8 sembol, 15,100 trade toplam — her kâr seviyesine ulaşan trade sayısı tarandı:

| Kâr hedefi | Ulaşan trade | Oran |
|---|---|---|
| %0.5 | 4,983 | %33.0 |
| %1.0 | 3,517 | %23.3 |
| %1.5 | 2,468 | %16.3 |
| %2.0 | 1,724 | %11.4 |
| %2.5 | 1,173 | %7.8 |
| **%3.0** | **790** | **%5.2** |
| %4.0 | 375 | %2.5 |
| %5.0 | 197 | %1.3 |

**%3'e sadece 790/15,100 trade (%5.2) ulaşıyor** — mekanizma trade'lerin büyük çoğunluğunda hiç devreye girmiyor. %2'ye düşürülürse 2.2× daha fazla trade tetiklenir (1,724), %1.5'te 3.1× (2,468).

---

## 4. En Güncel Varyant — SCALE-OUT (kullanıcı tarifi, implemente edildi, koşu bekleniyor)

Kullanıcının tarifi: **giriş fiyatı 100 örneğiyle**
1. Fiyat **103** (%3 kâr) olunca → pozisyonun **%50'sini sat**, kalanın **SL'sini 101.5'e** (girişin %1.5 kârı) taşı, **TP'yi de aynı delta kadar ötele** (SL 1.5 dolar ötelendiyse TP de 1.5 dolar).
2. Fiyat ilk seviyeden **+%2 daha** giderse (**105.06**) → kalan **tamamını sat**.

Kod durumu: `analyzer_v5.py`'ye `PARTIAL_TP_SL_PROTECT_PCT` + `PARTIAL_TP_SCALE_STEP_PCT` eklendi; long/short iki taraf; `exit_price` KeyError fix'i yapıldı. Smoke: SOLUSDT **1,506 trade / +26,413.87 / 49 partial** (varyant etiketi: `PARTIAL_TP_2R_70PCT`, parametreler PCT=3.0, FRAC=0.5, SL_PROTECT=1.5, SCALE_STEP=2.0).

**8 sembol koşusu bekleniyor** — LUNA'nın akıl verebilmesi için şu karar noktaları açık:

---

## 5. LUNA'ya Sorular / Karar Noktaları

1. **%3 tetikleyici çok seyrek (%5.2 vuruş).** Tetikleyiciyi düşürmek (%2 → %11.4 vuruş) mi, %3'te bırakıp kalan pozisyonu trailing'e mi bırakmak mı? *Fiyat bazlı %3 + %70 kapanış zaten +1.2% verdi — bu bölgede tetikleyiciyi optimize etmenin yolu nedir?*
2. **Scale-out mantığı** (yarısını sat + SL taşı + kalanı trailing'le/ikinci kademeyle kapat) değerli mi, yoksa tek-kademe kısmi TP yeterli mi? Koşu sonucuyla kanıtlanacak.
3. **Risk parametresi:** Bu seri RISK_PER_TRADE=0.002 ile koşuldu. Kullanıcı 0.003 ile koşulması gerektiğini belirtti (kıyaslama notu) — LUNA hangi risk seviyesinde kıyas yapmamızı ister?
4. **8 → 28 sembol:** Sembol listesi 28'e geri alındı. 8 semboldeki kazanım (%3 fiyat bazlı +1.2%) 28 sembolde korunuyor mu?

---

## 6. Yapılan İşlerin Commit Kaydı

- `55a15fa` — baseline (BIAS_LOCKED + sweep_sync 3-dal + temiz state + pozisyon guard)
- `07e3816` — determinizm doğrulaması (bit-bit)
- `c4edf98` — Plan C trailing deney framework'ü (`--trail-exp`)
- `8f9a3f7`+ — kısmi TP serisi (1_2R_70PCT, 1_8R_50PCT, 2R_70PCT) + scale-out (`PARTIAL_TP_SL_PROTECT_PCT`/`SCALE_STEP_PCT`)
- `b887d2c` (sniper) — SYMBOLS 8→28 coin

---

## 7. Özet Karar Önerisi (ajanın geçici görüşü)

1. **Trailing tarafı kapanmıştır:** 5/5 Plan C deneyi baseline'ı geçemedi → canlı trailing değişmez, baseline retrace korunur.
2. **Kısmi TP tarafı açık ve umut verici:** fiyat bazlı %3 + kısmi kapanış, 8 sembolde baseline üzeri +1.2% (tek pozitif varyant). Ama vuruş oranı %5.2 — kazanımın kapsamı dar.
3. **Scale-out koşusu (8 sembol) tamamlanınca sonuç LUNA'ya sunulacak**; bu serinin canlıya değip değmeyeceği kararını LUNA verir.
