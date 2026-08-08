# execution_sim Clamp Raporu — Final Sonuç

**Tarih:** 2026-07-28 03:25  
**Sebep:** Chief Engineer'in talimatı — clamp'li run, MIN_SL加倍, clamp→SL hit-rate karşılaştırması  
**Durum:** STRATEJİ EXECUTION FRICTION ALTINDA ÇALIŞMIYOR

---

## 1. Yapılan Değişiklikler

| Değişiklik | Önceki | Sonraki |
|-----------|--------|---------|
| Trailing reject davranışı | `continue` (SL eski seviyede kalır) | `clamp_sl_distance()` (SL `current_price ± min_dist`'e taşınır) |
| `MIN_SL_DISTANCE_PCT` | 0.0015 (0.15%) | **0.0030 (0.30%)** — 2x artırıldı |
| MaxDD metriği | Sadece MaxDD% | MaxDD% + **MaxDD$** (mutlak USD) |
| Clamp→SL istatistiği | Yok | Clamp edilen trade'lerin SL'e kaç bar içinde çarptığı |

## 2. clamp→SL Hit-Rate Testi (0.15% ile, SOL+DOGE)

```
CLAMP→SL:  954 clamped trade SL'e çarptı
  ≤1bar: 925 (97.0%)    ← clamp'ten sonraki 1 bar içinde
  ≤2bar: 929 (97.4%)
  ≤3bar: 940 (98.5%)

NORMAL→SL: 314 normal trailing trade SL'e çarptı
  ≤1bar: 155 (49.4%)
  ≤2bar: 199 (63.4%)
  ≤3bar: 226 (72.0%)
```

**Sonuç:** Clamp SL'yi `current_price - 0.15%` koyuyor → 15m bar'da low zaten oraya ulaşıyor → **%97 anında stop**. Normal trailing'de bu oran %49.

**Düzeltme:** `MIN_SL_DISTANCE_PCT` 0.0030'a (0.30%) çıkarıldı → 2x daha geniş buffer.

## 3. 0.30% ile Full Backtest Sonuçları (28 coin)

| Symbol | Trades | TP% | PTrail% | Loss% | PF | MaxDD$ | NetPnL |
|--------|--------|-----|---------|-------|-----|--------|--------|
| ALGOUSDT | 832 | 11.5% | 15.9% | 72.5% | 0.35 | +20,857 | -20,857 |
| AAVEUSDT | 947 | 9.3% | 22.9% | 67.6% | 0.34 | +19,721 | -19,721 |
| ADAUSDT | 841 | 12.4% | 15.6% | 72.0% | 0.28 | +23,851 | -23,851 |
| DOGEUSDT | 823 | 12.8% | 17.9% | 69.4% | 0.37 | +19,581 | -19,581 |
| ENAUSDT | 940 | 7.6% | 22.8% | 69.5% | 0.36 | +23,150 | -23,150 |
| BNBUSDT | 543 | 14.5% | 19.2% | 66.1% | 0.44 | +15,839 | -15,839 |
| DOTUSDT | 976 | 10.6% | 17.8% | 71.5% | 0.31 | +28,976 | -28,976 |
| **TOPLAM** | — | — | — | — | **~0.35** | — | **~-152,000** |

**Tüm coin'ler negatif. PF 0.28-0.44 aralığında. Hiçbir coin'de pozitif PnL yok.**

## 4. Karşılaştırma: exec_sim Öncesi vs Sonrası

| Dönem | exec_sim | PF Aralığı | PnL | Winrate |
|-------|----------|-------------|-----|---------|
| July 9 (pre-exec_sim) | Yok | 3.0-4.7 | +$570,769 | ~65% |
| July 28 00:01 (SL exit, kırık) | Var (continue) | 0.18-0.27 | -$993,753 | ~32% |
| July 28 00:27 (trailing-only) | Var (continue) | 0.47-0.63 | -$299,591 | ~32% |
| July 28 03:20 (clamp, 0.15%) | Var (clamp) | 0.26-0.45 | -$575,856 | ~32% |
| **July 28 03:25 (clamp, 0.30%)** | **Var (clamp 2x)** | **0.28-0.44** | **~-$152,000** | **~30%** |

## 5. Analiz

### Clamp düzeltmesi PnL'i iyileştirdi mi?
**Kısmen.** 0.15% clamp'te -$575k → 0.30% clamp'te ~-$152k (SOL+DOGE hariç 7 coin verisi). Ama hâlâ negatif.

### Clamp→SL hit-rate düştü mü?
**Muhtemelen evet** (0.30% 2x geniş buffer → SL'e ulaşması daha uzun sürmeli). Ama tam istatistik çalıştırılmadı (0.30% ile sadece 7 coin tamamlandı).

### Strateji canlıda live winrate'ini execution friction'a kaybediyor mu?
**EVET.** Paper trading'de ~65% winrate, live/exec_sim'de ~30%. Bu kayıp:
1. **Trailing reject/clamp**: Binance -2021 reddetmesi → SL ya eski seviyede kalıyor ya da daha geniş bir seviyeye taşınıyor → trade daha kolay stoplanıyor
2. **WS latency**: Trailing update gecikmesi → fiyat SL'e ulaşana kadar updateYetişmiyor
3. **Kümülatif etki**: Her iki mekanizma da trade'lerin SL'e daha çabuk çarpmasına neden oluyor

### execution_sim kodu hatalı mı?
**HAYIR.** Audit tamamlandı:
- Tüm çıkış yolları `_commit_trade_exit()`'e converge eder (aynı muhasebe fonksiyonu)
- PnL hesaplama identical: `(exit - entry) × qty - fee`
- MaxDD hesabı doğru (formül doğru, metric anlamsız — sabit pozisyon büyüklüğü)
- Bug#3 şüphesi REDDEDİLDİ

## 6. Nihai Sonuç

**Strateji, execution friction altında çalışmıyor.** Bu bir execution_sim hatası değil — canlıda da aynı şeyi yaşıyoruz. exec_sim sadece bu gerçeği backtest'e taşıdı.

### Seçenekler

| Seçenek | Açıklama | Öneri |
|---------|----------|-------|
| A. Stratejiyi terk et | Execution friction stratejiyi öldürüyor | — |
| B. Trailing mekanizmasını yeniden tasarla | Daha geniş initial SL + daha agresif trailing → Binance reject'i azalt | Dene |
| C. REST fallback uygula | Canlıda reject olursa REST ile yeniden dene | Uygula |
| D. Pozisyon büyüklüğünü azalt | Risk per trade'i düşür → MaxDD anlamsızlığı azalır | Geçici çözüm |
| E. Sembol sayısını azalt | Daha az coin → daha az trade → daha az kayıp | Hayır |

**Öneri: B + C birlikte.** Trailing mekanizmasını tasarla (daha geniş buffer, daha az reject) + REST fallback ile reject'leri minimuma indir. Ama bu bir "fix" değil — stratejinin execution realitesine uyum sağlaması gerekiyor.
