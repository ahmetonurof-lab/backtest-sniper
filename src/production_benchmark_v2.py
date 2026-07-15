#!/usr/bin/env python
# production_benchmark_v2.py
import time
import statistics
from pathlib import Path
import pandas as pd

DATA_DIR = Path("data/daily")
SYMBOLS = [
    "AAVEUSDT",
    "ADAUSDT",
    "ALGOUSDT",
    "APTUSDT",
    "ARBUSDT",
    "ATOMUSDT",
    "AVAXUSDT",
    "BNBUSDT",
    "DOGEUSDT",
    "DOTUSDT",
    "DYDXUSDT",
    "ENAUSDT",
    "GMXUSDT",
    "INJUSDT",
    "LDOUSDT",
    "LINKUSDT",
    "NEARUSDT",
    "ONDOUSDT",
    "OPUSDT",
    "PYTHUSDT",
    "RENDERUSDT",
    "SEIUSDT",
    "SOLUSDT",
    "STRKUSDT",
    "SUIUSDT",
    "TIAUSDT",
    "UNIUSDT",
    "XRPUSDT",
]

RUNS = 10
WARMUP = 2


def load_csv(sym):
    return pd.read_csv(DATA_DIR / f"{sym}_1m_raw.csv")


def load_feather(sym):
    return pd.read_feather(DATA_DIR / f"{sym}_1m_raw.feather")


LOADERS = {"csv": load_csv, "feather": load_feather}


def import_analyzer():
    from _worker import analyze_one_symbol

    return analyze_one_symbol


def bench(loader_name, symbol, runs=RUNS):
    loader = LOADERS[loader_name]
    analyzer = import_analyzer()
    times = []
    for i in range(runs + WARMUP):
        t0 = time.perf_counter()
        df = loader(symbol)
        _ = analyzer(df)
        elapsed = time.perf_counter() - t0
        if i >= WARMUP:
            times.append(elapsed)
    return {
        "mean": statistics.mean(times),
        "stdev": statistics.stdev(times) if len(times) > 1 else 0,
    }


def main():
    print(f"\n{'='*50}")
    print(f"  PRODUCTION LOADER BENCHMARK — {time.strftime('%H:%M:%S')}")
    print(f"{'='*50}\n")
    for sym in SYMBOLS:
        print(f"\n--- {sym} ---")
        csv_r = bench("csv", sym)
        ft_r = bench("feather", sym)
        speedup = csv_r["mean"] / ft_r["mean"]
        print(f"  CSV      {csv_r['mean']*1000:8.1f}ms ± {csv_r['stdev']*1000:.1f}ms")
        print(f"  FEATHER  {ft_r['mean']*1000:8.1f}ms ± {ft_r['stdev']*1000:.1f}ms")
        print(f"  SPEEDUP  {speedup:.2f}x  {'✓' if speedup>=1.2 else '✗'}")
    print(f"\n{'='*50}")


if __name__ == "__main__":
    main()
