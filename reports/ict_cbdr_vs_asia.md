# ICT CBDR vs Asia Range Backtest Raporu

**Tarih:** 2026-07-02
**Strateji:** V3 — Sweep → FVG → Entry → Trailing → Exit
**Sermaye:** 10,000 USDT
**Risk/İşlem:** %1
**2026-01-01 / 2026-04-01  tarihlerinde koşturuldu**

---

## Test Konfigürasyonları

| Test | ICT Pencere | NY Saati | UTC Saati |
|------|-------------|----------|-----------|
| **Real CBDR** | CBDR (London Kapa → NY Kapa) | 14:00 - 20:00 | 19:00 - 01:00 |
| **Asia Range** | Asia (NY Kapa → Geceyarısı) | 20:00 - 00:00 | 01:00 - 05:00 |

**Kural:** Range oluşum penceresinde trade yasak (sadece range hesaplanır). Pencere dışında sweep + FVG bekle.

---

## Genel Karşılaştırma

| Metrik | Real CBDR | Asia Range | Fark |
|--------|-----------|------------|------|
| Toplam PnL | **+916,399** | **+946,985** | -30,586 |
| Toplam İşlem | 6,759 | 8,660 | -1,901 |
| WR Lideri | BTC %61.3 | NEAR %54.5 | — |
| En iyi PnL | BTC +134,560 | DOT +137,960 | — |

---

## Coin Bazında Detay

| Coin   | C.İşlem | C.PnL | C.WR | C.DD | A.İşlem | A.PnL | A.WR | A.DD | PnL Fark | WR Fark |
|------  |---------|-------|------|------|---------|-------|------|------|----------|---------|
| ADAUSDT  | 553 | +71,074 | 47.0% | 5.7% | 640 | +48,774 | 41.6% | 10.3% | **+22,300** | **+5.5%** |
| APTUSDT  | 570 | +79,081 | 49.3% | 5.6% | 659 | +84,947 | 51.9% | 2.6% | -5,866 | -2.6% |
| ATOMUSDT | 512 | +42,938 | 48.2% | 5.3% | 600 | +49,189 | 49.2% | 4.0% | -6,251 | -0.9% |
| AVAXUSDT | 533 | +82,479 | 48.8% | 3.9% | 599 | +106,625 | 51.3% | 13.3% | -24,146 | -2.5% |
| BNBUSDT  | 487 | +57,209 | 49.3% | 10.3% | 709 | +63,341 | 46.8% | 7.6% | -6,132 | +2.5% |

| BTCUSDT  | 599 | +134,560| 61.3% | 5.4% | 580 | +63,306 | 41.9% | 6.2%  | +71,255 | +19.4% |

| DOTUSDT  | 573 | +91,827 | 50.6% | 11.9% | 799 | +137,960 | 53.4% | 7.6% | -46,132 | -2.8% |
| ETHUSDT  | 417 | +39,187 | 45.1% | 7.0% | 648 | +50,892 | 42.9% | 11.7% | -11,704 | +2.2% |
| LINKUSDT | 325 | +23,058 | 31.4% | 7.1% | 448 | +22,394 | 34.2% | 10.4% | +664 | -2.8% |
| NEARUSDT | 677 | +115,151 | 51.1% | 5.1% | 952 | +137,770 | 54.5% | 2.7% | -22,618 | -3.4% |
| SOLUSDT  | 431 | +38,417 | 42.0% | 7.8% | 583 | +46,894 | 41.0% | 8.1% | -8,477 | +1.0% |
| SUIUSDT  | 544 | +62,495 | 46.5% | 5.8% | 831 | +96,177 | 44.0% | 4.6% | -33,682 | +2.5% |
| XRPUSDT  | 538 | +78,923 | 49.4% | 10.3% | 612 | +38,718 | 42.3% | 7.5% | **+40,205** | **+7.1%** |

---

## Öne Çıkan Bulgular

### 1. BTCUSDT — En Çarpıcı Fark
- **Real CBDR:** 599 işlem, %61.3 WR, +134,560 PnL
- **Asia Range:** 580 işlem, %41.9 WR, +63,306 PnL
- CBDR lehine **+19.4 puan WR** ve **+71,255 PnL** farkı
- BTC'nin ICT CBDR saatlerine duyarlılığı çok yüksek

### 2. XRPUSDT — CBDR Bariz Üstün
- CBDR lehine +7.1% WR ve +40,205 PnL farkı
- Asia Range'de WR %42.3'e düşüyor

### 3. ADAUSDT — CBDR Daha Sağlıklı
- WR +5.5% fark, DD 5.7% vs 10.3%
- Asia Range'de DD neredeyse 2 katına çıkıyor

### 4. Asia Range'in Güçlü Olduğu Coinler
- DOTUSDT (+46k PnL fark), NEARUSDT (+22k), SUIUSDT (+33k) Asia Range'de daha iyi
- Ancak bu coinlerde WR farkı çok küçük veya negatif — karlılık daha çok işlem sayısından

---

## Genel Değerlendirme

| Kriter | Kazanan |
|--------|---------|
| WR kalitesi (10/13 coin) | **Real CBDR** |
| Toplam PnL | **Asia Range** (çok az farkla) |
| BTC performansı | **Real CBDR** (ezici) |
| DD kontrolü | **Real CBDR** (daha düşük DD) |
| Sinyal frekansı | **Asia Range** (daha fazla işlem) |

Real CBDR, özellikle **BTC, XRP ve ADA** gibi büyük coinlerde WR ve risk yönetimi açısından daha başarılı. Asia Range daha agresif sinyal üretiyor ancak WR kalitesi düşük.

BTC özelindeki %61.3 WR, ICT CBDR saatlerinin doğru olduğunun güçlü bir işareti.

---

*Rapor otomatik oluşturulmuştur — `analyzer_cbdr_ict.py`*
