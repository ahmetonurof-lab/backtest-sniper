"""
download_binance_15d.py — Son 15 günlük Binance USDT-M 1m kline indirici.

KULLANIM:  python tools/download_binance_15d.py

Binance public API (api.binance.com) kullanır, API key gerektirmez.
Rate limit: ~1200 req/dakika, biz ~28 sembol × 1-2 request/sembol yeterli.

ÇIKTI: src/data/binance_15d/{SYMBOL}_1m.csv
  Kolonlar: open_time, open, high, low, close, volume
  open_time: ms (int) — analyzer_v5.py load_data()'nın CSV dispatch'i parse eder.

TARIH PENCERESI: 2026-08-13 13:06:00 → 2026-08-28 13:06:00 UTC (15 gün, yuvarlak)

Bu script analyzer_v5.py'yi değiştirmez; sadece CSV indirir.
analyzer_v5.py load_data() içine eklenen CSV dispatch (commit ile birlikte)
bu CSV'leri okuyabilir.
"""

from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import List

# ── Sabitler ───────────────────────────────────────────────────────────
END_TS_MS = 1787961960000  # 2026-08-28 13:06:00 UTC (epoch ms)
START_TS_MS = 1787961960000 - 15 * 24 * 60 * 60 * 1000  # 15 gün önce
INTERVAL = "1m"
LIMIT = 1000  # Binance /klines max
RATE_SLEEP_S = 0.25  # her istek arası, rate limit için güvenli

SYMBOLS = [
    "BNBUSDT",
    "SOLUSDT",
    "AVAXUSDT",
    "LINKUSDT",
    "XRPUSDT",
    "ATOMUSDT",
    "ADAUSDT",
    "APTUSDT",
    "DOTUSDT",
    "NEARUSDT",
    "SUIUSDT",
    "OPUSDT",
    "ARBUSDT",
    "INJUSDT",
    "ALGOUSDT",
    "AAVEUSDT",
    "UNIUSDT",
    "DOGEUSDT",
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

OUT_DIR = Path(__file__).resolve().parent.parent / "src" / "data" / "binance_15d"


def fetch_klines(symbol: str, start_ms: int, end_ms: int) -> List[list]:
    """Binance /api/v3/klines ile sayfalı 1m veri indir.

    Returns: her satır = [open_time, open, high, low, close, volume, ...]
    Binance 12 kolon döner; biz ilk 6'yı kullanacağız.
    """
    import requests

    rows: List[list] = []
    cur = start_ms
    base = "https://api.binance.com"
    while cur < end_ms:
        url = (
            f"{base}/api/v3/klines"
            f"?symbol={symbol}&interval={INTERVAL}"
            f"&startTime={cur}&endTime={end_ms}&limit={LIMIT}"
        )
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        rows.extend(batch)
        # Son satırın close_time'ı bir sonraki startTime olur
        last_close = batch[-1][6]  # close_time ms
        cur = last_close + 1
        time.sleep(RATE_SLEEP_S)
        if len(batch) < LIMIT:
            break
    return rows


def to_csv_rows(raw: List[list]) -> List[dict]:
    """Binance 12-kolon çıktısını 6-kolon dict listesine indir.

    ÇIKTI KOLONLARI (analyzer_v5.py CSV dispatch uyumu):
      open_time (int ms), open (str/float), high, low, close, volume
    """
    out = []
    for k in raw:
        out.append(
            {
                "open_time": int(k[0]),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
            }
        )
    return out


def write_csv(symbol: str, rows: List[dict]) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{symbol}_1m.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f, fieldnames=["open_time", "open", "high", "low", "close", "volume"]
        )
        w.writeheader()
        w.writerows(rows)
    return path


def main():
    print("=== BINANCE 15D DOWNLOADER ===")
    print(f"Window: {START_TS_MS} -> {END_TS_MS} ms")
    print(f"        ({(END_TS_MS - START_TS_MS) / 86400000:.1f} gun)")
    print(f"Symbols: {len(SYMBOLS)}")
    print(f"Output:  {OUT_DIR}")
    print()

    total_rows = 0
    ok = 0
    fail = 0
    t0 = time.time()
    for i, sym in enumerate(SYMBOLS, 1):
        try:
            print(f"[{i:2d}/{len(SYMBOLS)}] {sym:<12} ", end="", flush=True)
            raw = fetch_klines(sym, START_TS_MS, END_TS_MS)
            if not raw:
                print("EMPTY (delisted?)")
                fail += 1
                continue
            rows = to_csv_rows(raw)
            path = write_csv(sym, rows)
            n = len(rows)
            total_rows += n
            ok += 1
            print(f"OK  {n:>6} bar -> {path.name}")
        except Exception as e:
            print(f"FAIL  {type(e).__name__}: {e}")
            fail += 1
    elapsed = time.time() - t0
    print()
    print(
        f"=== DONE: {ok} ok / {fail} fail / {total_rows} total bars / {elapsed:.1f}s ==="
    )


if __name__ == "__main__":
    main()
