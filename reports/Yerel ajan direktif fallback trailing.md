# DİREKTİF: Structural Fallback Trailing (Ladder + Swing) — FİNAL SPEC

## Durum

Bu, önceki (çelişkili) direktifin **yerine geçer**. Eğer bu direktiften
önce başlanan implementasyon "FVG varken de ladder/swing hesaplanıp
`max()`/`min()` ile yarışır" varsayımıyla yazıldıysa (competition
modeli), o kısmı at ve aşağıdaki GATE modeline göre yeniden yaz. Zaten
geçen testler, gate modeline uyacak şekilde yeniden gözden geçirilmeli
— eski modelin testleri yeşil olması yeni modelde de doğru olduğu
anlamına gelmez.

---

## 1) ÇEKİRDEK KARAR: GATE modeli (competition değil)

```
15m kapanış
   │
   ▼
Geçerli + close-confirmed FVG var mı? (mevcut fvg_close_confirmed())
   │
 ┌─┴──────────────┐
YES               NO
 │                 │
 ▼                 ▼
FVG TRAIL        FALLBACK (Ladder / Swing)
(mevcut, dokunma)
```

```python
if valid_fvg_exists:
    candidate = best_fvg_candidate       # mevcut _fvg_multihop / fvg producer
else:
    candidate = fallback_candidate       # yeni: ladder veya swing producer
```

**FVG varsa ladder/swing hiç hesaplanmaz, hiç çağrılmaz.** `max(fvg_sl,
ladder_sl, swing_sl)` gibi bir rekabet YOK. FVG ana motor, ladder/swing
sadece FVG'nin sağlayamadığı boşlukta devreye giren yedek.

---

## 2) Mimari — mevcut altyapıya candidate producer olarak ekleniyor

Yeni bir paralel sistem kurulmuyor. Mevcut akış:

```
FVG producer (mevcut _fvg_multihop / trail_level_extractor)
Ladder producer (YENİ)
Swing producer (YENİ — ama detector'ı YENİDEN YAZMA, aşağıya bak)
       │
       ▼
   TrailLevel / TrailCandidate  (mevcut dataclass'lar)
       │
       ▼
compute_trail_candidate()   (mevcut, trailing_manager.py)
       │
       ▼
orchestrate_trail()          (mevcut)
       │
       ▼
is_placeable()                (mevcut — SL + TP birlikte, atomik)
       │
       ▼
fingerprint / dedup (last_applied_fingerprint / last_invalid_fingerprint)
       │
       ▼
apply (trade["sl"], trade["tp"], trail_count, trail_steps)
```

Gate seçimi, hangi producer'ın `trail_level_extractor` olarak trade'e
bağlanacağına karar veren üst katmanda yapılır: FVG geçerliyse FVG
producer çağrılır, sonuç yoksa (veya hiç geçerli FVG yoksa) ladder/swing
producer'a düşülür. **İkisi asla aynı candidate havuzuna girip
yarışmaz** — sıralı, exclusive seçim.

**Swing detector'ı sıfırdan yazma:** `trailing_manager.py` içinde
`TrailingManager._default_level_from_swings()` zaten confirmed 15m
swing high/low tespit ediyor (pivot_strength=2). Bu fonksiyona
`- ATR15 * SWING_TRAIL_BUFFER` (long) / `+ ATR15 * SWING_TRAIL_BUFFER`
(short) offset'ini ekleyip doğrudan swing producer olarak kullan. Aynı
"swing" kavramının iki farklı yerde iki farklı tanımla var olmasını
istemiyoruz — bu hem gereksiz kod hem gelecekte parity bug'ı riski.

**Rejected candidate state'e yazılmaz:**
```
candidate üret
   ↓
is_placeable? (SL VE TP birlikte, atomik — biri fail ederse ikisi de red)
   ├─ NO → discard. applied-state/fingerprint DEĞİŞTİRİLMEZ.
   └─ YES → apply + last_applied_fingerprint kaydet
```
Bu kural ladder/swing için de FVG kadar sıkı uygulanacak — reddedilen
bir aday `trail_steps`'e ya da herhangi bir persist edilen alana
YAZILMAYACAK (geçmişte tam bu sınıftan bir prod bug'ı bulup düzelttik:
aday, dedup kontrolünden önce state'e yazılıyordu — bunun tekrarı
istenmiyor).

---

## 3) R-multiple tanımı — mevcut koda tutarlı olsun

Ladder/swing eşikleri (`1R`, `1.5R`, `2R`, `3R`) hesaplanırken
`risk_pts`, mevcut FVG trailing'in kullandığı **aynı** tanımla
hesaplanmalı:
```python
risk_pts = abs(trade["initial_sl"] - trade["entry_price"])
```
(entry anındaki SABİT risk mesafesi — trade ilerledikçe yeniden
hesaplanmaz). Ayrı/farklı bir R tanımı kullanma; aksi halde ladder/swing
eşikleri FVG trail'inkiyle karşılaştırılamaz hale gelir.

---

## 4) LADDER (fallback #1)

```
FVG yoksa:
  <1R      → NONE (trailing yok)
  ≥1R      → SL = BE + fees
  ≥1.5R    → SL = ENTRY + 0.5R
  ≥2R      → SL = ENTRY + 1.0R
  ≥3R      → SL = ENTRY + 1.5R
```
Short için simetrik. Kademe **yalnızca 15m candle CLOSE** ile aktive
olur (intrabar high/low ile DEĞİL — lookahead/noise önleme). Bir kere
aktive olan kademe geri alınmaz (trade R'de gerileyse bile).

---

## 5) SWING (fallback #2)

```
FVG yoksa:
  <2R   → NONE
  ≥2R   → confirmed 15m swing ± 0.10 ATR15  (mevcut _default_level_from_swings + offset)
```
Swing henüz confirmed değilse candidate üretilmez. Yeni swing, eski
SL'den daha iyi değilse hiçbir değişiklik yapılmaz. **Sadece 15m swing
— 1m swing kullanılmayacak.**

---

## 6) Varyant tanımları — ÜÇÜNDE de FVG gate aktif

```
VARIANT A — FVG + LADDER
  FVG varsa   → baseline FVG trailing
  FVG yoksa:
    <1R       → none
    ≥1R       → ladder
  (swing yok)

VARIANT B — FVG + SWING
  FVG varsa   → baseline FVG trailing
  FVG yoksa:
    <2R       → none
    ≥2R       → confirmed 15m swing
  (ladder yok)

VARIANT C — FVG + LADDER→SWING (exclusive, yarışmasız)
  FVG varsa   → baseline FVG trailing
  FVG yoksa:
    <1R       → none
    1R–<2R    → ladder
    ≥2R       → swing
```
C'de 2R altında ladder, 2R ve üstünde swing — **ikisi aynı anda
candidate üretip yarışmaz**, R aralığına göre kesin/exclusive geçiş.

Üç varyant da baseline FVG trailing'i aynı şekilde koruduğu için
birbiriyle temiz karşılaştırılabilir.

---

## 7) TP davranışı

Mevcut baseline TP-shift korunuyor: `delta = abs(new_sl - current_sl)`,
TP aynı yönde delta kadar ötelenir. Candidate mevcut SL'den daha iyi
değilse TP'ye dokunulmaz. SL+TP değerlendirmesi **atomik** — biri
placeable değilse ikisi de reddedilir, "SL güncellendi TP reddedildi"
gibi yarı-güncel bir state asla oluşmaz.

---

## 8) Raporlama — her trade için yeni alanlar

```
trail_source     (FVG | LADDER | SWING | NONE)
trail_candidate
trail_reason
trail_r
trail_fvg
trail_ladder
trail_swing
trail_sl_before
trail_sl_after
```

Özet metrikler:
```
FVG trail count
Ladder trail count
Swing trail count
Trades with no trail
Trades rescued by fallback
Fallback-only PnL
FVG-only PnL
Fallback vs baseline delta
```

**Zorunlu karşılaştırma:** İlk raporda `OLD_PROFIT_GATE_1.0R`,
`NEW_LADDER_FALLBACK`, `BASELINE_FVG` **yan yana** gösterilecek —
NetPnL, PF, Exp$/trade, PTrail%, Loss%, MaxDD, ladder activation count,
fallback-only trade count ile. Amaç: "yeni isim verdik farklı oldu"
değil, gerçekten farklı davrandığını kanıtlamak. Ladder, eskiden
başarısız olan `PROFIT_GATE_0.8R`/`1.0R` deneyleriyle aynı aileden
geliyor — bu karşılaştırma olmadan rapor eksik sayılır.

Özellikle şu iki soruya odaklan:
- FVG olmayınca fallback gerçekten para kazanıyor mu, yoksa baseline'ın
  iyi trade'lerini erken mi kesiyor?
- PTrail% azalırken Exp$/trade düşüyor mu?

---

## 9) Kesin yasaklar (değişmedi)

Entry mantığı, sweep mantığı, MSS/FVG detection, FVG quality threshold,
FVG expiry, CBDR, risk sizing, TP_RR, 1m stratejik trailing, 1m swing,
1m ATR trailing, erken profit gate, partial TP — hiçbiri bu deneyde
değiştirilmeyecek. **Tek değişken: FVG yokken devreye giren fallback.**

1m katmanı sadece: SL'nin borsada mevcut olup olmadığını kontrol eder,
silinmişse restore eder, reddedildiyse tekrar gönderir, 15m'den gelen
`desired_sl`'i uygular. 1m yeni stratejik SL üretmez.

---

## 10) Sıra

Önce A, sonra B, sonra C — ayrı ayrı koş, aynı baseline üzerinde
karşılaştır. C'yi ayrı raporla, entry/config değişiklikleriyle
karıştırma. C en önemli varyant.

## 11) Testler

- Gate modelinin gerçekten exclusive olduğunu doğrulayan test: FVG
  geçerliyken ladder/swing producer'ının HİÇ çağrılmadığını (mock ile)
  doğrula.
- Reddedilen ladder/swing candidate'ının `trail_steps`/fingerprint'e
  yazılmadığını doğrulayan regresyon testi (mevcut FVG tarafı için
  zaten var olan testin ladder/swing için karşılığı).
- `_default_level_from_swings()`'in swing producer'da yeniden
  implemente edilmediğini, doğrudan çağrıldığını doğrulayan test.
- SL placeable + TP not-placeable senaryosunda candidate'ın komple
  reddedildiğini (SL de uygulanmadığını) doğrulayan test.
