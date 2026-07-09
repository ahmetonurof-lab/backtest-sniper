# backtest-sniper — Active Context

## Current State
2026-07-09: Bug fix marathon (6 real bugs fixed across 3 engines). Config reference/docs snapshot alindi. 20-coin test config hazir. Tum veriler futures'tan indirildi.

## Recently Completed (Bug Fix Marathon)
- **BUG 3 — Bearish FVG onayı:** `fvg_close_confirmed` bearish dalinda `if fvg.bottom <= close <= fvg.top` kontrolu yoktu, her close confirmed sayiliyordu. + `confirmed` flag ile sonraki barlarda invalidation kontrolu eklendi.
- **BUG 4 — Stop-loss cap:** `if tf and rd > rp2 * 2.0` cap'i kaldirildi. Yapisal SL (FVG tabani) korunuyor, quantity otomatik kuculuyor.
- **BUG 5 — Break-even trailing_count:** `be_triggered` ayri flag'i eklendi. FVG trailing trailing_count'i break-even'i engellemiyor artik.
- **BUG 6 — Profit_factor loss=0:** `gross_loss = 0` iken PF 999.0'a cap'lendi (1e-9'a bolup patlamasin diye).
- **BUG 7 — MaxDD base:** `initial_balance` yerine `peak_balance = initial_balance + peak` kullaniliyor.
- **BUG 9 — Sharpe gun sayisi:** Trade olmayan gunler de PnL=0 olarak hesaba katiliyor (`daily_rows` uzerinden).
- **BUG 10 — Sweep direction None:** `or "bullish"` varsayimi kaldirildi, None ise skip.
- **Dead code cleanup:** `captured_fvgs` listesi, `old_state` degiskeni, `results_data` 5. elemani, `h = edt.hour` tekrari kaldirildi.

## Active Decisions
- Session filter inverted mantigi DOGRU (CBDR hesaplanirken trade yasak).
- RSM reset kalite filtresinde DOGRU (sonsuz dongu onler).
- `analyze_cbdr_thresholds.py` vs `analyzer_v5.py`: Ayni motor, farkli raporlama. Ikisi de guncellendi.
- `config_20.py` bagimsiz test config'i, canli config'e dokunmaz.
- `docs/config_reference.py` + `docs/session_router_reference.py`: Snapshot, import edilmez.

## Next Actions
1. **RSM multi-FVG pursuit:** Kalite filtresine takilan FVG'den sonra RSM resetleniyor, ayni sweep icindeki diger FVG'ler kaciyor. Cozum: rejected FVG UID'lerini takip et, reset atmadan sonraki FVG'ye gec.
2. Tum 20 coin backtest'i futures verisiyle kos, sonuclari analyze_cbdr_thresholds.py referansiyla karsilastir.
3. Session assignment + bucket multiplier tuning.
4. `sniper/src/config.py` guncelle (yeni coinler + tuned bucket mult + weekend_bonus).

## Open Questions
- (none)
