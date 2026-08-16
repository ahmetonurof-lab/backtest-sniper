# STRUCTURAL FALLBACK TRAILING: baseline vs A/B/C — 2026-08-16 14:52

- **Baseline**: FVG retrace trailing (fallback KAPALI) — canli config ile birebir.
- **A (LADDER_ONLY)**: FVG yoksa 15m close `R>=1.0` → BE, `>=1.5` → +0.5R, `>=2.0` → +1.0R, `>=3.0` → +1.5R (ratchet).
- **B (SWING_ONLY)**: FVG yoksa `R>=2.0` → confirmed 15m swing `SL = swing -/+ {SWING_TRAIL_BUFFER}*ATR15`.
- **C (HYBRID)**: FVG ana motor; FVG yoksa `<1R` none, `1-2R` ladder, `>2R` confirmed swing. **(LUNA direktif: oncelikli test)**
- Entry/state/sweep/MSS/FVG detection/risk/TP-RR 4 modda da AYNI; 1m stratejik trailing kullanilmaz. SL LONG→max / SHORT→min, TP delta kadar paralel tasinir.

## Ozet (toplam)

| Mod | Trade | TP% | PTrail% | Loss% | PE% | PF | MaxDD% | NetPnL | Exp$/trade |
|---|---|---|---|---|---|---|---|---|---|
| BASELINE | 1198 | 18.3% | 41.4% | 40.3% | 59.7% | 999.00 | 1.1% | +24,130 | +20.14 |
| A_LADDER_ONLY | 1195 | 11.2% | 49.1% | 39.7% | 60.3% | 999.00 | 1.5% | +22,733 | +19.02 |
| B_SWING_ONLY | 1198 | 18.3% | 41.4% | 40.3% | 59.7% | 999.00 | 1.1% | +24,171 | +20.18 |
| C_HYBRID | 1197 | 12.7% | 47.5% | 39.7% | 60.2% | 999.00 | 1.4% | +22,936 | +19.16 |

## Fallback devreye girme (madde 14)

| Mod | FVG trail | Ladder trail | Swing trail | No-trail | Rescued | Fallback-only | FVG-only |
|---|---|---|---|---|---|---|---|
| BASELINE | 672 | 0 | 0 | 526 | 0 | 0 (PnL +0) | 672 (PnL +27,322) |
| A_LADDER_ONLY | 671 | 112 | 0 | 426 | 93 | 98 (PnL +845) | 657 (PnL +26,879) |
| B_SWING_ONLY | 672 | 0 | 1 | 525 | 0 | 1 (PnL +102) | 672 (PnL +27,322) |
| C_HYBRID | 669 | 101 | 3 | 441 | 76 | 87 (PnL +844) | 655 (PnL +26,918) |

## Reached (fiyat bazli rejim, bilgi)

| Mod | >=1pct | >=1.5pct | >=2pct | >=3pct |
|---|---|---|---|---|
| BASELINE | 180 | 88 | 42 | 14 |
| A_LADDER_ONLY | 177 | 79 | 40 | 18 |
| B_SWING_ONLY | 180 | 88 | 42 | 14 |
| C_HYBRID | 174 | 79 | 40 | 16 |

## Coin bazli: C_HYBRID vs BASELINE

| Symbol | Tr(B) | PE%(B) | PnL(B) | Tr(C) | PE%(C) | PnL(C) | ΔPnL(C-B) |
|---|---|---|---|---|---|---|---|
| BNBUSDT | 1198 | 59.7% | +24,130 | 1197 | 60.3% | +22,936 | -1,194 |

## Sonuc

- Baseline, toplam NetPnL'de C_HYBRID'den onde (Baseline: +24,130 vs C: +22,936, fark -1,194).
- C, 0/1 coinde baseline'i NetPnL'de gecti; MaxDD Baseline: 1.1% / C: 1.4%.
- Fallback gercekten kurtarici mi: C fallback-only 87 trade / +844 PnL; baseline FVG-only 672 trade / +27,322 PnL.
