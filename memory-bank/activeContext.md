# backtest-sniper — Active Context

## Current State
2026-07-31: Canlı (sniper) bot artık backtest ile birebir strateji:
1. **Trailing:** `rsm.trigger_fvg` yerine post-entry taze FVG taraması + `fvg_close_confirmed` + ATR×0.25 buffer + delta-shift TP + çoklu-hop (analyzer_v5 ile aynı).
2. **FVG expiry:** 45-bar zaman bazlı `is_fvg_valid` KALDIRILDI → `fvg_is_alive` (dokunulmamış + invalid değilse FVG sınırsız yaşar).

## Recently Completed
- **FVG Expiry Kaldırma (2026-07-31):** `sniper/src/session_router.py` `is_fvg_valid()` ve `sniper/src/config.py` `GLOBAL_FVG_EXPIRY_BARS=45` silindi. `sniper/src/fvg.py`'ye `fvg_is_alive(direction, top, bottom, formation_index, bars)` eklendi — backtest `get_fvg_status` INVALIDATED semantiği: gap içine close (dokunma/fill) veya far-side close (invalid) görmüşse ölü, aksi halde yaşı ne olursa olsun canlı. `sniper/src/bot.py` trigger bloğunda `is_fvg_valid` → `fvg_is_alive(tf.direction, tf.top, tf.bottom, tf.bar_index, bars_15m[:-1])` (trigger barı scan dışında). Eski kod FVG'yi 45 bar sonra öldürüyordu — mıknatıs etkisi yaştan bağımsız, dokunulmadıkça sürer.
- **Canlı Trailing Backtest Konsepti (2026-07-31):** `TrailLevel.sl_buffered` flag + `_fvg_multihop` (trailing_manager.py) + `_build_fvg_scan_trail_extractor` (bot.py). Detay: backtest-sniper ile birebir.
- **Empty Bucket Fix (2026-07-16):** `bucket_data_extractor_v2.py:89-101` — boş bucket'ları n=0 ile JSON'a yaz. `bucket_risk_engine.py:160-194` — n=0 → 0.0x (skip normalize). Öncesinde: extractor boş bucket'ı atlıyordu → config'de eksik bucket → session_router fallback 1.0x.
- **load_data Optimizasyonu (2026-07-15):** `analyze_cbdr_thresholds.py` ve `_analyze_all_20.py` — `_make_bar()` bypass (frozen dataclass __post_init__), list comprehension, numpy direkt okuma. ~10x hız.
- **bar_index=None Fix (2026-07-15):** `analyze_cbdr_thresholds.py:396` — `bar_index=sb` → `bar_index=None` (sweep dedup bypass, analyzer_v5.py ile uyumlu).
- **Timestamp Fix (2026-07-15):** `datetime64[us]` → `datetime64[ms]` dönüşümü, `values.astype("datetime64[ms]").astype("int64")` ile milisaniye.
- **Division-by-Zero Fix (2026-07-15):** `_analyze_all_20.py:123` — `dd = st.get("max_dd_pct", 1) or 1`.
- **CBDR Threshold Testi — 10 Yeni Coin (2026-07-15):** `_analyze_all_20.py` ile koşuldu, sonuçlar `reports/yeni_coin_cbdr_test.txt`'de. Session assignments: ASIA_RANGE=7, DEFAULT=3.
- **Config Güncellemesi (2026-07-15):** `sniper/src/config.py` — 10 yeni coin CBDR_RISK_MATRIX, SYMBOLS, FVG_SIZE_MAP eklendi. `FVG_MIN_SIZE_ATR_MULT` 0.08→0.06.
- **FVG Size Sweep (2026-07-15):** `profile_fvg_size.py` ile 0.01-0.60 arası 60 adım × 10 coin sweep tamamlandı. Optimum değerler config'e yazıldı.
- **New Coin Data Download (2026-07-15):** 10 new coins downloaded via `dl_newcoins.py`. All feather files in `src/data/daily/`.

## Next Actions
1. **Canlıya Geçiş:** 10 yeni coin'i canlı bot listesine ekle, paper trade başlat
2. **15m Feather Ön-Hesaplama:** `*_15m.feather` yaz, run'larda direkt yükle (cache sorununu çöz)
3. **Canlı Backtest Karşılaştırması:** analyzer_v5.py sonuçları ile canlı performans karşılaştırması

## Notlar
- `FVG_SIZE_MAP` optimum değerleri: DYDX=0.040, ENA/GMX/LDO=0.020, ONDO=0.040, PYTH=0.130, RENDER/SEI/TIA=0.070, STRK=0.060.
- `analyze_cbdr_thresholds.py` ve `analyzer_v5.py` strateji farkları:前者 `is_high_quality_fvg` filtresi var,后者 yok.
- Strategy differences: `analyze_cbdr_thresholds.py` has `is_high_quality_fvg` filter (FVG/ATR >= 0.5); `analyzer_v5.py` does NOT.
