# LOGIC DRIFT RAPORU: Backtest vs Canli (sniper)

---

## 1. Ortak Moduller

Backtest (`analyzer_v5.py`, `fvg_profile_v5.py`, `analyze_cbdr_thresholds.py`) **dogrudan `sniper/src/` modullerini import eder** — ayni fiziksel dosyalar:

| Modul | Dosya | Ortak mi? |
|---|---|---|
| `config` | `sniper/src/config.py` | ** AYNI ** |
| `retrace_state` | `sniper/src/retrace_state.py` | ** AYNI ** |
| `fvg` | `sniper/src/fvg.py` | ** AYNI ** |
| `indicators` | `sniper/src/indicators.py` | ** AYNI ** |
| `models` | `sniper/src/models.py` | ** AYNI ** |
| `session` | `sniper/src/session.py` | ** AYNI ** |
| `session_router` | `sniper/src/session_router.py` | ** AYNI ** |
| `state_manager` | `sniper/src/state_manager.py` | ** AYNI ** (lazy import) |
| `risk_manager` | `backtest-sniper/src/risk_manager.py` | ** OZDES KOPYA ** |

**Kritik:** Backtest, canli sistemin birebir ayni `RetraceStateMachine`, `SessionState`, `detect_fvgs`, `is_high_quality_fvg`, `should_trade` fonksiyonlarini kullanir. Cekirdek state machine ortak.

---

## 2. Backtest Override / Monkey Patch

### MIN_REL_FVG_THRESHOLD = 0.40 (3 dosyada override)

| Dosya | Satir | Canli | Backtest |
|---|---|---|---|
| `analyzer_v5.py` | 26, 836 | 0.50 | **0.40** |
| `fvg_profile_v5.py` | 32 | 0.50 | **0.40** |
| `analyze_cbdr_thresholds.py` | 44 | 0.50 | **0.40** |

**Etki:** Backtest canlidan %20 daha dusuk kaliteli FVG'leri kabul eder.

### analyze_cbdr_thresholds.py: Tamamen Bagimsiz Config

Canli config'i import etmez. Kendi `_cfg` sinifi (satir 37-80):
- `CBDR_RISK_MATRIX = {}` (bos) — Canlida dolu 20 coin matrix
- `MIN_REL_FVG_THRESHOLD = 0.40` — Canlida 0.50

### fvg_profile_v5.py: Farkli Islemler

| Parametre | analyzer_v5 | fvg_profile_v5 |
|---|---|---|
| Veri formati | `.feather` | `.csv` |
| Komisyon | 0.0005 | **0.0004** |
| Entry fiyati | `next_bar.open` | **`cur.close`** (look-ahead bias) |
| BE mantigi | KALDIRILDI | **HALA DURUYOR** (satir 905-922) |
| FVG expiry | Global 45 | Per-coin: BTC/BNB/SOL=45, **digerleri=5** |

---

## 3. Event Zinciri

### HTF_BIAS - SWEEP

| Adim | Canli | Backtest |
|---|---|---|
| Bias tespiti | `SessionState.update()` - `CBDRState.check_sweep()` | **AYNI** (`session.py` ortak) |
| Sweep tolerance | `atr * CBDR_SWEEP_ATR_TOLERANCE_MULT (0.5)` | **AYNI** |
| | | |

### SWEEP - on_sweep()

| Adim | Canli | Backtest |
|---|---|---|
| Nereden | `signal_engine.py:75` | `analyzer_v5.py:277` |
| Fonksiyon | AYNI (`retrace_state.py`) | AYNI |
| bar_index | **`current.index`** | **`None`** |
| Sweep dedup ID | essiz (bar bazli) | **tumu ayni ID** |
| State gecisi | IDLE - SWEEP_DETECTED | AYNI |
| **SONUC** | Her bar'da yeni sweep | **Gunde 1 sweep/direction** |

### SWEEP_DETECTED - on_sweep_confirmed()

| Adim | Canli | Backtest |
|---|---|---|
| Cagri | `rsm.on_sweep_confirmed(bars_15m, current, atr_val)` | `rsm.on_sweep_confirmed(chunk, cur, atr)` |
| Parametreler | AYNI | AYNI |
| FVG taramasi | `scan_htf_fvgs(bars_15m, lookback=100)` | AYNI |
| Wick rejection | AYNI | AYNI |
| FVG close confirm | AYNI | AYNI |
| | (ortak `retrace_state.py`) | |

### TRIGGER_READY - Entry Filtreleri

| Filtre | Canli | Backtest |
|---|---|---|
| Bias filter | AYNI | AYNI |
| Session filter | `if session == ASIA: return` | `if h >= sh or h < eh: reset` |
| FVG quality | `is_high_quality_fvg(0.50)` | **is_high_quality_fvg(0.40)** |
| FVG expiry | `is_fvg_valid(GLOBAL=45)` | AYNI |
| CBDR mult | `get_cbdr_multiplier()` | AYNI fonksiyon **farkli matrix** |
| should_trade | AYNI | AYNI |

### Entry Creation

| Adim | Canli | Backtest |
|---|---|---|
| SL calc | `trigger_fvg.bottom - adaptive_buf` | AYNI |
| Risk dist | `atr * SL_ATR_MULT (1.5)` | AYNI |
| TP calc | `entry + risk_dist * TP_RR (2.0)` | AYNI |
| Qty calc | `(balance * risk_pct * final_mult) / risk_dist` | AYNI |
| EL mult | `EARLY_LONDON_RISK_MULT = 1.5` | AYNI |
| | | |

### Trade Management

| Adim | Canli | Backtest |
|---|---|---|
| Break-even | `BE_RISK_MULT=1.0` **AKTIF** | analyzer_v5: **KALDIRILMIS** |
| FVG trailing | `ATR_TRAIL_MULT=0.25` | AYNI |
| Exit check | SL/TP hit | AYNI |

---

## 4. Parametre Farkliliklari (Ozet)

| Parametre | Canli | Backtest (analyzer_v5) |
|---|---|---|
| `bar_index` in `on_sweep()` | `current.index` | **`None`** |
| `MIN_REL_FVG_THRESHOLD` | 0.50 | **0.40** |
| `CBDR_RISK_MATRIX` sessions | Canli degerler | **Tamamen farkli (11/13 coin)** |
| `CBDR_RISK_MATRIX` buckets | Canli degerler | **Tamamen farkli** |
| Weekend bonus (APT/ATOM/SUI) | False | **True** |
| Break-even (BE) | **AKTIF** | **KALDIRILMIS** |
| `SL_ATR_MULT` | 1.5 | 1.5 (AYNI) |
| `TP_RR` | 2.0 | 2.0 (AYNI) |
| `FVG_BUFFER_MULT` | 0.50 | 0.50 (AYNI) |
| `ATR_TRAIL_MULT` | 0.25 | 0.25 (AYNI) |
| `FVG_WICK_RATIO_MAX` | 0.75 | 0.75 (AYNI) |
| `RISK_PER_TRADE` | 0.003 | 0.003 (AYNI) |

---

## 5. Nihai Yanit

### Backtest ve canli ayni OHLC verisini alsa ayni trade'i uretir mi?

### HAYIR, uretmez.

### 3 Kesin Logic Drift:

**1. bar_index=None vs bar_index=current.index (En kritik)**
- Canli (`signal_engine.py:75`): her bar essiz index, her bar'da yeni sweep
- Backtest (`analyzer_v5.py:277`): tum sweep'ler "bullish_None" ID'si alir
- **Sonuc:** Gunde sadece 1 sweep/direction. Backtest cogu sweep'i kacirir.

**2. MIN_REL_FVG_THRESHOLD = 0.40 vs 0.50**
- Backtest %20 daha dusuk kaliteli FVG kabul eder
- `analyzer_v5.py:26,836`, `fvg_profile_v5.py:32`, `analyze_cbdr_thresholds.py:44`

**3. CBDR_RISK_MATRIX tamamen farkli**
- 11/13 coin'de session farkli, bucket multiplier'lar farkli
- Weekend bonus'lar farkli (APT/ATOM/SUI)
- `config_20.py:52-74` vs `config.py:140-434`

### Yardimci Driftler:
- **BE:** Canlida aktif, `analyzer_v5.py`'de yok
- **fvg_profile_v5.py:** Ayri engine — komisyon 0.0004, entry cur.close, BE hala var

### Duzeltme icin:
```
1. analyzer_v5.py:277    bar_index=None -> bar_index=sb (veya cur.index)
2. analyzer_v5.py:26     cfg.MIN_REL_FVG_THRESHOLD override kaldir (0.40 -> 0.50)
3. config_20.py:         CBDR_RISK_MATRIX canli config.py ile esitle
```
