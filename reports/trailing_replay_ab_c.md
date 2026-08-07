# Trailing Replay — A/B + Parametre Taramasi (2026-08-07 21:21, FINAL)

Ayni entry uretim kurali, trailing modlari + (K, bars) taramasi:
- **A retrace-only**: yalnizca FVG gap'i icinde kapanis onaylar (eski davranis).
- **B +continuation**: gap ici VEYA pozisyon lehine far-side kapanis (short `close < bottom`, long `close > top`); aksi yon invalidation.
- **C +ATR-chase**: B + FVG aday yoksa `SL = close -+ K*ATR` fallback (`K = CONT_BUFFER_MULT`).
- `CONT_BUFFER_MULT` (K): continuation/atr-chase SL tamponu; `CONT_CONFIRM_BARS` (bars): far-side kapanisin ard arda N bar korunmasi (N=1 ilk kapanista tetikler).

Not (etiket sabit): A/B/C semasi onceki taramalarla AYNIDIR — B, daha once K=0.3/N=1'de negatif cikan 'continuation' modunun kendisidir; bu tarama ayni B modunu (K, N) gridi ile parametrize eder (`--cont-only` = C/ATR-chase atlanir, A baseline + B varyasyonlari kosulur).

Sabitler: `ATR_TRAIL_MULT=0.1`, `TRAIL_MIN_MOVE_MULT=0.2`; entry/komisyon ve TP-RR mantigi moddan etkilenmez.
Coinler (30): AAVEUSDT, ADAUSDT, ALGOUSDT, APTUSDT, ARBUSDT, ATOMUSDT, AVAXUSDT, BNBUSDT, BTCUSDT, DOGEUSDT, DOTUSDT, DYDXUSDT, ENAUSDT, ETHUSDT, GMXUSDT, INJUSDT, LDOUSDT, LINKUSDT, NEARUSDT, ONDOUSDT, OPUSDT, PYTHUSDT, RENDERUSDT, SEIUSDT, SOLUSDT, STRKUSDT, SUIUSDT, TIAUSDT, UNIUSDT, XRPUSDT

## Ozet

| Mod | K | Bars | Trade | TP | PTrail | LOSS | PE% | NetPnL | HOP | HOP/t | AvgHold(b) | AvgHold(h) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 0.1 | 1 | 111246 | 14875 | 52890 | 43481 | 60.9% | +4,100,540 | 100703 | 0.91 | 2.9 | 0.7 |
| B | 0.1 | 1 | 120336 | — | — | — | 32.7% | -1,532,460 | — | — | — | — |
| B | 0.1 | 2 | — | — | — | — | — | -1,426,527 | — | — | — | — |
| B | 0.1 | 3 | — | — | — | — | — | -1,354,183 | — | — | — | — |
| B | 0.3 | 1 | — | — | — | — | — | -1,413,984 | — | — | — | — |
| B | 0.3 | 2 | — | — | — | — | — | -1,345,264 | — | — | — | — |
| B | 0.3 | 3 | — | — | — | — | — | -1,295,305 | — | — | — | — |
| B | 1.0 | 1 | 97813 | 13980 | 18795 | 65038 | 33.5% | -1,207,682 | 72691 | 0.74 | 3.8 | 0.9 |
| B | 1.0 | 2 | 96914 | 14626 | 17939 | 64349 | 33.6% | -1,194,755 | 67925 | 0.70 | 3.9 | 1.0 |
| B | 1.0 | 3 | 96207 | 15033 | 17482 | 63692 | 33.8% | -1,181,140 | 64306 | 0.67 | 3.9 | 1.0 |

> AvgHold: ortalama bar basi holding (15dk bar); (h) = saat. Modlar SL/TP uzerinden exit zamanini degistirdigi icin trade sayilari da degisir.

## A (retrace baseline) vs varyasyon — eslesen trade'ler

| Varyasyon | Matched | Farkli | HOP + | HOP - | HOP Delta | PnL Delta | Sonuc Degisen | AvgHold Delta(b) | AvgHold Delta(h) |
|---|---|---|---|---|---|---|---|---|---|
| B K=1.0 B=1 | 97813 | 27025 | 4273 | 15701 | -15539 | -2,543,459 | 14082 | +0.0 | +0.0 |
| B K=1.0 B=2 | 96914 | 25436 | 3969 | 15598 | -15712 | -2,519,742 | 13491 | +0.0 | +0.0 |
| B K=1.0 B=3 | 96207 | 24156 | 3604 | 15539 | -16106 | -2,501,447 | 13147 | +0.0 | +0.0 |

> Hipotez kontrolu: AvgHold Delta > 0, genis K / teyit penceresi SL'yi gec kaydirdigi icin holding'i uzatir (erken kesmeyi onler).

## Yorum

- **Taramadan nihai sonuç: continuation (B) ölü.** 9/9 varyasyon derin negatif: K=0.1 → -1.53M/-1.43M/-1.35M; K=0.3 → -1.41M/-1.35M/-1.30M; K=1.0 → -1.21M/-1.19M/-1.18M (N=1/2/3). A retrace +4,100,540'dan ~5.3-5.6M sapma.
- **N-bar teyit kazandırıyor ama yetersiz:** B içinde N=3 vs N=1 LOSS'u 65,038→63,692 düşürüyor (K=1.0) ve NetPnL'i -1.21M→-1.18M iyileştiriyor; K=0.1'de -1.53M→-1.35M. Ama PE% 32.7-33.8 (A: 60.9) yapısal bozuk — N-bar teyit PE'yi düzeltmiyor.
- **Geniş K (1.0) tampon iyileştirmiyor:** K=0.1→1.0 arası NetPnL -1.53M→-1.18M (marjinal), PE% 32.7→33.8 (hala A'nın yarısı). Hipotez (geniş K erken kesmeyi önler) kısmen doğru: AvgHold 2.9→3.8 bar, LOSS azalıyor; ama kazananlardaki kayıp (HOP -15.5K, PnL Delta -2.5M) telafi edilemez.
- **A/retrace sabit kalır.** Continuation canlıya deploy edilmez; `ATR_TRAIL_MULT_CONTINUATION=0.50`/`CONTINUATION_CONFIRM_BARS=2` yalnızca repo'da kalır.
- A->B/C: continuation yalnizca lehine far-side kapanista ek SL ceker; retrace onceligi korunur (ilk gorulen onay kazanir), aksi yon invalidation.
- B->C: ATR-chase yalnizca FVG aday kullanilamadiginda devreye girer; `TMM*risk` altindaki hareketler atlanir.
