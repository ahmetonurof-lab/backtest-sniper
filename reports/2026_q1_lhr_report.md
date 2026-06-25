# 2026 Q1 Backtest — LHR Retrade Eklendi

**Dönem:** 2026-01-01 → 2026-03-31

## Değişiklikler

### session.py
- `retrade_fvg_attempts: int` — FVG deneme sayacı (__init__ + _reset_for_new_cbdr_cycle)
- `retrade_mode: str` — "fvg" / "lhr" mod takibi

### analyzer.py
- `LONDON_RETEST_PCT = 0.003` — London retest zone genişliği (%0.3)
- `MAX_FVG_ATTEMPTS = 3` — FVG max deneme, sonra LHR fallback
- **Retrade FVG bloğu:** FVG entry başarısızsa `ss.retrade_fvg_attempts += 1`, retrade kapanmıyor
- **LHR fallback:** `MAX_FVG_ATTEMPTS` sonrası London High/Low retest zone kontrolü
- `min_risk_dist = atr_val * 0.1` kontrolü LHR entry'de de var
- Pipeline counters: `retrade_lhr_checked`, `retrade_lhr_inzone`, `retrade_lhr_entry`

---

## Toplam Sonuçlar (13 Sembol)

| Sembol | İşlem | WR | PnL(custom) | PF | MaxDD | Retrade% | LHR Entry |
|---|---|---|---|---|---|---|---|
| BTCUSDT | 1,137 | 72.9% | +206,630 | 4.24 | 5.0% | 0.2% | 1 |
| ETHUSDT | 1,067 | 69.6% | +138,807 | 4.12 | 2.3% | 0.1% | 0 |
| BNBUSDT | 987 | 75.1% | +168,665 | 4.27 | 3.0% | 0.3% | 2 |
| SOLUSDT | 674 | 66.3% | +104,386 | 4.15 | 5.5% | 0.1% | 1 |
| AVAXUSDT | 720 | 74.9% | +207,964 | 4.44 | 5.9% | -0.1% | 0 |
| LINKUSDT | 560 | 66.8% | +111,951 | 3.68 | 3.2% | 0.9% | 2 |
| XRPUSDT | 989 | 72.4% | +161,413 | 3.99 | 4.5% | 0.5% | 4 |
| ATOMUSDT | 612 | 68.5% | +77,116 | 3.42 | 2.2% | -0.3% | 2 |
| ADAUSDT | 1,064 | 72.1% | +172,831 | 4.27 | 1.6% | 0.4% | 2 |
| SUIUSDT | 1,000 | 69.6% | +156,171 | 4.32 | 1.4% | 7.4% | 1 |
| APTUSDT | 738 | 66.8% | +105,369 | 4.05 | 3.1% | -0.0% | 3 |
| DOTUSDT | 838 | 69.2% | +162,536 | 3.75 | 1.8% | 0.4% | 4 |
| NEARUSDT | 1,027 | 73.7% | +214,391 | 4.70 | 3.1% | -0.0% | 1 |
| **TOPLAM** | **13,413** | **~71%** | **+1,988,230** | **4.07** | — | — | **23** |

## LHR Özeti
- **23 LHR entry** tüm sembollerde
- En aktif: XRPUSDT (4), DOTUSDT (4), APTUSDT (3)
- LHR sayesinde retrade fırsatı kaçmıyor: FVG başarısız olunca London retest deneniyor
