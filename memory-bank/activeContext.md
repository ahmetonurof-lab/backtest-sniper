# backtest-sniper — Active Context

## Current State
2026-07-09: Bug fix marathon tamamlandi (6 bug + cleanup). Session secimi yeni Skor formuluyle (`BE+% * PF * PnL / DD`). Bucket multiplier esiklari yenilendi (WR>=45&Wilson>=40 -> 1.5x, n<100->1.0x). Makine restart oncesi son durum.

## Recently Completed
- **BUG 3-10 fix:** Bearish FVG, stop-loss cap, break-even flag, PF cap, MaxDD peak, Sharpe tum gunler, sweep direction None.
- **Dead code cleanup:** captured_fvgs, old_state, results_data 5.eleman, h=edt.hour tekrari.
- **Score formulu:** `Skor = (BE+% * PF * PnL) / DD` ile session secimi. analyze_cbdr_thresholds.py ciktisina BEST isareti + Skor sutunu eklendi.
- **auto_multiplier:** Yeni esik tablosu. n<100 her zaman 1.0x.
- **config_20.py:** 20 coin test configi (13 mevcut + 7 yeni). Canli config'e dokunmaz.
- **docs/:** config_reference.py + session_router_reference.py snapshotlari.

## Next Actions (Restart Sonrasi)
1. **RSM multi-FVG pursuit:** Kalite filtresine takilan FVG sonrasi ayni sweep icindeki diger FVG'ler kaciyor. Cozum: rejected FVG UID takibi. (Dusuk oncelik)
2. **`python _analyze_all_20.py`** — 20 coin futures verisiyle kos:
   - Adim 1: 3 session backtest, Skor formuluyle en iyi session secimi
   - Adim 2: Kazanan session'da CBDR bucket + Wilson CI + auto_multiplier
   - Adim 3: Config ciktisi (yapistirmaya hazir)
3. **Sonuclari degerlendir:** analyze_cbdr_thresholds.py referansiyla karsilastir.
4. **`sniper/src/config.py` guncelle:** SYMBOLS + CBDR_RISK_MATRIX + FVG_SIZE_MAP + weekend_bonus.

## Notlar
- Tum veriler futures'tan indirildi (20 coin de hazir).
- `_analyze_all_20.py`, `analyze_cbdr_thresholds.py`, `analyzer_v5.py` — 3'u de ayni motor, farkli raporlama.
- Gercek config `sniper/src/config.py`'de. `config_20.py` sadece test icin.
