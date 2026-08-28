# PARITY REPORT -- Canli (8.5g) vs Backtest (Binance 15d)

## Ortak istatistik

| Kaynak | Trade | Win% | Net PnL | Ort/trade | PF |
|---|---|---|---|---|---|
| **CANLI** (USDT) | 221 | 30.8 | -475.80 | -2.15 | 0.76 |
| **BACKTEST** (R) | 187 | 54.5 | +4266.00 | +22.81 | 2.71 |

Notlar:
- **CANLI**: production bot, events_2026-08-2*.jsonl, USDT. Sadece kapanan (exit) trade'ler. Trailing_count dahil degil, qty birebir Binance tarafindan raporlanan (testnet) miktardir.
- **BACKTEST**: analyzer_v5.py + Binance 1m CSV (15 gun). Metrikler **R cinsinden** (1R = ATR risk, forex mantigi). USDT karsiligi icin trade-level qty + entry/exit fiyati gerekir; bu raporda sadece R tablosu kullanildi. Tam USDT karsiligi icin analyzer_v5.py'ye trade dump (qty + prices) eklemek gerekir.

## Per-symbol

| Symbol | Live N | Live Win% | Live NetPnL (USDT) | BT N | BT Win% | BT NetPnL (R) | Eslesme |
|---|---|---|---|---|---|---|---|
| AAVEUSDT | 2 | 50.0 | +9.92 | 11 | 81.8 | +200 | MATCH |
| ADAUSDT | 25 | 36.0 | +24.64 | 10 | 40.0 | -115 | MATCH |
| ALGOUSDT | 9 | 22.2 | -67.72 | 10 | 40.0 | +77 | MATCH |
| APTUSDT | 9 | 44.4 | +14.70 | 8 | 50.0 | +25 | MATCH |
| ARBUSDT | 1 | 0.0 | +2.02 | 10 | 40.0 | +175 | MATCH |
| ATOMUSDT | — | — | — | 10 | 70.0 | +120 | bt-only |
| AVAXUSDT | 7 | 28.6 | +5.15 | 10 | 50.0 | -31 | MATCH |
| BNBUSDT | 3 | 0.0 | -12.94 | 5 | 20.0 | -47 | MATCH |
| DOGEUSDT | 10 | 50.0 | +34.64 | 0 | 0.0 | +0 | MATCH |
| DOTUSDT | 14 | 21.4 | -35.99 | 4 | 50.0 | +11 | MATCH |
| DYDXUSDT | 2 | 0.0 | -23.13 | 5 | 40.0 | +51 | MATCH |
| ENAUSDT | 17 | 29.4 | -109.73 | — | — | — | live-only |
| GMXUSDT | 11 | 27.3 | -84.75 | 3 | 33.3 | -96 | MATCH |
| INJUSDT | 6 | 33.3 | +40.31 | 4 | 50.0 | +438 | MATCH |
| LDOUSDT | 12 | 16.7 | -98.79 | 5 | 80.0 | +36 | MATCH |
| LINKUSDT | 4 | 25.0 | -7.81 | 12 | 50.0 | -7 | MATCH |
| NEARUSDT | 15 | 13.3 | -105.39 | 6 | 66.7 | +161 | MATCH |
| ONDOUSDT | 22 | 40.9 | +15.58 | 12 | 50.0 | +33 | MATCH |
| OPUSDT | — | — | — | 10 | 70.0 | +307 | bt-only |
| PYTHUSDT | 8 | 62.5 | +60.49 | 10 | 50.0 | +105 | MATCH |
| RENDERUSDT | 6 | 16.7 | -15.91 | 6 | 50.0 | +3 | MATCH |
| SEIUSDT | — | — | — | 11 | 81.8 | +1171 | bt-only |
| SOLUSDT | 1 | 0.0 | -21.44 | 2 | 50.0 | +49 | MATCH |
| STRKUSDT | — | — | — | 6 | 66.7 | +972 | bt-only |
| SUIUSDT | 19 | 31.6 | -86.13 | 10 | 60.0 | +572 | MATCH |
| TIAUSDT | 4 | 25.0 | -17.30 | 7 | 28.6 | +56 | MATCH |
| UNIUSDT | 8 | 12.5 | -52.40 | — | — | — | live-only |
| XRPUSDT | 6 | 66.7 | +56.18 | 0 | 0.0 | +0 | MATCH |
