# Trailing Replay — Aktivasyonlu ATR-Chase Taramasi (dinamik R) (2026-08-08 19:53)

Ayni entry uretim kurali, trailing modlari + (K, activation R) taramasi:
- **A retrace-only**: yalnizca FVG gap'i icinde kapanis onaylar (eski davranis, kontrol grubu).
- **D +activation ATR-chase**: FVG yolu retrace ile BIREBIR; FVG adayi yoksa ATR-chase fallback `SL = close -+ K*ATR` YALNIZCA unrealized kar `>= TRAIL_ACTIVATION_R_MULT * risk_pts` oldugunda devreye girer (`risk_pts = |entry - initial_sl|`, `TRAIL_MIN_MOVE_MULT` + is_placeable sartlariyla).
- `TRAIL_ACTIVATION_R_MULT` (R): grid [0.8, 1.0, 1.2, 1.5]; `CONT_BUFFER_MULT` (K): grid [2.0].

Sabitler: `ATR_TRAIL_MULT=0.1`, `TRAIL_MIN_MOVE_MULT=0.2`; entry/komisyon ve TP-RR mantigi moddan etkilenmez.
Coinler (1): SUIUSDT

## Ozet

| Mod | K | R | Trade | TP | PTrail | LOSS | PE% | NetPnL | MaxDD | HOP | HOP/t | AvgHold(b) | AvgHold(h) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 0.1 | 1 | 4294 | 610 | 1892 | 1792 | 58.3% | +113,069 | 677 | 3527 | 0.82 | 3.1 | 0.8 |
| D | 2.0 | 0.8 | 4270 | 351 | 2136 | 1783 | 58.2% | +110,676 | 731 | 4612 | 1.08 | 3.1 | 0.8 |
| D | 2.0 | 1.0 | 4253 | 351 | 2131 | 1771 | 58.4% | +110,901 | 731 | 4480 | 1.05 | 3.1 | 0.8 |
| D | 2.0 | 1.2 | 4234 | 352 | 2120 | 1762 | 58.4% | +111,417 | 731 | 4370 | 1.03 | 3.2 | 0.8 |
| D | 2.0 | 1.5 | 4230 | 371 | 2097 | 1762 | 58.3% | +107,476 | 733 | 4201 | 0.99 | 3.2 | 0.8 |

> AvgHold: ortalama bar basi holding (15dk bar); (h) = saat. MaxDD: trade-bazli kumulatif PnL eğrisi uzerinde maksimum cekilme (USD). Modlar SL/TP uzerinden exit zamanini degistirdigi icin trade sayilari da degisir.

## A (retrace baseline) vs varyasyon — eslesen trade'ler

| Varyasyon | Matched | Farkli | HOP + | HOP - | HOP Delta | PnL Delta | Sonuc Degisen | AvgHold Delta(b) | AvgHold Delta(h) |
|---|---|---|---|---|---|---|---|---|---|
| D K=2.0 R=0.8 | 4270 | 205 | 175 | 7 | +219 | -315 | 66 | +0.0 | +0.0 |
| D K=2.0 R=1.0 | 4253 | 183 | 157 | 7 | +186 | -431 | 67 | +0.0 | +0.0 |
| D K=2.0 R=1.2 | 4234 | 168 | 142 | 8 | +157 | -281 | 68 | +0.0 | +0.0 |
| D K=2.0 R=1.5 | 4230 | 140 | 122 | 6 | +125 | -179 | 68 | +0.0 | +0.0 |

> Hipotez kontrolu: AvgHold Delta > 0, genis K / teyit penceresi SL'yi gec kaydirdigi icin holding'i uzatir (erken kesmeyi onler).

## Yorum

### PYTH+SEI ortak grid (2026-08-07 22:54, 13 kosis) — orijinal bulgu
- Hicbir D (K, R) toplam NetPnL'de A'yi gecmiyor — en iyi D (K=2.0, R=1.5) +437,071 (A: +438,205, -0.26%).
- R etkisi (K sabitken): dusuk R fallback'i erken aktiflestirir -> TP'ler kesilir, NetPnL duser; R yukseldikce A'ya yaklasilir (K=1.0'da R=0.8: -31,004).
- K etkisi: K=1.0 tum R'lerde negatif; K=2.0'da fark ~1K'ya iner VE MaxDD 1,035'e duser (A: 1,088, -4.9%) — tek tutarli iyilesme.
- K-R etkilesimi: R=1.5/K=1.0 MaxDD'yi 1,220'ye cikarir — genis K korumasi olmadan yuksek R bile cekilmeyi artirir.

### SUIUSDT tek-coin R-grid (2026-08-08 19:53, K=2.0 sabit) — YENI
- **Hicbir R A'yi gecmiyor; en iyi D R=1.2 (-1,652, -1.5%)**, en kotu R=1.5 (-5,593, -4.9%). PYTH+SEI'de en iyi R=1.5 iken SUIUSDT'de R=1.5 ANADAN en kotu — coin-bazli farklilasma net.
- **MaxDD tum D'lerde A'dan kotu (731-733 vs 677, +8%):** PYTH+SEI'deki "K=2.0 MaxDD'yi iyilestirir" bulgusu SUIUSDT'de dogrulanmiyor, tersine cekilme artiyor.
- HOP her R'de artiyor (4201-4612 vs 3527): fallback daha cok kar tasiyor (PTrail 2097-2136 vs 1892) ama TP'yi bekleyemiyor (TP 351-371 vs 610), kapanista daha az birakiyor. PnL Delta en iyimser R=0.8'de -315, en kotu R=1.0'da -431 (matched trade'lerde).
- **Sonuc:** SUIUSDT'de D modu parametrik olarak kurtarilamadi — R degiskeni marjinal (A'dan fark 1653-5593), yapisal kayip ATR-chase fallback'in TP sonrasi kalinti riski ve TP kesiminden geliyor. Canliya degisiklik onerilmez — A (retrace) SUIUSDT icin de sabit kaliyor.
