"""
_worker.py â€” Ayri process worker fonksiyonu.
ProcessPoolExecutor child process'lerinde calisir.
Ayri dosyada olmasi Windows spawn deadlock'ini onler.
"""

import os
import sys
from collections import defaultdict

from analyze_cbdr_thresholds import (
    collect_daily_data,
    compute_session_stats,
    wilson_lower,
    wilson_upper,
    auto_multiplier,
    SESSION_CONFIGS,
)

_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _dir)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


class _cfg:
    INITIAL_BALANCE = 10000.0
    RISK_PER_TRADE = 0.003
    SL_ATR_MULT = 1.5
    TP_RR = 2.0
    FVG_BUFFER_MULT = 0.50
    EARLY_LONDON_RISK_MULT = 1.5
    MIN_REL_FVG_THRESHOLD = 0.50
    FVG_WICK_RATIO_MAX = 0.75
    FVG_BUFFER_MIN_FACTOR = 0.10
    ATR_TRAIL_MULT = 0.25
    TRAIL_MIN_MOVE_MULT = 0.2
    BE_RISK_MULT = 1.0
    BE_SPREAD_PTS = 0.0
    FVG_MIN_SIZE_ATR_MULT = 0.06
    FVG_SIZE_MAP: dict = {}
    GLOBAL_FVG_EXPIRY_BARS = 45
    MIN_RISK_DIST_ATR_MULT = 0.1
    CBDR_DEAD_THRESHOLD_PCT = 0.5
    ASIA_DEAD_THRESHOLD_PCT = 0.3
    CBDR_SWEEP_ATR_TOLERANCE_MULT = 0.5
    CBDR_SWEEP_DEFAULT_TOLERANCE = 10.0
    CBDR_RISK_MATRIX: dict = {}


sys.modules["config"] = _cfg


DEFAULT_BUCKET_BOUNDS = [
    (0.0, 1.0),
    (1.0, 1.5),
    (1.5, 2.0),
    (2.0, 3.0),
    (3.0, 5.0),
    (5.0, 999.0),
]


def analyze_one_symbol(sym: str) -> dict | None:
    """Bir sembol icin Adim 1 (session fit) + Adim 2 (bucket) calistirir.
    Ayri ProcessPoolExecutor worker'inda calismasi icin ayri dosyada."""
    feather_path = os.path.join(
        os.path.dirname(__file__), "data", "daily", f"{sym}_1m_raw.feather"
    )
    if not os.path.isfile(feather_path):
        return None

    session_results = {}
    collect_cache = {}
    for sname, shours in SESSION_CONFIGS.items():
        display_name = f"{sym}/{sname}"
        r = collect_daily_data(
            sym, session_name=display_name, session_hours=shours, quiet=True
        )
        if r is None:
            print(f"    [{display_name}] VERI YOK", flush=True)
            continue
        collect_cache[(sym, sname)] = r
        daily_rows, wins, losses, trade_records, rejection_counts = r
        stats = compute_session_stats(
            [(t["trade_id"], sname, t["pnl"], t["result"]) for t in trade_records],
            _cfg.INITIAL_BALANCE,
        )
        stats["trades"] = len(trade_records)
        stats["rejections"] = dict(rejection_counts)
        session_results[sname] = stats

    if not session_results:
        return None

    ranked = []
    for sname, st in session_results.items():
        bep = st.get("be_plus_pct", 0)
        pf = st.get("profit_factor", 0)
        pnl = abs(st.get("total_pnl", 0))
        dd = st.get("max_dd_pct", 1)
        score = (bep * pf * pnl) / dd
        ranked.append((score, sname, st))
    ranked.sort(key=lambda x: x[0], reverse=True)
    best_score, best_sname, best_st = ranked[0]

    bucket_result = None
    cached = collect_cache.get((sym, best_sname))
    if cached is not None:
        daily_rows, wins, losses, trade_records, _ = cached
        valid = [d for d in daily_rows if d["cbdr_pct"] is not None]
        if valid:
            bucket_data: dict = defaultdict(lambda: {"trades": 0, "wins": 0})
            for d in valid:
                cbdr_w = d["cbdr_pct"]
                for lo, hi in DEFAULT_BUCKET_BOUNDS:
                    if lo <= cbdr_w < hi:
                        bucket_data[(lo, hi)]["trades"] += d.get("trades", 0)
                        bucket_data[(lo, hi)]["wins"] += d.get("wins", 0)
                        break
            bucket_stats = []
            for lo, hi in DEFAULT_BUCKET_BOUNDS:
                bd = bucket_data.get((lo, hi), {"trades": 0, "wins": 0})
                n = bd["trades"]
                w = bd["wins"]
                wr = w / n if n > 0 else 0.0
                wl = wilson_lower(w, n) * 100
                wh = wilson_upper(w, n) * 100
                mult = auto_multiplier(wr * 100, wl, n)
                bucket_stats.append(
                    {
                        "lo": lo,
                        "hi": hi,
                        "mult": mult,
                        "label": f"({lo:.1f}, {hi:.1f}, {mult:.1f})",
                        "trades": n,
                        "wins": w,
                        "wr": round(wr * 100, 1),
                        "wilson_lower": round(wl, 1),
                        "wilson_upper": round(wh, 1),
                    }
                )
            bucket_result = bucket_stats

    print(
        f"  [{sym}] bitti -> BEST={best_sname} ({best_st['total_trades']} trade, PnL={best_st['total_pnl']:+.0f})",
        flush=True,
    )
    return {
        "sym": sym,
        "best_sname": best_sname,
        "best_score": best_score,
        "best_stats": best_st,
        "session_results": session_results,
        "bucket_stats": bucket_result,
    }
