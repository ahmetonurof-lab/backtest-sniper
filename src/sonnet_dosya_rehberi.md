# Bucket Risk Sistemi — Dosya Rehberi

Bu dosyaların hepsi tek bir zincirin parçası: **CBDR bucket'larına göre risk
multiplier üretmek, ve bunun gerçekten hak edilip edilmediğini bağımsız
yöntemlerle çapraz kontrol etmek.**

## Çalıştırma Sırası (pipeline)

```
1. bucket_data_extractor_v2.py   (src/ klasöründe çalıştır)
        ↓ üretir
2. bucket_data.json               (ara veri — bucket bazlı PF/Sharpe/MaxDD/n/PE)
        ↓ girdi olarak kullanır
3. bucket_risk_engine.py bucket_data.json config.py   (nerede istersen çalıştır)
        ↓ üretir
4. bucket_risk_report.md          (İNCELE — her bucket'ın gerekçesi burada)
   cbdr_risk_matrix_v2.py         (ONAYLADIYSAN config.py'ye yapıştır)
```

**Ayrı, opsiyonel doğrulama araçları (pipeline'ın parçası değil, bağımsız kontrol):**

```
5. weekend_monster_detector.py    (src/'de çalıştır) → hangi coin'in hafta
                                    sonu gerçekten farklı davrandığını,
                                    istatistiksel olarak (gürültü değil,
                                    gerçek fark) tespit eder.

6. kelly_calibration_check.py     (src/'de çalıştır) → mevcut multiplier'ların
                                    (0.0-1.5x) gerçekten hak edilip
                                    edilmediğini Kelly kriteriyle ve
                                    walk-forward testle bağımsız doğrular.
```

## Dosya Dosya Ne İşe Yarar

| Dosya | Ne yapar | Nerede çalıştır | Ne zaman kullan |
|---|---|---|---|
| **bucket_data_extractor_v2.py** | `analyzer_v5.py`'nin trade verisini CBDR% bucket'larına göre gruplar, her bucket için PF/Sharpe/MaxDD/n/PE hesaplar | `src/` (analyzer_v5.py ile aynı yer) | Her yeni backtest sonrası, bucket verisini tazelemek için |
| **bucket_data.json** | Yukarıdakinin çıktısı — ham bucket istatistikleri | — (otomatik üretilir) | Sadece ara veri, elle dokunma |
| **bucket_risk_engine.py** | `bucket_data.json`'dan composite score + PF gate + güvenlik kilidiyle multiplier hesaplar, gerekçeli rapor + config bloğu üretir | Herhangi bir yer (json dosyası yeter) | Multiplier'ları güncellemek istediğinde |
| **bucket_risk_report.md** | Her bucket için "neden bu multiplier" açıklaması (✓/✗ gerekçeler) | — (otomatik üretilir) | **Config'e yazmadan önce MUTLAKA oku** |
| **cbdr_risk_matrix_v2.py** | `config.py`'ye yapıştırmaya hazır `CBDR_RISK_MATRIX` bloğu | — (otomatik üretilir) | Rapor onaylandıktan sonra config.py'ye elle taşı |
| **weekend_monster_detector.py** | Hafta içi/sonu performans farkının gerçek mi tesadüf mü olduğunu test eder (permütasyon testi + çoklu test düzeltmesi) | `src/` | `weekend_bonus` flag'ini hangi coin'de açman gerektiğine karar vermeden önce |
| **kelly_calibration_check.py** | Mevcut multiplier eşiklerinin (0.80/0.65/0.50... skorları, PF gate sınırları) gerçekten optimal mi yoksa keyfi mi olduğunu Kelly kriteri + walk-forward ile bağımsız doğrular | `src/` | Multiplier sistemini gözden geçirirken, "bu sayılar gerçekten doğru mu" sorusuna cevap ararken |

## Tek Cümlelik Akış Hatırlatması

> "Trade verisini bucket'la (extractor) → multiplier hesapla (engine) →
> raporu oku, onayla, config'e yapıştır → sonra iki bağımsız gözle kontrol et
> (weekend detector + kelly check) → şüpheli çıkanı elden geçir."

## Önemli Uyarılar (unutma listesi)

- `bucket_risk_engine.py` **asla config.py'yi otomatik değiştirmez** — bilerek böyle, sen onaylamadan yazılmasın diye.
- `bucket_data_extractor_v2.py` boş (n=0) bucket'ları ARTIK atlamıyor, açıkça `0.0x` ile yazıyor (eski bug buydu — eksik bucket sessizce `1.0x` varsayılana düşüyordu).
- Her iki doğrulama script'i de (`weekend_monster_detector.py`, `kelly_calibration_check.py`) `day_key` formatının `"%Y-%m-%d"` olduğunu ve `collect_fvg_profile()`'ın 5'li tuple döndürdüğünü varsayıyor — bu ikisi teyit edildi (bkz. `fixes_applied.md`), ama `analyzer_v5.py` değişirse tekrar kontrol et.
