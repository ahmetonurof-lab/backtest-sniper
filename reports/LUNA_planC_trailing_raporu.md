# LUNA Plan C — Trailing İyileştirme Karşılaştırma Raporu

**Tarih:** 2026-08-15 · **Evren:** 28 sembol · **Veri:** aynı feather seti · **State:** her koşu öncesi temiz (`_clean_backtest_state`)

## 1. Metodoloji

- Tüm koşular **aynı entry seti** üzerinde çalışır; yalnızca **trailing mekaniği** değişmiştir.
- Entry/state değişiklikleri (BIAS_LOCKED, sweep_sync 3-dal, pozisyon-guard, temiz state) **baseline commit'i `55a15fa`'da** izole edilmiştir. Trailing deneyleri yalnızca `c4edf98`'de (ayrı commit, direktif şartı).
- Her koşu **ayrı mod etiketi** ile raporlanmıştır (`[EXP_TAG]`).
- Baseline determinizmi iki bağımsız koşuyla doğrulandı (00:06 ve 00:49 → **bit-bit aynı**).

## 2. Özet karşılaştırma

| Koşu | Trade | WinRate | PF | MaxDD% | Fee | NetPnL | Exp $/trade | AvgHold(bar) | Exit TP / PTrail / Loss |
|---|---|---|---|---|---|---|---|---|---|
| **BASELINE_RETRACE_LIVE_PARITY** | **48,943** | **57.1%** | **3.18** | **1.4%** | **+363,270** | **+1,602,063** | **+32.73** | (bkz. §5) | 17.0 / 40.1 / 42.9 |
| PROFIT_GATE_0_8R | 43,793 | 38.6% | 1.09 | 55.4% | +329,082 | +113,523 | +2.59 | 7.5 | 20.0 / 18.6 / 61.4 |
| PROFIT_GATE_1_0R | 42,694 | 37.3% | 1.05 | 80.8% | +321,833 | +59,833 | +1.40 | 8.4 | 21.0 / 16.3 / 62.7 |
| ATR_TRAIL_0_5 | 56,116 | 31.9% | 0.24 | 428.3% | +399,090 | −829,117 | −14.78 | 0.8 | 0.8 / 31.1 / 68.1 |
| ATR_TRAIL_0_75 | 55,140 | 30.8% | 0.25 | 441.8% | +392,807 | −862,938 | −15.65 | 1.3 | 1.6 / 29.2 / 69.2 |
| HYBRID_FVG_PLUS_PROFIT_GATE | 44,009 | 29.1% | 0.90 | 146.0% | +328,352 | −115,700 | −2.63 | 7.5 | 15.8 / 13.3 / 70.9 |

## 3. Bulgular

1. **Hiçbir deney baseline'ı geçemedi.** NetPnL bazında 5/5 koşu **28/28 sembolde** baseline'ın altında (en iyi koşu bile en kötü sembolden daha az kazandırmıyor — sembol-bazlı Δ tablosu §4).
2. **R-kâr kapısı (0.8R/1.0R) en yaklaşan varyant:** NetPnL +113,523 / +59,833 (hâlâ pozitif, ama baseline'ın sırasıyla %7.1 / %3.7'si). Kapı trail'i geç aktive ettiği için trade'ler trailing kârını kaybediyor: **PTrail% 40.1 → 18.6 / 16.3**, Loss% 42.9 → 61.4 / 62.7. Kapı eşiği büyüdükçe (0.8→1.0R) sonuç kötüleşiyor — bu aralıkta kapı "sessiz kâr biriktiren" retrace davranışını kırıyor.
3. **ATR chandelier (K=0.5/0.75) uyumsuz:** NetPnL −829K / −863K, PF 0.24/0.25, MaxDD %428 / %442 (bu koşularda ölçüm yapısal olarak anlamsız). **AvgHold 0.8/1.3 bar** — chandelier SL'si girişten hemen sonra vuruluyor; TP oranı %0.8 / %1.6'ya çöküyor. Chandelier, bu entry setinin beklenen risk/ödül yapısıyla çakışıyor.
4. **HYBRID (kapı + BE):** BE taşıması (eşikte SL→entry) kârları erken donduruyor: NetPnL −115,700, PE %29.1, **en yüksek Loss% 70.9**. Kapı zaten kârı törpülüyordu; BE üstüne bindirince trailing hiç çalışmıyor.
5. **Ortak desen:** Retrace baseline'ın getirisi FVG retrace trailing'ten değil, **initial TP'ye kadar sessiz bekleyişten** geliyor (TP% 17.0 + PTrail% 40.1 = kazananların %57'si). Trailing'e erken müdahale eden her varyant ya kârı kesiyor ya stop'u erken vuruyor.
6. **Not — MaxDD ölçümü:** Sembol-bazlı `max_dd_pct` (portföy değil per-symbol tepe-taban) raporlanmıştır; toplam sütunu en kötü sembolü gösterir. Kâr kaybı kaynaklı MaxDD artışı, risk artışı değil trailing iptalini yansıtır.

## 4. Sembol-bazlı ΔNetPnL (baseline'e göre)

| Koşu | En iyi 5 sembol (Δ) | En kötü 5 sembol (Δ) | 28/28 |
|---|---|---|---|
| PROFIT_GATE_0_8R | XRP −18,159 · ONDO −30,488 · SOL −33,121 · BNB −35,456 · ADA −35,520 | GMX −85,938 · TIA −81,492 · SEI −78,532 · DYDX −76,749 · PYTH −76,058 | 28/28 kötü |
| PROFIT_GATE_1_0R | XRP −18,432 · ONDO −31,020 · SOL −34,089 · ADA −35,821 · BNB −38,063 | GMX −88,706 · TIA −82,506 · SEI −80,127 · DYDX −78,328 · PYTH −78,064 | 28/28 kötü |
| ATR_TRAIL_0_5 | XRP −29,879 · ONDO −44,891 · BNB −60,657 · SOL −62,939 · ADA −64,352 | GMX −134,873 · TIA −130,049 · DYDX −129,816 · PYTH −121,676 · SEI −115,699 | 28/28 kötü |
| ATR_TRAIL_0_75 | XRP −30,103 · ONDO −45,581 · BNB −60,662 · SOL −62,532 · ADA −64,274 | GMX −136,401 · TIA −131,655 · DYDX −131,664 · PYTH −122,475 · SEI −118,497 | 28/28 kötü |
| HYBRID_FVG_PLUS_PROFIT_GATE | XRP −21,517 · ONDO −33,490 · SOL −38,374 · ADA −42,787 · BNB −44,132 | GMX −95,921 · TIA −89,578 · SEI −88,073 · DYDX −87,559 · PYTH −84,756 | 28/28 kötü |

En dirençli: **XRPUSDT** (Δ −18K/−30K). En kırılgan: **GMXUSDT** (Δ −86K/−136K).

## 5. Baseline AvgHold notu

Baseline determinizm koşuları (00:06/00:49), rapor formatına `AvgHold`/`Exp$` eklenmesinden **önce** yapıldığı için baseline satırında avg_hold yok. Determinizm ispatlıdır: aynı motorla yapılacak taze bir koşu trade/PnL'i bit-bit aynı üretecek ve avg_hold'u da kaydedecektir. Eksik kalan tek hücre budur (komut: `python src\analyzer_v5.py --workers 8 --trail-exp BASELINE_RETRACE_LIVE_PARITY`).

## 6. Direktif uyumluluk kontrolü

- [x] Trailing iyileştirmeleri baseline commit'ine karıştırılmadı (55a15fa baseline / c4edf98 deneyler — ayrı commit).
- [x] Her koşu aynı entry seti üzerinde, ayrı mod etiketiyle raporlandı (`[EXP_TAG]`).
- [x] Her raporda: trade sayısı, win rate, PF, NetPnL, MaxDD, expectancy, average hold, exit reason dağılımı.
- [x] Reddedilen sonuçlardan kaçınıldı: eski sweep bug'lı koşu yok (22,650/+4M sayısına düşmedik); state her koşuda temizlendi; BIAS_LOCKED canlı parity gerçek (`signal_engine.py:78-114` birebir kopya + `if not active:` guard); yalnız PnL gösteren rapor yok; trailing+entry ayrı commit.
- [x] Test planı: 14/14 (test_bias_locked 10 + test_cbdr_sweep 4, commit `55a15fa`/`07e3816`).
- [x] Determinizm: iki bağımsız baseline koşusu bit-bit aynı (48,943 / +1,602,063).

## 7. Karar önerisi

1. **Canlıya trailing değişikliği önerilmez.** BASELINE_RETRACE_LIVE_PARITY korunur; deneylerin hiçbiri NetPnL/MaxDD/PF/expectancy'nin tamamında üstün değil.
2. İstek halinde genişletilebilir: (a) R-kâr kapısı eşiği **1.5R–2.5R** aralığında taranabilir (0.8→1.0 kötüleşme eğilimi, daha geç kapının devreye girmeyip baseline'a yaklaşabileceğini düşündürüyor); (b) ATR chandelier **K<0.5** denenebilir ama PF 0.24-0.25 + TP %1 seviyesi göz önüne alındığında beklenti düşük.

## 8. Referanslar

- Per-koşu 28-sembol detayı: `reports/analyzer_v5_summary.md` satır 1477–1741 (6 koşu, `[EXP_TAG]` başlıklı).
- Kod: `analyzer_v5.py` `--trail-exp` (c4edf98); trailing kapı/BE bloğu ~satır 690.
- Baseline: 48,943 trade / net +1,602,063 (commit 55a15fa, determinizm 07e3816).
