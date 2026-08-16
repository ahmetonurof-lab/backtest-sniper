# STRUCTURAL FALLBACK TRAILING: baseline vs A/B/C — 2026-08-16 16:31

- **Baseline**: FVG retrace trailing (fallback KAPALI) — canli config ile birebir.
- **OLD_PROFIT_GATE_1R**: eski deney (madde 8 karsilastirmasi) — TRAIL_MODE=retrace, `PROFIT_GATE_R=1.0`, BE=False. R-kapisinda trailing; FVG gerekli.
- **A (LADDER_ONLY)**: FVG yoksa 15m close `R>=1.0` → BE, `>=1.5` → +0.5R, `>=2.0` → +1.0R, `>=3.0` → +1.5R (ratchet).
- **B (SWING_ONLY)**: FVG yoksa `R>=2.0` → confirmed 15m swing `SL = swing -/+ {SWING_TRAIL_BUFFER}*ATR15` (canli `trailing_manager._default_level_from_swings`).
- **C (HYBRID)**: FVG ana motor; FVG yoksa `<1R` none, `1-2R` ladder, `>2R` confirmed swing. **(LUNA direktif: oncelikli test)**
- Entry/state/sweep/MSS/FVG detection/risk/TP-RR tum modlarda AYNI; 1m stratejik trailing kullanilmaz. SL LONG→max / SHORT→min, TP delta kadar paralel tasinir.

## Ozet (toplam)

| Mod | Trade | TP% | PTrail% | Loss% | PE% | PF | MaxDD% | NetPnL | Exp$/trade |
|---|---|---|---|---|---|---|---|---|---|
| BASELINE | 0 | 0.0% | 0.0% | 0.0% | 0.0% | 999.00 | 0.0% | +0 | +0.00 |
| OLD_PROFIT_GATE_1R | 0 | 0.0% | 0.0% | 0.0% | 0.0% | 999.00 | 0.0% | +0 | +0.00 |
| A_LADDER_ONLY | 0 | 0.0% | 0.0% | 0.0% | 0.0% | 999.00 | 0.0% | +0 | +0.00 |
| B_SWING_ONLY | 0 | 0.0% | 0.0% | 0.0% | 0.0% | 999.00 | 0.0% | +0 | +0.00 |
| C_HYBRID | 0 | 0.0% | 0.0% | 0.0% | 0.0% | 999.00 | 0.0% | +0 | +0.00 |

## Madde 8: Zorunlu karsilastirma (eski kapidan ayrim)

- Amaç: ladder fallback'in, basarisiz `PROFIT_GATE_0.8R/1.0R` deney ailesinden GERCEKTEN farkli davrandigini kanitlamak — 'yeni isim verdik farkli oldu' degil. Ladder, FVG gerektirmez (R kapisi + 15m close); eski kapida FVG sart.

| Mod | NetPnL | PF | Exp$/trade | PTrail% | Loss% | MaxDD% | Ladder act. | Fallback-only |
|---|---|---|---|---|---|---|---|---|
| OLD_PROFIT_GATE_1R | +0 | 999.00 | +0.00 | 0.0% | 0.0% | 0.0% | 0 | 0 (PnL +0) |
| A_LADDER_ONLY | +0 | 999.00 | +0.00 | 0.0% | 0.0% | 0.0% | 0 | 0 (PnL +0) |
| BASELINE | +0 | 999.00 | +0.00 | 0.0% | 0.0% | 0.0% | 0 | 0 (PnL +0) |

- Odak: (1) fallback FVG olmayinca gercekten para kazaniyor mu, yoksa baseline'in iyi trade'lerini erken mi kesiyor? (2) PTrail% azalirken Exp$/trade dusuyor mu?

## Fallback devreye girme (madde 14)

| Mod | FVG trail | Ladder trail | Swing trail | No-trail | Rescued | Fallback-only | FVG-only |
|---|---|---|---|---|---|---|---|
| BASELINE | 0 | 0 | 0 | 0 | 0 | 0 (PnL +0) | 0 (PnL +0) |
| OLD_PROFIT_GATE_1R | 0 | 0 | 0 | 0 | 0 | 0 (PnL +0) | 0 (PnL +0) |
| A_LADDER_ONLY | 0 | 0 | 0 | 0 | 0 | 0 (PnL +0) | 0 (PnL +0) |
| B_SWING_ONLY | 0 | 0 | 0 | 0 | 0 | 0 (PnL +0) | 0 (PnL +0) |
| C_HYBRID | 0 | 0 | 0 | 0 | 0 | 0 (PnL +0) | 0 (PnL +0) |

## Reached (fiyat bazli rejim, bilgi)

| Mod | >=1pct | >=1.5pct | >=2pct | >=3pct |
|---|---|---|---|---|
| BASELINE | 0 | 0 | 0 | 0 |
| OLD_PROFIT_GATE_1R | 0 | 0 | 0 | 0 |
| A_LADDER_ONLY | 0 | 0 | 0 | 0 |
| B_SWING_ONLY | 0 | 0 | 0 | 0 |
| C_HYBRID | 0 | 0 | 0 | 0 |

## Coin bazli: C_HYBRID vs BASELINE

| Symbol | Tr(B) | PE%(B) | PnL(B) | Tr(C) | PE%(C) | PnL(C) | ΔPnL(C-B) |
|---|---|---|---|---|---|---|---|
| AAVEUSDT | — | — | — | — | — | — | HATA |
| ADAUSDT | — | — | — | — | — | — | HATA |
| ALGOUSDT | — | — | — | — | — | — | HATA |
| APTUSDT | — | — | — | — | — | — | HATA |
| ARBUSDT | — | — | — | — | — | — | HATA |
| ATOMUSDT | — | — | — | — | — | — | HATA |
| AVAXUSDT | — | — | — | — | — | — | HATA |
| BNBUSDT | — | — | — | — | — | — | HATA |
| DOGEUSDT | — | — | — | — | — | — | HATA |
| DOTUSDT | — | — | — | — | — | — | HATA |
| DYDXUSDT | — | — | — | — | — | — | HATA |
| ENAUSDT | — | — | — | — | — | — | HATA |
| GMXUSDT | — | — | — | — | — | — | HATA |
| INJUSDT | — | — | — | — | — | — | HATA |
| LDOUSDT | — | — | — | — | — | — | HATA |
| LINKUSDT | — | — | — | — | — | — | HATA |
| NEARUSDT | — | — | — | — | — | — | HATA |
| ONDOUSDT | — | — | — | — | — | — | HATA |
| OPUSDT | — | — | — | — | — | — | HATA |
| PYTHUSDT | — | — | — | — | — | — | HATA |
| RENDERUSDT | — | — | — | — | — | — | HATA |
| SEIUSDT | — | — | — | — | — | — | HATA |
| SOLUSDT | — | — | — | — | — | — | HATA |
| STRKUSDT | — | — | — | — | — | — | HATA |
| SUIUSDT | — | — | — | — | — | — | HATA |
| TIAUSDT | — | — | — | — | — | — | HATA |
| UNIUSDT | — | — | — | — | — | — | HATA |
| XRPUSDT | — | — | — | — | — | — | HATA |

## Sonuc

- Baseline, toplam NetPnL'de C_HYBRID'den onde (Baseline: +0 vs C: +0, fark +0).
- C, 0/28 coinde baseline'i NetPnL'de gecti; MaxDD Baseline: 0.0% / C: 0.0%.
- Fallback gercekten kurtarici mi: C fallback-only 0 trade / +0 PnL; baseline FVG-only 0 trade / +0 PnL.
