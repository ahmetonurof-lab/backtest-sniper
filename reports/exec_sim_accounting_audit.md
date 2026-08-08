# execution_sim Muhasebe Yolu Denetimi Raporu

**Tarih:** 2026-07-28  
**Sebep:** Chief Engineer'in 3 kırmızı flag'i — PF/MaxDD/Winrate anomalileri  
**Durum:** TAMAMLANDI — Bug#3 şüphesi REDDEDİLDİ

---

## 1. Chief Engineer'in Şüpheleri

| Flag | Değer | Şüphe |
|------|-------|-------|
| MaxDD% | 560-772% | "Matematiksel olarak anlamsız — yanlış ölçeklendirme/birikmiş hata" |
| Winrate | ~65% → ~32% | "Ters dönüş — kazanan trade'ler kayıp olarak işaretleniyor" |
| PF | 0.45-0.66 (tüm zone'larda) | "Global muhasebe hatası — her trade'e aynı ceza uygulanıyor" |

**Temel soru:** Clamp uygulanan trade'lerin PnL/result hesaplaması, normal (reddedilmeyen) trade'lerle aynı muhasebe fonksiyonundan mı geçiyor?

---

## 2. Kod Denetimi Sonuçları

### 2.1 Çıkış Yollarının Tamamı Tek Fonksiyona Converge Ediyor

`analyzer_v5.py` dosyasında 4 çıkış yolu mevcut:

| Çıkış Yolu | Satır | Sonuç |
|------------|-------|-------|
| `pending_exit` (SL rounded >= current) | L633-636 | `_commit_trade_exit()` |
| SL hit (bar low ≤ SL) | L679-682 | `_commit_trade_exit()` |
| TP hit (bar high ≥ TP) | L656-661 | `_commit_trade_exit()` |
| Açık trade kapanış (session sonu) | L697-700 | `_commit_trade_exit()` |

**Sonuç: Clamp uygulanan trade'ler AYRI bir muhasebe yolundan GEÇMİYOR.**

### 2.2 `_commit_trade_exit()` Fonksiyonu (L184-244)

```python
# Tek PnL hesaplama formülü — tüm trade'ler için aynı
diff = current_price - entry_price  # long için
pnl = diff * qty - total_fee        # swap + funding dahil

# Result sınıflandırması — tüm trade'ler için aynı
if trailing_count > 0 and sl > entry_price:
    result = "PROFIT_TRAIL"    # trailing ile karlı kapatıldı
elif pnl > 0:
    result = "PROFIT"          # normal kar
else:
    result = "LOSS"            # zarar
```

### 2.3 exec_sim Entegrasyon Noktası (L607-617)

```python
# Trailing update yolunda — SL HAREKETİNDE reddetme
if would_reject_immediately(current_price, sl, side):
    _trailing_rejects += 1
    continue  # sl güncellenmez, eski (daha geniş) seviyede kalır
```

**Reddetme sadece SL'yi hareket ettirmeye çalışırken çalışır.** SL/TP'ye ulaşıldığında reddetme YOK.

### 2.4 MaxDD Hesaplama (L774-785)

```python
peak_balance = initial_balance + max(cumulative_pnl_history)
max_dd_pct = (max_dd_dollars / peak_balance) * 100
```

Bu formül teknik olarak doğrudur. Ancak backtest sabit pozisyon büyüklüğü kullanır — her trade aynı dolar riskini alır. 23,816 trade × sabit risk = kümülatif kayıp initial_balance'in birçok katına ulaşır. Bu **matematiksel olarak doğru** ama **anlamsız** bir metrik üretir.

---

## 3. Anomalilerin Açıklaması

### 3.1 Winrate Ters Dönüşü (65% → 32%)

**Mekanizma:**

1. Trade açılır: `entry=100, sl=98, trailing_count=0`
2. Bar 1: Trailing update → `sl=99.5` kabul → `trailing_count=1`
3. Bar 2: Trailing update → `sl=101` **RED** → `trailing_count=1` kalır, `sl=99.5` kalır
4. Fiyat 99.5'e düşer → SL hit → `sl > entry_price` → `99.5 > 100` → **FALSE** → result = **"LOSS"**

**exec_sim OLMADAN:** Bar 2'de trailing kabul → `sl=101` → `sl > entry_price` → TRUE → **"PROFIT_TRAIL"**

**Sonuç:** 44,515 reddedilen trailing update, trade'leri PROFIT_TRAIL'den LOSS'a dönüştürür. Bu **beklenen davranış** — Binance'de de aynı reddedilme yaşanacaktı.

### 3.2 PF Konsantrasyonu (0.45-0.66 tüm zone'larda)

`MIN_SL_DISTANCE_PCT=0.0015` tüm zone'lara aynı anda uygulanır. Zone bazında diferansiyasyon (önceki PF 2.47-8.09 aralığı) ortadan kalkar. Bu **sistematik ama doğru** — execution realitesi tüm zone'ları eşit şekilde etkiler.

### 3.3 MaxDD% 560-772%

Backtest sabit pozisyon büyüklüğü kullanır, bakiye takibi yapmaz. 586$ initial balance ile 23,816 trade sonucunda kümülatif kayıp binlerce dolar ulaşır. Bu **backtest tasarımının bir sınırlaması**, hesaplama hatası değil.

---

## 4. Sonuç

| Soru | Cevap |
|------|-------|
| Clamp trade'leri ayrı muhasebe yolundan mı geçiyor? | **HAYIR** — tüm yollar `_commit_trade_exit()`'e converge eder |
| PnL hesaplama farklı mı? | **HAYIR** — `(exit-entry) × qty - fee` tüm trade'ler için aynı |
| Result sınıflandırması farklı mı? | **HAYIR** — trailing_count + sl > entry_price kriteri tüm trade'ler için aynı |
| MaxDD hesabı hatalı mı? | **HAYIR** — formül doğru, metric anlamsız (sabit pozisyon büyüklüğü) |
| Winrate neden ters döndü? | Reddedilen trailing update'ler SL'yi entry altında tutar → PROFIT_TRAIL → LOSS |
| PF neden konsantre oldu? | Reddetme eşiği tüm zone'lara eşit uygulanır |

**Bug#3 Şüphesi: REDDEDİLDİ**

exec_sim entegrasyonu muhasebe yolunu bozmamıştır. Sayılar stratejinin execution realitesi altındaki **gerçekçi performansını** yansıtmaktadır. Strateji, paper trading'de看到ılan ~65% winrate'ini live execution friction'la kaybetmektedir.

---

## 5. Öneriler

1. **Strateji kararı verme:** Bu sayıları "fibo filter zararlı" olarak yorumlama — sadece "execution friction stratejiyi zayıflatıyor" sonucunu çıkar
2. **Reddetme eşiğini test et:** `MIN_SL_DISTANCE_PCT=0.0010` veya `0.0020` ile tekrar çalıştır — belki 0.15% çok agresif
3. **MaxDD metriğini düzelt:** Gerçek equity curve takibi (pozisyon büyüklüğü bakiyeye göre scale edilmeli) veya MaxDD% yerine absolute USD kaybı raporla
4. **Backtest Limitasyonunu belgele:** Sabit pozisyon büyüklüğü + bankroll yönetimi yok = MaxDD% anlamsız
