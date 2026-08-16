# FALLBACK LADDER (Kâr Merdiveni) — 28 Sembol Koşu Raporu

**Tarih:** 2026-08-16 · **Branch:** feat/fallback-trail · **Risk:** RISK_PER_TRADE=0.002 · **TP_RR:** 1.8 (sabit) · **TP_FIXED:** False (TP paralel öteleniyor) · **Referans:** BASELINE_RETRACE_LIVE_PARITY (00:06 koşusu, bit-bit deterministik)

## 1. Özet Tablo (direktif §6 formatı)

| Varyant | Trade | NetPnL | PF* | Exp$/trade | TP% | PTrail% | Loss% | MaxDD% (ort) | AvgHold |
|---|---|---|---|---|---|---|---|---|---|
| **BASELINE_RETRACE_LIVE_PARITY** | **48,943** | **+1,602,063** | **3.18** | **+32.73** | **17.0** | **40.1** | **42.9** | **0.80** | — |
| LADDER_DEFAULT | 52,863 | +881,930 | 2.96 | +16.68 | 0.3 | 65.2 | 34.6 | 1.10 | 2.3 |
| LADDER_AGGRESSIVE | 51,968 | +868,054 | 2.94 | +16.70 | 0.6 | 65.1 | 34.3 | 1.16 | 2.5 |
| LADDER_CONSERVATIVE | 52,552 | +870,036 | 2.95 | +16.56 | 0.3 | 65.2 | 34.5 | 1.10 | 2.4 |
| LADDER_SHALLOW | 52,251 | +850,366 | 2.87 | +16.27 | 0.8 | 64.8 | 34.4 | 1.19 | 2.4 |

*PF: toplam PF raporlanmıyor (gross profit/loss özet dosyasında yok); 28 sembolün per-symbol PF ortalamasıdır. Baseline PF 3.18 = per-symbol ort (LUNA Plan C raporu).*

**Sonuç: 4/4 varyant baseline'ın çok altında.** En iyi (LADDER_DEFAULT) baseline NetPnL'sinin **%55'i**; Exp$ baseline'ın **YARISI** (+32.73 → +16.68). Directifteki başarı kriterleri:

| Metrik | Hedef | LADDER_DEFAULT | Durum |
|---|---|---|---|
| NetPnL | > baseline (1,602,063) | +881,930 | ❌ (%45 düşük) |
| Exp$/trade | > +32.73 | +16.68 | ❌ |
| PTrail% | > 40.1 | 65.2 | ✅ (istatistik oyunu, bkz. §3) |
| Loss% | < 42.9 | 34.6 | ✅ (aynı nedenle) |
| MaxDD | < baseline × 1.2 | 1.10 vs 0.96 sınır | ❌ (MaxDD de arttı) |

## 2. Segmentasyon (direktif §4.4)

Segmentler baseline per-symbol MaxDD'sine göre: **LOW8** (düşük DD: PYTH/TIA/GMX/SEI/ATOM/INJ/LDO/LINK), **HIGH8** (yüksek DD: SOL/UNI/AVAX/DOT/RENDER/BNB/ADA/XRP), **MID12** (kalan 12).

| Segment | Baseline | DEFAULT | AGGRESSIVE | CONSERVATIVE | SHALLOW |
|---|---|---|---|---|---|
| LOW8 | 610,793 | 348,468 (−43%) | 344,258 (−44%) | 345,171 (−43%) | 338,142 (−45%) |
| MID12 | 664,429 | 359,669 (−46%) | 353,968 (−47%) | 353,758 (−47%) | 345,494 (−48%) |
| HIGH8 | 326,841 | 173,793 (−47%) | 169,826 (−48%) | 171,107 (−48%) | 166,732 (−49%) |

**3/3 segmentte kazanamadı; kayıp oranı homojen (−%43..−%49).** Ladder'ın düşük-DD kaldıraç grubunda dahi faydası yok.

## 3. Bulgular

1. **Merdiden "kâr kaçırma" mekanizması olarak çalışıyor.** TP% baseline 17.0 → ladder 0.3-0.8 (%95+ çöküş). SL 0.1R'den (BE) itibaren çekildiği için hiçbir trade 1.8R TP'ye ulaşamıyor; hepsi PTrail'de kilitleniyor. PTrail% artışı (40→65) **istatistik oyunu**: kazanan SAYISI artıyor ama kazanan BOYUTU küçülüyor (Exp$ yarıya indi). LUNA Profit Protect'te gördüğümüz desenin aynısı.
2. **⚠️ Entry seti DEĞİŞTİ (kıyaslama ihlali).** FVGEnt baseline 48,943 → ladder ~52K (+%8, ör. SOLUSDT 1503→1620). Neden: merdiven SL'yi erken taşıyıp trade'i kapatınca RSM aynı gün içinde daha erken reset oluyor ve yeni sweep/FVG'den **ekstra entry** doğuyor. Yani "aynı entry seti üzerinde trailing testi" prensibi (LUNA direktif madde 4) dolaylı olarak ihlal edildi — bu, NetPnL farkının bir kısmını açıklıyor. Merdiven trade'leri erken kapattığı için FVGEnt sabit kalmıyor.
3. **MaxDD ARTMIŞ (0.80 → 1.10).** Daha sıkı SL, daha çok küçük kayıp döngüsü üretiyor; portföy tepe-taban drawdown'ı ladder'da daha kötü. Hedef (< baseline×1.2) bile tutmadı.
4. **Varyantlar arası fark küçük.** DEFAULT vs SHALLOW arası NetPnL farkı yalnızca %3.6 — merdiven şekli (2 basamak vs 4) sonucu değiştirmiyor. Ana etken merdivenin VARLIĞI.
5. **Trade sayısı +%8.** Entry seti sabit olsaydı trade sayısı sabit kalırdı (önceki tüm koşularda görüldü); artış §2'deki RSM reset yan etkisinin kanıtı.

## 4. Kritik Ek Metrik (direktif §6)

- **Ladder'ın tetiklediği trade sayısı (proxy):** Trade +3,920 (48,943→52,863). Trade-level "ladder tetikleme sayacı" eklenmediği için kesin sayı yok; ancak tüm artış entry seti değişiminden geliyor (§3-2). Ladder'ın SL'yi herhangi bir FVG'den daha yukarı çektiği trade sayısını raporlamak istersen `trailing_count`'a ayrı bir sayaç (örn. `ladder_count`) eklemek gerekir.
- **Exit dağılımı (LADDER_DEFAULT):** TP=141 (%0.3) | PTrail=34,450 (%65.2) | LOSS/OPEN=18,272 (%34.6). Baseline: TP 8,310 / PTrail 19,645 / Loss 20,988.
- **Ladder tetiklenen trade'lerde ortalama kâr:** Exp$ +16.68 (baseline +32.73) — merdivenin devreye girdiği trade'ler ortalamayı AŞAĞI çekiyor.

## 5. Direktif §7 Sonraki Adımlar Kararı

Merdiven baseline'ı GEÇEMEDİ (4/4 varyant, 3/3 segmentte). Direktife göre:
- ❌ `LADDER_3BAR` kombinasyonu / `TP_PROXIMITY_ADAPTIVE` (Strateji 3) **denenmeyecek** — koşul "LADDER_DEFAULT baseline'ı geçerse" idi, geçmedi.
- ✅ `EXPONENTIAL_APPROACH` (Strateji 5) bu hipotez sınıfı için bir sonraki aday olarak not edildi — ancak desen (Profit Protect + Ladder: erken SL taşıma → Exp$ ölümü) iki bağımsız deneyde aynı sonucu verdiği için, **fiyat/SL yaklaştırma tabanlı trailing'in tamamının bu entry setinde zararlı olduğu** yönünde güçlü bir kanıt birikti.

## 6. Referanslar

- Koşular: `reports/analyzer_v5_summary.md` satır 2119 (DEFAULT 01:42), 2158 (AGGRESSIVE 02:12), 2197 (CONSERVATIVE 07:12), 2236 (SHALLOW 07:27); baseline satır 1477 (00:06, deterministik 00:49).
- Kod: `src/analyzer_v5.py` `compute_fallback_ladder_sl` + trailing entegrasyonu (FVG döngüsü sonrası); `--trail-exp LADDER_*` (branch feat/fallback-trail, commit `c4d1c48`).
- Segment hesabı: `segment_calc.py` (baseline per-symbol MaxDD sıralaması, silinecek).
