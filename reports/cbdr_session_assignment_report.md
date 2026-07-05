# CBDR Coin → Session Ataması — Karar Raporu

**Tarih:** 2026-07-05
**Proje:** V3 sniper bot, 13 coin, CBDR + Sweep + FVG + Trailing
**Kaynak raporlar:** `cbdr_default_report.md`, `cbdr_real_cbdr_report.md`, `cbdr_asia_range_report.md`

## Amaç

Her coin için 3 backtest sonucu (DEFAULT [22:00-02:00], REAL_CBDR [19:00-01:00], ASIA_RANGE [01:00-05:00]) karşılaştırılıp, `CBDR_RISK_MATRIX` config'ine yazılacak coin bazlı session ataması belirlendi. Karar kriteri: **PnL/MaxDD** (risk-ayarlı getiri) öncelikli, WR ve PF destekleyici.

Not: Backtest'te entry filtreleri (relative FVG, expiry) henüz aktif değil — sadece qty çarpanı (Wilson matrisi + EL 1.5x) test ediliyor. Bu karşılaştırma yalnızca **session/saat seçimi** içindir.

---

## Karşılaştırma Tablosu

| Coin | Session | Trades | WR% | PF | MaxDD% | PnL | PnL/DD |
|---|---|---:|---:|---:|---:|---:|---:|
| **ADA** | DEFAULT | 5045 | 41.2 | 3.35 | 12.03 | 127035 | 10556 |
| | REAL_CBDR | 3934 | 38.7 | 3.04 | 9.04 | 94632 | 10468 |
| | ASIA_RANGE | 4191 | 40.9 | 3.42 | 15.42 | 102140 | 6624 |
| **APT** | DEFAULT | 4125 | 44.5 | 3.27 | 9.69 | 103188 | 10648 |
| | REAL_CBDR | 4394 | 41.7 | 2.97 | 12.83 | 105626 | 8232 |
| | ASIA_RANGE | 4263 | 43.7 | 3.18 | 7.76 | 101081 | **13026** |
| **ATOM** | DEFAULT | 3122 | 43.8 | 4.10 | 9.79 | 123878 | 12654 |
| | REAL_CBDR | 3411 | **45.8** | **4.15** | 11.90 | **139269** | 11704 |
| | ASIA_RANGE | 3253 | 43.4 | 3.79 | 10.23 | 116077 | 11347 |
| **AVAX** | DEFAULT | 4582 | **44.0** | **3.57** | 11.22 | **139041** | 12392 |
| | REAL_CBDR | 4334 | 42.4 | 2.92 | 10.56 | 108415 | 10267 |
| | ASIA_RANGE | 4456 | 43.2 | 3.26 | 8.26 | 115742 | **14012** |
| **BNB** | DEFAULT | 3105 | 44.0 | 3.40 | 13.94 | 79170 | 5680 |
| | REAL_CBDR | 2961 | 43.5 | 3.69 | 12.82 | 87973 | 6863 |
| | ASIA_RANGE | 3375 | **44.9** | **3.79** | **7.56** | **89990** | **11903** |
| **BTC** | DEFAULT | 2270 | 42.4 | 4.10 | 14.56 | 82882 | 5693 |
| | REAL_CBDR | 2689 | 40.4 | 3.44 | **9.75** | 82341 | **8445** |
| | ASIA_RANGE | 2378 | 37.9 | 2.60 | 9.25 | 50137 | 5420 |
| **DOT** | DEFAULT | 5305 | **43.4** | 3.85 | 13.83 | **168999** | 12220 |
| | REAL_CBDR | 4367 | 41.1 | 3.65 | 10.93 | 137484 | **12579** |
| | ASIA_RANGE | 4979 | 40.2 | 3.15 | 12.40 | 115947 | 9351 |
| **ETH** | REAL_CBDR | 4661 | **36.1** | **2.23** | 11.38 | 63749 | **5602** |
| | ASIA_RANGE | 5038 | 35.2 | 2.22 | 14.33 | 63513 | 4432 |
| **LINK** | DEFAULT | 4899 | 40.6 | 3.09 | 10.23 | 116070 | 11347 |
| | REAL_CBDR | 4703 | 40.6 | 2.95 | **9.36** | 105940 | 11318 |
| | ASIA_RANGE | 4814 | **41.4** | **3.52** | 11.04 | **121387** | 10995 |
| **NEAR** | DEFAULT | 5414 | **42.8** | 3.56 | 10.89 | **164809** | 15134 |
| | REAL_CBDR | 4407 | 39.0 | 3.53 | ⚠️19.47 | 152239 | 7818 |
| | ASIA_RANGE | 5402 | 41.7 | 3.32 | **7.99** | 146566 | **18344** |
| **SOL** | DEFAULT | 4423 | **41.3** | **2.78** | **8.47** | **79270** | **9361** |
| | REAL_CBDR | 3980 | 41.5 | 2.89 | 8.67 | 76864 | 8866 |
| | ASIA_RANGE | 4102 | 36.4 | 2.24 | 9.53 | 51833 | 5439 |
| **SUI** | REAL_CBDR | 4500 | 37.8 | **2.60** | ⚠️15.38 | **96016** | **6242** |
| | ASIA_RANGE | 4824 | **39.0** | 2.51 | ⚠️15.02 | 86348 | 5749 |
| **XRP** | DEFAULT | 6508 | **41.1** | **3.10** | **10.36** | **138849** | **13403** |
| | REAL_CBDR | 5232 | 40.7 | 2.89 | 13.56 | 108064 | 7970 |
| | ASIA_RANGE | 6154 | 40.8 | 2.82 | 8.73 | 104555 | 11978 |

*Not: SUI için ASIA_RANGE raporunda "SUI" görülmüyor olabilir kontrolü — orijinal raporlarda SUI yalnızca REAL_CBDR ve ASIA_RANGE dosyalarında mevcut, DEFAULT raporunda SUI satırı yok.*

---

## Önerilen Coin → Session Ataması

| Coin | Önerilen Session | Gerekçe |
|---|---|---|
| ADA | **DEFAULT** | En yüksek PnL + en iyi ratio + en iyi WR, açık ara |
| APT | **ASIA_RANGE** | PnL/DD ratio çok daha iyi (13026 vs 10648), PnL farkı ihmal edilebilir |
| ATOM | **REAL_CBDR** | En yüksek WR, PF, PnL — ratio farkı marjinal |
| AVAX | **ASIA_RANGE** | DEFAULT PnL'de az önde ama ASIA ratio'da çok önde (14012 vs 12392) |
| BNB | **ASIA_RANGE** | Tüm metriklerde en iyi — net kazanan |
| BTC | **REAL_CBDR** | PnL neredeyse eşit, DD çok daha düşük (9.75 vs 14.56), ratio en iyi |
| DOT | **DEFAULT** | En yüksek PnL (168999) + en iyi WR, ratio farkı ihmal edilebilir |
| ETH | **REAL_CBDR** | Tüm metriklerde (marjinal de olsa) önde |
| LINK | **ASIA_RANGE** | En yüksek PnL, WR, PF — ratio farkı çok küçük |
| NEAR | **ASIA_RANGE** | ⚠️ REAL_CBDR'de DD %19.47, circuit breaker eşiğini (%15) fiilen aşıyor — elenmeli. ASIA'da ratio en iyi (18344), DD güvenli |
| SOL | **DEFAULT** | Tüm metriklerde önde |
| SUI | **REAL_CBDR** | Daha yüksek PnL ve ratio — ama ⚠️ her iki seçenekte de DD ~%15, circuit breaker sınırında |
| XRP | **DEFAULT** | Açık ara en iyi PnL, WR, ratio |

### Session bazında dağılım (öneri)

- **DEFAULT:** ADA, DOT, SOL, XRP (4 coin)
- **REAL_CBDR:** ATOM, BTC, ETH, SUI (4 coin)
- **ASIA_RANGE:** APT, AVAX, BNB, LINK, NEAR (5 coin)

---

## Riskli Noktalar

1. **NEAR + REAL_CBDR kombinasyonu güvenilmez.** MaxDD %19.47, RiskManager circuit breaker eşiğinin (%15) üzerinde. Bu session zaten elenmeli — karar kolay, ASIA_RANGE'e geçiş net.
2. **SUI için her iki seçenek de sınırda riskli** (DD ~%15). Paper trade öncesi SUI için qty multiplier manuel düşürülmesi ya da ek DD-azaltıcı filtre değerlendirilebilir.

---

## Sonraki Adımlar

1. ✅ 3 raporun SUMMARY'leri karşılaştırıldı (bu rapor)
2. ⬜ Yukarıdaki atamayı `CBDR_RISK_MATRIX` config'ine yaz
3. ⬜ Bot coin bazlı `SessionState` kullandığı için config güncellenince otomatik aktif olacak
4. ⬜ (İsteğe bağlı) Relative FVG filtresini backtest'e ekle
5. ⬜ (İsteğe bağlı) Expiry filtresini backtest'e ekle
6. ⬜ Paper trade'i başlat
