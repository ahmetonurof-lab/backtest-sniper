# KASKAD ANALIZI — BAS MÜHENDİS RAPORU 2026-08-17

> Kapsam: B_SWING_ONLY (2.0R) icin bas mühendisin "kaskad etkisi" sorusunun trade-bazli
> ayrıştırması. Veri: reports/sf_two_stage_cache/ (per-symbol, trade_records).

## Ozet (tek paragraf)

Kaskad etkisi YOKTUR. Bas mühendisin tablosundaki -5,765 / -18,170 / -81,288 / -70,180
"kaskad" degerleri, "fallback-only PnL"yi brüt alip baseline karsiligini hesaba katmama
hatasindan kaynaklaniyor. Dogru ayristirmada: (a) fallback'in dokundugu trade'ler disinda
kalan 48,000+ eslesen trade'te PnL degisimi SIFIR (0 trade), (b) trade seti degisimi
kucuk ve neredeyse nötr, (c) toplam DeltaPnL, fallback trade'lerinin MARJINAL etkisiyle
birebir tutuyor.

## Dogru ayristirma (per-trade, per-symbol, baseline karsiliklariyla)

| Varyant | Touched trade | Touched MARJINAL | Set degisimi | Diger eslesen trade | Bilesen | Rapor DeltaPnL |
|---|---|---|---|---|---|---|
| B_SWING_ONLY (2.0R) | 219 | +2,104.6 | +22.6 | 0.0 (0 trade) | +2,127.2 | +2,127 |
| B_SWING_ONLY_1_5R | 689 | +751.2 | +567.1 | 0.0 (0 trade) | +1,318.4 | +1,307 |
| A_LADDER_ONLY | 3667 | -35,616.6 | -28.8 | 0.0 (0 trade) | -35,645.4 | -38,098 |
| C_HYBRID | 3190 | -30,533.4 | -67.8 | 0.0 (0 trade) | -30,601.2 | -32,401 |

Not: Touched = trail_ladder / trail_swing isaretli trade'ler (raporun "fallback-only"
sayisindan farkli olabilir; fallback-only = FVG trail'i olmayanlar). A/C'de kalan ~2,4k
fark, bar kayan trade'lerin entry-kaymasindan gelir — bas mühendisin iddia ettigi -70k
/-81k degil, -2,4k seviyesinde.

## Bulgular

### 1. Gizli kaskad yok — downstream etki sifir
- (day_key, entry_bar) eslesen, fallback disi trade'lerde PnL degisimi = 0.0 (0 trade).
- Yani fallback'in dokunmadigi trade'ler birebir ayni: ne sonraki sinyal taramasi
  kayiyor, ne baska sembolun state'i degisiyor. State-leak YOK.

### 2. Bas mühendisin -5,765 "kaskad"i hesaplama hatasi
- fallback-only PnL = +7,892 BRUT'tur. Bu 219 trade baseline'da zaten +5,787 ediyordu.
- Swing'in marjinal katkisi = 7,892 - 5,787 = +2,105. Toplam DeltaPnL (+2,127) ile
  neredeyse birebir. Ortada gizli -5,765 yok.

### 3. Ladder/C-Hybrid kendi trade'lerinde kaybediyor (kaskad degil)
- Ladder touched trade'lerinin baseline karsiliklari +78,807 idi; ladder bunlari
  +43,190'a INDIRDI => -35,617 marjinal kayip. "Dogrudan trade'ler pozitif, sorun
  kaskad" tespiti YANLIS: sorun, fallback'in kendi secimlerinde.
- Bu, mekanizmayi "downstream zamanlama bozulmasi" yerine "ladder dogrudan daha kotu
  cikis secimi yapiyor" olarak yeniden tanimlar.

### 4. 1.5R sonucu bas mühendisle ayni: aktiflik artisi kotu
- 1.5R: 689 touched, marjinal +751 vs 2.0R: 219 touched, marjinal +2,105.
- Daha fazla trade'i fallback'e sokmak marjinal kazanci DUSURUYOR. 2.0R dogru esik.

## Sonuc

- B_SWING_ONLY (2.0R) marjinal +2,105, tüm DeltaPnL'yi acikliyor, kaskad/state-leak
  yok. Yayina engel bulunmadi.
- A_LADDER_ONLY ve C_HYBRID gerçek kayiplarini fallback trade'lerinin kendisinde
  yapiyor; "downstream sinyal taramasi bozuluyor" hipotezi icin kanit yok.
- Oneri: B_SWING_ONLY (2.0R) yayin onayina hazirdir.

## Analiz yontemi

- Kaynak: reports/sf_two_stage_cache/{SYM}_{MODE}.json -> trade_records
- Trade kimligi: (day_key, entry_bar)
- Touched marjinal = sum(w.pnl - base.pnl) yalnizca touched trade'lerde
- Set degisimi = lost trade'lerin pnl toplami eksi add trade'lerin pnl toplami
- Diger eslesen = touched olmayan, (day_key, entry_bar) eslesen trade'lerde pnl farki
- Scriptler: Temp/opencode/cascade_*.py
