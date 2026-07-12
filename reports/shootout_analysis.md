
# NEXUS Config Shootout — Analiz Sonuçları

**Score Formula:**
```
Score = (PF × (PE/100) × (NetPnL / Fee)) / (1 + MaxDD%/100) × 100
```
where `PE = TP% + PTrail%`

---

## 1. Per-Coin Comparison
Coin	     A	 B	 C	 D	Winner
Config2 + 0.40 (A)
ARBUSDT 	426	368	325	363	A
ALGOUSDT	413	284	278	398	A
AAVEUSDT	313	193	159	253	A
APTUSDT 	272	194	180	270	A
UNIUSDT 	234	207	171	199	A
SUIUSDT	    230	145	132	213	A
ADAUSDT	    186	151	149	175	A
ETHUSDT	    98	28	29	95	A

Config2 + 0.50 (D)
DOGEUSDT	346	231	271	414	D
NEARUSDT	313	245	268	337	D
OPUSDT	    262	242	256	274	D
INJUSDT	    213	163	180	231	D
LINKUSDT	172	125	119	227	D
SOLUSDT	    171	131	176	223	D
ATOMUSDT	180	142	162	211	D
DOTUSDT	    184	163	170	199	D
AVAXUSDT	180	125	141	197	D
BNBUSDT	    155	50	55	160	D
XRPUSDT	    129	46	51	139	D
BTCUSDT	    119	2	8	131	D

## 3. Coin Character Analysis

**Config3 failure:** Config3 (her iki threshold'da) hiçbir coinde kazanamadı. Config3 sistemli olarak en düşük skorları üretti.

**Threshold 0.50 dominance:** Config2 + 0.50 (D), 12 coin'de en iyi skoru verdi. Özellikle ATOM, BNB, DOGE, DOT, LINK, NEAR, OP, SOL gibi coinler bu gruba düştü.

**Threshold 0.40 cluster:** Config2 + 0.40 (A), 8 coin'de kazandı. ALGO, APT, ARB, AAVE, ADA, ETH, SUI, UNI.

**ETH edge case:** ETH, A seçeneği ile D seçeneği arasında çok yakın (98 vs 95). Iki yapılandırma da iyi, A biraz daha yüksek.

**Low-score outliers:** BNB, BTC, XRP gibi bazı coinler tüm konfigürasyonlarda düşük skor verdi. Özellikle BNB ve BTC'nin MaxDD% değerleri yüksek.

**Coin başına en iyi aralık:** En yüksek tek skor ARBUSDT (A: 426), en düşük tek skor BNB (B: 50).

## 4. Engineering Recommendation

**Default production configuration → Config2 + Threshold 0.50 (D)**

Kanıt:
- 12/20 coin'de (%60) en iyi skoru verdi
- Toplam aggregated PnL ve Score değerleri en yüksek
- Major coinlerde daha iyi drawdown kontrolü sağlıyor

**Custom coin configurations:**
- **Config2 + Threshold 0.40 (A):** ALGO, APT, ARB, AAVE, ADA, ETH, SUI, UNI (8 coin)
- **Config2 + Threshold 0.50 (D):** ATOM, BNB, DOGE, DOT, LINK, NEAR, OP, SOL, XRP (9 coin)
- **Config3:** Hiçbir coinde kullanılması önerilmez.

**FVG_SIZE_MAP justification:**
Threshold seçimi coin bazlı olduğu için, `FVG_SIZE_MAP` (ATR-bazlı dinamik eşik) implementasyonu için yeterli kanıt var. Ancak mutlak threshold'u kaldırmadan önce önce config2 + 0.50 temel alınarak çalışılmalı. Gerekirse ileride ATR-bazlı dinamik FVG_SIZE_MAP'e geçilebilir.
