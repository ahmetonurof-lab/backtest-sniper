"""
session_router_reference.py — SNAPSHOT: sniper/src/session_router.py (2026-07-09)
Import edilmez, sadece kiyaslama icindir.
"""
import config as cfg  # sniper/src/config.py

def get_cbdr_multiplier(symbol: str, cbdr_pct: float | None) -> float:
    profile = cfg.CBDR_RISK_MATRIX.get(symbol)
    if not profile:
        return 1.0
    for lo, hi, mult in profile["buckets"]:
        if lo <= cbdr_pct < hi:
            return mult
    return 1.0

def get_session_hours(symbol: str) -> dict[str, int]:
    profile = cfg.CBDR_RISK_MATRIX.get(symbol)
    if not profile:
        return {"start": 22, "end": 2}
    hours = cfg.SESSION_HOURS.get(profile["session"])
    return hours or {"start": 22, "end": 2}

def should_trade(symbol: str, cbdr_width_pct: float | None = None) -> tuple:
    profile = cfg.CBDR_RISK_MATRIX.get(symbol)
    if profile is None:
        return False, symbol + " CBDR_RISK_MATRIX'te tanimli degil"
    if cbdr_width_pct is not None:
        cbdr_mult = get_cbdr_multiplier(symbol, cbdr_width_pct)
        if cbdr_mult == 0.0:
            return False, symbol + " CBDR=" + f"{cbdr_width_pct:.2f}%" + " Zehirli Bolge (mult=0.0)"
    return True, ""
