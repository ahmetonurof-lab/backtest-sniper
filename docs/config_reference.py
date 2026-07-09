"""
config_reference.py — SNAPSHOT: sniper/src/config.py (2026-07-09)
Import edilmez, sadece kiyaslama icindir.
17 coin mevcut (13 canli + 4 yeni), futures verisiyle kiyaslanacak.
"""
# ── Semboller ───────────────────────────────────────────────
SYMBOLS = [
    "BTCUSDT", "BNBUSDT", "SOLUSDT", "AVAXUSDT", "LINKUSDT",
    "XRPUSDT", "ATOMUSDT", "ADAUSDT", "APTUSDT", "DOTUSDT",
    "NEARUSDT", "ETHUSDT", "SUIUSDT",
]

# ── ATR-bazli FVG esigi ────────────────────────────────────
FVG_MIN_SIZE_ATR_MULT = 0.06

# ── Session saatleri ───────────────────────────────────────
SESSION_HOURS = {
    "DEFAULT":    {"start": 22, "end": 2},
    "REAL_CBDR":  {"start": 19, "end": 1},
    "ASIA_RANGE": {"start": 1,  "end": 5},
}

# ── CBDR Risk Matrisi (coin bazli session + bucket carpani) ──
CBDR_RISK_MATRIX = {
    "ADAUSDT":  {"session": "DEFAULT",    "weekend_bonus": False, "weekend_mult": 1.0, "buckets": [(0.0, 1.0, 1.0), (1.0, 1.5, 1.0), (1.5, 2.0, 1.0), (2.0, 3.0, 1.0), (3.0, 5.0, 1.5), (5.0, 999.0, 1.0)]},
    "APTUSDT":  {"session": "ASIA_RANGE", "weekend_bonus": True,  "weekend_mult": 1.5, "buckets": [(0.0, 1.0, 1.0), (1.0, 1.5, 1.0), (1.5, 2.0, 1.0), (2.0, 3.0, 1.5), (3.0, 5.0, 1.2), (5.0, 999.0, 1.5)]},
    "ATOMUSDT": {"session": "REAL_CBDR",  "weekend_bonus": True,  "weekend_mult": 1.5, "buckets": [(0.0, 1.0, 1.0), (1.0, 1.5, 1.0), (1.5, 2.0, 1.5), (2.0, 3.0, 1.5), (3.0, 5.0, 1.0), (5.0, 999.0, 1.0)]},
    "AVAXUSDT": {"session": "ASIA_RANGE", "weekend_bonus": False, "weekend_mult": 1.0, "buckets": [(0.0, 1.0, 1.0), (1.0, 1.5, 1.0), (1.5, 2.0, 1.0), (2.0, 3.0, 1.5), (3.0, 5.0, 1.0), (5.0, 999.0, 0.8)]},
    "BNBUSDT":  {"session": "ASIA_RANGE", "weekend_bonus": False, "weekend_mult": 1.0, "buckets": [(0.0, 1.0, 1.0), (1.0, 1.5, 1.0), (1.5, 2.0, 1.5), (2.0, 3.0, 1.0), (3.0, 5.0, 1.0), (5.0, 999.0, 1.0)]},
    "BTCUSDT":  {"session": "REAL_CBDR",  "weekend_bonus": False, "weekend_mult": 1.0, "buckets": [(0.0, 1.0, 1.0), (1.0, 1.5, 1.2), (1.5, 2.0, 1.2), (2.0, 3.0, 1.0), (3.0, 5.0, 0.8), (5.0, 999.0, 1.0)]},
    "DOTUSDT":  {"session": "REAL_CBDR",  "weekend_bonus": False, "weekend_mult": 1.0, "buckets": [(0.0, 1.0, 0.8), (1.0, 1.5, 1.0), (1.5, 2.0, 1.0), (2.0, 3.0, 1.2), (3.0, 5.0, 1.0), (5.0, 999.0, 1.5)]},
    "ETHUSDT":  {"session": "REAL_CBDR",  "weekend_bonus": False, "weekend_mult": 1.0, "buckets": [(0.0, 1.0, 0.8), (1.0, 1.5, 1.0), (1.5, 2.0, 1.2), (2.0, 3.0, 0.8), (3.0, 5.0, 1.5), (5.0, 999.0, 0.8)]},
    "LINKUSDT": {"session": "ASIA_RANGE", "weekend_bonus": False, "weekend_mult": 1.0, "buckets": [(0.0, 1.0, 1.0), (1.0, 1.5, 1.0), (1.5, 2.0, 1.0), (2.0, 3.0, 1.5), (3.0, 5.0, 1.0), (5.0, 999.0, 1.0)]},
    "NEARUSDT": {"session": "ASIA_RANGE", "weekend_bonus": False, "weekend_mult": 1.0, "buckets": [(0.0, 1.0, 0.8), (1.0, 1.5, 1.0), (1.5, 2.0, 1.0), (2.0, 3.0, 1.2), (3.0, 5.0, 1.2), (5.0, 999.0, 1.5)]},
    "SOLUSDT":  {"session": "DEFAULT",    "weekend_bonus": False, "weekend_mult": 1.0, "buckets": [(0.0, 1.0, 1.2), (1.0, 1.5, 1.0), (1.5, 2.0, 1.0), (2.0, 3.0, 1.0), (3.0, 5.0, 0.8), (5.0, 999.0, 1.2)]},
    "SUIUSDT":  {"session": "DEFAULT",    "weekend_bonus": True,  "weekend_mult": 1.5, "buckets": [(0.0, 1.0, 1.0), (1.0, 1.5, 1.0), (1.5, 2.0, 1.0), (2.0, 3.0, 1.2), (3.0, 5.0, 1.0), (5.0, 999.0, 1.0)]},
    "XRPUSDT":  {"session": "DEFAULT",    "weekend_bonus": False, "weekend_mult": 1.0, "buckets": [(0.0, 1.0, 1.0), (1.0, 1.5, 1.0), (1.5, 2.0, 1.0), (2.0, 3.0, 1.0), (3.0, 5.0, 1.5), (5.0, 999.0, 1.0)]},
}

# ── Risk parametreleri ──────────────────────────────────────
INITIAL_BALANCE = 10000.0
RISK_PER_TRADE = 0.003
SL_ATR_MULT = 1.5
TP_RR = 2.0
FVG_BUFFER_MULT = 0.50
EARLY_LONDON_RISK_MULT = 1.5
MIN_REL_FVG_THRESHOLD = 0.50
