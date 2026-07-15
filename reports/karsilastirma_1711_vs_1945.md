# Backtest Karşılaştırma Raporu

## 17:11 (Eski Config) vs 19:45 (Yeni Config — Profil Sonucu)

### Config Farkı

| Parametre | 17:11 (Eski) | 19:45 (Yeni) |
|---|---|---|
| fvg_close_confirmed | OFF | OFF |
| FVG_SIZE_MAP | Eski CBDR threshold (0.22-0.60) | Profil çıktısı (0.020-0.190) |
| MIN_REL_FVG_THRESHOLD | 0.40 (fallback) | 0.40 (fallback) |
| Threshold formülü | FVG_SIZE_MAP.get(symbol, 0.40) | FVG_SIZE_MAP.get(symbol, 0.40) |

### Coin Bazlı Score Karşılaştırması

| Coin | 17:11 Score | 19:45 Score | Δ Score | Δ% | Kazanan |
|---|---|---|---|---|---|
| AAVEUSDT | 496 | **644** | +148 | +30% | 19:45 🏆 |
| ALGOUSDT | 514 | **519** | +5 | +1% | 19:45 |
| APTUSDT | 430 | **529** | +99 | +23% | 19:45 🏆 |
| ARBUSDT | 525 | **615** | +90 | +17% | 19:45 🏆 |
| ADAUSDT | 226 | **264** | +38 | +17% | 19:45 |
| ATOMUSDT | 241 | **308** | +67 | +28% | 19:45 🏆 |
| AVAXUSDT | 237 | **292** | +55 | +23% | 19:45 |
| BNBUSDT | 319 | 316 | -3 | -1% | 17:11 |
| BTCUSDT | 125 | **325** | +200 | +160% | 19:45 🏆 |
| DOGEUSDT | 430 | **525** | +95 | +22% | 19:45 🏆 |
| DOTUSDT | 225 | **308** | +83 | +37% | 19:45 🏆 |
| ETHUSDT | 152 | **184** | +32 | +21% | 19:45 |
| INJUSDT | 347 | **426** | +79 | +23% | 19:45 🏆 |
| LINKUSDT | 278 | **284** | +6 | +2% | 19:45 |
| NEARUSDT | 435 | 421 | -14 | -3% | 17:11 |
| OPUSDT | 290 | **462** | +172 | +59% | 19:45 🏆 |
| SOLUSDT | 295 | **310** | +15 | +5% | 19:45 |
| SUIUSDT | 380 | **499** | +119 | +31% | 19:45 🏆 |
| UNIUSDT | 352 | **354** | +2 | +1% | 19:45 |
| XRPUSDT | 264 | 253 | -11 | -4% | 17:11 |

**Score Özeti: 19:45 kazandı: 17/20 coin'de daha yüksek skor**

### Coin Bazlı PF Karşılaştırması

| Coin | 17:11 PF | 19:45 PF | Δ PF | Δ% |
|---|---|---|---|---|
| AAVEUSDT | 2.88 | **3.26** | +0.38 | +13% |
| ALGOUSDT | 2.90 | **3.03** | +0.13 | +4% |
| APTUSDT | 2.64 | **2.93** | +0.29 | +11% |
| ARBUSDT | 2.90 | **3.22** | +0.32 | +11% |
| ADAUSDT | 2.18 | **2.39** | +0.21 | +10% |
| ATOMUSDT | 2.20 | **2.62** | +0.42 | +19% |
| AVAXUSDT | 2.12 | **2.45** | +0.33 | +16% |
| BNBUSDT | 2.80 | 2.79 | -0.01 | -0% |
| BTCUSDT | 1.96 | **2.94** | +0.98 | +50% |
| DOGEUSDT | 2.72 | **3.11** | +0.39 | +14% |
| DOTUSDT | 2.11 | **2.53** | +0.42 | +20% |
| ETHUSDT | 1.94 | **2.13** | +0.19 | +10% |
| INJUSDT | 2.28 | **2.58** | +0.30 | +13% |
| LINKUSDT | 2.32 | **2.48** | +0.16 | +7% |
| NEARUSDT | 2.58 | **2.63** | +0.05 | +2% |
| OPUSDT | 2.20 | **2.82** | +0.62 | +28% |
| SOLUSDT | 2.34 | **2.52** | +0.18 | +8% |
| SUIUSDT | 2.43 | **2.77** | +0.34 | +14% |
| UNIUSDT | 2.49 | **2.59** | +0.10 | +4% |
| XRPUSDT | 2.40 | **2.43** | +0.03 | +1% |

**PF Özeti: 19:45 kazandı: 19/20 coin'de daha yüksek PF**

### Trade Bazlı Ortalama Kazanç

| Metrik | 17:11 | 19:45 | Δ |
|---|---|---|---|
| Ortalama PnL/Trade | +18.08 | **+21.62** | +3.54 |
| Ortalama Fee/Trade | 7.40 | 8.61 | +1.21 |
| Ortalama Net/Trade | +10.68 | **+13.01** | +2.33 |

### MaxDD Karşılaştırması

| Coin | 17:11 MaxDD% | 19:45 MaxDD% | Δ |
|---|---|---|---|
| AAVEUSDT | 0.9% | **0.7%** | -0.2% |
| ALGOUSDT | 0.9% | **0.7%** | -0.2% |
| APTUSDT | 0.9% | **0.7%** | -0.2% |
| ARBUSDT | 1.2% | **0.7%** | -0.5% |
| BTCUSDT | 4.5% | **2.8%** | -1.7% |
| OPUSDT | 2.3% | **0.8%** | -1.5% |

**19:45 tüm coin'lerde daha düşük MaxDD gösteriyor.**

### Özet ve Yorum

| Kategori | 17:11 | 19:45 | Kazanan |
|---|---|---|---|
| Toplam Trade | 42,215 | **75,143** | 19:45 |
| Net PnL | +763,282 | **+1,624,767** | 19:45 🏆 |
| Ortalama Score | 328 | **403** | 19:45 |
| Ortalama PF | 2.40 | **2.69** | 19:45 |
| Ortalama Net/Trade | +10.68 | **+13.01** | 19:45 |
| MaxDD (ortalama) | 2.1% | **1.2%** | 19:45 |
| Kazanılan coin (Score) | 3/20 | **17/20** | 19:45 🏆 |
| Kazanılan coin (PF) | 1/20 | **19/20** | 19:45 🏆 |

**Sonuç: 19:45 Config'i açık ara kazandı.**

- Trade sayısı 2 katına çıktı (+78%)
- Net PnL 2 katından fazla arttı (+113%)
- PF 19/20 coin'de yükseldi
- MaxDD tüm coin'lerde düştü
- Ortalama trade başı kazanç arttı

**Kritik değişiklik:** FVG_SIZE_MAP'in eski CBDR threshold değerlerinden (0.22-0.60) profil optimize değerlere (0.020-0.190) çekilmesi. Bu sayede daha fazla FVG kalite filtresinden geçebildi, trade sayısı arttı, PF ve skor da yükseldi.
