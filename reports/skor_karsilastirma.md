# Skor Karsilastirma Raporu

## Karsilastirilan Runlar

| Run | Tarih | Trailing | Config | Coin |
|-----|-------|----------|--------|------|
| **19:17** | 2026-07-09 | Eski permissive (bearish bug) | Eski 13 coin config | 13 |
| **11:12** | 2026-07-10 | Eski permissive (bearish bug) | Yeni 20 coin config (13 ortak) | 13 |

Not: Her iki run da ayni trailing kodunu kullanir (eski permissive).
Fark: config (session atamalari + bucket multiplier) degisti.

## Coin Bazli Skor Tablosu

| Coin | ESKI Skor | YENI Skor | Kazanan | ESKI PnL | YENI PnL | ESKI DD% | YENI DD% |
|------|-----------|-----------|---------|----------|----------|----------|----------|
| ADAUSDT |     4814348 |    13857113 | YENI |   +54117 |   +53610 |   3.8% |   1.0% |
| APTUSDT |     3692687 |    14278746 | YENI |   +56128 |   +46503 |   4.4% |   0.8% |
| ATOMUSDT |     3237571 |    22134724 | YENI |   +58433 |   +53756 |   5.5% |   0.7% |
| AVAXUSDT |     4284620 |    10199829 | YENI |   +42684 |   +46899 |   2.9% |   1.2% |
| BNBUSDT |     4731603 |    28522832 | YENI |   +49151 |   +53969 |   3.3% |   0.5% |
| BTCUSDT |     1232337 |     2752687 | YENI |   +34016 |   +30087 |   7.0% |   2.2% |
| DOTUSDT |     4410174 |    19323045 | YENI |   +44933 |   +57022 |   3.3% |   0.8% |
| ETHUSDT |     1253493 |     2365106 | YENI |   +22494 |   +21776 |   3.7% |   1.5% |
| LINKUSDT |     2334162 |     5136647 | YENI |   +40071 |   +36823 |   4.5% |   1.6% |
| NEARUSDT |     3875313 |    11147573 | YENI |   +46792 |   +47060 |   3.5% |   1.0% |
| SOLUSDT |     2613315 |    10661494 | YENI |   +38760 |   +42340 |   4.0% |   0.9% |
| SUIUSDT |     2118227 |     3599440 | YENI |   +45221 |   +32746 |   5.4% |   1.6% |
| XRPUSDT |     1961987 |     5588409 | YENI |   +38293 |   +41785 |   4.7% |   1.5% |

**ESKI kazandigi coin:** 0
**YENI kazandigi coin:** 13
**Toplam ESKI PnL:** +571093
**Toplam YENI PnL:** +564376

## Analiz

Yeni config 13/13 coinde daha yuksek skor aldi.
Bunun sebebi yeni bucket multiplier'larin daha agresif olmasi (1.2x-1.5x).
DD orani yeni config'te belirgin sekilde dusuk (0.5-2.2% vs 2.9-7.0%).
Dusuk DD skor formulunde buyuk avantaj sagliyor.

### Session Degerlendirme

Session atamalari degisen coinler:
| Coin | ESKI session | YENI session |
|------|-------------|-------------|
| APT | ASIA_RANGE | DEFAULT |
| ATOM | REAL_CBDR | ASIA_RANGE |
| AVAX | ASIA_RANGE | REAL_CBDR |
| DOT | REAL_CBDR | DEFAULT |
| ETH | REAL_CBDR | DEFAULT |

Degisen session'larin hepsi yeni config'te daha yuksek skor aldi.
