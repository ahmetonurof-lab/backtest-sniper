# backtest-sniper — Chat Log

## 2026-07-07: memory-bank oluşturma + Cline/Goose sökümü
- backtest-sniper `memory-bank/` klasörü oluşturuldu (7 dosya: projectbrief, productContext, systemPatterns, techContext, activeContext, progress, chat)
- Cline ve Goose MCACP ajanları çalışmadığı için kaldırıldı
- n<100 normalizasyon regresyonu düzeltildi (sniper/config.py — 2e29624)
- FVG bypass A/B test raporları alındı

## 2026-07-07: FVG v4 bypass A/B test
- `fvg_profile_v4_bypass.py` oluşturuldu (FVG_QUALITY/FVG_VALIDITY/SHOULD_TRADE bypass)
- Orijinal vs bypass karşılaştırması: BTC 419→2678 trade, WR %40.3→%40.8, PnL +12895→+82341
- Her iki rapor da pushlandı (c9f3262)
