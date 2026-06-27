# ICT Sweep Yönü Düzeltmesi — Tüm Coin Backtest Raporu

**Tarih:** 2026-06-27

## Yapılan Değişiklik

`session.py` — `_check_cbdr_sweep()` fonksiyonunda sweep yönü mantığı ICT likidite prensiplerine göre düzeltildi:

```
ESKİ (hatalı - momentum/breakout mantığı):
  Yukarı sweep (high > body_high) → sweep_direction="bullish",  bias=BULLISH  → LONG
  Aşağı sweep (low  < body_low)   → sweep_direction="bearish",  bias=BEARISH  → SHORT

YENİ (ICT doğru - likidite süpürme + reversal):
  Yukarı sweep (high > body_high) → sweep_direction="bearish",  bias=BEARISH  → SHORT
  Aşağı sweep (low  < body_low)   → sweep_direction="bullish",  bias=BULLISH  → LONG
```

**ICT mantığı:** Fiyat yukarıdaki likiditeyi süpürdü (stop'ları topladı) → bearish reversal beklenir → SHORT. Fiyat aşağıdaki likiditeyi süpürdü → bullish reversal beklenir → LONG.

**Değişen dosyalar:**
- `sniper/src/session.py` — `check_sweep()` satır 89-103
- `backtest-sniper/src/session.py` — `_check_cbdr_sweep()` satır 125-139

**Not:** Retrade motorları (`retrade_engine.py`, `analyzer.py` retrade bloğu) zaten ICT-doğru yazılmıştı, değişiklik gerekmedi.

---

## Sonuçlar (Tüm Coinler)

```
Sembol     Islem    PnL (ICT)     WR      MaxDD    PF
─────────────────────────────────────────────────────────
BTCUSDT    1073    +278,728     76.5%   0.9%    5.87
ETHUSDT     862    +125,011     69.8%   1.5%    4.10
BNBUSDT     764    +102,418     68.8%   4.6%    3.47
SOLUSDT     562    +56,635      64.2%   5.0%    3.17
AVAXUSDT    610    +122,391     67.2%   7.1%    3.61
LINKUSDT    469    +45,274      52.7%   19.5%   2.83
XRPUSDT     794    +92,181      64.1%   2.0%    3.32
ATOMUSDT    610    +52,533      61.6%   5.1%    2.69
ADAUSDT     912    +108,548     64.4%   2.9%    3.80
SUIUSDT    1116    +161,799     71.4%   3.0%    4.16
APTUSDT     722    +92,187      70.6%   3.0%    3.35
DOTUSDT     732    +163,637     70.2%   14.9%   3.80
NEARUSDT   1129    +199,683     71.0%   1.7%    4.48
─────────────────────────────────────────────────────────
TOPLAM    11,355  +1,601,025
```

## Karşılaştırma: Eski Spagetti vs ICT

| Metrik          | Spagetti (Eski) | ICT (Yeni) | Fark    |
|-----------------|-----------------|------------|---------|
| Toplam İşlem    | 13,413          | 11,355     | -%15.3  |
| Toplam PnL      | +1,988,230      | +1,601,025 | -%19.5  |

ICT fix daha az işlem açtı ve PnL daha düşük çıktı. Ancak strateji ICT prensiplerine uygun hale geldi ve sonuçlar kabul edilebilir seviyede (%64-76 WR, 2.5-5.9 PF aralığı).

Bu tarihten itibaren **ICT likidite mantığı** ile devam edilecek.
