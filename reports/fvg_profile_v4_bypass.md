# FVG Profile V4 — V4 Engine ile Kapsamli FVG Karakteristik Profili
**Session:** MULTI_SESSION (her coin kendi session'inda — DEFAULT/REAL_CBDR/ASIA_RANGE)
**Engine:** V4 (live-identical) — Sweep → RSM → Quality → Entry → Trailing
**BYPASS:** is_high_quality_fvg / is_fvg_valid / should_trade devre disi — A/B karsilastirma icin
**Coinler:** BTCUSDT, BNBUSDT, SOLUSDT, AVAXUSDT, LINKUSDT, XRPUSDT, ATOMUSDT, ADAUSDT, APTUSDT, DOTUSDT, NEARUSDT, ETHUSDT, SUIUSDT
**Tarih:** 2026-07-07 03:59

---

## 0. Genel Performans (analyser_v4)

| Coin | Trades | WIN | BE | LOSS | WR% | BE+% | PF | MaxDD% | PnL |
|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|
| BTCUSDT  |   2678 | 1092 | 623 |  963 | 40.8% | 64.0% | 3.51 |  8.89% |   +75639 |
| BNBUSDT  |   3372 | 1525 | 731 | 1116 | 45.2% | 66.9% | 3.82 |  7.56% |   +90164 |
| SOLUSDT  |   5884 | 2324 | 1395 | 2165 | 39.5% | 63.2% | 2.62 | 12.28% |  +100134 |
| AVAXUSDT |   5884 | 2515 | 1262 | 2107 | 42.7% | 64.2% | 3.07 |  8.56% |  +125926 |
| LINKUSDT |   4786 | 1968 | 1150 | 1668 | 41.1% | 65.1% | 3.47 |  9.43% |  +119182 |
| XRPUSDT  |   6475 | 2670 | 1514 | 2291 | 41.2% | 64.6% | 3.10 | 11.98% |  +138130 |
| ATOMUSDT |   3360 | 1505 | 704 | 1151 | 44.8% | 65.7% | 3.96 | 12.28% |  +133642 |
| ADAUSDT  |   4999 | 2021 | 1196 | 1782 | 40.4% | 64.4% | 3.22 | 11.70% |  +120168 |
| APTUSDT  |   5664 | 2372 | 1244 | 2048 | 41.9% | 63.8% | 2.82 |  8.70% |  +115470 |
| DOTUSDT  |   5537 | 2293 | 1307 | 1937 | 41.4% | 65.0% | 3.46 | 10.95% |  +143026 |
| NEARUSDT |   6648 | 2784 | 1520 | 2344 | 41.9% | 64.7% | 3.33 | 10.46% |  +154354 |
| ETHUSDT  |   4670 | 1692 | 1209 | 1769 | 36.2% | 62.1% | 2.31 | 10.30% |   +65281 |
| SUIUSDT  |   6066 | 2399 | 1370 | 2297 | 39.5% | 62.1% | 2.65 | 16.13% |  +110982 |

---

## 1. Coin × Kategori Ana Tablo

| Coin | Kat | N | Mit% | Inv% | p50Bar | p90Bar | Cont@10% | Cont@40% | RR_WR% | NetExp | n<30? |
|------|------|------|------|------|------|------|------|------|------|------|------|
| BTCUSDT  | CONSOLIDATION | 2743 |   0.0 |  51.5 |    0 |    0 |   0.0 |   0.0 |   0.0 |  -1.22R |      |
| BTCUSDT  | EXPANSION     |   10 |   0.0 |   0.0 |    0 |    0 |   0.0 |   0.0 |   0.0 |  +0.00R |   ⚠️ |
| BNBUSDT  | CONSOLIDATION | 3728 |   0.0 |  43.4 |    0 |    0 |   0.0 |   0.0 |  43.8 |  -0.26R |      |
| BNBUSDT  | EXPANSION     |   60 |   0.0 |  91.7 |    0 |    0 |   0.0 |   0.0 |   0.0 |  +0.00R |      |
| SOLUSDT  | CONSOLIDATION | 1050 |   0.2 |  52.4 |   55 |   55 | 100.0 | 100.0 | 100.0 |  +1.60R |      |
| SOLUSDT  | EXPANSION     |   57 |   0.0 |  80.7 |    0 |    0 |   0.0 |   0.0 |   0.0 |  +0.00R |      |
| SOLUSDT  | REJECTION     |   11 |   0.0 | 100.0 |    0 |    0 |   0.0 |   0.0 |   0.0 |  +0.00R |   ⚠️ |
| AVAXUSDT | CONSOLIDATION | 1174 |   2.4 |  57.4 |   11 |  193 |  60.7 |  32.1 |  27.3 |  -0.67R |      |
| AVAXUSDT | EXPANSION     |  103 |   0.0 |  75.7 |    0 |    0 |   0.0 |   0.0 |   0.0 |  +0.00R |      |
| AVAXUSDT | REJECTION     |   13 |   0.0 | 100.0 |    0 |    0 |   0.0 |   0.0 |   0.0 |  +0.00R |   ⚠️ |
| LINKUSDT | CONSOLIDATION | 1999 |   4.2 |  40.3 |    9 |   54 |  83.1 |  72.3 |  16.2 |  -0.98R |      |
| LINKUSDT | EXPANSION     |  110 |   2.7 |  70.0 |   43 |   46 |   0.0 |   0.0 |   0.0 |  -1.66R |      |
| XRPUSDT  | CONSOLIDATION | 1042 |   4.0 |  53.2 |  110 |  191 |  57.1 |  57.1 |  50.0 |  -0.77R |      |
| XRPUSDT  | EXPANSION     |    9 |   0.0 |  11.1 |    0 |    0 |   0.0 |   0.0 |   0.0 |  -2.42R |   ⚠️ |
| XRPUSDT  | REJECTION     |    5 |   0.0 |  20.0 |    0 |    0 |   0.0 |   0.0 |   0.0 |  +0.00R |   ⚠️ |
| ATOMUSDT | CONSOLIDATION | 2998 |   3.6 |  52.9 |   34 |   78 |  38.5 |  91.7 |  71.2 |  +0.75R |      |
| ATOMUSDT | EXPANSION     |  817 |   0.0 |  47.9 |    0 |    0 |   0.0 |   0.0 |   0.0 |  +0.00R |      |
| ATOMUSDT | REJECTION     |   69 |   0.0 | 100.0 |    0 |    0 |   0.0 |   0.0 |   0.0 |  +0.00R |      |
| ADAUSDT  | CONSOLIDATION | 2372 |   2.9 |  56.8 |   88 |  115 |   7.4 |   4.4 |  61.1 |  +0.08R |      |
| ADAUSDT  | EXPANSION     |  130 |   0.0 |  51.5 |    0 |    0 |   0.0 |   0.0 |   0.0 |  +0.00R |      |
| ADAUSDT  | REJECTION     |    6 |   0.0 | 100.0 |    0 |    0 |   0.0 |   0.0 |   0.0 |  +0.00R |   ⚠️ |
| APTUSDT  | CONSOLIDATION | 1372 |   1.6 |  67.0 |   28 |  144 |  59.1 |  50.0 |  48.8 |  -0.10R |      |
| APTUSDT  | EXPANSION     |  192 |   2.6 |  51.0 |  190 |  195 |  40.0 |   0.0 |  83.3 |  +0.89R |      |
| APTUSDT  | REJECTION     |   80 |   3.8 | 100.0 |    6 |    7 |   0.0 |   0.0 |  25.0 |  -0.80R |      |
| DOTUSDT  | CONSOLIDATION |  837 |   1.3 |  60.8 |    2 |  191 |  27.3 |  27.3 |  15.1 |  -1.37R |      |
| DOTUSDT  | EXPANSION     |  105 |   0.0 |  65.7 |    0 |    0 |   0.0 |   0.0 |   0.0 |  +0.00R |      |
| DOTUSDT  | REJECTION     |    1 |   0.0 | 100.0 |    0 |    0 |   0.0 |   0.0 |   0.0 |  +0.00R |   ⚠️ |
| NEARUSDT | CONSOLIDATION | 1050 |   3.0 |  57.0 |   36 |  120 |  53.1 |  43.8 |  39.2 |  -1.09R |      |
| NEARUSDT | EXPANSION     |  111 |   0.0 |  62.2 |    0 |    0 |   0.0 |   0.0 |   0.0 |  +0.00R |      |
| NEARUSDT | REJECTION     |   13 |   0.0 | 100.0 |    0 |    0 |   0.0 |   0.0 |   0.0 |  +0.00R |   ⚠️ |
| ETHUSDT  | CONSOLIDATION |  839 |   4.8 |  52.3 |   46 |  128 |  65.0 |  17.5 |  39.5 |  -1.27R |      |
| ETHUSDT  | EXPANSION     |   71 |   0.0 |  42.3 |    0 |    0 |   0.0 |   0.0 |   0.0 |  -1.27R |      |
| SUIUSDT  | CONSOLIDATION | 1233 |   3.8 |  48.5 |    4 |  125 |  38.3 |  42.6 |  48.0 |  -0.70R |      |
| SUIUSDT  | EXPANSION     |  131 |   0.8 |  43.5 |   22 |   22 | 100.0 | 100.0 | 100.0 |  +1.27R |      |
| SUIUSDT  | REJECTION     |    1 |   0.0 | 100.0 |    0 |    0 |   0.0 |   0.0 |   0.0 |  +0.00R |   ⚠️ |

---

## 2. Mitigasyon Zamanlamasi

### 2a. Persentil Tablosu (bar-to-mitigate)

| Coin | Kategori | N_mit | p25 | p50 | p75 | p90 | Ortalama |
|------|------|------|------|------|------|------|------|
| SOLUSDT  | CONSOLIDATION |     2 |   38 |   55 |   55 |   55 |   46.5 |
| AVAXUSDT | CONSOLIDATION |    28 |    0 |   11 |  132 |  193 |   65.1 |
| LINKUSDT | CONSOLIDATION |    83 |    3 |    9 |   33 |   54 |   23.7 |
| LINKUSDT | EXPANSION     |     3 |   42 |   43 |   46 |   46 |   43.7 |
| XRPUSDT  | CONSOLIDATION |    42 |   19 |  110 |  135 |  191 |   87.5 |
| ATOMUSDT | CONSOLIDATION |   109 |    2 |   34 |   61 |   78 |   33.4 |
| ADAUSDT  | CONSOLIDATION |    68 |    1 |   88 |  105 |  115 |   67.4 |
| APTUSDT  | CONSOLIDATION |    22 |    0 |   28 |  101 |  144 |   53.8 |
| APTUSDT  | EXPANSION     |     5 |  187 |  190 |  192 |  195 |  188.4 |
| APTUSDT  | REJECTION     |     3 |    1 |    6 |    7 |    7 |    4.7 |
| DOTUSDT  | CONSOLIDATION |    11 |    1 |    2 |   48 |  191 |   40.2 |
| NEARUSDT | CONSOLIDATION |    32 |   16 |   36 |   45 |  120 |   42.8 |
| ETHUSDT  | CONSOLIDATION |    40 |   12 |   46 |   92 |  128 |   52.9 |
| SUIUSDT  | CONSOLIDATION |    47 |    0 |    4 |   35 |  125 |   29.5 |
| SUIUSDT  | EXPANSION     |     1 |   22 |   22 |   22 |   22 |   22.0 |

### 2b. Kumulatif Mitigasyon Egrisi & Diminishing Returns

| Coin | Kategori | 1b | 2b | 3b | 5b | 10b | 20b | 30b | 50b | 75b | 100b | 150b | 200b | DR_nok |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BTCUSDT  | CONSOLIDATION | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 200b |
| BTCUSDT  | EXPANSION     | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 200b |
| BNBUSDT  | CONSOLIDATION | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 200b |
| BNBUSDT  | EXPANSION     | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 200b |
| SOLUSDT  | CONSOLIDATION | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 75b |
| SOLUSDT  | EXPANSION     | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 200b |
| SOLUSDT  | REJECTION     | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 200b |
| AVAXUSDT | CONSOLIDATION | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 2 | 2 | 2 | 2b |
| AVAXUSDT | EXPANSION     | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 200b |
| AVAXUSDT | REJECTION     | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 200b |
| LINKUSDT | CONSOLIDATION | 0 | 1 | 1 | 1 | 2 | 3 | 3 | 4 | 4 | 4 | 4 | 4 | 2b |
| LINKUSDT | EXPANSION     | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 3 | 3 | 3 | 3 | 75b |
| XRPUSDT  | CONSOLIDATION | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 2 | 2 | 2 | 3 | 4 | 2b |
| XRPUSDT  | EXPANSION     | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 200b |
| XRPUSDT  | REJECTION     | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 200b |
| ATOMUSDT | CONSOLIDATION | 1 | 1 | 1 | 1 | 2 | 2 | 2 | 2 | 3 | 4 | 4 | 4 | 2b |
| ATOMUSDT | EXPANSION     | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 200b |
| ATOMUSDT | REJECTION     | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 200b |
| ADAUSDT  | CONSOLIDATION | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 2 | 3 | 3 | 2b |
| ADAUSDT  | EXPANSION     | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 200b |
| ADAUSDT  | REJECTION     | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 200b |
| APTUSDT  | CONSOLIDATION | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 2 | 2 | 2b |
| APTUSDT  | EXPANSION     | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 200b |
| APTUSDT  | REJECTION     | 0 | 1 | 1 | 1 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 3b |
| DOTUSDT  | CONSOLIDATION | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 2b |
| DOTUSDT  | EXPANSION     | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 200b |
| NEARUSDT | CONSOLIDATION | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 2 | 2 | 3 | 3 | 3 | 2b |
| NEARUSDT | EXPANSION     | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 200b |
| NEARUSDT | REJECTION     | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 200b |
| ETHUSDT  | CONSOLIDATION | 0 | 0 | 0 | 0 | 1 | 2 | 2 | 3 | 3 | 4 | 5 | 5 | 2b |
| ETHUSDT  | EXPANSION     | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 200b |
| SUIUSDT  | CONSOLIDATION | 1 | 1 | 2 | 2 | 2 | 2 | 3 | 3 | 3 | 3 | 4 | 4 | 2b |
| SUIUSDT  | EXPANSION     | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 50b |

### 2c. Kosullu Iptal Esigi (Cancel Threshold)

P(mitigate | henuz mitigate olmadi VE N bar gecti)

| Coin | Kategori | 5b | 10b | 20b | 30b | 50b | 75b | 100b | 150b |
|---|---|---|---|---|---|---|---|---|---|
| BTCUSDT  | CONSOLIDATION | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% |
| BTCUSDT  | EXPANSION     | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% |
| BNBUSDT  | CONSOLIDATION | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% |
| BNBUSDT  | EXPANSION     | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% |
| SOLUSDT  | CONSOLIDATION | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% |
| SOLUSDT  | EXPANSION     | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% |
| SOLUSDT  | REJECTION     | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% |
| AVAXUSDT | CONSOLIDATION | 1% | 1% | 1% | 1% | 1% | 1% | 1% | 0% |
| AVAXUSDT | EXPANSION     | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% |
| AVAXUSDT | REJECTION     | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% |
| LINKUSDT | CONSOLIDATION | 3% | 2% | 1% | 1% | 1% | 0% | 0% | 0% |
| LINKUSDT | EXPANSION     | 3% | 3% | 3% | 3% | 0% | 0% | 0% | 0% |
| XRPUSDT  | CONSOLIDATION | 3% | 3% | 3% | 3% | 2% | 2% | 2% | 1% |
| XRPUSDT  | EXPANSION     | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% |
| XRPUSDT  | REJECTION     | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% |
| ATOMUSDT | CONSOLIDATION | 2% | 2% | 2% | 2% | 1% | 0% | 0% | 0% |
| ATOMUSDT | EXPANSION     | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% |
| ATOMUSDT | REJECTION     | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% |
| ADAUSDT  | CONSOLIDATION | 2% | 2% | 2% | 2% | 2% | 2% | 1% | 0% |
| ADAUSDT  | EXPANSION     | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% |
| ADAUSDT  | REJECTION     | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% |
| APTUSDT  | CONSOLIDATION | 1% | 1% | 1% | 1% | 1% | 1% | 0% | 0% |
| APTUSDT  | EXPANSION     | 3% | 3% | 3% | 3% | 3% | 3% | 3% | 3% |
| APTUSDT  | REJECTION     | 3% | 0% | 0% | 0% | 0% | 0% | 0% | 0% |
| DOTUSDT  | CONSOLIDATION | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% |
| DOTUSDT  | EXPANSION     | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% |
| NEARUSDT | CONSOLIDATION | 3% | 3% | 2% | 2% | 1% | 1% | 0% | 0% |
| NEARUSDT | EXPANSION     | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% |
| NEARUSDT | REJECTION     | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% |
| ETHUSDT  | CONSOLIDATION | 4% | 4% | 3% | 3% | 2% | 2% | 1% | 0% |
| ETHUSDT  | EXPANSION     | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% |
| SUIUSDT  | CONSOLIDATION | 2% | 1% | 1% | 1% | 1% | 1% | 1% | 0% |
| SUIUSDT  | EXPANSION     | 1% | 1% | 1% | 0% | 0% | 0% | 0% | 0% |

### 2d. Onerilen Iptal Esigi (diminishing returns noktasi)

| Coin | CONS | EXP | REJ |
|---|---|---|---|
| BTCUSDT  | 200b | 200b |  N/A |
| BNBUSDT  | 200b | 200b |  N/A |
| SOLUSDT  |  75b | 200b | 200b |
| AVAXUSDT |   2b | 200b | 200b |
| LINKUSDT |   2b |  75b |  N/A |
| XRPUSDT  |   2b | 200b | 200b |
| ATOMUSDT |   2b | 200b | 200b |
| ADAUSDT  |   2b | 200b | 200b |
| APTUSDT  |   2b | 200b |   3b |
| DOTUSDT  |   2b | 200b |  N/A |
| NEARUSDT |   2b | 200b | 200b |
| ETHUSDT  |   2b | 200b |  N/A |
| SUIUSDT  |   2b |  50b |  N/A |

---

## 3. FVG Boyutu / ATR Orani

### 3a. gap/ATR dagilimi

| Coin | Kons. medyan | Kons. p75 | Exp. medyan | Exp. p75 | Rej. medyan | Rej. p75 |
|---|---|---|---|---|---|---|
| BTCUSDT  | 0.19 | 0.42 | 0.04 | 0.56 | - | - |
| BNBUSDT  | 0.12 | 0.26 | 0.32 | 0.34 | - | - |
| SOLUSDT  | 0.22 | 0.52 | 0.28 | 0.41 | 0.05 | 0.05 |
| AVAXUSDT | 0.49 | 1.20 | 1.00 | 2.65 | 0.98 | 1.18 |
| LINKUSDT | 0.44 | 0.79 | 0.58 | 0.75 | - | - |
| XRPUSDT  | 0.07 | 0.23 | 1.06 | 1.16 | 28.45 | 29.92 |
| ATOMUSDT | 0.44 | 1.08 | 0.62 | 1.52 | 0.46 | 0.48 |
| ADAUSDT  | 0.40 | 0.78 | 0.66 | 1.72 | 1.91 | 1.91 |
| APTUSDT  | 0.49 | 1.22 | 2.46 | 3.57 | 0.28 | 0.31 |
| DOTUSDT  | 0.40 | 0.92 | 1.17 | 1.50 | 0.04 | 0.04 |
| NEARUSDT | 0.24 | 0.78 | 1.19 | 1.59 | 0.44 | 0.45 |
| ETHUSDT  | 0.17 | 0.41 | 0.45 | 0.57 | - | - |
| SUIUSDT  | 0.30 | 0.71 | 0.83 | 2.08 | 0.24 | 0.24 |

### 3b. gap/ATR × Kategori (2×3 tablosu — mitigasyon orani)

| FVG Boyutu | CONS Mit% | EXP Mit% | REJ Mit% |
|---|---|---|---|
| Kucuk (<0.5xATR) | 2.3% (n=15132) | 1.2% (n=728) | 1.8% (n=164) |
| Orta (0.5-1.5xATR) | 2.7% (n=5086) | 0.0% (n=624) | 0.0% (n=25) |
| Buyuk (>1.5xATR) | 0.1% (n=2219) | 0.0% (n=554) | 0.0% (n=10) |

---

## 4. Volatilite Rejimi Analizi

Her FVG'nin olustugu donemdeki ATR'nin son 50 bar icindeki percentile'ina gore LOW/MID/HIGH rejim.

| Coin | Kategori | Rejim | N | Mit% | MedBar | Cont@10% | NetExp |
|---|---|---|---|---|---|---|---|
| BTCUSDT  | CONSOLIDATION |  LOW |  491 |   0.0 |    0 |   0.0 |  -0.01R |
| BTCUSDT  | CONSOLIDATION |  MID |  317 |   0.0 |    0 |   0.0 |  -0.02R |
| BTCUSDT  | CONSOLIDATION | HIGH | 1935 |   0.0 |    0 |   0.0 |  +0.00R |
| BTCUSDT  | EXPANSION     |  MID |    6 |   0.0 |    0 |   0.0 |  +0.00R |
| BNBUSDT  | CONSOLIDATION |  LOW |  292 |   0.0 |    0 |   0.0 |  +0.00R |
| BNBUSDT  | CONSOLIDATION |  MID |  297 |   0.0 |    0 |   0.0 |  -0.01R |
| BNBUSDT  | CONSOLIDATION | HIGH | 3139 |   0.0 |    0 |   0.0 |  -0.00R |
| BNBUSDT  | EXPANSION     |  LOW |   52 |   0.0 |    0 |   0.0 |  +0.00R |
| BNBUSDT  | EXPANSION     |  MID |    5 |   0.0 |    0 |   0.0 |  +0.00R |
| BNBUSDT  | EXPANSION     | HIGH |    3 |   0.0 |    0 |   0.0 |  +0.00R |
| SOLUSDT  | CONSOLIDATION |  LOW |  268 |   0.7 |   55 | 100.0 |  +0.01R |
| SOLUSDT  | CONSOLIDATION |  MID |  192 |   0.0 |    0 |   0.0 |  +0.01R |
| SOLUSDT  | CONSOLIDATION | HIGH |  590 |   0.0 |    0 |   0.0 |  +0.00R |
| SOLUSDT  | EXPANSION     |  LOW |   39 |   0.0 |    0 |   0.0 |  +0.00R |
| SOLUSDT  | EXPANSION     |  MID |    7 |   0.0 |    0 |   0.0 |  +0.00R |
| SOLUSDT  | EXPANSION     | HIGH |   11 |   0.0 |    0 |   0.0 |  +0.00R |
| SOLUSDT  | REJECTION     |  LOW |    7 |   0.0 |    0 |   0.0 |  +0.00R |
| SOLUSDT  | REJECTION     |  MID |    4 |   0.0 |    0 |   0.0 |  +0.00R |
| AVAXUSDT | CONSOLIDATION |  LOW |  750 |   2.5 |    2 |  47.4 |  -0.05R |
| AVAXUSDT | CONSOLIDATION |  MID |  221 |   0.5 |  132 | 100.0 |  -0.04R |
| AVAXUSDT | CONSOLIDATION | HIGH |  203 |   3.9 |  104 |  87.5 |  +0.02R |
| AVAXUSDT | EXPANSION     |  LOW |   83 |   0.0 |    0 |   0.0 |  +0.00R |
| AVAXUSDT | EXPANSION     |  MID |    8 |   0.0 |    0 |   0.0 |  +0.00R |
| AVAXUSDT | EXPANSION     | HIGH |   12 |   0.0 |    0 |   0.0 |  +0.00R |
| AVAXUSDT | REJECTION     |  LOW |   12 |   0.0 |    0 |   0.0 |  +0.00R |
| LINKUSDT | CONSOLIDATION |  LOW | 1110 |   1.3 |    6 |  35.7 |  -0.06R |
| LINKUSDT | CONSOLIDATION |  MID |  417 |   7.9 |   14 |  97.0 |  -0.18R |
| LINKUSDT | CONSOLIDATION | HIGH |  472 |   7.6 |    5 |  88.9 |  -0.25R |
| LINKUSDT | EXPANSION     |  LOW |  102 |   2.9 |   43 |   0.0 |  -0.05R |
| LINKUSDT | EXPANSION     |  MID |    6 |   0.0 |    0 |   0.0 |  +0.00R |
| XRPUSDT  | CONSOLIDATION |  LOW |   85 |   3.5 |  107 | 100.0 |  +0.07R |
| XRPUSDT  | CONSOLIDATION |  MID |  129 |   1.6 |  136 |   0.0 |  -0.01R |
| XRPUSDT  | CONSOLIDATION | HIGH |  828 |   4.5 |   52 |  56.8 |  -0.09R |
| XRPUSDT  | EXPANSION     |  MID |    7 |   0.0 |    0 |   0.0 |  +0.00R |
| XRPUSDT  | REJECTION     |  LOW |    5 |   0.0 |    0 |   0.0 |  +0.00R |
| ATOMUSDT | CONSOLIDATION |  LOW | 2143 |   1.6 |    1 |  94.3 |  +0.03R |
| ATOMUSDT | CONSOLIDATION |  MID |  305 |   4.6 |    1 |  64.3 |  +0.36R |
| ATOMUSDT | CONSOLIDATION | HIGH |  550 |  10.9 |   59 |   0.0 |  +0.04R |
| ATOMUSDT | EXPANSION     |  LOW |  804 |   0.0 |    0 |   0.0 |  +0.00R |
| ATOMUSDT | EXPANSION     |  MID |   13 |   0.0 |    0 |   0.0 |  +0.00R |
| ATOMUSDT | REJECTION     |  LOW |   69 |   0.0 |    0 |   0.0 |  +0.00R |
| ADAUSDT  | CONSOLIDATION |  LOW | 1120 |   2.0 |    0 |  22.7 |  +0.06R |
| ADAUSDT  | CONSOLIDATION |  MID |  473 |   7.8 |   90 |   0.0 |  -0.05R |
| ADAUSDT  | CONSOLIDATION | HIGH |  779 |   1.2 |  105 |   0.0 |  -0.04R |
| ADAUSDT  | EXPANSION     |  LOW |  130 |   0.0 |    0 |   0.0 |  +0.00R |
| ADAUSDT  | REJECTION     |  LOW |    6 |   0.0 |    0 |   0.0 |  +0.00R |
| APTUSDT  | CONSOLIDATION |  LOW |  957 |   1.4 |    0 |  46.2 |  -0.00R |
| APTUSDT  | CONSOLIDATION |  MID |  212 |   1.4 |  145 | 100.0 |  +0.02R |
| APTUSDT  | CONSOLIDATION | HIGH |  203 |   3.0 |  101 |  66.7 |  -0.06R |
| APTUSDT  | EXPANSION     |  LOW |  172 |   2.9 |  190 |  40.0 |  +0.04R |
| APTUSDT  | EXPANSION     |  MID |    7 |   0.0 |    0 |   0.0 |  -0.18R |
| APTUSDT  | EXPANSION     | HIGH |   13 |   0.0 |    0 |   0.0 |  +0.00R |
| APTUSDT  | REJECTION     |  LOW |   80 |   3.8 |    6 |   0.0 |  -0.04R |
| DOTUSDT  | CONSOLIDATION |  LOW |  511 |   0.6 |    3 |  66.7 |  -0.06R |
| DOTUSDT  | CONSOLIDATION |  MID |  150 |   2.0 |  191 |   0.0 |  -0.05R |
| DOTUSDT  | CONSOLIDATION | HIGH |  176 |   2.8 |    1 |  20.0 |  -0.20R |
| DOTUSDT  | EXPANSION     |  LOW |  101 |   0.0 |    0 |   0.0 |  +0.00R |
| DOTUSDT  | EXPANSION     |  MID |    4 |   0.0 |    0 |   0.0 |  +0.00R |
| NEARUSDT | CONSOLIDATION |  LOW |  444 |   0.0 |    0 |   0.0 |  -0.12R |
| NEARUSDT | CONSOLIDATION |  MID |  158 |   0.0 |    0 |   0.0 |  -0.06R |
| NEARUSDT | CONSOLIDATION | HIGH |  448 |   7.1 |   36 |  53.1 |  -0.10R |
| NEARUSDT | EXPANSION     |  LOW |  105 |   0.0 |    0 |   0.0 |  +0.00R |
| NEARUSDT | EXPANSION     |  MID |    6 |   0.0 |    0 |   0.0 |  +0.00R |
| NEARUSDT | REJECTION     |  LOW |   13 |   0.0 |    0 |   0.0 |  +0.00R |
| ETHUSDT  | CONSOLIDATION |  LOW |  112 |   0.9 |    0 |   0.0 |  -0.02R |
| ETHUSDT  | CONSOLIDATION |  MID |  192 |   2.6 |   15 |  60.0 |  -0.12R |
| ETHUSDT  | CONSOLIDATION | HIGH |  535 |   6.4 |   61 |  67.6 |  -0.14R |
| ETHUSDT  | EXPANSION     |  LOW |   19 |   0.0 |    0 |   0.0 |  +0.00R |
| ETHUSDT  | EXPANSION     |  MID |   19 |   0.0 |    0 |   0.0 |  +0.00R |
| ETHUSDT  | EXPANSION     | HIGH |   33 |   0.0 |    0 |   0.0 |  -0.08R |
| SUIUSDT  | CONSOLIDATION |  LOW |  491 |   4.7 |    3 |  26.1 |  +0.01R |
| SUIUSDT  | CONSOLIDATION |  MID |  193 |   3.6 |   25 |  28.6 |  -0.08R |
| SUIUSDT  | CONSOLIDATION | HIGH |  549 |   3.1 |    2 |  58.8 |  -0.07R |
| SUIUSDT  | EXPANSION     |  LOW |   93 |   0.0 |    0 |   0.0 |  +0.00R |
| SUIUSDT  | EXPANSION     |  MID |   33 |   3.0 |   22 | 100.0 |  +0.04R |
| SUIUSDT  | EXPANSION     | HIGH |    5 |   0.0 |    0 |   0.0 |  +0.00R |

---

## 5. Hafta Ici / Hafta Sonu Etkisi

| Coin | Kategori | Haftaici N | Hftici Mit% | Hftici NetExp | Haftasonu N | Hftsonu Mit% | Hftsonu NetExp |
|---|---|---|---|---|---|---|---|
| BTCUSDT  | CONSOLIDATION |  1903 |   0.0 |   -1.22R |   840 |   0.0 |   +0.00R |
| BTCUSDT  | EXPANSION     |    10 |   0.0 |   +0.00R |     0 |   0.0 |   +0.00R |
| BNBUSDT  | CONSOLIDATION |  2613 |   0.0 |   -0.26R |  1115 |   0.0 |   +0.00R |
| BNBUSDT  | EXPANSION     |     9 |   0.0 |   +0.00R |    51 |   0.0 |   +0.00R |
| SOLUSDT  | CONSOLIDATION |   699 |   0.3 |   +1.80R |   351 |   0.0 |   +1.40R |
| SOLUSDT  | EXPANSION     |    48 |   0.0 |   +0.00R |     9 |   0.0 |   +0.00R |
| SOLUSDT  | REJECTION     |    11 |   0.0 |   +0.00R |     0 |   0.0 |   +0.00R |
| AVAXUSDT | CONSOLIDATION |   916 |   1.3 |   -0.65R |   258 |   6.2 |   -0.73R |
| AVAXUSDT | EXPANSION     |    65 |   0.0 |   +0.00R |    38 |   0.0 |   +0.00R |
| AVAXUSDT | REJECTION     |    11 |   0.0 |   +0.00R |     2 |   0.0 |   +0.00R |
| LINKUSDT | CONSOLIDATION |  1326 |   5.2 |   -0.90R |   673 |   2.1 |   -1.55R |
| LINKUSDT | EXPANSION     |    40 |   7.5 |   -1.66R |    70 |   0.0 |   +0.00R |
| XRPUSDT  | CONSOLIDATION |   786 |   5.1 |   -0.82R |   256 |   0.8 |   -0.29R |
| XRPUSDT  | EXPANSION     |     1 |   0.0 |   -2.42R |     8 |   0.0 |   +0.00R |
| XRPUSDT  | REJECTION     |     5 |   0.0 |   +0.00R |     0 |   0.0 |   +0.00R |
| ATOMUSDT | CONSOLIDATION |  1769 |   2.8 |   -0.31R |  1229 |   4.9 |   +1.71R |
| ATOMUSDT | EXPANSION     |   591 |   0.0 |   +0.00R |   226 |   0.0 |   +0.00R |
| ATOMUSDT | REJECTION     |    69 |   0.0 |   +0.00R |     0 |   0.0 |   +0.00R |
| ADAUSDT  | CONSOLIDATION |  1832 |   3.6 |   +0.07R |   540 |   0.4 |   +0.86R |
| ADAUSDT  | EXPANSION     |   119 |   0.0 |   +0.00R |    11 |   0.0 |   +0.00R |
| ADAUSDT  | REJECTION     |     1 |   0.0 |   +0.00R |     5 |   0.0 |   +0.00R |
| APTUSDT  | CONSOLIDATION |  1028 |   1.6 |   -0.10R |   344 |   1.7 |   -0.08R |
| APTUSDT  | EXPANSION     |   152 |   0.0 |   -1.28R |    40 |  12.5 |   +1.33R |
| APTUSDT  | REJECTION     |     8 |  37.5 |   -0.80R |    72 |   0.0 |   +0.00R |
| DOTUSDT  | CONSOLIDATION |   527 |   2.1 |   -1.26R |   310 |   0.0 |   -2.74R |
| DOTUSDT  | EXPANSION     |    80 |   0.0 |   +0.00R |    25 |   0.0 |   +0.00R |
| DOTUSDT  | REJECTION     |     1 |   0.0 |   +0.00R |     0 |   0.0 |   +0.00R |
| NEARUSDT | CONSOLIDATION |   817 |   3.2 |   -1.14R |   233 |   2.6 |   -0.26R |
| NEARUSDT | EXPANSION     |    79 |   0.0 |   +0.00R |    32 |   0.0 |   +0.00R |
| NEARUSDT | REJECTION     |     1 |   0.0 |   +0.00R |    12 |   0.0 |   +0.00R |
| ETHUSDT  | CONSOLIDATION |   613 |   5.9 |   -1.40R |   226 |   1.8 |   -0.53R |
| ETHUSDT  | EXPANSION     |    49 |   0.0 |   -1.27R |    22 |   0.0 |   +0.00R |
| SUIUSDT  | CONSOLIDATION |   843 |   2.8 |   -1.15R |   390 |   5.9 |   +0.20R |
| SUIUSDT  | EXPANSION     |    84 |   1.2 |   +1.27R |    47 |   0.0 |   +0.00R |
| SUIUSDT  | REJECTION     |     0 |   0.0 |   +0.00R |     1 |   0.0 |   +0.00R |

---

## 6. BOS / MSS Yapi Kirilimi Analizi

| Kategori | Yapi | N | Mit% | Cont@10% | RR_WR% | NetExp | n<30? |
|---|---|---|---|---|---|---|---|
| CONSOLIDATION | BOS_ONLY  |  943 |   0.8 |  75.0 |  42.9 |  -0.27R |      |
| CONSOLIDATION | MSS_ONLY  | 8750 |   2.3 |  67.3 |  43.7 |  -0.48R |      |
| CONSOLIDATION | BOTH      | 12744 |   2.1 |  33.9 |  44.1 |  -0.37R |      |
| EXPANSION     | BOS_ONLY  |  222 |   0.0 |   0.0 |   0.0 |  +0.00R |      |
| EXPANSION     | MSS_ONLY  |  783 |   1.1 |  33.3 |  50.0 |  -0.17R |      |
| EXPANSION     | BOTH      |  901 |   0.0 |   0.0 |   0.0 |  -1.28R |      |
| REJECTION     | MSS_ONLY  |   81 |   0.0 |   0.0 |   0.0 |  +0.00R |      |
| REJECTION     | BOTH      |  118 |   2.5 |   0.0 |  25.0 |  -0.80R |      |

### 6b. Coin Bazli BOS/MSS Dagitimi

| Coin | Kategori | N | NONE | BOS_ONLY | MSS_ONLY | BOTH | BOS+ MSS% |
|---|---|---|---|---|---|---|---|
| BTCUSDT  | CONSOLIDATION | 2743 |    0 |  113 |  933 | 1697 | 100.0% |
| BTCUSDT  | EXPANSION     |   10 |    0 |    0 |    0 |   10 | 100.0% |
| BNBUSDT  | CONSOLIDATION | 3728 |    0 |  163 | 1174 | 2391 | 100.0% |
| BNBUSDT  | EXPANSION     |   60 |    0 |    0 |   57 |    3 | 100.0% |
| SOLUSDT  | CONSOLIDATION | 1050 |    0 |   72 |  393 |  585 | 100.0% |
| SOLUSDT  | EXPANSION     |   57 |    0 |    1 |    7 |   49 | 100.0% |
| SOLUSDT  | REJECTION     |   11 |    0 |    0 |    0 |   11 | 100.0% |
| AVAXUSDT | CONSOLIDATION | 1174 |    0 |   28 |  443 |  703 | 100.0% |
| AVAXUSDT | EXPANSION     |  103 |    0 |    0 |   38 |   65 | 100.0% |
| AVAXUSDT | REJECTION     |   13 |    0 |    0 |    0 |   13 | 100.0% |
| LINKUSDT | CONSOLIDATION | 1999 |    0 |   63 |  876 | 1060 | 100.0% |
| LINKUSDT | EXPANSION     |  110 |    0 |    0 |   24 |   86 | 100.0% |
| XRPUSDT  | CONSOLIDATION | 1042 |    0 |   78 |  447 |  517 | 100.0% |
| XRPUSDT  | EXPANSION     |    9 |    0 |    8 |    1 |    0 | 100.0% |
| XRPUSDT  | REJECTION     |    5 |    0 |    0 |    5 |    0 | 100.0% |
| ATOMUSDT | CONSOLIDATION | 2998 |    0 |  256 | 1074 | 1668 | 100.0% |
| ATOMUSDT | EXPANSION     |  817 |    0 |  183 |  427 |  207 | 100.0% |
| ATOMUSDT | REJECTION     |   69 |    0 |    0 |   69 |    0 | 100.0% |
| ADAUSDT  | CONSOLIDATION | 2372 |    0 |   52 | 1108 | 1212 | 100.0% |
| ADAUSDT  | EXPANSION     |  130 |    0 |    2 |   46 |   82 | 100.0% |
| ADAUSDT  | REJECTION     |    6 |    0 |    0 |    0 |    6 | 100.0% |
| APTUSDT  | CONSOLIDATION | 1372 |    0 |   44 |  465 |  863 | 100.0% |
| APTUSDT  | EXPANSION     |  192 |    0 |    5 |   44 |  143 | 100.0% |
| APTUSDT  | REJECTION     |   80 |    0 |    0 |    5 |   75 | 100.0% |
| DOTUSDT  | CONSOLIDATION |  837 |    0 |   22 |  351 |  464 | 100.0% |
| DOTUSDT  | EXPANSION     |  105 |    0 |    5 |   49 |   51 | 100.0% |
| DOTUSDT  | REJECTION     |    1 |    0 |    0 |    1 |    0 | 100.0% |
| NEARUSDT | CONSOLIDATION | 1050 |    0 |   20 |  435 |  595 | 100.0% |
| NEARUSDT | EXPANSION     |  111 |    0 |    0 |   52 |   59 | 100.0% |
| NEARUSDT | REJECTION     |   13 |    0 |    0 |    1 |   12 | 100.0% |
| ETHUSDT  | CONSOLIDATION |  839 |    0 |   15 |  418 |  406 | 100.0% |
| ETHUSDT  | EXPANSION     |   71 |    0 |   18 |    5 |   48 | 100.0% |
| SUIUSDT  | CONSOLIDATION | 1233 |    0 |   17 |  633 |  583 | 100.0% |
| SUIUSDT  | EXPANSION     |  131 |    0 |    0 |   33 |   98 | 100.0% |
| SUIUSDT  | REJECTION     |    1 |    0 |    0 |    0 |    1 | 100.0% |

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
| BTCUSDT  | -1.22R | [-1.22,-1.22] | N/A | N/A | N/A | N/A | BELIRSIZ |
| BNBUSDT  | -0.26R | [-0.85,+0.50] | N/A | N/A | N/A | N/A | CONSOLIDATION (-0.26R) |
| SOLUSDT  | +1.60R | [+1.40,+1.80] | N/A | N/A | N/A | N/A | BELIRSIZ |
| AVAXUSDT | -0.67R | [-1.01,-0.35] | N/A | N/A | N/A | N/A | BELIRSIZ |
| LINKUSDT | -0.98R | [-1.12,-0.85] | -1.66R | [-1.66,-1.66] | N/A | N/A | BELIRSIZ |
| XRPUSDT  | -0.77R | [-1.11,-0.54] | N/A | N/A | N/A | N/A | BELIRSIZ |
| ATOMUSDT | +0.75R | [+0.56,+0.94] | N/A | N/A | N/A | N/A | BELIRSIZ |
| ADAUSDT  | +0.08R | [-0.10,+0.32] | N/A | N/A | N/A | N/A | CONSOLIDATION (+0.08R) |
| APTUSDT  | -0.10R | [-0.39,+0.21] | +0.89R | [-0.41,+1.33] | -0.80R | [-1.55,+0.70] | EXPANSION (+0.89R) |
| DOTUSDT  | -1.37R | [-1.60,-1.07] | N/A | N/A | N/A | N/A | BELIRSIZ |
| NEARUSDT | -1.09R | [-1.37,-0.77] | N/A | N/A | N/A | N/A | BELIRSIZ |
| ETHUSDT  | -1.27R | [-1.67,-0.69] | N/A | N/A | N/A | N/A | BELIRSIZ |
| SUIUSDT  | -0.70R | [-1.17,-0.25] | N/A | N/A | N/A | N/A | BELIRSIZ |

---

## 8. Nihai Degerlendirme

### BTCUSDT

- **CONSOLIDATION:** n=2743, exp=-1.22R [-1.22, -1.22] — **negatif expectancy, kacinilmali**
- **EXPANSION:** n=10, yetersiz orneklem
- **REJECTION:** n=0, yetersiz orneklem

### BNBUSDT

- **CONSOLIDATION:** n=3728, exp=-0.26R [-0.85, +0.50] — sifiri kapsiyor, belirsiz
- **EXPANSION:** n=60, yetersiz orneklem
- **REJECTION:** n=0, yetersiz orneklem

### SOLUSDT

- **CONSOLIDATION:** n=1050, exp=+1.60R [+1.40, +1.80] — **olumlu edge**
- **EXPANSION:** n=57, yetersiz orneklem
- **REJECTION:** n=11, yetersiz orneklem

### AVAXUSDT

- **CONSOLIDATION:** n=1174, exp=-0.67R [-1.01, -0.35] — **negatif expectancy, kacinilmali**
- **EXPANSION:** n=103, yetersiz orneklem
- **REJECTION:** n=13, yetersiz orneklem

### LINKUSDT

- **CONSOLIDATION:** n=1999, exp=-0.98R [-1.12, -0.85] — **negatif expectancy, kacinilmali**
- **EXPANSION:** n=110, exp=-1.66R [-1.66, -1.66] — **negatif expectancy, kacinilmali**
- **REJECTION:** n=0, yetersiz orneklem

### XRPUSDT

- **CONSOLIDATION:** n=1042, exp=-0.77R [-1.11, -0.54] — **negatif expectancy, kacinilmali**
- **EXPANSION:** n=9, yetersiz orneklem
- **REJECTION:** n=5, yetersiz orneklem

### ATOMUSDT

- **CONSOLIDATION:** n=2998, exp=+0.75R [+0.56, +0.94] — **olumlu edge**
- **EXPANSION:** n=817, yetersiz orneklem
- **REJECTION:** n=69, yetersiz orneklem

### ADAUSDT

- **CONSOLIDATION:** n=2372, exp=+0.08R [-0.10, +0.32] — sifiri kapsiyor, belirsiz
- **EXPANSION:** n=130, yetersiz orneklem
- **REJECTION:** n=6, yetersiz orneklem

### APTUSDT

- **CONSOLIDATION:** n=1372, exp=-0.10R [-0.39, +0.21] — sifiri kapsiyor, belirsiz
- **EXPANSION:** n=192, exp=+0.89R [-0.41, +1.33] — sifiri kapsiyor, belirsiz
- **REJECTION:** n=80, exp=-0.80R [-1.55, +0.70] — sifiri kapsiyor, belirsiz

### DOTUSDT

- **CONSOLIDATION:** n=837, exp=-1.37R [-1.60, -1.07] — **negatif expectancy, kacinilmali**
- **EXPANSION:** n=105, yetersiz orneklem
- **REJECTION:** n=1, yetersiz orneklem

### NEARUSDT

- **CONSOLIDATION:** n=1050, exp=-1.09R [-1.37, -0.77] — **negatif expectancy, kacinilmali**
- **EXPANSION:** n=111, yetersiz orneklem
- **REJECTION:** n=13, yetersiz orneklem

### ETHUSDT

- **CONSOLIDATION:** n=839, exp=-1.27R [-1.67, -0.69] — **negatif expectancy, kacinilmali**
- **EXPANSION:** n=71, yetersiz orneklem
- **REJECTION:** n=0, yetersiz orneklem

### SUIUSDT

- **CONSOLIDATION:** n=1233, exp=-0.70R [-1.17, -0.25] — **negatif expectancy, kacinilmali**
- **EXPANSION:** n=131, yetersiz orneklem
- **REJECTION:** n=1, yetersiz orneklem


---

## 9. C2 Mum Anatomisi × Continuation

### 9a. C2 Anatomi Metrikleri — Tanimlayici Istatistikler

| Metrik | p25 | p50 | p75 | Ortalama |
|---|---|---|---|---|
| body_ratio           | +0.2609 | +0.4690 | +0.6800 | +0.4681 |
| upper_wick_ratio     | +0.0833 | +0.2039 | +0.3845 | +0.2509 |
| lower_wick_ratio     | +0.1068 | +0.2450 | +0.4231 | +0.2810 |
| clv                  | -0.4953 | +0.0370 | +0.6000 | +0.0436 |
| gap_atr_ratio        | +0.2344 | +0.4384 | +0.7464 | +0.6322 |

### 9b. Spearman Korelasyonu: C2 Metrikleri × Continuation

| Metrik | Cont@10 rho | Cont@20 rho | Cont@40 rho |
|---|---|---|---|
| body_ratio           | +0.0005 | +0.0066 | +0.0020 |
| upper_wick_ratio     | -0.0178 | -0.0139 | -0.0245 |
| lower_wick_ratio     | +0.0146 | +0.0041 | +0.0174 |
| clv                  | +0.0081 | +0.0066 | +0.0162 |
| gap_atr_ratio        | -0.1536 | -0.1249 | -0.1171 |

### 9c. Body_Ratio Quartile × Continuation (Kategori Bagimsiz)

| Kategori | Body_Q | N | Mit% | Cont@10% | NetExp (rr_new) |
|---|---|---|---|---|---|
| CONSOLIDATION | Q1(0.07-0.56) | 5675 |   3.5 |  52.8 |  -0.51R |
| CONSOLIDATION | Q2(0.56-0.71) | 5662 |   4.7 |  52.2 |  -0.52R |
| CONSOLIDATION | Q3(0.71-0.83) | 5933 |   7.4 |  67.4 |  -0.00R |
| CONSOLIDATION | Q4(0.83-1.00) | 5634 |   7.0 |  26.1 |  -0.72R |
| EXPANSION     | Q1(0.10-0.49) |  480 |   0.4 |  50.0 |  -0.01R |
| EXPANSION     | Q2(0.49-0.64) |  485 |   1.2 |  83.3 |  -1.66R |
| EXPANSION     | Q3(0.64-0.75) |  484 |   0.0 |   0.0 |  +0.00R |
| EXPANSION     | Q4(0.75-1.00) |  479 |   1.0 |  40.0 |  +1.33R |
| REJECTION     | Q1(0.63-0.82) |   52 |   7.7 |  25.0 |  -0.80R |
| REJECTION     | Q2(0.82-0.87) |   75 |   5.3 |  25.0 |  -0.80R |
| REJECTION     | Q3(0.87-0.90) |  141 |   0.0 |   0.0 |  +0.00R |
| REJECTION     | Q4(0.90-0.92) |   75 |   0.0 |   0.0 |  +0.00R |

---

## 10. Retracement Derinligi × Continuation

| Derinlik | WICK_ONLY N | WICK_ONLY Cont@10% | WICK_ONLY Cont@40% | WICK_ONLY NetExp | BODY_CLOSE N | BODY_CLOSE Cont@10% | BODY_CLOSE Cont@40% | BODY_CLOSE NetExp |
|---|---|---|---|---|---|---|---|---|
| 0-25% | 4981 | 65.9 | 57.0 | +1.45R | 452 | 30.3 | 34.1 | +1.59R |
| 25-50% | 3827 | 70.1 | 62.9 | +1.52R | 835 | 66.8 | 44.0 | +1.66R |
| 50-75% | 3222 | 71.2 | 57.1 | +1.46R | 1415 | 58.6 | 50.7 | +1.65R |
| 75-100% | 2323 | 69.0 | 56.3 | +1.47R | 1757 | 66.0 | 57.4 | +1.59R |
| 100-150% | 11617 | 35.2 | 40.2 | -0.43R | 4955 | 56.4 | 51.7 | +0.91R |
| >150% | 44517 | 36.1 | 41.3 | -1.20R | 7736 | 50.5 | 51.7 | +0.10R |

---

## 11. Entry Delay — FVG'den Kac Mum Sonra Ilk Touch?

FVG olusumundan sonra fiyatin FVG bolgesine ilk kez girdigi mum sayisi.
Dusuk = hizli reaksiyon, yuksek = gecikmeli giris.

| Coin | Kategori | N_touch | p25 | p50 | p75 | <=5b | <=10b | <=20b |
|---|---|---|---|---|---|---|---|---|
| BTCUSDT  | CONSOLIDATION |    11 |  14 |  49 |  63 |   0.0 |   0.0 |  36.4 |
| BNBUSDT  | CONSOLIDATION |    16 |   4 |  31 |  35 |  37.5 |  37.5 |  37.5 |
| SOLUSDT  | CONSOLIDATION |     4 |  55 | 188 | 191 |   0.0 |   0.0 |   0.0 |
| AVAXUSDT | CONSOLIDATION |    66 |   7 |  33 | 109 |  21.2 |  30.3 |  37.9 |
| LINKUSDT | CONSOLIDATION |   261 |   9 |  64 | 114 |  17.6 |  28.0 |  34.1 |
| LINKUSDT | EXPANSION     |     3 |  39 |  40 |  43 |   0.0 |   0.0 |   0.0 |
| XRPUSDT  | CONSOLIDATION |    86 |  10 |  39 | 107 |  19.8 |  25.6 |  33.7 |
| XRPUSDT  | EXPANSION     |     1 |   1 |   1 |   1 | 100.0 | 100.0 | 100.0 |
| ATOMUSDT | CONSOLIDATION |   250 |  31 | 105 | 147 |  18.0 |  22.0 |  24.0 |
| ADAUSDT  | CONSOLIDATION |   167 |  14 |  59 |  86 |  19.2 |  22.2 |  29.3 |
| APTUSDT  | CONSOLIDATION |    82 |   8 |  24 |  98 |  19.5 |  26.8 |  46.3 |
| APTUSDT  | EXPANSION     |     6 | 178 | 190 | 192 |   0.0 |   0.0 |   0.0 |
| APTUSDT  | REJECTION     |     4 |   1 |   3 | 125 |  75.0 |  75.0 |  75.0 |
| DOTUSDT  | CONSOLIDATION |    53 |   3 |  30 | 125 |  28.3 |  32.1 |  41.5 |
| NEARUSDT | CONSOLIDATION |    97 |  23 |  41 | 138 |   9.3 |  12.4 |  23.7 |
| ETHUSDT  | CONSOLIDATION |    81 |  12 |  60 |  98 |  14.8 |  21.0 |  34.6 |
| ETHUSDT  | EXPANSION     |     2 |  10 |  12 |  12 |   0.0 |  50.0 | 100.0 |
| SUIUSDT  | CONSOLIDATION |    75 |   0 |  25 |  75 |  41.3 |  45.3 |  46.7 |
| SUIUSDT  | EXPANSION     |     1 |  22 |  22 |  22 |   0.0 |   0.0 |   0.0 |

---

## 12. V4 Filtre Kirilimi

V4 motorunda trigger-ready FVG'lerin hangi asamada elendigini gosterir.

| Coin | Toplam FVG | ENTERED | FVG_QUALITY | FVG_VALIDITY | MIN_RISK | CBDR/SHOULD_TRADE | QTY_ZERO |
|---|---|---|---|---|---|---|---|
| BTCUSDT  |  14068 |   2678 |      0 |      0 |     33 |  11357 |      0 |
| BNBUSDT  |  17695 |   3372 |      0 |      0 |     42 |  14281 |      0 |
| SOLUSDT  |   5947 |   5884 |      0 |      0 |     63 |      0 |      0 |
| AVAXUSDT |   5951 |   5884 |      0 |      0 |     67 |      0 |      0 |
| LINKUSDT |  11063 |   4786 |      0 |      0 |     39 |   6238 |      0 |
| XRPUSDT  |   6555 |   6475 |      0 |      0 |     80 |      0 |      0 |
| ATOMUSDT |  13629 |   3360 |      0 |      0 |     43 |  10226 |      0 |
| ADAUSDT  |  12823 |   4999 |      0 |      0 |     74 |   7750 |      0 |
| APTUSDT  |   9091 |   5664 |      0 |      0 |     57 |   3370 |      0 |
| DOTUSDT  |   5607 |   5537 |      0 |      0 |     70 |      0 |      0 |
| NEARUSDT |   6719 |   6648 |      0 |      0 |     71 |      0 |      0 |
| ETHUSDT  |   4736 |   4670 |      0 |      0 |     66 |      0 |      0 |
| SUIUSDT  |   6149 |   6066 |      0 |      0 |     83 |      0 |      0 |

---

## 13. Hipotez Testi: Derinlik × Continuation Iliskisi

- **TUM FVG'ler** — Sig(<=50%, n=10379): 0.658 [0.648,0.667] | Derin(>50%, n=77346): 0.422 [0.418,0.426] | Sig > Derin (dusuk depth daha iyi)
- **WICK_ONLY** — Sig(<=50%, n=7883): 0.687 [0.678,0.696] | Derin(>50%, n=61550): 0.389 [0.385,0.394] | Sig > Derin (dusuk depth daha iyi)
- **BODY_CLOSE** — Sig(<=50%, n=1321): 0.530 [0.500,0.556] | Derin(>50%, n=15796): 0.549 [0.542,0.555] | ANLAMLI FARK YOK

---

## 14. Early London (02:00-08:00 UTC) Performansi

| Coin | Kategori | EL_N | EL_Mit% | EL_NetExp | Normal_N | Normal_Mit% | Normal_NetExp | Delta_Mit | Delta_Exp |
|---|---|---|---|---|---|---|---|---|---|
| BTCUSDT  | CONSOLIDATION |  532 |   0.0 |   -1.22R | 2211 |   0.0 |   -1.22R |  +0.0 |   +0.00R |
| BTCUSDT  | EXPANSION     |    0 |   0.0 |   +0.00R |   10 |   0.0 |   +0.00R |  +0.0 |   +0.00R |
| BNBUSDT  | CONSOLIDATION |   97 |   0.0 |   +0.00R | 3631 |   0.0 |   -0.26R |  +0.0 |   +0.26R |
| BNBUSDT  | EXPANSION     |    4 |   0.0 |   +0.00R |   56 |   0.0 |   +0.00R |  +0.0 |   +0.00R |
| SOLUSDT  | CONSOLIDATION |  155 |   1.3 |   +1.80R |  895 |   0.0 |   +1.40R |  +1.3 |   +0.40R |
| SOLUSDT  | EXPANSION     |   17 |   0.0 |   +0.00R |   40 |   0.0 |   +0.00R |  +0.0 |   +0.00R |
| SOLUSDT  | REJECTION     |    0 |   0.0 |   +0.00R |   11 |   0.0 |   +0.00R |  +0.0 |   +0.00R |
| AVAXUSDT | CONSOLIDATION |   74 |   0.0 |   +0.00R | 1100 |   2.5 |   -0.67R |  -2.5 |   +0.67R |
| AVAXUSDT | EXPANSION     |    9 |   0.0 |   +0.00R |   94 |   0.0 |   +0.00R |  +0.0 |   +0.00R |
| AVAXUSDT | REJECTION     |    0 |   0.0 |   +0.00R |   13 |   0.0 |   +0.00R |  +0.0 |   +0.00R |
| LINKUSDT | CONSOLIDATION |   81 |  13.6 |   -1.31R | 1918 |   3.8 |   -0.96R |  +9.8 |   -0.35R |
| LINKUSDT | EXPANSION     |    9 |   0.0 |   +0.00R |  101 |   3.0 |   -1.66R |  -3.0 |   +1.66R |
| XRPUSDT  | CONSOLIDATION |  219 |   1.8 |   -0.66R |  823 |   4.6 |   -0.79R |  -2.8 |   +0.13R |
| XRPUSDT  | EXPANSION     |    0 |   0.0 |   +0.00R |    9 |   0.0 |   -2.42R |  +0.0 |   +2.42R |
| XRPUSDT  | REJECTION     |    0 |   0.0 |   +0.00R |    5 |   0.0 |   +0.00R |  +0.0 |   +0.00R |
| ATOMUSDT | CONSOLIDATION |  694 |   3.7 |   +0.93R | 2304 |   3.6 |   +0.68R |  +0.1 |   +0.25R |
| ATOMUSDT | EXPANSION     |  220 |   0.0 |   +0.00R |  597 |   0.0 |   +0.00R |  +0.0 |   +0.00R |
| ATOMUSDT | REJECTION     |   24 |   0.0 |   +0.00R |   45 |   0.0 |   +0.00R |  +0.0 |   +0.00R |
| ADAUSDT  | CONSOLIDATION |  345 |   0.9 |   -0.37R | 2027 |   3.2 |   +0.14R |  -2.3 |   -0.52R |
| ADAUSDT  | EXPANSION     |   28 |   0.0 |   +0.00R |  102 |   0.0 |   +0.00R |  +0.0 |   +0.00R |
| ADAUSDT  | REJECTION     |    1 |   0.0 |   +0.00R |    5 |   0.0 |   +0.00R |  +0.0 |   +0.00R |
| APTUSDT  | CONSOLIDATION |   72 |   2.8 |   +0.27R | 1300 |   1.5 |   -0.12R |  +1.2 |   +0.38R |
| APTUSDT  | EXPANSION     |   10 |   0.0 |   +0.00R |  182 |   2.7 |   +0.89R |  -2.7 |   -0.89R |
| APTUSDT  | REJECTION     |    9 |   0.0 |   +1.45R |   71 |   4.2 |   -1.55R |  -4.2 |   +3.00R |
| DOTUSDT  | CONSOLIDATION |  252 |   2.4 |   -1.48R |  585 |   0.9 |   -1.30R |  +1.5 |   -0.18R |
| DOTUSDT  | EXPANSION     |   48 |   0.0 |   +0.00R |   57 |   0.0 |   +0.00R |  +0.0 |   +0.00R |
| DOTUSDT  | REJECTION     |    0 |   0.0 |   +0.00R |    1 |   0.0 |   +0.00R |  +0.0 |   +0.00R |
| NEARUSDT | CONSOLIDATION |   68 |   2.9 |   -0.26R |  982 |   3.1 |   -1.14R |  -0.1 |   +0.88R |
| NEARUSDT | EXPANSION     |    7 |   0.0 |   +0.00R |  104 |   0.0 |   +0.00R |  +0.0 |   +0.00R |
| NEARUSDT | REJECTION     |    0 |   0.0 |   +0.00R |   13 |   0.0 |   +0.00R |  +0.0 |   +0.00R |
| ETHUSDT  | CONSOLIDATION |  234 |   2.1 |   -1.10R |  605 |   5.8 |   -1.30R |  -3.6 |   +0.20R |
| ETHUSDT  | EXPANSION     |   18 |   0.0 |   +0.00R |   53 |   0.0 |   -1.27R |  +0.0 |   +1.27R |
| SUIUSDT  | CONSOLIDATION |  282 |   1.4 |   -0.06R |  951 |   4.5 |   -0.87R |  -3.1 |   +0.81R |
| SUIUSDT  | EXPANSION     |   23 |   0.0 |   +0.00R |  108 |   0.9 |   +1.27R |  -0.9 |   -1.27R |
| SUIUSDT  | REJECTION     |    0 |   0.0 |   +0.00R |    1 |   0.0 |   +0.00R |  +0.0 |   +0.00R |

---

## 15. Coin × Aylik / Sezon Analizi

### 15a. Coin × Ay Mitigasyon Orani

| Coin | Kategori | Ay | N | Mit% | NetExp |
|---|---|---|---|---|---|
| BTCUSDT  | CONSOLIDATION |  1 |  266 |   0.0 |  +0.00R |
| BTCUSDT  | CONSOLIDATION |  2 |  222 |   0.0 |  +0.00R |
| BTCUSDT  | CONSOLIDATION |  3 |  160 |   0.0 |  +0.00R |
| BTCUSDT  | CONSOLIDATION |  4 |  427 |   0.0 |  +0.00R |
| BTCUSDT  | CONSOLIDATION |  5 |  208 |   0.0 |  +0.00R |
| BTCUSDT  | CONSOLIDATION |  6 |  502 |   0.0 |  -1.22R |
| BTCUSDT  | CONSOLIDATION |  7 |  121 |   0.0 |  +0.00R |
| BTCUSDT  | CONSOLIDATION |  8 |  116 |   0.0 |  +0.00R |
| BTCUSDT  | CONSOLIDATION |  9 |  113 |   0.0 |  +0.00R |
| BTCUSDT  | CONSOLIDATION | 10 |  139 |   0.0 |  +0.00R |
| BTCUSDT  | CONSOLIDATION | 11 |  214 |   0.0 |  +0.00R |
| BTCUSDT  | CONSOLIDATION | 12 |  255 |   0.0 |  +0.00R |
| BTCUSDT  | EXPANSION     |  5 |    4 |   0.0 |  +0.00R |
| BTCUSDT  | EXPANSION     |  6 |    6 |   0.0 |  +0.00R |
| BNBUSDT  | CONSOLIDATION |  1 |  560 |   0.0 |  -0.26R |
| BNBUSDT  | CONSOLIDATION |  2 |  309 |   0.0 |  +0.00R |
| BNBUSDT  | CONSOLIDATION |  3 |  256 |   0.0 |  +0.00R |
| BNBUSDT  | CONSOLIDATION |  4 |  333 |   0.0 |  +0.00R |
| BNBUSDT  | CONSOLIDATION |  5 |  580 |   0.0 |  +0.00R |
| BNBUSDT  | CONSOLIDATION |  6 |  428 |   0.0 |  +0.00R |
| BNBUSDT  | CONSOLIDATION |  7 |  204 |   0.0 |  +0.00R |
| BNBUSDT  | CONSOLIDATION |  8 |  246 |   0.0 |  +0.00R |
| BNBUSDT  | CONSOLIDATION |  9 |  246 |   0.0 |  +0.00R |
| BNBUSDT  | CONSOLIDATION | 10 |  240 |   0.0 |  +0.00R |
| BNBUSDT  | CONSOLIDATION | 11 |  131 |   0.0 |  +0.00R |
| BNBUSDT  | CONSOLIDATION | 12 |  195 |   0.0 |  +0.00R |
| BNBUSDT  | EXPANSION     |  1 |    5 |   0.0 |  +0.00R |
| BNBUSDT  | EXPANSION     |  2 |   52 |   0.0 |  +0.00R |
| BNBUSDT  | EXPANSION     | 10 |    3 |   0.0 |  +0.00R |
| SOLUSDT  | CONSOLIDATION |  1 |   69 |   0.0 |  +1.40R |
| SOLUSDT  | CONSOLIDATION |  2 |   65 |   3.1 |  +1.80R |
| SOLUSDT  | CONSOLIDATION |  3 |  158 |   0.0 |  +0.00R |
| SOLUSDT  | CONSOLIDATION |  4 |   99 |   0.0 |  +0.00R |
| SOLUSDT  | CONSOLIDATION |  5 |   84 |   0.0 |  +0.00R |
| SOLUSDT  | CONSOLIDATION |  6 |  144 |   0.0 |  +0.00R |
| SOLUSDT  | CONSOLIDATION |  7 |   71 |   0.0 |  +0.00R |
| SOLUSDT  | CONSOLIDATION |  8 |   97 |   0.0 |  +0.00R |
| SOLUSDT  | CONSOLIDATION |  9 |   36 |   0.0 |  +0.00R |
| SOLUSDT  | CONSOLIDATION | 10 |   38 |   0.0 |  +0.00R |
| SOLUSDT  | CONSOLIDATION | 11 |  106 |   0.0 |  +0.00R |
| SOLUSDT  | CONSOLIDATION | 12 |   83 |   0.0 |  +0.00R |
| SOLUSDT  | EXPANSION     |  1 |    3 |   0.0 |  +0.00R |
| SOLUSDT  | EXPANSION     |  2 |    5 |   0.0 |  +0.00R |
| SOLUSDT  | EXPANSION     |  4 |    3 |   0.0 |  +0.00R |
| SOLUSDT  | EXPANSION     |  6 |   26 |   0.0 |  +0.00R |
| SOLUSDT  | EXPANSION     |  8 |    1 |   0.0 |  +0.00R |
| SOLUSDT  | EXPANSION     |  9 |    6 |   0.0 |  +0.00R |
| SOLUSDT  | EXPANSION     | 10 |   12 |   0.0 |  +0.00R |
| SOLUSDT  | EXPANSION     | 12 |    1 |   0.0 |  +0.00R |
| SOLUSDT  | REJECTION     |  1 |   11 |   0.0 |  +0.00R |
| AVAXUSDT | CONSOLIDATION |  1 |  136 |   8.8 |  -0.18R |
| AVAXUSDT | CONSOLIDATION |  2 |   72 |   1.4 |  +0.51R |
| AVAXUSDT | CONSOLIDATION |  3 |  102 |   0.0 |  +0.00R |
| AVAXUSDT | CONSOLIDATION |  4 |  109 |   0.9 |  -1.27R |
| AVAXUSDT | CONSOLIDATION |  5 |  168 |   8.3 |  -0.69R |
| AVAXUSDT | CONSOLIDATION |  6 |  148 |   0.0 |  +0.00R |
| AVAXUSDT | CONSOLIDATION |  7 |   31 |   0.0 |  +0.00R |
| AVAXUSDT | CONSOLIDATION |  8 |   68 |   0.0 |  +0.00R |
| AVAXUSDT | CONSOLIDATION |  9 |   91 |   0.0 |  +0.00R |
| AVAXUSDT | CONSOLIDATION | 10 |   54 |   0.0 |  +0.00R |
| AVAXUSDT | CONSOLIDATION | 11 |   70 |   0.0 |  +0.00R |
| AVAXUSDT | CONSOLIDATION | 12 |  125 |   0.0 |  +0.00R |
| AVAXUSDT | EXPANSION     |  1 |    9 |   0.0 |  +0.00R |
| AVAXUSDT | EXPANSION     |  2 |   13 |   0.0 |  +0.00R |
| AVAXUSDT | EXPANSION     |  3 |   19 |   0.0 |  +0.00R |
| AVAXUSDT | EXPANSION     |  4 |    7 |   0.0 |  +0.00R |
| AVAXUSDT | EXPANSION     |  5 |    7 |   0.0 |  +0.00R |
| AVAXUSDT | EXPANSION     |  6 |   15 |   0.0 |  +0.00R |
| AVAXUSDT | EXPANSION     |  7 |    3 |   0.0 |  +0.00R |
| AVAXUSDT | EXPANSION     |  8 |   14 |   0.0 |  +0.00R |
| AVAXUSDT | EXPANSION     |  9 |    2 |   0.0 |  +0.00R |
| AVAXUSDT | EXPANSION     | 10 |    3 |   0.0 |  +0.00R |
| AVAXUSDT | EXPANSION     | 12 |   11 |   0.0 |  +0.00R |
| AVAXUSDT | REJECTION     |  1 |    2 |   0.0 |  +0.00R |
| AVAXUSDT | REJECTION     |  2 |   11 |   0.0 |  +0.00R |
| LINKUSDT | CONSOLIDATION |  1 |  258 |   1.6 |  -1.20R |
| LINKUSDT | CONSOLIDATION |  2 |  280 |   0.7 |  -2.45R |
| LINKUSDT | CONSOLIDATION |  3 |   81 |  16.0 |  -1.50R |
| LINKUSDT | CONSOLIDATION |  4 |  199 |  10.6 |  +0.60R |
| LINKUSDT | CONSOLIDATION |  5 |  305 |   4.3 |  -1.34R |
| LINKUSDT | CONSOLIDATION |  6 |  184 |   1.6 |  -0.24R |
| LINKUSDT | CONSOLIDATION |  7 |   88 |   0.0 |  -1.49R |
| LINKUSDT | CONSOLIDATION |  8 |  216 |   0.0 |  +0.00R |
| LINKUSDT | CONSOLIDATION |  9 |  112 |  22.3 |  -0.91R |
| LINKUSDT | CONSOLIDATION | 10 |   29 |   0.0 |  +0.00R |
| LINKUSDT | CONSOLIDATION | 11 |   92 |   2.2 |  +1.21R |
| LINKUSDT | CONSOLIDATION | 12 |  155 |   0.0 |  +0.00R |
| LINKUSDT | EXPANSION     |  1 |   24 |   0.0 |  +0.00R |
| LINKUSDT | EXPANSION     |  2 |    9 |   0.0 |  +0.00R |
| LINKUSDT | EXPANSION     |  3 |    2 |   0.0 |  +0.00R |
| LINKUSDT | EXPANSION     |  4 |    5 |   0.0 |  +0.00R |
| LINKUSDT | EXPANSION     |  5 |   47 |   6.4 |  -1.66R |
| LINKUSDT | EXPANSION     |  6 |    2 |   0.0 |  +0.00R |
| LINKUSDT | EXPANSION     |  7 |    4 |   0.0 |  +0.00R |
| LINKUSDT | EXPANSION     |  9 |    3 |   0.0 |  +0.00R |
| LINKUSDT | EXPANSION     | 11 |    1 |   0.0 |  +0.00R |
| LINKUSDT | EXPANSION     | 12 |   13 |   0.0 |  +0.00R |
| XRPUSDT  | CONSOLIDATION |  1 |  119 |   3.4 |  -0.49R |
| XRPUSDT  | CONSOLIDATION |  2 |   82 |   1.2 |  +1.16R |
| XRPUSDT  | CONSOLIDATION |  3 |  106 |   0.0 |  +1.23R |
| XRPUSDT  | CONSOLIDATION |  4 |   80 |  21.2 |  +0.47R |
| XRPUSDT  | CONSOLIDATION |  5 |   67 |   3.0 |  +0.86R |
| XRPUSDT  | CONSOLIDATION |  6 |  127 |   0.0 |  +0.00R |
| XRPUSDT  | CONSOLIDATION |  7 |   68 |  13.2 |  -1.89R |
| XRPUSDT  | CONSOLIDATION |  8 |  104 |   1.9 |  -0.99R |
| XRPUSDT  | CONSOLIDATION |  9 |   34 |  14.7 |  -1.38R |
| XRPUSDT  | CONSOLIDATION | 10 |   56 |   1.8 |  -1.42R |
| XRPUSDT  | CONSOLIDATION | 11 |  109 |   0.9 |  -2.41R |
| XRPUSDT  | CONSOLIDATION | 12 |   90 |   0.0 |  +0.00R |
| ATOMUSDT | CONSOLIDATION |  1 |  233 |   0.0 |  +0.00R |
| ATOMUSDT | CONSOLIDATION |  2 |  281 |  17.4 |  +0.64R |
| ATOMUSDT | CONSOLIDATION |  3 |  325 |   0.0 |  +0.00R |
| ATOMUSDT | CONSOLIDATION |  4 |  431 |   0.0 |  +0.00R |
| ATOMUSDT | CONSOLIDATION |  5 |  422 |   0.0 |  +0.00R |
| ATOMUSDT | CONSOLIDATION |  6 |  149 |   0.0 |  +0.00R |
| ATOMUSDT | CONSOLIDATION |  7 |   57 |   0.0 |  +0.00R |
| ATOMUSDT | CONSOLIDATION |  8 |  167 |   0.0 |  +0.00R |
| ATOMUSDT | CONSOLIDATION |  9 |  272 |   0.0 |  +0.00R |
| ATOMUSDT | CONSOLIDATION | 10 |  124 |   0.0 |  +0.00R |
| ATOMUSDT | CONSOLIDATION | 11 |  247 |  24.3 |  +1.65R |
| ATOMUSDT | CONSOLIDATION | 12 |  290 |   0.0 |  +0.37R |
| ATOMUSDT | EXPANSION     |  1 |   69 |   0.0 |  +0.00R |
| ATOMUSDT | EXPANSION     |  2 |  129 |   0.0 |  +0.00R |
| ATOMUSDT | EXPANSION     |  3 |  142 |   0.0 |  +0.00R |
| ATOMUSDT | EXPANSION     |  4 |   70 |   0.0 |  +0.00R |
| ATOMUSDT | EXPANSION     |  5 |  133 |   0.0 |  +0.00R |
| ATOMUSDT | EXPANSION     |  6 |   95 |   0.0 |  +0.00R |
| ATOMUSDT | EXPANSION     |  8 |   28 |   0.0 |  +0.00R |
| ATOMUSDT | EXPANSION     |  9 |   69 |   0.0 |  +0.00R |
| ATOMUSDT | EXPANSION     | 10 |   21 |   0.0 |  +0.00R |
| ATOMUSDT | EXPANSION     | 11 |    4 |   0.0 |  +0.00R |
| ATOMUSDT | EXPANSION     | 12 |   57 |   0.0 |  +0.00R |
| ATOMUSDT | REJECTION     |  5 |   69 |   0.0 |  +0.00R |
| ADAUSDT  | CONSOLIDATION |  1 |  181 |   0.0 |  +0.00R |
| ADAUSDT  | CONSOLIDATION |  2 |  311 |   5.1 |  +1.14R |
| ADAUSDT  | CONSOLIDATION |  3 |  138 |   0.0 |  +0.00R |
| ADAUSDT  | CONSOLIDATION |  4 |  263 |  17.1 |  +0.12R |
| ADAUSDT  | CONSOLIDATION |  5 |  380 |   0.0 |  +0.00R |
| ADAUSDT  | CONSOLIDATION |  6 |  263 |   0.0 |  +0.00R |
| ADAUSDT  | CONSOLIDATION |  7 |  144 |   0.0 |  +0.00R |
| ADAUSDT  | CONSOLIDATION |  8 |   69 |   0.0 |  +0.00R |
| ADAUSDT  | CONSOLIDATION |  9 |   40 |   0.0 |  +0.00R |
| ADAUSDT  | CONSOLIDATION | 10 |  236 |   0.0 |  -1.73R |
| ADAUSDT  | CONSOLIDATION | 11 |  121 |   5.8 |  -0.90R |
| ADAUSDT  | CONSOLIDATION | 12 |  226 |   0.0 |  +0.00R |
| ADAUSDT  | EXPANSION     |  1 |   29 |   0.0 |  +0.00R |
| ADAUSDT  | EXPANSION     |  2 |    3 |   0.0 |  +0.00R |
| ADAUSDT  | EXPANSION     |  3 |    4 |   0.0 |  +0.00R |
| ADAUSDT  | EXPANSION     |  4 |   32 |   0.0 |  +0.00R |
| ADAUSDT  | EXPANSION     |  6 |   12 |   0.0 |  +0.00R |
| ADAUSDT  | EXPANSION     |  8 |   36 |   0.0 |  +0.00R |
| ADAUSDT  | EXPANSION     |  9 |    4 |   0.0 |  +0.00R |
| ADAUSDT  | EXPANSION     | 10 |    8 |   0.0 |  +0.00R |
| ADAUSDT  | EXPANSION     | 11 |    2 |   0.0 |  +0.00R |
| APTUSDT  | CONSOLIDATION |  1 |  115 |   0.0 |  -0.16R |
| APTUSDT  | CONSOLIDATION |  2 |   98 |   0.0 |  +0.00R |
| APTUSDT  | CONSOLIDATION |  3 |   50 |   0.0 |  +0.00R |
| APTUSDT  | CONSOLIDATION |  4 |  190 |   3.2 |  +0.01R |
| APTUSDT  | CONSOLIDATION |  5 |  145 |   4.1 |  +1.42R |
| APTUSDT  | CONSOLIDATION |  6 |  197 |   2.5 |  -1.11R |
| APTUSDT  | CONSOLIDATION |  7 |   88 |   0.0 |  +0.00R |
| APTUSDT  | CONSOLIDATION |  8 |   85 |   0.0 |  +0.00R |
| APTUSDT  | CONSOLIDATION |  9 |  195 |   0.0 |  +0.00R |
| APTUSDT  | CONSOLIDATION | 10 |   54 |   9.3 |  +1.17R |
| APTUSDT  | CONSOLIDATION | 11 |   85 |   0.0 |  -3.29R |
| APTUSDT  | CONSOLIDATION | 12 |   70 |   0.0 |  +0.00R |
| APTUSDT  | EXPANSION     |  1 |   30 |   0.0 |  +0.00R |
| APTUSDT  | EXPANSION     |  2 |   14 |  35.7 |  +0.89R |
| APTUSDT  | EXPANSION     |  4 |    3 |   0.0 |  +0.00R |
| APTUSDT  | EXPANSION     |  5 |   96 |   0.0 |  +0.00R |
| APTUSDT  | EXPANSION     |  6 |    2 |   0.0 |  +0.00R |
| APTUSDT  | EXPANSION     |  7 |   13 |   0.0 |  +0.00R |
| APTUSDT  | EXPANSION     |  8 |    6 |   0.0 |  +0.00R |
| APTUSDT  | EXPANSION     |  9 |    4 |   0.0 |  +0.00R |
| APTUSDT  | EXPANSION     | 10 |   18 |   0.0 |  +0.00R |
| APTUSDT  | EXPANSION     | 11 |    1 |   0.0 |  +0.00R |
| APTUSDT  | EXPANSION     | 12 |    5 |   0.0 |  +0.00R |
| APTUSDT  | REJECTION     |  1 |    5 |   0.0 |  +0.00R |
| APTUSDT  | REJECTION     |  5 |    4 |  75.0 |  -0.80R |
| APTUSDT  | REJECTION     |  7 |   71 |   0.0 |  +0.00R |
| DOTUSDT  | CONSOLIDATION |  1 |   94 |   5.3 |  -1.47R |
| DOTUSDT  | CONSOLIDATION |  2 |   71 |   4.2 |  -1.57R |
| DOTUSDT  | CONSOLIDATION |  3 |   81 |   0.0 |  +0.00R |
| DOTUSDT  | CONSOLIDATION |  4 |   87 |   1.1 |  -1.26R |
| DOTUSDT  | CONSOLIDATION |  5 |   64 |   3.1 |  -0.69R |
| DOTUSDT  | CONSOLIDATION |  6 |  145 |   0.0 |  +0.00R |
| DOTUSDT  | CONSOLIDATION |  7 |   75 |   0.0 |  +0.00R |
| DOTUSDT  | CONSOLIDATION |  8 |   65 |   0.0 |  +0.00R |
| DOTUSDT  | CONSOLIDATION |  9 |   40 |   0.0 |  +0.00R |
| DOTUSDT  | CONSOLIDATION | 10 |   35 |   0.0 |  +0.00R |
| DOTUSDT  | CONSOLIDATION | 11 |   26 |   0.0 |  +0.00R |
| DOTUSDT  | CONSOLIDATION | 12 |   54 |   0.0 |  -1.74R |
| DOTUSDT  | EXPANSION     |  1 |    1 |   0.0 |  +0.00R |
| DOTUSDT  | EXPANSION     |  2 |    9 |   0.0 |  +0.00R |
| DOTUSDT  | EXPANSION     |  3 |   22 |   0.0 |  +0.00R |
| DOTUSDT  | EXPANSION     |  4 |   12 |   0.0 |  +0.00R |
| DOTUSDT  | EXPANSION     |  5 |   24 |   0.0 |  +0.00R |
| DOTUSDT  | EXPANSION     |  6 |   13 |   0.0 |  +0.00R |
| DOTUSDT  | EXPANSION     |  8 |    2 |   0.0 |  +0.00R |
| DOTUSDT  | EXPANSION     |  9 |    3 |   0.0 |  +0.00R |
| DOTUSDT  | EXPANSION     | 11 |    5 |   0.0 |  +0.00R |
| DOTUSDT  | EXPANSION     | 12 |   14 |   0.0 |  +0.00R |
| NEARUSDT | CONSOLIDATION |  1 |   83 |   0.0 |  -1.49R |
| NEARUSDT | CONSOLIDATION |  2 |  110 |  12.7 |  -0.06R |
| NEARUSDT | CONSOLIDATION |  3 |  144 |   1.4 |  -1.48R |
| NEARUSDT | CONSOLIDATION |  4 |  101 |   0.0 |  +0.00R |
| NEARUSDT | CONSOLIDATION |  5 |  107 |   5.6 |  -1.63R |
| NEARUSDT | CONSOLIDATION |  6 |  118 |   0.0 |  +0.00R |
| NEARUSDT | CONSOLIDATION |  7 |   86 |  11.6 |  -0.59R |
| NEARUSDT | CONSOLIDATION |  8 |   83 |   0.0 |  +0.00R |
| NEARUSDT | CONSOLIDATION |  9 |   52 |   0.0 |  -1.17R |
| NEARUSDT | CONSOLIDATION | 10 |   52 |   0.0 |  +0.00R |
| NEARUSDT | CONSOLIDATION | 11 |   78 |   0.0 |  +0.00R |
| NEARUSDT | CONSOLIDATION | 12 |   36 |   0.0 |  +0.00R |
| NEARUSDT | EXPANSION     |  1 |    6 |   0.0 |  +0.00R |
| NEARUSDT | EXPANSION     |  2 |   35 |   0.0 |  +0.00R |
| NEARUSDT | EXPANSION     |  3 |    9 |   0.0 |  +0.00R |
| NEARUSDT | EXPANSION     |  4 |    5 |   0.0 |  +0.00R |
| NEARUSDT | EXPANSION     |  5 |    5 |   0.0 |  +0.00R |
| NEARUSDT | EXPANSION     |  6 |   22 |   0.0 |  +0.00R |
| NEARUSDT | EXPANSION     |  8 |    3 |   0.0 |  +0.00R |
| NEARUSDT | EXPANSION     |  9 |    3 |   0.0 |  +0.00R |
| NEARUSDT | EXPANSION     | 10 |   15 |   0.0 |  +0.00R |
| NEARUSDT | EXPANSION     | 11 |    8 |   0.0 |  +0.00R |
| NEARUSDT | REJECTION     |  1 |   12 |   0.0 |  +0.00R |
| NEARUSDT | REJECTION     |  2 |    1 |   0.0 |  +0.00R |
| ETHUSDT  | CONSOLIDATION |  1 |   66 |  10.6 |  -0.72R |
| ETHUSDT  | CONSOLIDATION |  2 |   75 |   0.0 |  -2.24R |
| ETHUSDT  | CONSOLIDATION |  3 |   80 |   0.0 |  -5.11R |
| ETHUSDT  | CONSOLIDATION |  4 |   95 |   0.0 |  +0.00R |
| ETHUSDT  | CONSOLIDATION |  5 |   66 |   0.0 |  +0.00R |
| ETHUSDT  | CONSOLIDATION |  6 |   90 |   2.2 |  -0.39R |
| ETHUSDT  | CONSOLIDATION |  7 |   57 |   0.0 |  +0.00R |
| ETHUSDT  | CONSOLIDATION |  8 |   39 |  28.2 |  +1.11R |
| ETHUSDT  | CONSOLIDATION |  9 |   65 |   0.0 |  +0.00R |
| ETHUSDT  | CONSOLIDATION | 10 |   36 |  22.2 |  +0.32R |
| ETHUSDT  | CONSOLIDATION | 11 |   77 |  15.6 |  -2.25R |
| ETHUSDT  | CONSOLIDATION | 12 |   93 |   0.0 |  -1.59R |
| ETHUSDT  | EXPANSION     |  2 |   10 |   0.0 |  +0.00R |
| ETHUSDT  | EXPANSION     |  3 |    2 |   0.0 |  +0.00R |
| ETHUSDT  | EXPANSION     |  4 |   38 |   0.0 |  +0.00R |
| ETHUSDT  | EXPANSION     |  5 |   11 |   0.0 |  +0.00R |
| ETHUSDT  | EXPANSION     | 10 |    2 |   0.0 |  -1.27R |
| ETHUSDT  | EXPANSION     | 12 |    8 |   0.0 |  +0.00R |
| SUIUSDT  | CONSOLIDATION |  1 |  129 |  24.0 |  -1.30R |
| SUIUSDT  | CONSOLIDATION |  2 |   66 |   0.0 |  +0.00R |
| SUIUSDT  | CONSOLIDATION |  3 |   76 |   0.0 |  +0.00R |
| SUIUSDT  | CONSOLIDATION |  4 |  128 |   0.0 |  +0.00R |
| SUIUSDT  | CONSOLIDATION |  5 |  209 |   0.0 |  +0.00R |
| SUIUSDT  | CONSOLIDATION |  6 |  160 |   4.4 |  +1.89R |
| SUIUSDT  | CONSOLIDATION |  7 |   99 |   0.0 |  +0.00R |
| SUIUSDT  | CONSOLIDATION |  8 |   66 |   0.0 |  +0.00R |
| SUIUSDT  | CONSOLIDATION |  9 |   55 |   7.3 |  -1.06R |
| SUIUSDT  | CONSOLIDATION | 10 |   89 |   0.0 |  -1.30R |
| SUIUSDT  | CONSOLIDATION | 11 |   95 |   5.3 |  -0.46R |
| SUIUSDT  | CONSOLIDATION | 12 |   61 |   0.0 |  +0.00R |
| SUIUSDT  | EXPANSION     |  2 |   10 |   0.0 |  +0.00R |
| SUIUSDT  | EXPANSION     |  3 |    3 |   0.0 |  +0.00R |
| SUIUSDT  | EXPANSION     |  4 |   41 |   0.0 |  +0.00R |
| SUIUSDT  | EXPANSION     |  5 |   30 |   0.0 |  +0.00R |
| SUIUSDT  | EXPANSION     |  6 |   22 |   0.0 |  +0.00R |
| SUIUSDT  | EXPANSION     |  7 |    6 |   0.0 |  +0.00R |
| SUIUSDT  | EXPANSION     |  8 |   10 |   0.0 |  +0.00R |
| SUIUSDT  | EXPANSION     |  9 |    2 |   0.0 |  +0.00R |
| SUIUSDT  | EXPANSION     | 11 |    1 | 100.0 |  +1.27R |
| SUIUSDT  | EXPANSION     | 12 |    6 |   0.0 |  +0.00R |

### 15b. Coin × Uc Aylik (Quarterly)

| Coin | Kategori | Q | N | Mit% | NetExp |
|---|---|---|---|---|---|
| BTCUSDT  | CONSOLIDATION | Q1 |  648 |   0.0 |  +0.00R |
| BTCUSDT  | CONSOLIDATION | Q2 | 1137 |   0.0 |  -1.22R |
| BTCUSDT  | CONSOLIDATION | Q3 |  350 |   0.0 |  +0.00R |
| BTCUSDT  | CONSOLIDATION | Q4 |  608 |   0.0 |  +0.00R |
| BTCUSDT  | EXPANSION     | Q2 |   10 |   0.0 |  +0.00R |
| BNBUSDT  | CONSOLIDATION | Q1 | 1125 |   0.0 |  -0.26R |
| BNBUSDT  | CONSOLIDATION | Q2 | 1341 |   0.0 |  +0.00R |
| BNBUSDT  | CONSOLIDATION | Q3 |  696 |   0.0 |  +0.00R |
| BNBUSDT  | CONSOLIDATION | Q4 |  566 |   0.0 |  +0.00R |
| BNBUSDT  | EXPANSION     | Q1 |   57 |   0.0 |  +0.00R |
| BNBUSDT  | EXPANSION     | Q4 |    3 |   0.0 |  +0.00R |
| SOLUSDT  | CONSOLIDATION | Q1 |  292 |   0.7 |  +1.60R |
| SOLUSDT  | CONSOLIDATION | Q2 |  327 |   0.0 |  +0.00R |
| SOLUSDT  | CONSOLIDATION | Q3 |  204 |   0.0 |  +0.00R |
| SOLUSDT  | CONSOLIDATION | Q4 |  227 |   0.0 |  +0.00R |
| SOLUSDT  | EXPANSION     | Q1 |    8 |   0.0 |  +0.00R |
| SOLUSDT  | EXPANSION     | Q2 |   29 |   0.0 |  +0.00R |
| SOLUSDT  | EXPANSION     | Q3 |    7 |   0.0 |  +0.00R |
| SOLUSDT  | EXPANSION     | Q4 |   13 |   0.0 |  +0.00R |
| SOLUSDT  | REJECTION     | Q1 |   11 |   0.0 |  +0.00R |
| AVAXUSDT | CONSOLIDATION | Q1 |  310 |   4.2 |  -0.15R |
| AVAXUSDT | CONSOLIDATION | Q2 |  425 |   3.5 |  -0.89R |
| AVAXUSDT | CONSOLIDATION | Q3 |  190 |   0.0 |  +0.00R |
| AVAXUSDT | CONSOLIDATION | Q4 |  249 |   0.0 |  +0.00R |
| AVAXUSDT | EXPANSION     | Q1 |   41 |   0.0 |  +0.00R |
| AVAXUSDT | EXPANSION     | Q2 |   29 |   0.0 |  +0.00R |
| AVAXUSDT | EXPANSION     | Q3 |   19 |   0.0 |  +0.00R |
| AVAXUSDT | EXPANSION     | Q4 |   14 |   0.0 |  +0.00R |
| AVAXUSDT | REJECTION     | Q1 |   13 |   0.0 |  +0.00R |
| LINKUSDT | CONSOLIDATION | Q1 |  619 |   3.1 |  -1.36R |
| LINKUSDT | CONSOLIDATION | Q2 |  688 |   5.4 |  -0.82R |
| LINKUSDT | CONSOLIDATION | Q3 |  416 |   6.0 |  -1.09R |
| LINKUSDT | CONSOLIDATION | Q4 |  276 |   0.7 |  +1.21R |
| LINKUSDT | EXPANSION     | Q1 |   35 |   0.0 |  +0.00R |
| LINKUSDT | EXPANSION     | Q2 |   54 |   5.6 |  -1.66R |
| LINKUSDT | EXPANSION     | Q3 |    7 |   0.0 |  +0.00R |
| LINKUSDT | EXPANSION     | Q4 |   14 |   0.0 |  +0.00R |
| XRPUSDT  | CONSOLIDATION | Q1 |  307 |   1.6 |  +0.03R |
| XRPUSDT  | CONSOLIDATION | Q2 |  274 |   6.9 |  +0.51R |
| XRPUSDT  | CONSOLIDATION | Q3 |  206 |   7.8 |  -1.38R |
| XRPUSDT  | CONSOLIDATION | Q4 |  255 |   0.8 |  -1.46R |
| ATOMUSDT | CONSOLIDATION | Q1 |  839 |   5.8 |  +0.64R |
| ATOMUSDT | CONSOLIDATION | Q2 | 1002 |   0.0 |  +0.00R |
| ATOMUSDT | CONSOLIDATION | Q3 |  496 |   0.0 |  +0.00R |
| ATOMUSDT | CONSOLIDATION | Q4 |  661 |   9.1 |  +0.78R |
| ATOMUSDT | EXPANSION     | Q1 |  340 |   0.0 |  +0.00R |
| ATOMUSDT | EXPANSION     | Q2 |  298 |   0.0 |  +0.00R |
| ATOMUSDT | EXPANSION     | Q3 |   97 |   0.0 |  +0.00R |
| ATOMUSDT | EXPANSION     | Q4 |   82 |   0.0 |  +0.00R |
| ATOMUSDT | REJECTION     | Q2 |   69 |   0.0 |  +0.00R |
| ADAUSDT  | CONSOLIDATION | Q1 |  630 |   2.5 |  +1.14R |
| ADAUSDT  | CONSOLIDATION | Q2 |  906 |   5.0 |  +0.12R |
| ADAUSDT  | CONSOLIDATION | Q3 |  253 |   0.0 |  +0.00R |
| ADAUSDT  | CONSOLIDATION | Q4 |  583 |   1.2 |  -1.17R |
| ADAUSDT  | EXPANSION     | Q1 |   36 |   0.0 |  +0.00R |
| ADAUSDT  | EXPANSION     | Q2 |   44 |   0.0 |  +0.00R |
| ADAUSDT  | EXPANSION     | Q3 |   40 |   0.0 |  +0.00R |
| ADAUSDT  | EXPANSION     | Q4 |   10 |   0.0 |  +0.00R |
| APTUSDT  | CONSOLIDATION | Q1 |  263 |   0.0 |  -0.16R |
| APTUSDT  | CONSOLIDATION | Q2 |  532 |   3.2 |  +0.16R |
| APTUSDT  | CONSOLIDATION | Q3 |  368 |   0.0 |  +0.00R |
| APTUSDT  | CONSOLIDATION | Q4 |  209 |   2.4 |  -0.55R |
| APTUSDT  | EXPANSION     | Q1 |   44 |  11.4 |  +0.89R |
| APTUSDT  | EXPANSION     | Q2 |  101 |   0.0 |  +0.00R |
| APTUSDT  | EXPANSION     | Q3 |   23 |   0.0 |  +0.00R |
| APTUSDT  | EXPANSION     | Q4 |   24 |   0.0 |  +0.00R |
| APTUSDT  | REJECTION     | Q1 |    5 |   0.0 |  +0.00R |
| APTUSDT  | REJECTION     | Q2 |    4 |  75.0 |  -0.80R |
| APTUSDT  | REJECTION     | Q3 |   71 |   0.0 |  +0.00R |
| DOTUSDT  | CONSOLIDATION | Q1 |  246 |   3.3 |  -1.50R |
| DOTUSDT  | CONSOLIDATION | Q2 |  296 |   1.0 |  -1.07R |
| DOTUSDT  | CONSOLIDATION | Q3 |  180 |   0.0 |  +0.00R |
| DOTUSDT  | CONSOLIDATION | Q4 |  115 |   0.0 |  -1.74R |
| DOTUSDT  | EXPANSION     | Q1 |   32 |   0.0 |  +0.00R |
| DOTUSDT  | EXPANSION     | Q2 |   49 |   0.0 |  +0.00R |
| DOTUSDT  | EXPANSION     | Q3 |    5 |   0.0 |  +0.00R |
| DOTUSDT  | EXPANSION     | Q4 |   19 |   0.0 |  +0.00R |
| NEARUSDT | CONSOLIDATION | Q1 |  337 |   4.7 |  -0.86R |
| NEARUSDT | CONSOLIDATION | Q2 |  326 |   1.8 |  -1.63R |
| NEARUSDT | CONSOLIDATION | Q3 |  221 |   4.5 |  -0.71R |
| NEARUSDT | CONSOLIDATION | Q4 |  166 |   0.0 |  +0.00R |
| NEARUSDT | EXPANSION     | Q1 |   50 |   0.0 |  +0.00R |
| NEARUSDT | EXPANSION     | Q2 |   32 |   0.0 |  +0.00R |
| NEARUSDT | EXPANSION     | Q3 |    6 |   0.0 |  +0.00R |
| NEARUSDT | EXPANSION     | Q4 |   23 |   0.0 |  +0.00R |
| NEARUSDT | REJECTION     | Q1 |   13 |   0.0 |  +0.00R |
| ETHUSDT  | CONSOLIDATION | Q1 |  221 |   3.2 |  -1.74R |
| ETHUSDT  | CONSOLIDATION | Q2 |  251 |   0.8 |  -0.39R |
| ETHUSDT  | CONSOLIDATION | Q3 |  161 |   6.8 |  +1.11R |
| ETHUSDT  | CONSOLIDATION | Q4 |  206 |   9.7 |  -1.65R |
| ETHUSDT  | EXPANSION     | Q1 |   12 |   0.0 |  +0.00R |
| ETHUSDT  | EXPANSION     | Q2 |   49 |   0.0 |  +0.00R |
| ETHUSDT  | EXPANSION     | Q4 |   10 |   0.0 |  -1.27R |
| SUIUSDT  | CONSOLIDATION | Q1 |  271 |  11.4 |  -1.30R |
| SUIUSDT  | CONSOLIDATION | Q2 |  497 |   1.4 |  +1.89R |
| SUIUSDT  | CONSOLIDATION | Q3 |  220 |   1.8 |  -1.06R |
| SUIUSDT  | CONSOLIDATION | Q4 |  245 |   2.0 |  -0.66R |
| SUIUSDT  | EXPANSION     | Q1 |   13 |   0.0 |  +0.00R |
| SUIUSDT  | EXPANSION     | Q2 |   93 |   0.0 |  +0.00R |
| SUIUSDT  | EXPANSION     | Q3 |   18 |   0.0 |  +0.00R |
| SUIUSDT  | EXPANSION     | Q4 |    7 |  14.3 |  +1.27R |

---

## 16. Coin Bazli Esik Onerileri

Per-coin: optimal iptal bar (DR noktasi), FVG expiry, seans, ve en iyi kategori.

| Coin | Session | BestCat | Expiry (bar) | CONS_DR | EXP_DR | REJ_DR | BestMonth | WorstMonth |
|---|---|---|---|---|---|---|---|---|
| BTCUSDT  | 19:00-01:00 | BELIRSIZ     |  45b |  200b |  200b |   N/A |    7 |   10 |
| BNBUSDT  | 01:00-05:00 | CONSOLIDATION (-0.26R) |  45b |  200b |  200b |   N/A |   11 |    7 |
| SOLUSDT  | 22:00-02:00 | BELIRSIZ     |  45b |   75b |  200b |  200b |    8 |    7 |
| AVAXUSDT | 01:00-05:00 | BELIRSIZ     |  45b |    2b |  200b |  200b |   12 |    9 |
| LINKUSDT | 01:00-05:00 | BELIRSIZ     |  45b |    2b |   75b |   N/A |   10 |    5 |
| XRPUSDT  | 22:00-02:00 | BELIRSIZ     |  45b |    2b |  200b |  200b |   11 |    9 |
| ATOMUSDT | 19:00-01:00 | BELIRSIZ     |  45b |    2b |  200b |  200b |    2 |   10 |
| ADAUSDT  | 22:00-02:00 | CONSOLIDATION (+0.08R) |  45b |    2b |  200b |  200b |    8 |    9 |
| APTUSDT  | 01:00-05:00 | EXPANSION (+0.89R) |  45b |    2b |  200b |    3b |   11 |    6 |
| DOTUSDT  | 19:00-01:00 | BELIRSIZ     |  45b |    2b |  200b |   N/A |    2 |    9 |
| NEARUSDT | 01:00-05:00 | BELIRSIZ     |  45b |    2b |  200b |  200b |   11 |    9 |
| ETHUSDT  | 19:00-01:00 | BELIRSIZ     |  45b |    2b |  200b |   N/A |    7 |    9 |
| SUIUSDT  | 22:00-02:00 | BELIRSIZ     |  45b |    2b |   50b |   N/A |    5 |   10 |

---
*Auto-generated by fvg_profile_v4.py*