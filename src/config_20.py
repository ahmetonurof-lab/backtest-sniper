"""
config_20.py — 20 coin test configi (futures verisiyle backtest icin).
Mevcut 13 coin'in ayarlarini korur, 7 yeni coini defaultla ekler.
Gercek config'ten import edilmez, bagimsizdir (test amaciyla).
"""
INITIAL_BALANCE = 10000.0
RISK_PER_TRADE = 0.003
LEVERAGE = 5

SYMBOLS = [
    "BTCUSDT","BNBUSDT","SOLUSDT","AVAXUSDT","LINKUSDT",
    "XRPUSDT","ATOMUSDT","ADAUSDT","APTUSDT","DOTUSDT",
    "NEARUSDT","ETHUSDT","SUIUSDT",
    "OPUSDT","ARBUSDT","INJUSDT","ALGOUSDT",
    "AAVEUSDT","UNIUSDT","DOGEUSDT",
]

SESSION_HOURS = {
    "DEFAULT":    {"start": 22, "end": 2},
    "REAL_CBDR":  {"start": 19, "end": 1},
    "ASIA_RANGE": {"start": 1,  "end": 5},
}

FVG_MIN_SIZE_ATR_MULT = 0.06
FVG_SIZE_MAP = {}
SL_ATR_MULT = 1.5
TP_RR = 2.0
FVG_BUFFER_MULT = 0.50
EARLY_LONDON_RISK_MULT = 1.5
MIN_REL_FVG_THRESHOLD = 0.50
GLOBAL_FVG_EXPIRY_BARS = 45
CBDR_DEAD_THRESHOLD_PCT = 0.5
ASIA_DEAD_THRESHOLD_PCT = 0.3
TRAIL_MIN_MOVE_MULT = 0.2
BE_RISK_MULT = 1.0
BE_SPREAD_PTS = 0.0
ATR_TRAIL_MULT = 0.25
MIN_STOP_DIST_PCT = 0.006
MAX_MARGIN_PCT = 0.20
MIN_RISK_DIST_ATR_MULT = 0.1
MAX_SL_DIST_MULT = 2.0
DEFAULT_ATR_FALLBACK_PCT = 0.0001
CBDR_SWEEP_ATR_TOLERANCE_MULT = 0.5
CBDR_SWEEP_DEFAULT_TOLERANCE = 10.0
FVG_BUFFER_MIN_FACTOR = 0.10
FVG_WICK_RATIO_MAX = 0.75
BINANCE_API_KEY = ""
BINANCE_API_SECRET = ""
IS_TESTNET = True

# ── CBDR Risk Matrisi ───────────────────────────────────────
CBDR_RISK_MATRIX = {
    # ── Mevcut 13 coin (sniper/config.py'deki ayarlar) ──
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
    # ── Yeni 7 coin (default 1.0x, sonra analiz sonucu guncellenecek) ──
    "OPUSDT":   {"session": "ASIA_RANGE", "weekend_bonus": False, "weekend_mult": 1.0, "buckets": [(0.0, 1.0, 1.0), (1.0, 1.5, 1.0), (1.5, 2.0, 1.0), (2.0, 3.0, 1.0), (3.0, 5.0, 1.0), (5.0, 999.0, 1.0)]},
    "ARBUSDT":  {"session": "ASIA_RANGE", "weekend_bonus": False, "weekend_mult": 1.0, "buckets": [(0.0, 1.0, 1.0), (1.0, 1.5, 1.0), (1.5, 2.0, 1.0), (2.0, 3.0, 1.0), (3.0, 5.0, 1.0), (5.0, 999.0, 1.0)]},
    "INJUSDT":  {"session": "ASIA_RANGE", "weekend_bonus": False, "weekend_mult": 1.0, "buckets": [(0.0, 1.0, 1.0), (1.0, 1.5, 1.0), (1.5, 2.0, 1.0), (2.0, 3.0, 1.0), (3.0, 5.0, 1.0), (5.0, 999.0, 1.0)]},
    "ALGOUSDT": {"session": "ASIA_RANGE", "weekend_bonus": False, "weekend_mult": 1.0, "buckets": [(0.0, 1.0, 1.0), (1.0, 1.5, 1.0), (1.5, 2.0, 1.0), (2.0, 3.0, 1.0), (3.0, 5.0, 1.0), (5.0, 999.0, 1.0)]},
    "AAVEUSDT": {"session": "ASIA_RANGE", "weekend_bonus": False, "weekend_mult": 1.0, "buckets": [(0.0, 1.0, 1.0), (1.0, 1.5, 1.0), (1.5, 2.0, 1.0), (2.0, 3.0, 1.0), (3.0, 5.0, 1.0), (5.0, 999.0, 1.0)]},
    "UNIUSDT":  {"session": "ASIA_RANGE", "weekend_bonus": False, "weekend_mult": 1.0, "buckets": [(0.0, 1.0, 1.0), (1.0, 1.5, 1.0), (1.5, 2.0, 1.0), (2.0, 3.0, 1.0), (3.0, 5.0, 1.0), (5.0, 999.0, 1.0)]},
    "DOGEUSDT": {"session": "ASIA_RANGE", "weekend_bonus": False, "weekend_mult": 1.0, "buckets": [(0.0, 1.0, 1.0), (1.0, 1.5, 1.0), (1.5, 2.0, 1.0), (2.0, 3.0, 1.0), (3.0, 5.0, 1.0), (5.0, 999.0, 1.0)]},
}
