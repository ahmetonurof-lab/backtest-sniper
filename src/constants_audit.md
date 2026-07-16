# Constants Audit — 2026-07-16

## analyze_cbdr_thresholds.py → config.py

`analyze_cbdr_thresholds.py` defines a local `_cfg` class (lines 37-70) with all constants
hardcoded, then aliases `cfg = _cfg` (line 110). This duplicates (and sometimes
diverges from) `sniper/src/config.py`.

### Constants that MATCH

| Constant | `_cfg` | `config.py` | Status |
|---|---|---|---|
| INITIAL_BALANCE | 10000.0 | 10000.0 | ✅ |
| RISK_PER_TRADE | 0.003 | 0.003 | ✅ |
| SL_ATR_MULT | 1.5 | 1.5 | ✅ |
| TP_RR | 2.0 | 2.0 | ✅ |
| FVG_BUFFER_MULT | 0.50 | 0.5 | ✅ (0.5 == 0.50) |
| EARLY_LONDON_RISK_MULT | 1.5 | 1.5 | ✅ |
| FVG_WICK_RATIO_MAX | 0.75 | 0.75 | ✅ |
| FVG_BUFFER_MIN_FACTOR | 0.10 | 0.1 | ✅ |
| ATR_TRAIL_MULT | 0.25 | 0.25 | ✅ |
| TRAIL_MIN_MOVE_MULT | 0.2 | 0.2 | ✅ |
| BE_RISK_MULT | 1.0 | 1.0 | ✅ |
| FVG_MIN_SIZE_ATR_MULT | 0.06 | 0.06 | ✅ |
| GLOBAL_FVG_EXPIRY_BARS | 45 | 45 | ✅ |
| MIN_RISK_DIST_ATR_MULT | 0.1 | 0.1 | ✅ |
| CBDR_SWEEP_ATR_TOLERANCE_MULT | 0.5 | 0.5 | ✅ |
| CBDR_SWEEP_DEFAULT_TOLERANCE | 10.0 | 10.0 | ✅ |

### Constants that DIFFER

| Constant | `_cfg` | `config.py` | Impact |
|---|---|---|---|
| **MIN_REL_FVG_THRESHOLD** | **0.50** | **0.40** | `is_high_quality_fvg()` filters FVG/ATR >= 0.50 vs 0.40. analyzer_v5.py does NOT use this filter at all. Lower threshold = more FVGs pass = more trades. |

### Constants that DON'T EXIST in config.py (dead code)

| Constant | `_cfg` | Used anywhere? |
|---|---|---|
| **CBDR_DEAD_THRESHOLD_PCT** | 0.5 | **Never used.** grep shows 0 hits. Dead code. |
| **ASIA_DEAD_THRESHOLD_PCT** | 0.3 | **Never used.** grep shows 0 hits. Dead code. |
| **BE_SPREAD_PTS** | 0.0 | 0.0 ✅ Already in config.py |

### CBDR_RISK_MATRIX
- `_cfg` has `CBDR_RISK_MATRIX: dict = {}` (empty — forces test)
- `config.py` has full production matrix with all 28 coins
- `analyze_cbdr_thresholds.py` uses `cfg.CBDR_RISK_MATRIX.get(symbol)` at lines 497 and 806 to check existing multipliers

### SYMBOLS
- `_cfg.SYMBOLS`: only 10 new coins (TIA, SEI, ONDO, PYTH, RENDER, ENA, STRK, GMX, DYDX, LDO)
- `config.SYMBOLS`: all 28 coins

## SESSION_HOURS / SESSION_CONFIGS

`analyze_cbdr_thresholds.py` has its own `SESSION_CONFIGS` (line 112-119):
```python
SESSION_CONFIGS = {
    "REAL_CBDR": {"start": 19, "end": 1},
    "DEFAULT": {"start": 22, "end": 2},
    "ASIA_RANGE": {"start": 1, "end": 5},
}
```

`config.py` has identical `SESSION_HOURS` (line 74-78). These are exact matches.

## Engine Differences

| Feature | `analyze_cbdr_thresholds.py` | `analyzer_v5.py` |
|---|---|---|
| `is_high_quality_fvg` filter | YES (MIN_REL_FVG_THRESHOLD) | NO |
| `BE_SPREAD_PTS` | `_cfg` has 0.0, but not used | Not imported either |
| `CBDR_DEAD_THRESHOLD_PCT` | Defined (0.5) but never used | Not present |
| `ASIA_DEAD_THRESHOLD_PCT` | Defined (0.3) but never used | Not present |

## Recommendation
1. Remove `_cfg` class → `import config as cfg` (with env-var-aware path)
2. `MIN_REL_FVG_THRESHOLD` will change from 0.50 → 0.40 for threshold analysis
3. Remove `CBDR_DEAD_THRESHOLD_PCT`, `ASIA_DEAD_THRESHOLD_PCT` dead constants
4. Add `BE_SPREAD_PTS = 0.0` to config.py (used by fvg_profile_v5.py)
