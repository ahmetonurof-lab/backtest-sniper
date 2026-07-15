"""
dl_newcoins.py — Yeni coin verilerini Binance'dan indir + feather'a cevir.
output: backtest-sniper/src/data/daily/{SYM}_1m_raw.feather

Kullanim (arka planda):
  start /min /wait cmd /c python dl_newcoins.py
  python dl_newcoins.py --sym TIAUSDT   (tek coin)
"""

import os
import sys
import time
from datetime import datetime, timezone

import pandas as pd
import requests

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "daily")
os.makedirs(DATA_DIR, exist_ok=True)

ALL_SYMS = [
    "TIAUSDT",
    "SEIUSDT",
    "ONDOUSDT",
    "PYTHUSDT",
    "RENDERUSDT",
    "ENAUSDT",
    "STRKUSDT",
    "GMXUSDT",
    "DYDXUSDT",
    "LDOUSDT",
]

START_MS = int(datetime(2023, 12, 31, 21, 0, tzinfo=timezone.utc).timestamp() * 1000)
END_MS = int(datetime(2026, 7, 1, 8, 59, tzinfo=timezone.utc).timestamp() * 1000)

LOG = os.path.join(os.path.dirname(__file__), "..", "..", "reports", "dl_newcoins.log")


def log(msg):
    t = datetime.now().strftime("%H:%M:%S")
    line = f"[{t}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def download_klines(sym: str) -> list[list]:
    rows = []
    cur = START_MS
    fails = 0
    last_log = 0

    while cur < END_MS:
        url = (
            f"https://api.binance.com/api/v3/klines"
            f"?symbol={sym}&interval=1m&startTime={cur}&limit=1000"
        )
        try:
            resp = requests.get(url, timeout=15)
            data = resp.json()
        except Exception:
            fails += 1
            if fails > 10:
                log(f"  {sym} COK HATA, durduruldu")
                break
            time.sleep(2)
            continue

        if not data or isinstance(data, dict):
            fails += 1
            if fails > 10:
                break
            cur += 60000
            continue

        fails = 0
        rows.extend(data)
        cur = data[-1][6] + 60000  # close_time + 1dk

        if len(rows) - last_log >= 50000:
            log(f"  {sym}: {len(rows)} bar")
            last_log = len(rows)

        if len(rows) % 200 == 0:
            time.sleep(0.05)

    log(f"  {sym}: {len(rows)} bar indirildi")
    return rows


def to_feather(sym: str, rows: list[list]):
    cols = [
        "open_time",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "close_time",
        "quote_volume",
        "trades",
        "taker_buy_base",
        "taker_buy_quote",
        "ignore",
    ]
    df = pd.DataFrame(rows, columns=cols)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms").dt.strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms").dt.strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    for col in [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "quote_volume",
        "taker_buy_base",
        "taker_buy_quote",
    ]:
        df[col] = df[col].astype(float)
    df["trades"] = df["trades"].astype(int)
    df.drop(columns=["ignore"], inplace=True)

    out = os.path.join(DATA_DIR, f"{sym}_1m_raw.feather")
    df.to_feather(out)
    sz = os.path.getsize(out) / 1024 / 1024
    log(f"  {sym}: feather kaydedildi ({sz:.1f} MB)")


if __name__ == "__main__":
    # Log dosyasi varsa uzerine yazma, yoksa olustur
    if not os.path.exists(LOG):
        open(LOG, "w").close()

    # Tek coin argumani
    syms = [s.upper() for s in sys.argv[1:]] if len(sys.argv) > 1 else ALL_SYMS

    for sym in syms:
        if sym not in ALL_SYMS:
            log(f"ATLANDI: {sym} (taninmiyor)")
            continue
        log(f"=== {sym} ===")
        rows = download_klines(sym)
        if rows:
            to_feather(sym, rows)
        else:
            log(f"  {sym}: HIC VERI")

    log("\nTAMAMLANDI!")
