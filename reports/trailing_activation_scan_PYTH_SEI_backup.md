# Trailing Replay — Aktivasyonlu ATR-Chase Taramasi (dinamik R) (2026-08-07 22:54)

Ayni entry uretim kurali, trailing modlari + (K, activation R) taramasi:
- **A retrace-only**: yalnizca FVG gap'i icinde kapanis onaylar (eski davranis, kontrol grubu).
- **D +activation ATR-chase**: FVG yolu retrace ile BIREBIR; FVG adayi yoksa ATR-chase fallback `SL = close -+ K*ATR` YALNIZCA unrealized kar `>= TRAIL_ACTIVATION_R_MULT * risk_pts` oldugunda devreye girer (`risk_pts = |entry - initial_sl|`, `TRAIL_MIN_MOVE_MULT` + is_placeable sartlariyla).
- `TRAIL_ACTIVATION_R_MULT` (R): grid [0.8, 1.0, 1.2, 1.5]; `CONT_BUFFER_MULT` (K): grid [1.0, 1.5, 2.0].

Sabitler: `ATR_TRAIL_MULT=0.1`, `TRAIL_MIN_MOVE_MULT=0.2`; entry/komisyon ve TP-RR mantigi moddan etkilenmez.
Coinler (2): PYTHUSDT, SEIUSDT

## Ozet

| Mod | K | R | Trade | TP | PTrail | LOSS | PE% | NetPnL | MaxDD | HOP | HOP/t | AvgHold(b) | AvgHold(h) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 0.1 | 1 | 7955 | 902 | 4155 | 2898 | 63.6% | +438,205 | 1,088 | 8154 | 1.03 | 2.8 | 0.7 |
| D | 1.0 | 0.8 | 8416 | 203 | 5126 | 3087 | 63.3% | +407,201 | 1,101 | 9841 | 1.17 | 2.3 | 0.6 |
| D | 1.0 | 1.0 | 8238 | 208 | 5011 | 3019 | 63.4% | +412,142 | 1,133 | 9570 | 1.16 | 2.5 | 0.6 |
| D | 1.0 | 1.2 | 8103 | 215 | 4934 | 2954 | 63.5% | +416,354 | 1,133 | 9366 | 1.16 | 2.6 | 0.7 |
| D | 1.0 | 1.5 | 7990 | 298 | 4774 | 2918 | 63.5% | +422,428 | 1,220 | 9056 | 1.13 | 2.7 | 0.7 |
| D | 1.5 | 0.8 | 8116 | 367 | 4802 | 2947 | 63.7% | +424,378 | 1,123 | 10151 | 1.25 | 2.6 | 0.6 |
| D | 1.5 | 1.0 | 8019 | 364 | 4758 | 2897 | 63.9% | +426,370 | 1,123 | 9856 | 1.23 | 2.7 | 0.7 |
| D | 1.5 | 1.2 | 7964 | 365 | 4725 | 2874 | 63.9% | +427,822 | 1,123 | 9643 | 1.21 | 2.7 | 0.7 |
| D | 1.5 | 1.5 | 7915 | 416 | 4628 | 2871 | 63.7% | +430,503 | 1,137 | 9318 | 1.18 | 2.8 | 0.7 |
| D | 2.0 | 0.8 | 7952 | 518 | 4547 | 2887 | 63.7% | +434,905 | 1,035 | 10064 | 1.27 | 2.7 | 0.7 |
| D | 2.0 | 1.0 | 7911 | 517 | 4537 | 2857 | 63.9% | +436,458 | 1,035 | 9862 | 1.25 | 2.8 | 0.7 |
| D | 2.0 | 1.2 | 7882 | 506 | 4525 | 2851 | 63.8% | +436,244 | 1,035 | 9663 | 1.23 | 2.8 | 0.7 |
| D | 2.0 | 1.5 | 7860 | 542 | 4474 | 2844 | 63.8% | +437,071 | 1,035 | 9366 | 1.19 | 2.9 | 0.7 |

> AvgHold: ortalama bar basi holding (15dk bar); (h) = saat. MaxDD: trade-bazli kumulatif PnL eğrisi uzerinde maksimum cekilme (USD). Modlar SL/TP uzerinden exit zamanini degistirdigi icin trade sayilari da degisir.

## A (retrace baseline) vs varyasyon — eslesen trade'ler

| Varyasyon | Matched | Farkli | HOP + | HOP - | HOP Delta | PnL Delta | Sonuc Degisen | AvgHold Delta(b) | AvgHold Delta(h) |
|---|---|---|---|---|---|---|---|---|---|
| D K=1.0 R=0.8 | 8416 | 374 | 293 | 24 | +332 | -5,309 | 225 | -0.1 | -0.0 |
| D K=1.0 R=1.0 | 8238 | 373 | 308 | 16 | +343 | -5,993 | 252 | -0.0 | -0.0 |
| D K=1.0 R=1.2 | 8103 | 386 | 333 | 12 | +365 | -7,230 | 288 | -0.0 | -0.0 |
| D K=1.0 R=1.5 | 7990 | 368 | 339 | 5 | +356 | -6,900 | 310 | -0.0 | -0.0 |
| D K=1.5 R=0.8 | 8116 | 363 | 290 | 17 | +350 | -2,101 | 138 | -0.2 | -0.0 |
| D K=1.5 R=1.0 | 8019 | 339 | 270 | 15 | +308 | -2,758 | 149 | -0.1 | -0.0 |
| D K=1.5 R=1.2 | 7964 | 316 | 256 | 11 | +282 | -2,817 | 153 | -0.1 | -0.0 |
| D K=1.5 R=1.5 | 7915 | 269 | 230 | 8 | +239 | -2,805 | 152 | -0.1 | -0.0 |
| D K=2.0 R=0.8 | 7952 | 319 | 254 | 11 | +317 | +903 | 57 | -0.2 | -0.1 |
| D K=2.0 R=1.0 | 7911 | 290 | 229 | 8 | +276 | +851 | 58 | -0.2 | -0.0 |
| D K=2.0 R=1.2 | 7882 | 254 | 197 | 7 | +223 | +703 | 56 | -0.2 | -0.0 |
| D K=2.0 R=1.5 | 7860 | 199 | 160 | 5 | +172 | +753 | 55 | -0.2 | -0.1 |

> Hipotez kontrolu: AvgHold Delta > 0, genis K / teyit penceresi SL'yi gec kaydirdigi icin holding'i uzatir (erken kesmeyi onler).

## Yorum

- Bulgu (PYTHUSDT + SEIUSDT, 13-kosis gridi): hicbir D (K, R) kombinasyonu toplam NetPnL'de A'yi gecmiyor — en iyi D (K=2.0, R=1.5) +437,071 (A: +438,205, -0.26%). Aktivasyonlu ATR-chase genel skorda A'nin altinda kaliyor.
- R etkisi (K sabitken): dusuk R fallback'i erken aktiflestirir -> TP'ler kesilir (A: 902 TP; R=0.8/K=1.0: 203 TP), trade/PTrail/HOP artar, NetPnL duser (K=1.0'da R=0.8: -31,004). R yukseldikce A'ya yaklasilir.
- K etkisi: K=1.0 tum R'lerde NetPnL farki negatif (-5.3K ila -7.2K); K=2.0'da fark A'nin ~1K altina iner VE MaxDD 1,035'e duser (A: 1,088, -4.9%) — tek tutarli iyilesme. Genis K tamponu chase'i gurultuden korur, TP'ye ulasima izin verir.
- K-R etkilesimi: R=1.5/K=1.0 MaxDD'yi 1,220'ye cikarir (A'dan +132) — K=1.0'da yuksek R bile genis-K korumasi olmadan cekilmeyi artirir.
- Sonuc: hipotez NetPnL'de dogrulanmadi (A hala en iyi); K=2.0 MaxDD'de ~%5 iyilestirme sunuyor ama 2-coin gridinde marjinal (53 USD). ATR-chase fallback TP'yi beklemeyip SL ile kesmek yerine kar tasiyor; TP sonrasi kalinti riskine karsi D modu icin yeni bir exit kosulu gerekir. Canliya degisiklik onerilmez — A (retrace) sabit kaliyor.
