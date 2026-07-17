# Apılacaklar — Backtest Sniper PTS

**Son güncelleme:** 2026-07-16

---

## 🔴 Yüksek Öncelik

### 1. `kelly_calibration_check.py` → "Önerilen Mult" kolonu ekle
- Mevcut durum: Sadece yön uyumu (✓/✗) ve çeyrek-Kelly fraksiyonu basıyor
- İstenen: Her bucket için **önerilen multiplier** hesapla
- Formül: `quarter_kelly = kelly_f * 0.25` → mevcut pozisyon büyüklüğüne göre bucket eşdeğeri
- Çıktı: `CBDR_RISK_MATRIX`'teki bucket aralıklarına en yakın multiplier'ı round-layan "Önerilen Mult" kolonu
- Amaç: Config'e yazmadan önce "bu bucket aslında hangi multiplier'ı hak ediyor" sorusuna cevap vermek
- Örnek satır: `AAVEUSDT | 1.0-1.5 | 0.8x | f*=0.306 | Önerilen=0.5x | ✗`

---

## 🟡 Orta Öncelik

### 2. PTS Test Suite Oluştur
- `sonnet_dosya_rehberi.md`'deki 6 dosyayı test et:
  - `bucket_data_extractor_v2.py` — girdi/çıktı kontratı, boş bucket n=0 yazımı
  - `bucket_risk_engine.py` — composite score, PF gate, n=0 → 0.0x guard
  - `weekend_monster_detector.py` — permütasyon testi, day_key formatı
  - `kelly_calibration_check.py` — Spearman korelasyon, Wilson CI, walk-forward
  - `analyze_cbdr_thresholds.py` — bağımsız yol (pipeline dışı), session karşılaştırma, bucket scaling
  - `analyzer_v5.py` — terminoloji (TP%/PTrail%), collect_fvg_profile() 5'li tuple
- Her dosya için: import edilebilirlik, fonksiyon imzası, girdi-çıktı kontratı, edge case'ler

### 3. `analyze_cbdr_thresholds.py` PTS'ye dahil edilsin mi?
- Pipeline (extractor→engine) ile bağımsız çalışan bir analyzer
- Rehberde belirtilmemiş ama aktif kullanımda (`--symbols` ile)
- Karar: PTS'de ayrı bir test kategorisi olarak mı, yoksa pipeline'a entegre mi?

---

## 🟢 Düşük Öncelik

### 4. Dead Constants Temizliği Devam
- `_worker.py`'de `CBDR_DEAD_THRESHOLD_PCT = 0.5` ve `ASIA_DEAD_THRESHOLD_PCT = 0.3` hala var
- Aktif kodda kullanılmıyor (sadece _worker.py'de local copy olarak tanımlı)
- Soru: `_worker.py`'de gerçekten kullanıyor mu? Kullanmıyorsa kaldırılabilir

### 5. Spearman Korelasyonu 0.918'in Altına Düşen Coin'ler
- Walk-forward test 0.702'ye düşüyor — hangi coin'lerde en büyük sapma var?
- Train-test gap'i > 0.25 olan bucket'ları tespit et ve raporla

### 6. 🔴 `analyze_cbdr_thresholds.py` FVG_SIZE_MAP Uyumsuzluğu (KRİTİK)
- **Sorun:** Backtest motoru sabit `FVG_MIN_SIZE_ATR_MULT=0.06` kullanıyor (satır 298, 510)
- **Ama canlı bot** `FVG_SIZE_MAP.get(symbol, FVG_MIN_SIZE_ATR_MULT)` kullanıyor (0.020-0.160 arası coin-bazlı)
- **Sonuç:** CBDR bucket analizi ile canlı bot arasında tutarsızlık var — backtest sonuçları geçersiz
- **Düzeltme:** `analyze_cbdr_thresholds.py`'ye `FVG_SIZE_MAP` desteği ekle:
  ```python
  # Mevcut (yanlış):
  FVG_MIN_SIZE_ATR_MULT = cfg.FVG_MIN_SIZE_ATR_MULT

  # Düzeltilmiş (doğru):
  # collect_daily_data() fonksiyonuna symbol parametresi zaten var
  # satır 510'da:
  min_mult = cfg.FVG_SIZE_MAP.get(symbol, cfg.FVG_MIN_SIZE_ATR_MULT)
  min_fvg_size = max(atr * min_mult, 1e-8)
  ```
- **Öncelik:** YÜKSEK — bu düzeltilmeden yapılacak hiçbir sweep sonucu güvenilir değil
- **Sweep bağımlılığı:** Bu fix yapılmadan madde 7 (threshold sweep) çalıştırılmamalı

---

## ✅ Tamamlananlar

- [x] `config_20.py` silindi (ölü dosya, hiçbir yerden import edilmiyor)
- [x] `_analyze_all_20.py` silindi (ölü duplicasyon)
- [x] Terminoloji rename: WR/BE+ → TP%/PTrail% (tüm codebase)
- [x] Session düzeltmeleri: PYTHUSDT ASIA→REAL_CBDR, GMXUSDT DEFAULT→REAL_CBDR
- [x] `bucket_data_extractor_v2.py` boş bucket fix (n=0 yazımı)
- [x] `bucket_risk_engine.py` n=0 → 0.0x guard
