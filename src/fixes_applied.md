# Fixes Applied — 2026-07-16

## Script Denetimi

### bucket_data_extractor_v2.py
| Varsayım | Gerçek | Durum |
|---|---|---|
| `collect_fvg_profile` return 5-tuple: (daily_rows, wins, losses, trade_records, rejection_counts) | Aynı — line 744 `return daily_rows, wins, losses, trade_records, rejection_counts` | ✅ Doğru |
| trade_records key: `day_key` | Var — line 562 `"day_key": t.get("day_key", "")` | ✅ |
| trade_records key: `pnl`, `result`, `fee`, `risk_usd` | Hepsi var — lines 557-565 | ✅ |
| daily_rows key: `day_key` | Var — line 722 | ✅ |
| daily_rows key: `cbdr_pct` | Var — line 723 `"cbdr_pct": w` | ✅ |
| day_key format: `"%Y-%m-%d"` | Doğru — session.py:367 `today = dt.strftime("%Y-%m-%d")` | ✅ |
| sys.path: `../../sniper/src` | Doğru — backtest-sniper/src → ../../sniper/src | ✅ |

**Değişiklikler:**
- `sys.path` → `_BASE` + `SNIPER_ROOT` env var desteği eklendi, fallback aynı relative path
- Empty bucket fix (önceki commit) — boş bucket'lar `n=0` ile yazılıyor

### weekend_monster_detector.py
| Varsayım | Gerçek | Durum |
|---|---|---|
| `collect_fvg_profile` return | Aynı — 5-tuple | ✅ |
| day_key format | `"%Y-%m-%d"` — session.py:367 | ✅ |
| `parse_day_key_weekday()` tahmin listesi | Sadece `%Y-%m-%d` gerekli, diğer 3 format hiç kullanılmıyor | ❌ Gereksiz |

**Değişiklikler:**
- `parse_day_key_weekday()`: 4 formatlı tahmin döngüsü → direkt `"%Y-%m-%d"` kullanımı
- `sys.path` → `_BASE` + `SNIPER_ROOT` env var desteği eklendi

### Genel
- Eski `bucket_extractor.py` (fvg/atr tabanlı): zaten silinmiş, müdahale gerekmedi
- Weekend monster detector 28 coin ile test edildi, rapor üretilemedi (timeout) — 2-3 coin subset ile manuel test başarılı
