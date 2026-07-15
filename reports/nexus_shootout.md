# NEXUS Config Shootout: 4-Run Analysis

## Config Matrix

| Run | Config | Threshold | Trades | Fee | NetPnL |
|---|---|---|---|---|---|
| A | config2 | 0.40 | 41,816 | +352,805 | +683,481 |
| B | config3 | 0.40 | 47,075 | +700,416 | +969,995 |
| C | config3 | 0.50 | 38,828 | +544,819 | +770,962 |
| D | config2 | 0.50 | 34,436 | +273,755 | +541,307 |

## Per-Coin Score Comparison

Score = (PF * PositiveExit * PnL/Fee) / (1 + MaxDD/100)

| Coin | A | B | C | D | Winner |
|---|---|---|---|---|---|
