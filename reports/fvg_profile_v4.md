# FVG Profile V4 — V4 Engine ile Kapsamli FVG Karakteristik Profili
**Session:** MULTI_SESSION (her coin kendi session'inda — DEFAULT/REAL_CBDR/ASIA_RANGE)
**Engine:** V4 (live-identical) — Sweep → RSM → Quality → Entry → Trailing
**Coinler:** BTCUSDT, ETHUSDT
**Tarih:** 2026-07-06 19:47

---

## 0. Genel Performans (analyser_v4)

| Coin | Trades | WIN | BE | LOSS | WR% | BE+% | PF | MaxDD% | PnL |
|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|
| BTCUSDT  |    982 |  414 | 212 |  356 | 42.2% | 63.7% | 2.68 |  8.31% |   +18677 |
| ETHUSDT  |   1689 |  626 | 435 |  628 | 37.1% | 62.8% | 2.15 | 13.84% |   +19395 |

---

## 1. Coin × Kategori Ana Tablo

| Coin | Kat | N | Mit% | Inv% | p50Bar | p90Bar | Cont@10% | Cont@40% | RR_WR% | NetExp | n<30? |
|------|------|------|------|------|------|------|------|------|------|------|------|
| BTCUSDT  | CONSOLIDATION | 1193 |   1.5 |  46.2 |   24 |   39 |   0.0 |   0.0 |   2.7 |  -1.11R |      |
| BTCUSDT  | EXPANSION     |   31 |   0.0 |   0.0 |    0 |    0 |   0.0 |   0.0 |   0.0 |  +0.00R |      |
| BTCUSDT  | REJECTION     |    1 |   0.0 |   0.0 |    0 |    0 |   0.0 |   0.0 |   0.0 |  +0.00R |   ⚠️ |
| ETHUSDT  | CONSOLIDATION | 1017 |   4.3 |  54.0 |   45 |  109 |  68.2 |  15.9 |  36.5 |  -1.27R |      |
| ETHUSDT  | EXPANSION     |   77 |   0.0 |  37.7 |    0 |    0 |   0.0 |   0.0 |   0.0 |  -1.27R |      |

---

## 2. Mitigasyon Zamanlamasi

### 2a. Persentil Tablosu (bar-to-mitigate)

| Coin | Kategori | N_mit | p25 | p50 | p75 | p90 | Ortalama |
|------|------|------|------|------|------|------|------|
| BTCUSDT  | CONSOLIDATION |    18 |   16 |   24 |   28 |   39 |   27.4 |
| ETHUSDT  | CONSOLIDATION |    44 |   12 |   45 |   92 |  109 |   51.7 |

### 2b. Kumulatif Mitigasyon Egrisi & Diminishing Returns

| Coin | Kategori | 1b | 2b | 3b | 5b | 10b | 20b | 30b | 50b | 75b | 100b | DR_nok |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BTCUSDT  | CONSOLIDATION | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 2 | 2 | 2b |
| BTCUSDT  | EXPANSION     | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 200b |
| ETHUSDT  | CONSOLIDATION | 0 | 0 | 0 | 0 | 1 | 2 | 2 | 2 | 3 | 4 | 4 | 4 | 2b |
| ETHUSDT  | EXPANSION     | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 200b |

### 2c. Kosullu Iptal Esigi (Cancel Threshold)

P(mitigate | henuz mitigate olmadi VE N bar gecti)

| Coin | Kategori | 5b | 10b | 20b | 30b | 50b | 75b | 100b | 150b |
|---|---|---|---|---|---|---|---|---|---|
| BTCUSDT  | CONSOLIDATION | 1% | 1% | 1% | 0% | 0% | 0% | 0% | 0% |
| BTCUSDT  | EXPANSION     | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% |
| ETHUSDT  | CONSOLIDATION | 4% | 3% | 3% | 3% | 2% | 1% | 1% | 0% |
| ETHUSDT  | EXPANSION     | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% |

### 2d. Onerilen Iptal Esigi (diminishing returns noktasi)

| Coin | CONS | EXP | REJ |
|---|---|---|---|
| BTCUSDT  |   2b | 200b |  N/A |
| ETHUSDT  |   2b | 200b |  N/A |

---

## 3. FVG Boyutu / ATR Orani

### 3a. gap/ATR dagilimi

| Coin | Kons. medyan | Kons. p75 | Exp. medyan | Exp. p75 | Rej. medyan | Rej. p75 |
|---|---|---|---|---|---|---|
| BTCUSDT  | 0.16 | 0.42 | 0.62 | 0.66 | 0.48 | 0.48 |
| ETHUSDT  | 0.17 | 0.40 | 0.38 | 0.51 | - | - |

### 3b. gap/ATR × Kategori (2×3 tablosu — mitigasyon orani)

| FVG Boyutu | CONS Mit% | EXP Mit% | REJ Mit% |
|---|---|---|---|
| Kucuk (<0.5xATR) | 2.1% (n=1738) | 0.0% (n=61) | 0.0% (n=1) |
| Orta (0.5-1.5xATR) | 2.1% (n=332) | 0.0% (n=36) | 0.0% (n=0) |
| Buyuk (>1.5xATR) | 12.9% (n=140) | 0.0% (n=11) | 0.0% (n=0) |

---

## 4. Volatilite Rejimi Analizi

Her FVG'nin olustugu donemdeki ATR'nin son 50 bar icindeki percentile'ina gore LOW/MID/HIGH rejim.

| Coin | Kategori | Rejim | N | Mit% | MedBar | Cont@10% | NetExp |
|---|---|---|---|---|---|---|---|
| BTCUSDT  | CONSOLIDATION |  LOW |  183 |   6.6 |   27 |   0.0 |  -0.10R |
| BTCUSDT  | CONSOLIDATION |  MID |  168 |   3.6 |   15 |   0.0 |  -0.14R |
| BTCUSDT  | CONSOLIDATION | HIGH |  842 |   0.0 |    0 |   0.0 |  +0.00R |
| BTCUSDT  | EXPANSION     |  LOW |   25 |   0.0 |    0 |   0.0 |  +0.00R |
| BTCUSDT  | EXPANSION     | HIGH |    4 |   0.0 |    0 |   0.0 |  +0.00R |
| ETHUSDT  | CONSOLIDATION |  LOW |  162 |   0.6 |    2 |   0.0 |  -0.02R |
| ETHUSDT  | CONSOLIDATION |  MID |  226 |   3.1 |   19 |  71.4 |  -0.19R |
| ETHUSDT  | CONSOLIDATION | HIGH |  629 |   5.7 |   61 |  69.4 |  -0.14R |
| ETHUSDT  | EXPANSION     |  LOW |   20 |   0.0 |    0 |   0.0 |  +0.00R |
| ETHUSDT  | EXPANSION     |  MID |   23 |   0.0 |    0 |   0.0 |  +0.00R |
| ETHUSDT  | EXPANSION     | HIGH |   34 |   0.0 |    0 |   0.0 |  -0.07R |

---

## 5. Hafta Ici / Hafta Sonu Etkisi

| Coin | Kategori | Haftaici N | Hftici Mit% | Hftici NetExp | Haftasonu N | Hftsonu Mit% | Hftsonu NetExp |
|---|---|---|---|---|---|---|---|
| BTCUSDT  | CONSOLIDATION |   888 |   2.0 |   -1.11R |   305 |   0.0 |   +0.00R |
| BTCUSDT  | EXPANSION     |    27 |   0.0 |   +0.00R |     4 |   0.0 |   +0.00R |
| BTCUSDT  | REJECTION     |     1 |   0.0 |   +0.00R |     0 |   0.0 |   +0.00R |
| ETHUSDT  | CONSOLIDATION |   729 |   5.5 |   -1.37R |   288 |   1.4 |   -0.69R |
| ETHUSDT  | EXPANSION     |    52 |   0.0 |   -1.27R |    25 |   0.0 |   +0.00R |

---

## 6. BOS / MSS Yapi Kirilimi Analizi

| Kategori | Yapi | N | Mit% | Cont@10% | RR_WR% | NetExp | n<30? |
|---|---|---|---|---|---|---|---|
| CONSOLIDATION | BOS_ONLY  |   54 |   0.0 |   0.0 | 100.0 |  -3.05R |      |
| CONSOLIDATION | MSS_ONLY  |  972 |   4.2 |  31.7 |  21.4 |  -1.41R |      |
| CONSOLIDATION | BOTH      | 1184 |   1.8 |  81.0 |  43.2 |  -0.68R |      |
| EXPANSION     | BOS_ONLY  |   19 |   0.0 |   0.0 |   0.0 |  +0.00R |   ⚠️ |
| EXPANSION     | MSS_ONLY  |   19 |   0.0 |   0.0 |   0.0 |  -1.27R |   ⚠️ |
| EXPANSION     | BOTH      |   70 |   0.0 |   0.0 |   0.0 |  +0.00R |      |
| REJECTION     | BOTH      |    1 |   0.0 |   0.0 |   0.0 |  +0.00R |   ⚠️ |

### 6b. Coin Bazli BOS/MSS Dagitimi

| Coin | Kategori | N | NONE | BOS_ONLY | MSS_ONLY | BOTH | BOS+ MSS% |
|---|---|---|---|---|---|---|---|
| BTCUSDT  | CONSOLIDATION | 1193 |    0 |   34 |  451 |  708 | 100.0% |
| BTCUSDT  | EXPANSION     |   31 |    0 |    0 |   14 |   17 | 100.0% |
| BTCUSDT  | REJECTION     |    1 |    0 |    0 |    0 |    1 | 100.0% |
| ETHUSDT  | CONSOLIDATION | 1017 |    0 |   20 |  521 |  476 | 100.0% |
| ETHUSDT  | EXPANSION     |   77 |    0 |   19 |    5 |   53 | 100.0% |

### 6c. Hipotez Testi: Teyitli (BOS/MSS) vs Teyitsiz (NONE)

| CONSOLIDATION | BOS_ONLY  | YETERSIZ ORNEKLEM |
| CONSOLIDATION | MSS_ONLY  | YETERSIZ ORNEKLEM |
| CONSOLIDATION | BOTH      | YETERSIZ ORNEKLEM |
| EXPANSION     | BOS_ONLY  | YETERSIZ ORNEKLEM |
| EXPANSION     | MSS_ONLY  | YETERSIZ ORNEKLEM |
| EXPANSION     | BOTH      | YETERSIZ ORNEKLEM |
| REJECTION     | BOS_ONLY  | YETERSIZ ORNEKLEM |
| REJECTION     | MSS_ONLY  | YETERSIZ ORNEKLEM |
| REJECTION     | BOTH      | YETERSIZ ORNEKLEM |

---

## 7. Coin -> Onerilen Kategori

| Coin | CONS exp | CONS CI | EXP exp | EXP CI | REJ exp | REJ CI | Oneri |
|---|---|---|---|---|---|---|---|
| BTCUSDT  | -1.11R | [-1.21,-0.96] | N/A | N/A | N/A | N/A | BELIRSIZ |
| ETHUSDT  | -1.27R | [-1.57,-0.97] | N/A | N/A | N/A | N/A | BELIRSIZ |

---

## 8. Nihai Degerlendirme

### BTCUSDT

- **CONSOLIDATION:** n=1193, exp=-1.11R [-1.21, -0.96] — **negatif expectancy, kacinilmali**
- **EXPANSION:** n=31, yetersiz orneklem
- **REJECTION:** n=1, yetersiz orneklem

### ETHUSDT

- **CONSOLIDATION:** n=1017, exp=-1.27R [-1.57, -0.97] — **negatif expectancy, kacinilmali**
- **EXPANSION:** n=77, yetersiz orneklem
- **REJECTION:** n=0, yetersiz orneklem


---

## 9. C2 Mum Anatomisi × Continuation

### 9a. C2 Anatomi Metrikleri — Tanimlayici Istatistikler

| Metrik | p25 | p50 | p75 | Ortalama |
|---|---|---|---|---|
| body_ratio           | +0.2810 | +0.4806 | +0.6716 | +0.4752 |
| upper_wick_ratio     | +0.0898 | +0.2106 | +0.3727 | +0.2525 |
| lower_wick_ratio     | +0.1044 | +0.2301 | +0.4144 | +0.2722 |
| clv                  | -0.5090 | +0.0752 | +0.5794 | +0.0383 |
| gap_atr_ratio        | +0.2454 | +0.4605 | +0.8135 | +0.6502 |

### 9b. Spearman Korelasyonu: C2 Metrikleri × Continuation

| Metrik | Cont@10 rho | Cont@20 rho | Cont@40 rho |
|---|---|---|---|
| body_ratio           | -0.3379 | -0.3009 | -0.3314 |
| upper_wick_ratio     | -0.3140 | -0.2507 | -0.2899 |
| lower_wick_ratio     | -0.3608 | -0.3364 | -0.3101 |
| clv                  | -0.3487 | -0.3246 | -0.3281 |
| gap_atr_ratio        | -0.4982 | -0.4304 | -0.4251 |

### 9c. Body_Ratio Quartile × Continuation (Kategori Bagimsiz)

| Kategori | Body_Q | N | Mit% | Cont@10% | NetExp (rr_new) |
|---|---|---|---|---|---|
| CONSOLIDATION | Q1(0.18-0.53) |  553 |   6.7 |  45.9 |  -2.09R |
| CONSOLIDATION | Q2(0.53-0.68) |  563 |   5.2 |   6.9 |  -2.26R |
| CONSOLIDATION | Q3(0.68-0.81) |  554 |   9.9 |  40.0 |  -0.46R |
| CONSOLIDATION | Q4(0.81-1.00) |  555 |   3.6 |  50.0 |  -0.27R |
| EXPANSION     | Q1(0.26-0.55) |   30 |   0.0 |   0.0 |  +0.00R |
| EXPANSION     | Q2(0.55-0.69) |   45 |   4.4 | 100.0 |  -1.27R |
| EXPANSION     | Q3(0.69-0.70) |   34 |   0.0 |   0.0 |  +0.00R |
| EXPANSION     | Q4(0.70-0.97) |   29 |   0.0 |   0.0 |  +0.00R |

---

## 10. Retracement Derinligi × Continuation

| Derinlik | WICK_ONLY N | WICK_ONLY Cont@10% | WICK_ONLY Cont@40% | WICK_ONLY NetExp | BODY_CLOSE N | BODY_CLOSE Cont@10% | BODY_CLOSE Cont@40% | BODY_CLOSE NetExp |
|---|---|---|---|---|---|---|---|---|
| 0-25% | 507 | 71.6 | 59.0 | +1.26R | 27 | 33.3 | 44.4 | +1.36R |
| 25-50% | 508 | 72.0 | 62.0 | +1.29R | 92 | 64.1 | 54.3 | +1.39R |
| 50-75% | 402 | 67.9 | 61.2 | +1.21R | 150 | 70.0 | 46.7 | +1.48R |
| 75-100% | 354 | 72.6 | 59.6 | +1.19R | 253 | 75.5 | 65.2 | +1.53R |
| 100-150% | 1497 | 32.1 | 40.1 | -0.66R | 580 | 62.6 | 54.3 | +0.90R |
| >150% | 4710 | 31.9 | 40.0 | -1.48R | 582 | 54.6 | 48.5 | +0.06R |

---

## 11. Entry Delay — FVG'den Kac Mum Sonra Ilk Touch?

FVG olusumundan sonra fiyatin FVG bolgesine ilk kez girdigi mum sayisi.
Dusuk = hizli reaksiyon, yuksek = gecikmeli giris.

| Coin | Kategori | N_touch | p25 | p50 | p75 | <=5b | <=10b | <=20b |
|---|---|---|---|---|---|---|---|---|
| BTCUSDT  | CONSOLIDATION |    37 |  17 |  27 |  55 |   2.7 |   5.4 |  29.7 |
| ETHUSDT  | CONSOLIDATION |   104 |  11 |  46 |  98 |  15.4 |  24.0 |  38.5 |
| ETHUSDT  | EXPANSION     |     2 |  10 |  12 |  12 |   0.0 |  50.0 | 100.0 |

---

## 12. V4 Filtre Kirilimi

V4 motorunda trigger-ready FVG'lerin hangi asamada elendigini gosterir.

| Coin | Toplam FVG | ENTERED | FVG_QUALITY | FVG_VALIDITY | MIN_RISK | CBDR/SHOULD_TRADE | QTY_ZERO |
|---|---|---|---|---|---|---|---|
| BTCUSDT  |   6432 |    982 |   3096 |    998 |      8 |   1348 |      0 |
| ETHUSDT  |   5576 |   1689 |   2765 |   1103 |     19 |      0 |      0 |

---

## 13. Hipotez Testi: Derinlik × Continuation Iliskisi

- **TUM FVG'ler** — Sig(<=50%, n=1137): 0.702 [0.681,0.726] | Derin(>50%, n=8525): 0.409 [0.398,0.422] | Sig > Derin (dusuk depth daha iyi)
- **WICK_ONLY** — Sig(<=50%, n=1010): 0.716 [0.699,0.745] | Derin(>50%, n=6960): 0.361 [0.350,0.375] | Sig > Derin (dusuk depth daha iyi)
- **BODY_CLOSE** — Sig(<=50%, n=118): 0.576 [0.483,0.644] | Derin(>50%, n=1565): 0.624 [0.601,0.649] | ANLAMLI FARK YOK

---

## 14. Early London (02:00-08:00 UTC) Performansi

| Coin | Kategori | EL_N | EL_Mit% | EL_NetExp | Normal_N | Normal_Mit% | Normal_NetExp | Delta_Mit | Delta_Exp |
|---|---|---|---|---|---|---|---|---|---|
| BTCUSDT  | CONSOLIDATION |  238 |   0.0 |   -1.22R |  955 |   1.9 |   -1.10R |  -1.9 |   -0.12R |
| BTCUSDT  | EXPANSION     |    0 |   0.0 |   +0.00R |   31 |   0.0 |   +0.00R |  +0.0 |   +0.00R |
| BTCUSDT  | REJECTION     |    0 |   0.0 |   +0.00R |    1 |   0.0 |   +0.00R |  +0.0 |   +0.00R |
| ETHUSDT  | CONSOLIDATION |  278 |   1.8 |   -1.35R |  739 |   5.3 |   -1.25R |  -3.5 |   -0.09R |
| ETHUSDT  | EXPANSION     |   20 |   0.0 |   +0.00R |   57 |   0.0 |   -1.27R |  +0.0 |   +1.27R |

---

## 15. Coin × Aylik / Sezon Analizi

### 15a. Coin × Ay Mitigasyon Orani

| Coin | Kategori | Ay | N | Mit% | NetExp |
|---|---|---|---|---|---|
| BTCUSDT  | CONSOLIDATION |  1 |  115 |   0.0 |  +0.00R |
| BTCUSDT  | CONSOLIDATION |  2 |  117 |  15.4 |  -1.07R |
| BTCUSDT  | CONSOLIDATION |  3 |  106 |   0.0 |  +0.00R |
| BTCUSDT  | CONSOLIDATION |  4 |  180 |   0.0 |  +0.00R |
| BTCUSDT  | CONSOLIDATION |  5 |  154 |   0.0 |  +0.00R |
| BTCUSDT  | CONSOLIDATION |  6 |  147 |   0.0 |  -1.16R |
| BTCUSDT  | CONSOLIDATION |  7 |  103 |   0.0 |  +0.00R |
| BTCUSDT  | CONSOLIDATION |  8 |   55 |   0.0 |  +0.00R |
| BTCUSDT  | CONSOLIDATION |  9 |   34 |   0.0 |  +0.00R |
| BTCUSDT  | CONSOLIDATION | 10 |   49 |   0.0 |  +0.00R |
| BTCUSDT  | CONSOLIDATION | 11 |   47 |   0.0 |  +0.00R |
| BTCUSDT  | CONSOLIDATION | 12 |   86 |   0.0 |  +0.00R |
| BTCUSDT  | EXPANSION     |  5 |   18 |   0.0 |  +0.00R |
| BTCUSDT  | EXPANSION     |  6 |    9 |   0.0 |  +0.00R |
| BTCUSDT  | EXPANSION     |  7 |    4 |   0.0 |  +0.00R |
| ETHUSDT  | CONSOLIDATION |  1 |   76 |   9.2 |  -0.56R |
| ETHUSDT  | CONSOLIDATION |  2 |   98 |   0.0 |  -2.20R |
| ETHUSDT  | CONSOLIDATION |  3 |   96 |   0.0 |  -5.11R |
| ETHUSDT  | CONSOLIDATION |  4 |  118 |   0.0 |  +0.00R |
| ETHUSDT  | CONSOLIDATION |  5 |   82 |   0.0 |  +0.00R |
| ETHUSDT  | CONSOLIDATION |  6 |  115 |   1.7 |  -0.39R |
| ETHUSDT  | CONSOLIDATION |  7 |   63 |   0.0 |  +0.00R |
| ETHUSDT  | CONSOLIDATION |  8 |   53 |  20.8 |  +1.11R |
| ETHUSDT  | CONSOLIDATION |  9 |   75 |   0.0 |  +0.00R |
| ETHUSDT  | CONSOLIDATION | 10 |   40 |  22.5 |  +0.27R |
| ETHUSDT  | CONSOLIDATION | 11 |   90 |  16.7 |  -1.94R |
| ETHUSDT  | CONSOLIDATION | 12 |  111 |   0.0 |  -1.59R |
| ETHUSDT  | EXPANSION     |  2 |   15 |   0.0 |  +0.00R |
| ETHUSDT  | EXPANSION     |  3 |    3 |   0.0 |  +0.00R |
| ETHUSDT  | EXPANSION     |  4 |   38 |   0.0 |  +0.00R |
| ETHUSDT  | EXPANSION     |  5 |   11 |   0.0 |  +0.00R |
| ETHUSDT  | EXPANSION     | 10 |    2 |   0.0 |  -1.27R |
| ETHUSDT  | EXPANSION     | 12 |    8 |   0.0 |  +0.00R |

### 15b. Coin × Uc Aylik (Quarterly)

| Coin | Kategori | Q | N | Mit% | NetExp |
|---|---|---|---|---|---|
| BTCUSDT  | CONSOLIDATION | Q1 |  338 |   5.3 |  -1.07R |
| BTCUSDT  | CONSOLIDATION | Q2 |  481 |   0.0 |  -1.16R |
| BTCUSDT  | CONSOLIDATION | Q3 |  192 |   0.0 |  +0.00R |
| BTCUSDT  | CONSOLIDATION | Q4 |  182 |   0.0 |  +0.00R |
| BTCUSDT  | EXPANSION     | Q2 |   27 |   0.0 |  +0.00R |
| BTCUSDT  | EXPANSION     | Q3 |    4 |   0.0 |  +0.00R |
| ETHUSDT  | CONSOLIDATION | Q1 |  270 |   2.6 |  -1.70R |
| ETHUSDT  | CONSOLIDATION | Q2 |  315 |   0.6 |  -0.39R |
| ETHUSDT  | CONSOLIDATION | Q3 |  191 |   5.8 |  +1.11R |
| ETHUSDT  | CONSOLIDATION | Q4 |  241 |  10.0 |  -1.52R |
| ETHUSDT  | EXPANSION     | Q1 |   18 |   0.0 |  +0.00R |
| ETHUSDT  | EXPANSION     | Q2 |   49 |   0.0 |  +0.00R |
| ETHUSDT  | EXPANSION     | Q4 |   10 |   0.0 |  -1.27R |

---

## 16. Coin Bazli Esik Onerileri

Per-coin: optimal iptal bar (DR noktasi), FVG expiry, seans, ve en iyi kategori.

| Coin | Session | BestCat | Expiry (bar) | CONS_DR | EXP_DR | REJ_DR | BestMonth | WorstMonth |
|---|---|---|---|---|---|---|---|---|
| BTCUSDT  | 19:00-01:00 | BELIRSIZ     |  45b |    2b |  200b |   N/A |    3 |    9 |
| ETHUSDT  | 19:00-01:00 | BELIRSIZ     |  45b |    2b |  200b |   N/A |    4 |   11 |

---
*Auto-generated by fvg_profile_v4.py*