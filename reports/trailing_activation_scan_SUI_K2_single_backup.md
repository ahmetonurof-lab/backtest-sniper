# Trailing Replay — Aktivasyonlu ATR-Chase Taramasi (dinamik R) (2026-08-08 19:36)

Ayni entry uretim kurali, trailing modlari + (K, activation R) taramasi:
- **A retrace-only**: yalnizca FVG gap'i icinde kapanis onaylar (eski davranis, kontrol grubu).
- **D +activation ATR-chase**: FVG yolu retrace ile BIREBIR; FVG adayi yoksa ATR-chase fallback `SL = close -+ K*ATR` YALNIZCA unrealized kar `>= TRAIL_ACTIVATION_R_MULT * risk_pts` oldugunda devreye girer (`risk_pts = |entry - initial_sl|`, `TRAIL_MIN_MOVE_MULT` + is_placeable sartlariyla).
- `TRAIL_ACTIVATION_R_MULT` (R): grid [1.5]; `CONT_BUFFER_MULT` (K): grid [2.0].

Sabitler: `ATR_TRAIL_MULT=0.1`, `TRAIL_MIN_MOVE_MULT=0.2`; entry/komisyon ve TP-RR mantigi moddan etkilenmez.
Coinler (1): SUIUSDT

## Ozet

| Mod | K | R | Trade | TP | PTrail | LOSS | PE% | NetPnL | MaxDD | HOP | HOP/t | AvgHold(b) | AvgHold(h) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 0.1 | 1 | 4294 | 610 | 1892 | 1792 | 58.3% | +113,069 | 677 | 3527 | 0.82 | 3.1 | 0.8 |
| D | 2.0 | 1.5 | 4230 | 371 | 2097 | 1762 | 58.3% | +107,476 | 733 | 4201 | 0.99 | 3.2 | 0.8 |

> AvgHold: ortalama bar basi holding (15dk bar); (h) = saat. MaxDD: trade-bazli kumulatif PnL eğrisi uzerinde maksimum cekilme (USD). Modlar SL/TP uzerinden exit zamanini degistirdigi icin trade sayilari da degisir.

## A (retrace baseline) vs varyasyon — eslesen trade'ler

| Varyasyon | Matched | Farkli | HOP + | HOP - | HOP Delta | PnL Delta | Sonuc Degisen | AvgHold Delta(b) | AvgHold Delta(h) |
|---|---|---|---|---|---|---|---|---|---|
| D K=2.0 R=1.5 | 4230 | 140 | 122 | 6 | +125 | -179 | 68 | +0.0 | +0.0 |

> Hipotez kontrolu: AvgHold Delta > 0, genis K / teyit penceresi SL'yi gec kaydirdigi icin holding'i uzatir (erken kesmeyi onler).

## Yorum

- Bulgu (PYTHUSDT + SEIUSDT, 13-kosis gridi): hicbir D (K, R) kombinasyonu toplam NetPnL'de A'yi gecmiyor — en iyi D (K=2.0, R=1.5) +437,071 (A: +438,205, -0.26%). Aktivasyonlu ATR-chase genel skorda A'nin altinda kaliyor.
- R etkisi (K sabitken): dusuk R fallback'i erken aktiflestirir -> TP'ler kesilir (A: 902 TP; R=0.8/K=1.0: 203 TP), trade/PTrail/HOP artar, NetPnL duser (K=1.0'da R=0.8: -31,004). R yukseldikce A'ya yaklasilir.
- K etkisi: K=1.0 tum R'lerde NetPnL farki negatif (-5.3K ila -7.2K); K=2.0'da fark A'nin ~1K altina iner VE MaxDD 1,035'e duser (A: 1,088, -4.9%) — tek tutarli iyilesme. Genis K tamponu chase'i gurultuden korur, TP'ye ulasima izin verir.
- K-R etkilesimi: R=1.5/K=1.0 MaxDD'yi 1,220'ye cikarir (A'dan +132) — K=1.0'da yuksek R bile genis-K korumasi olmadan cekilmeyi artirir.
- Sonuc: hipotez NetPnL'de dogrulanmadi (A hala en iyi); K=2.0 MaxDD'de ~%5 iyilestirme sunuyor ama 2-coin gridinde marjinal (53 USD). ATR-chase fallback TP'yi beklemeyip SL ile kesmek yerine kar tasiyor; TP sonrasi kalinti riskine karsi D modu icin yeni bir exit kosulu gerekir. Canliya degisiklik onerilmez — A (retrace) sabit kaliyor.
