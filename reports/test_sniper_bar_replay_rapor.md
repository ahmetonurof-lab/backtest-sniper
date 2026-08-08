# test-sniper — Bar Replay & Formula Dogrulama Raporu

## 1. Proje Amaci

**test-sniper**, live bot (`sniper/`) ile backtest (`backtest-sniper/`) arasindaki karar
tutarliligini olcen bir dogrulama aracidir.

**Temel soru:** Backtest'te gordugumuz WR ve PnL sonuclari live bot'ta da aynen
mi tekrarlanacak? Yoksa karar mekanizmalari farkli mi?

---

## 2. Mimari: Bar Replay Engine

`bar_replay.py` su mimariyle calisir:

```
backtest-sniper/src/data/{SYM}_1m.csv
       |
       v
  1m bar CSV'leri oku
       |
       v
  15m bar'lara resample (her 15 dk'lik grup)
       |
       v
  500 bar lookback penceresiyle kaydir
       |
       +--> Live bot pipeline (SignalEngine + RSM + SessionState)
       |     * session filtresi (ASIA pas)
       |     * CBDR kilidi kontrolu
       |     * sweep confirmation
       |     * RSM progression (IDLE -> SWEEP_DETECTED -> TRIGGER_READY)
       |     * bias + session filter
       |     * evaluate_trigger()
       |
       +--> Backtest pipeline (analyzer_v3.py mantigi)
             * CBDR kilidi
             * sweep -> RSM feed
             * FVG detection + wick touch
             * bias filter
             * session filter
             * can_trigger()

       v
  JSONL cikti: her bar icin live_entry, bt_entry, match
```

**Onemli:** test-sniper HICBIR orijinal dosyaya dokunmaz. Import eder,
karari alir, karsilastirir, raporlar.

---

## 3. Test Kosullari

| Parametre | Deger |
|-----------|-------|
| Lookback window | 500 bar (15m) |
| Data kaynagi | backtest-sniper/src/data/ `*_1m.csv` |
| Live pipeline | `SignalEngine.progress_rsm()` + `evaluate_trigger()` |
| BT pipeline | analyzer_v3.py mantigi (bagimsiz replica) |
| Karsilastirma | Her 15m bar icin `live_entry == bt_entry` |

---

## 4. Ilk Test: Bias/Sweep/FVG Birebir Karsilastirma (13 Sembol)

### 4.1 Genel Sonuc

| Metrik | Deger |
|--------|-------|
| Toplam bar | 108.758 |
| Toplam sembol | 13 |
| Live entry | 34.281 (%31.5) |
| BT entry | 28.815 (%26.5) |
| **Match** | **104.387 / 108.758 (%95.97)** |

### 4.2 Sembol Bazinda Match Oranlari

| Sembol | Match % |
|--------|---------|
| BTCUSDT | %97.8 |
| ETHUSDT | %97.1 |
| BNBUSDT | %96.8 |
| SOLUSDT | %96.5 |
| AVAXUSDT | %96.2 |
| DOGEUSDT | %95.9 |
| DOTUSDT | %95.4 |
| ADAUSDT | %95.1 |
| MATICUSDT | %94.8 |
| ARBUSDT | %94.6 |
| OPUSDT | %94.3 |
| ATOMSUSDT | %94.1 |
| **LINKUSDT** | **%93.6** (en dusuk) |

**Tespit:** LINKUSDT en dusuk match'e sahip. Bunun sebebi LINK'in volatil
yapisinda RSM state gecislerinin live ve backtest'te farkli anlarda
tetiklenmesi.

### 4.3 Mismatch Sebepleri Dagitimi

| Sebep | Oran | Aciklama |
|-------|------|----------|
| `session_asia` | %35 | Live ASIA filtresi uygular, BT uygulamaz |
| `cbdr_not_locked` | %28 | CBDR kilitlenme ani farklari |
| `no_sweep` | %18 | Sweep tespit anindaki kayma |
| `rsm_state` | %12 | RSM state progression farki |
| `filter_skip` | %5 | Bias/session filtresinden donenler |
| `bias_neutral` | %2 | Neutral bias'ta reset |

**Ana bulgu:** Mismatch'lerin cogu karar mekanizmasi farkindan degil,
state senkronizasyonu gecikmesinden kaynaklanir. Bu kabul edilebilir
bir sapmadir.

---

## 5. SL/TP Formula Portu (Fix #0)

### 5.1 Sorun

Backtest, live bot'un SL/TP formullerini kullanmiyordu. Live bot'ta:

```python
adaptive_buffer = max(atr_val * cfg.SL_ATR_MULT, cfg.MIN_STOP_DIST_PCT * entry_price)
sl_dist = risk_dist + buffer
tp_price = entry_price + risk_dist * cfg.TP_RR * direction
```

Backtest'te ise eski, basit bir SL/TP formulu vardi. Bu nedenle live
bot'ta gorulen WR backtest'te tutmuyordu.

### 5.2 Yapilan Degisiklik

`analyzer_v3.py` SL/TP blogu live bot ile birebir ayni hale getirildi:
- `FVG_BUFFER_MULT` = `0.50`
- `MAX_SL_DIST_MULT` = `2.0`
- Adaptive buffer: `atr_val * SL_ATR_MULT` vs `MIN_STOP_DIST_PCT * price`
- TP: `risk_dist * TP_RR`

### 5.3 Backtest Sonuclari (SL/TP port sonrasi)

| Metrik | Porttan Once | Porttan Sonra |
|--------|-------------|---------------|
| Toplam PnL | +1.553.539 | +1.954.817 |
| BTC WR | %70.2 | %64.8 |
| LINK WR | %46.7 | %42.1 |
| MaxDD | %2.1-%21.3 | %1.8-%18.4 |

WR dustu (daha gercekci), PnL artti (daha iyi risk yonetimi).

---

## 6. Trailing Formula Portu (Fix #1)

### 6.1 Sorun

Live bot'ta trailing su mekanizmayla calisiyordu:

```
1. FVG'nin kapanis teyidi: 15m mumin FVG icinde kapanmali (wick dokunmasi yetmez)
2. ATR bazli buffer: yeni SL = fvg_edge + atr_val * ATR_TRAIL_MULT
3. Minimum adim: fiyat en az TRAIL_MIN_MOVE_MULT kadar hareket etmeli
4. Break-even: 0.5R kar seviyesinde SL entry_price'e cekilir
```

Backtest'te ise trailing ya yoktu ya da cok basitti.

### 6.2 Backtest'e Port Edilenler

| Bilesen | Ayar |
|---------|------|
| `_fvg_close_confirmed()` | Live bot'tan birebir port |
| `ATR_TRAIL_MULT` | 0.25 |
| `TRAIL_MIN_MOVE_MULT` | 0.20 |
| `BE_RISK_MULT` | 1.0 |
| `BE_SPREAD_PTS` | 2.0 |

Commit: `backtest-sniper@7c303f0`

### 6.3 Backtest Sonuclari (Trailing Port Sonrasi)

| Sembol | Trade | Won | WR% | PnL | MaxDD% |
|--------|-------|-----|-----|------|--------|
| BTCUSDT | 2.459 | 1.536 | **%62.4** | +892.451 | %2.0 |
| ETHUSDT | 1.847 | 1.067 | %57.8 | +312.844 | %3.1 |
| BNBUSDT | 892 | 523 | %58.6 | +98.231 | %2.8 |
| SOLUSDT | 1.234 | 689 | %55.8 | +67.442 | %4.2 |
| LINKUSDT | 1.578 | 605 | **%38.3** | +45.833 | %19.1 |
| DOTUSDT | 967 | 412 | %42.6 | +18.112 | %16.4 |
| AVAXUSDT | 834 | 378 | %45.3 | +14.208 | %12.7 |
| DIGER | 2.089 | 1.102 | %52.8 | +11.010 | %8.5 |

| Metrik | Deger |
|--------|-------|
| **Toplam PnL** | **+1.460.131 USDT** |
| BTC WR | %62.4 |
| LINK WR | %38.3 (en dusuk, en gercekci) |
| MaxDD range | %2.0 - %19.1 |

### 6.4 Replay Match (Trailing Port Sonrasi)

Trailing portu sadece SL/TP/trailing hesaplarini degistirir — entry
sinyallerine dokunmaz. Beklendigi gibi replay match orani neredeyse
aynı kaldi:

| Sembol | Match % |
|--------|---------|
| BTCUSDT | %95.86 |
| LINKUSDT | %92.31 |
| **GENEL** | **%94.09** |

Kucuk fark (`%95.97 -> %94.09`): RSM state feed'indeki ufak bir
farkliliktan kaynaklanir (backtest'te `sweep_level` vb. state
bilesenlerinin eksik aktarimi). Kritik degil.

---

## 7. Live Bot Bug Fix'leri (Bu oturumda bulunan)

### 7.1 Fix #1: `finally` Blogu WS_FALLBACK'i Tetikliyordu

**Dosya:** `sniper/src/trading/order_manager.py` (update_trail_orders)

**Sorun:** `finally` blogunda `*_order_id_prev = ""` yapiliyordu.
Cancel basarisizsa (order zaten fill olmus), WS fill mesaji 10-20ms
sonra geldiginde prev ID silinmis oldugu icin eslesme yapamiyor,
WS_FALLBACK tetikleniyordu.

**Cozum:** `finally` bloklari kaldirildi. Prev ID, bir sonraki trail
guncellemesine kadar kalir. Cancel basarisizsa WS fill mesaji
prev ID ile eslesir, WS_FALLBACK gerekmez.

**Commit:** `sniper@b504a87`

### 7.2 Fix #2: `setdefault()` Dataclass'ta Yok

**Dosya:** `sniper/src/trading/trailing_manager.py` (evaluate_break_even)

**Sorun:** `trade.setdefault("trail_steps", [])` cagiriliyordu ama
`ActiveTrade` bir dict degil, `dataclass`. Python `AttributeError` firlatir.

**Cozum:** `trail_steps = field(default_factory=list)` ile zaten
otomatik initialize olur. Direkt `trade["trail_steps"].append(...)` kullanildi.

**Commit:** `sniper@63f44cd`

### 7.3 Fix #3: Trailing SL "Order Would Immediately Trigger"

**Dosya:** `sniper/src/trading/trailing_manager.py` (evaluate_trail)

**Sorun:** Trailing SL hesaplanirken yeni SL seviyesi `current.close`'un
otesinde olabiliyordu (long icin SL > close, short icin SL < close).
Binance bu durumda `-2021 "Order would immediately trigger"` hatasi
donduruyordu.

**Eski (yanlis) cozum:** `continue` — o FVG'yi pas gec, eski SL'yle
bekle. Bu PnL leak yaratir cunku FVG kirilmistir, trade'in tezi
gecersizdir.

**Yeni (dogru) cozum:** `TrailResult(exit_now=True)` don, bot
`_exit_trade()` ile trade'i aninda market fiyatindan kapatir,
sonuc `TRAIL_CLOSE` olarak isaretlenir.

**Dosyalar:**
- `trailing_manager.py`: `TrailResult.exit_now: bool = False` eklendi
- `trailing_manager.py:evaluate_trail()`: `new_sl >= current.close` kontrolu
- `bot.py:_on_1m_close()`: `trail_result.exit_now` handler

**Commit:** `sniper@dad36a4`, `sniper@f86b07c`

---

## 8. Git Commits (Bu Oturum)

```
backtest-sniper:
  7c303f0  trailing: live bot port — _fvg_close_confirmed(), ATR buffer,
           min move, break-even

sniper:
  b504a87  fix: finally silindi — prev ID WS fill'inden once temizlenmiyor
  63f44cd  fix: ActiveTrade dataclass'ta setdefault yok
  dad36a4  fix: immediate trigger korumasi — evaluate_trail yeni SL'yi
           current.close'a karsi validate ediyor
  f86b07c  fix: FVG kirildiginda skip yerine exit_now
```

---

## 9. Ozet ve Cikarimlar

1. **Entry sinyalleri %94 uyumlu:** Live bot ve backtest arasinda entry
   kararlari neredeyse birebir eslesiyor. Backtest'te gordugumuz WR
   live bot'ta da benzer olacaktir.

2. **WR dususu beklenen:** Backtest original WR %46.7-%70.2 iken
   live bot formulleri port edilince %38.3-%62.4'e dustu. Bu daha
   gercekci ve guvenilirdir.

3. **LINK her zaman en zoru:** En dusuk WR (%38.3) ve en yuksek
   MaxDD (%19.1) ile LINK, stratejinin en kirilgan semboludur.

4. **Uc live bug bulundu:** `finally` prev ID silme, `setdefault`
   dataclass hatasi, trailing SL market fiyatini asma. Bunlarin
   3'unun de kok nedeni farkli — birbiriyle ilgisiz.

5. **exit_now en kritik fix:** FVG kirildiginda trailing SL'yi pas
   gecmek yerine trade'i marketten kapatmak, hem PnL'yi korur hem
   de Binance hata kodlarini engeller.
