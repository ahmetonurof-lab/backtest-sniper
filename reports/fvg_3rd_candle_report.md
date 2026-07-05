# FVG 3. Mum Sınıflaması — Backtest Raporu (Düzeltilmiş)

**Session:** DEFAULT [22:00-02:00]
**Timeframe:** 15m
**Coinler:** BTCUSDT, BNBUSDT, SOLUSDT, AVAXUSDT, LINKUSDT, XRPUSDT, ATOMUSDT, ADAUSDT, APTUSDT, DOTUSDT, NEARUSDT, ETHUSDT, SUIUSDT
**Tarih:** 2026-07-05 19:18

**Düzeltmeler:**
- Hata 1: Session filtresi düzeltildi (22:00-02:00 artık doğru çalışıyor)
- Hata 2: R:R simülasyonu gerçek bar-bar fiyat takibi ile yeniden yazıldı
- Hata 3: ATR self-referans düzeltildi (C3 kendi ATR'sini etkilemiyor)
- Hata 4: Continuation 3 pencerede raporlanıyor (10/20/40 bar)

## Parametreler

| Parametre | Değer |
|---|---|
| EXPANSION ATR Mult | 1.5x |
| EXPANSION Body/Range | 0.7 |
| REJECTION ATR Mult | 1.0x |
| Lookback Bars | 200 |

## Coin Bazlı Özet

| Coin | FVG | CONS | EXP | REJ |
|---|---|---|---|---|
| BTCUSDT | 2220 | 2110 | 93 | 17 |
| BNBUSDT | 2573 | 2440 | 113 | 20 |
| SOLUSDT | 2217 | 2128 | 75 | 14 |
| AVAXUSDT | 2365 | 2252 | 99 | 14 |
| LINKUSDT | 2384 | 2296 | 75 | 13 |
| XRPUSDT | 2058 | 1951 | 94 | 13 |
| ATOMUSDT | 2383 | 2297 | 76 | 10 |
| ADAUSDT | 2190 | 2095 | 84 | 11 |
| APTUSDT | 2385 | 2269 | 100 | 16 |
| DOTUSDT | 2210 | 2125 | 75 | 10 |
| NEARUSDT | 2242 | 2138 | 93 | 11 |
| ETHUSDT | 2108 | 2022 | 69 | 17 |
| SUIUSDT | 2407 | 2295 | 99 | 13 |

## Toplu İstatistik

| Kategori | FVG | Mit% | Inv% | Cont10% | Cont40% | AvgBar | RR_W% | Exp | NoFill% |
|---|---|---|---|---|---|---|---|---|---|
| CONSOLIDATION | 28418 | 86.5% | 77.8% | 53.1% | 51.4% | 9 | 33.7% | +0.01R | 7.0% |
| EXPANSION | 1145 | 72.2% | 63.1% | 49.9% | 47.4% | 36 | 35.5% | +0.07R | 21.9% |
| REJECTION | 179 | 86.0% | 70.4% | 58.4% | 61.7% | 6 | 41.2% | +0.24R | 7.8% |

## Continuation Pencere Karşılaştırması

| Kategori | Cont@10 | Cont@20 | Cont@40 |
|---|---|---|---|
| CONSOLIDATION | 53.1% | 52.0% | 51.4% |
| EXPANSION | 49.9% | 47.6% | 47.4% |
| REJECTION | 58.4% | 63.0% | 61.7% |

## Trade Kalitesi (R:R Simülasyonu)

| Kategori | Toplam Trade | Win | Loss | NoFill | NoOutcome | WR% | Expectancy |
|---|---|---|---|---|---|---|---|
| CONSOLIDATION | 26340 | 8886 | 17454 | 2003 | 75 | 33.7% | +0.01R |
| EXPANSION | 890 | 316 | 574 | 251 | 4 | 35.5% | +0.07R |
| REJECTION | 165 | 68 | 97 | 14 | 0 | 41.2% | +0.24R |

## İddia Testi

- Mitigation: CONS=86.5% EXP=72.2% REJ=86.0%
- Continuation 10-bar: CONS=53.1% EXP=49.9% REJ=58.4%
- Continuation 40-bar: CONS=51.4% EXP=47.4% REJ=61.7%
- No-Fill: CONS=7.0% EXP=21.9% REJ=7.8%

**⚠️ Kısmen:** Consolidation mitigasyonu en yüksek (86.5%) ama Expansion/Rejection sıralaması beklendiği gibi değil.

## Session Filtresi Sanity Check

**Kabul edilen barların saat dağılımı (toplam 188544 bar):**

00:00=47112, 01:00=47112, 22:00=47160, 23:00=47160

✅ **Tüm barlar session penceresinde.** Filtre doğru çalışıyor.

## Bootstrap CI — REJECTION

**1000 resample, %95 güven aralığı, seed=42**

- WR: 41.2% [%95 CI: 33.9% — 49.1%]
- Expectancy: +0.11R [%95 CI: -0.11R — +0.33R]

**Non-Monotonik Cont@20 Check:**
- Cont@10: 58.4%
- Cont@20: 63.0%
- Cont@40: 61.7%
- ✅ WR CI genişliği 0.2% — Cont@20 sapma güvenilir pattern olabilir.

## Komisyon Sonrası Expectancy

**Taker fee: %0.04 (round-trip %0.08)**

| Kategori | Brüt Exp | Net Exp | Fark |
|---|---|---|---|
| CONSOLIDATION | +0.012R | -0.127R | -0.139R |
| EXPANSION | +0.065R | -0.070R | -0.134R |
| REJECTION | +0.236R | +0.107R | -0.129R |

## ATR Self-Reference Kanıtı

**C3 öncesi ATR (sınıflamada kullanılan) vs C3 sonrası ATR**

| # | Kategori | Yön | ATR (C3 öncesi) | TR(C3) | ATR (C3 sonrası) | Fark |
|---|---|---|---|---|---|---|
| 1 | CONSOLIDATION | bullish | 0.0874 | 0.0530 | 0.0850 | FARKLI |
| 2 | CONSOLIDATION | bullish | 1.6430 | 1.2900 | 1.6178 | FARKLI |
| 3 | CONSOLIDATION | bearish | 238.9714 | 235.8000 | 238.7449 | FARKLI |
| 4 | CONSOLIDATION | bullish | 0.0182 | 0.0120 | 0.0177 | FARKLI |
| 5 | CONSOLIDATION | bullish | 0.0444 | 0.0280 | 0.0432 | FARKLI |

## Coin Korelasyonu & Efektif Örneklem

| Coin | Toplam FVG | Eşsiz Gün | Saat Dilimleri |
|---|---|---|---|
| ADAUSDT | 2190 | 828 | 00:00(531), 01:00(533), 22:00(559), 23:00(567) |
| APTUSDT | 2385 | 845 | 00:00(569), 01:00(604), 22:00(650), 23:00(562) |
| ATOMUSDT | 2383 | 823 | 00:00(542), 01:00(623), 22:00(626), 23:00(592) |
| AVAXUSDT | 2365 | 845 | 00:00(563), 01:00(607), 22:00(643), 23:00(552) |
| BNBUSDT | 2573 | 872 | 00:00(654), 01:00(683), 22:00(622), 23:00(614) |
| BTCUSDT | 2220 | 828 | 00:00(540), 01:00(558), 22:00(544), 23:00(578) |
| DOTUSDT | 2210 | 827 | 00:00(532), 01:00(561), 22:00(577), 23:00(540) |
| ETHUSDT | 2108 | 817 | 00:00(515), 01:00(543), 22:00(502), 23:00(548) |
| LINKUSDT | 2384 | 831 | 00:00(556), 01:00(602), 22:00(632), 23:00(594) |
| NEARUSDT | 2242 | 818 | 00:00(513), 01:00(606), 22:00(581), 23:00(542) |
| SOLUSDT | 2217 | 835 | 00:00(528), 01:00(559), 22:00(535), 23:00(595) |
| SUIUSDT | 2407 | 839 | 00:00(585), 01:00(620), 22:00(629), 23:00(573) |
| XRPUSDT | 2058 | 820 | 00:00(486), 01:00(548), 22:00(514), 23:00(510) |
| **Ortalama** | | **833** | |
| **Min** | | **817** | |

---
*Auto-generated by analyze_fvg_3rd_candle.py (düzeltilmiş sürüm)*