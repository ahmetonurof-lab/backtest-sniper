"""
backtest_engine.py — V5 backtest engine: live-identical trade motoru.
"""

# ruff: noqa: E402, E702
import math
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

import pandas as pd

os.environ["SNIPER_OUTPUT_DIR"] = os.path.join(
    os.path.dirname(__file__), "..", "output"
)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_SNIPER_SRC = os.path.join(os.path.dirname(__file__), "..", "..", "sniper", "src")
if _SNIPER_SRC not in sys.path:
    sys.path.insert(0, _SNIPER_SRC)

import config as cfg

from fvg import detect_fvgs
from indicators import calculate_true_range, update_atr
from models import Bar
from retrace_state import RetraceStateMachine
from session import DailyBias, SessionState
from sweep_sync import process_sweep
from session_router import (
    get_cbdr_multiplier,
    should_trade,
    get_session_hours,
)
from mss import detect_mss
from pivot import SwingStateManager, find_swing_highs, find_swing_lows

# ── E varyanti (A/E1/E2): CHoCH giris filtresi ─────────────────
# ENTRY_VARIANT config'ten gelir; degilse baseline "A" kullanilir.
ENTRY_VARIANT = getattr(cfg, "ENTRY_VARIANT", "A")

# ── Komisyon ───────────────────────────────────────────────────────
COMMISSION_RATE = 0.0005  # %0.05 Binance futures taker fee (each leg)

# ─── Session ──────────────────────────────────────────────────────
SESSION_NAME = "MULTI_SESSION"
SESSION_HOURS = {"start": 22, "end": 2}

SYMBOLS_TO_TEST = [
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
]

_DATA_CACHE: dict[str, list] = {}


def load_data(filepath):
    if filepath in _DATA_CACHE:
        return _DATA_CACHE[filepath]
    t0 = time.time()
    df = pd.read_feather(filepath)
    t1 = time.time()
    ts_ms = (
        pd.to_datetime(df["open_time"], format="%Y-%m-%d %H:%M:%S")
        .values.astype("datetime64[ms]")
        .astype("int64")
    )
    n = len(df)
    bars = [None] * n
    o = df["open"].to_numpy(dtype=float)
    high_arr = df["high"].to_numpy(dtype=float)
    low_arr = df["low"].to_numpy(dtype=float)
    c = df["close"].to_numpy(dtype=float)
    v = df["volume"].to_numpy(dtype=float)
    for i in range(n):
        bars[i] = Bar(
            index=i,
            open=o[i],
            high=high_arr[i],
            low=low_arr[i],
            close=c[i],
            volume=v[i],
            is_closed=True,
            timestamp=int(ts_ms[i]),
        )
    t2 = time.time()
    print(
        f"      load_data: {n} bar {t1 - t0:.1f}s (feather) + {t2 - t1:.1f}s (bar) = {t2 - t0:.1f}s"
    )
    _DATA_CACHE[filepath] = bars
    return bars


def resample_15m(bars_1m):
    # BUG 13 FIX: Timestamp bazlı hizalama — veri 00:07'den başlıyorsa naif range()
    # yaklaşımı 00:07, 00:22, ... üretir; doğrusu 00:00, 00:15, 00:30 slot'larıdır
    _15M_MS = 15 * 60 * 1000  # 15 dakika milisaniye cinsinden
    buckets: dict = {}
    for b in bars_1m:
        slot = (b.timestamp // _15M_MS) * _15M_MS  # timestamp'i 15m sınırına yuvarla
        if slot not in buckets:
            buckets[slot] = []
        buckets[slot].append(b)
    m15 = []
    for slot in sorted(buckets):
        c = buckets[slot]
        if len(c) < 15:
            continue  # Eksik veri → bu 15m bar'ı atla
        m15.append(
            Bar(
                index=len(m15),
                open=c[0].open,
                high=max(b.high for b in c),
                low=min(b.low for b in c),
                close=c[-1].close,
                volume=sum(b.volume for b in c),
                is_closed=True,
                timestamp=slot,
            )
        )
    return m15


# ─── HTF (1D) BIAS — kullanici cikarimi: "CBDR ve 1D ayni ya da natural ise gir" ──
# Sonnet _detect_htf_bias ile AYNI BOS mantigi (D1_BOS_LOOKBACK=25, swing 2/2).
# NO-LOOKAHEAD: bias YALNIZCA kapali (tamamlanmis) gunluk barlardan hesaplanir.
#   _d1_bias_lookup(sym_b15) -> (d1_bars, day_end_15m_idx, bias_by_day)
#     - d1_bars: 15m bar dizisinden turetilmis gunluk barlar (OHLC, kapanis aninda
#       bilinen tek deger). Her gun YALNIZCA kendi son 15m bari kapandiktan sonra
#       "tamamlanmis" sayilir.
#     - bias_by_day[d] : d. gun kapandiktan SONRA bilinecek 1D bias ("LONG"/
#       "SHORT"/None=natural). d-1.gune kadar olan kapali barlar ile hesaplanir
#       (yani d. gunun kendisi HICBIR zaman bias'a dahil edilmez; guncel gunun
#       henuz kapali olmayan bari lookahead yapmaz).
#   _d1_bias_for_15m(sym_b15, d1_bars, day_end_15m_idx, bias_by_day)
#     -> her 15m bar sb icin o an bilinen bias (no-lookahead).
#   _d1_bos_bias(d1_segment) -> segmentin son kapanisi + swing BOS yonlu bias.
def _d1_bos_bias(d1_segment):
    """Son D1_BOS_LOOKBACK gunluk bar uzerinde 1D BOS bias (Sonnet ile ayni)."""
    if len(d1_segment) < 5:
        return None
    highs = find_swing_highs(d1_segment, left=2, right=2)
    lows = find_swing_lows(d1_segment, left=2, right=2)
    last_close = d1_segment[-1].close
    last_bull_bos = -1
    last_bear_bos = -1
    for sh in highs:
        if last_close > sh.price and sh.bar_index > last_bull_bos:
            last_bull_bos = sh.bar_index
    for sl in lows:
        if last_close < sl.price and sl.bar_index > last_bear_bos:
            last_bear_bos = sl.bar_index
    if last_bull_bos == -1 and last_bear_bos == -1:
        return None
    return "LONG" if last_bull_bos >= last_bear_bos else "SHORT"


_DAY_MS = 86400 * 1000


def _d1_bias_lookup(sym_b15):
    """15m bar dizisinden gunluk barlari + gunluk bias tablosunu uretir.

    No-lookahead invariantlari:
      - Gunluk bar d, 15m index'i day_end_15m_idx[d] olan bari ile biter; o bar
        indexli sb icin d. gun HENUZ kapali DEGILDIR (bias guncel gunu icermez).
      - bias_by_day[d], d-1 ve onceki KAPALI gunlerden hesaplanir.
    """
    buckets = {}
    for b in sym_b15:
        day = b.timestamp // _DAY_MS
        buckets.setdefault(day, []).append(b)
    d1_bars = []
    day_end_15m_idx = []
    for day in sorted(buckets):
        c = buckets[day]
        d1_bars.append(
            Bar(
                index=len(d1_bars),
                open=c[0].open,
                high=max(x.high for x in c),
                low=min(x.low for x in c),
                close=c[-1].close,
                volume=sum(x.volume for x in c),
                is_closed=True,
                timestamp=day * _DAY_MS,
            )
        )
        day_end_15m_idx.append(c[-1].index)
    bias_by_day = [None] * len(d1_bars)
    for d in range(len(d1_bars)):
        seg = d1_bars[max(0, d - D1_BOS_LOOKBACK + 1) : d + 1]
        bias_by_day[d] = _d1_bos_bias(seg)
    return d1_bars, day_end_15m_idx, bias_by_day


def _d1_bias_for_15m(sym_b15, day_end_15m_idx, bias_by_day):
    """Her 15m bar sb icin o an bilinen 1D bias (no-lookahead lookup).

    d = sb'de tamamen KAPANMIS gun sayisi. bias_by_day[k] k. gun kapandiktan
    SONRA bilinen bias oldugundan, sb'deki bilinen bias = bias_by_day[d-1]
    (son kapanan gunun bias'i). Henuz hicbir gun kapali degilse None.
    """
    n = len(sym_b15)
    out = [None] * n
    d = 0
    n_days = len(day_end_15m_idx)
    for sb in range(n):
        while d < n_days and day_end_15m_idx[d] < sb:
            d += 1
        out[sb] = bias_by_day[d - 1] if d > 0 else None
    return out


# ─── FVG status (3-state) ───────────────────────────────
def get_fvg_status(top, bottom, direction, b):
    """
    Returns: 'INVALIDATED', 'ACTIVE_ENTRY_ZONE', or 'ALIVE'

    INVALIDATED:  Fiyat gap'in karşı tarafına close yaptı (bullish → close < bottom,
                  bearish → close > top). Bu FVG ölmüştür, pool'dan sil.
    ACTIVE_ENTRY_ZONE: Fiyat FVG gap'inin içine girdi (bar overlap). Entry sinyali.
    ALIVE:        Henüz bir şey olmadı, bekle.
    """
    if direction == "bullish":
        if b.close < bottom:
            return "INVALIDATED"
        if b.high >= bottom and b.low <= top:
            return "ACTIVE_ENTRY_ZONE"
        return "ALIVE"
    # bearish
    if b.close > top:
        return "INVALIDATED"
    if b.high >= bottom and b.low <= top:
        return "ACTIVE_ENTRY_ZONE"
    return "ALIVE"


# ─── Trailing replikasyon modu (replay_trailing_v2.py kullanır) ──
# "retrace"      : yalnizca gap ici kapanis onaylar (eski davranis, DEFAULTS)
# "continuation" : gap ici VEYA pozisyon lehine far-side kapanis
# "atr_chase"    : + FVG aday kullanilamazsa SL = close ∓ K*ATR fallback
# "activation"   : FVG yolu retrace ile BIREBIR; ATR-chase fallback YALNIZCA
#                  unrealized kar >= TRAIL_ACTIVATION_R_MULT * risk_pts
#                  (dinamik R-kati esik) oldugunda devreye girer
# D-2 parite fixi: modul sabiti artik canli config default'undan turetilir.
# KAPANIS (2026-08-08): canli config TRAIL_MODE="retrace" — D modu (activation
# K=2.0/R=1.5) ve continuation-confirm tam evren taramasinda A/retrace'i
# geceMEDI, geri cekildi. Asagidaki continuation/activation degiskenleri
# DENEYSEL kalinti olarak tutulur (replay_trailing_v2.py grid taramasi icin
# kullanilabilir); silinecekse canli trailing_manager ile senkron silinmeli.
TRAIL_MODE = getattr(cfg, "TRAIL_MODE", "retrace")

# DENEYSEL (kullanilmiyor — TRAIL_MODE=retrace): activation ATR-chase kar
# esigi — dinamik R-kati. Esik = TRAIL_ACTIVATION_R_MULT * risk_pts
# (risk_pts = |entry - initial_sl|). D modu geri cekildi (2026-08-08).
TRAIL_ACTIVATION_R_MULT = getattr(cfg, "TRAIL_ACTIVATION_R_MULT", 1.5)

# DENEYSEL (kullanilmiyor): ATR-chase fallback SL tamponu K * ATR (canli:
# CONT_BUFFER_MULT=2.0). D modu geri cekildi (2026-08-08).
CONT_BUFFER_MULT = getattr(cfg, "CONT_BUFFER_MULT", 2.0)

# ─── Trailing deneyleri (LUNA direktifi Plan C madde 4: baseline'dan AYRI) ──
# PROFIT_GATE_R > 0: FVG retrace trail YALNIZCA unrealized kar >= R*risk_pts
# oldugunda devreye girer (R-kar kapisi). 0.0 = devre disi (baseline).
PROFIT_GATE_R = 0.0

# TRAIL_BE_ON_GATE: PROFIT_GATE_R esigi asilinca SL'yi once entry'ye (BE) tasir
# (profit protection / breakeven buffer). HYBRID_FVG_PLUS_PROFIT_GATE deneyi.
TRAIL_BE_ON_GATE = False

# ─── LUNA Profit Protection / Breakeven Buffer (Plan C madde 4) ──────────
# LUNA'nin 2026-08-15 onerisinin BIREBIR uygulamasi:
#   1) PROFIT_PROTECT_GATE_R > 0: trade en az +PROFIT_PROTECT_GATE_R*R unrealized
#      kar gorunce koruma AKTIFLESIR (intrabar high/low bazli — 'gordugu' an).
#   2) Ilk koruma: SL = entry + fees + PROFIT_PROTECT_BE_R*R (long),
#      SL = entry - fees - PROFIT_PROTECT_BE_R*R (short). fees = round-trip
#      komisyon (entry+exit leg). Trade BE + fees + 0.1R uzerine kilitlenir.
#   3) Trend devam: her bar son onayli swing low/high VEYA ATR chandelier:
#      long  SL = max(old, son_swing_low  - PROFIT_PROTECT_SWING_ATR_MULT*ATR)
#      short SL = min(old, son_swing_high + PROFIT_PROTECT_SWING_ATR_MULT*ATR)
#      (ratchet: sadece koruyucu yone hareket, geri donus yok).
#   4) FVG retrace trail DEVAM eder; profit-protection ile carpismaz — daha
#      korumaci seviye kazanir (long: max, short: min).
# KAPALI (0.0/None): baseline ile bit-bit ayni davranis.
PROFIT_PROTECT_GATE_R = 0.0
PROFIT_PROTECT_BE_R = 0.1
PROFIT_PROTECT_SWING_ATR_MULT = 0.5

# ─── HTF Bias Alignment (2026-08-15 kullanici cikarimi) ────────────────────
# Dünkü arastirma cikarimi: "CBDR ve 1D ayni ya da natural ise isleme gir".
# HTF_BIAS_ALIGN=True iken 1D BOS bias (son D1_BOS_LOOKBACK gunde swing
# high/low kirilimi) hesaplanir ve CBDR daily_bias ile eslestirilir:
#   - 1D bias ve CBDR ayni yon   -> giris serbest
#   - 1D bias yok (natural)      -> giris serbest
#   - 1D bias ve CBDR zit yon    -> giris REDDEDILIR (HTF_BIAS_CONTRA)
# KAPALI (False): baseline ile bit-bit ayni davranis (bias_reject degismez).
HTF_BIAS_ALIGN = False
D1_BOS_LOOKBACK = 25

# ─── KISMI TP (2026-08-15 LUNA 2. varyasyon) ────────────────────────────────
# PARTIAL_TP_R > 0 iken: pozisyonun PARTIAL_TP_FRAC orani, giris fiyatindan
# PARTIAL_TP_R * risk_pts (risk_pts = |entry - initial_sl|) uzakliktaki
# fiyatta KAPANIR (long: entry + R*risk_pts, short: entry - R*risk_pts).
# Kalan oran trailing (retrace) ile devam eder. Kismi kapanisin PnL'si
# t["locked_pnl"]'de birikir ve final kapanista toplam PnL'ye eklenir.
# 0.0 = devre disi (baseline ile bit-bit ayni davranis).
# [VARYASYON - Aktif] 1.2R @ %70 kapanis (LUNA 2: 1.5R @ %50'den degisti)
# PARTIAL_TP_PCT > 0 iken: R bazli seviye yerine FIYAT yuzdesi bazli tetikleyici.
# Long: entry*(1+PCT/100) fiyatina ulasinca (short: entry*(1-PCT/100)) pozisyonun
# PARTIAL_TP_FRAC orani kapanir. R bazli seviye (PARTIAL_TP_R) ile birbirini
# dislar: PCT onceliklidir (PCT > 0 ise R dikkate alinmaz).
PARTIAL_TP_R = 0.0
PARTIAL_TP_FRAC = 0.7
PARTIAL_TP_PCT = 0.0
# PARTIAL_TP_PCT > 0 iken: R bazli seviye yerine FIYAT yuzdesi bazli tetikleyici.
# Long: entry*(1+PCT/100) fiyatina ulasinca (short: entry*(1-PCT/100)) pozisyonun
# PARTIAL_TP_FRAC orani kapanir. R bazli seviye (PARTIAL_TP_R) ile birbirini
# dislar: PCT onceliklidir (PCT > 0 ise R dikkate alinmaz).
# SCALE-OUT kademesi (PARTIAL_TP_SL_PROTECT_PCT > 0 iken aktif):
#   1) Ilk tetikleyici (PCT) vurunca FRAC orani satilir, kalanin SL'si
#      entry*(1±SL_PROTECT_PCT/100)'e tasinir, TP de ayni delta kadar otelenir.
#   2) Fiyat ilk tetikleyiciden SCALE_STEP_PCT daha ileriye giderse (long:
#      entry*(1+PCT/100)*(1+SCALE_STEP_PCT/100)) kalan pozisyonun TAMAMI satilir.
# PARTIAL_TP_SCALE2_ABS_PCT > 0 ise 2. kademe GORELI yerine MUTLAK seviyededir:
#      long: entry*(1+SCALE2_ABS_PCT/100) (giristen itibaren), SCALE_STEP ezer.
PARTIAL_TP_SL_PROTECT_PCT = 0.0
PARTIAL_TP_SCALE_STEP_PCT = 0.0
PARTIAL_TP_SCALE2_ABS_PCT = 0.0
# PARTIAL_TP_TIME_EXIT_BARS > 0 iken: kismi TP sonrasi KALAN pozisyon, entry
# barindan itibaren bu kadar bar dolunca otomatik kapatilir (zaman cikisi).
# Amac: FVG trailing FVG bulamadigi senaryoda pozisyonun surunmesini onlemek.
# 0 = devre disi. TIME_EXIT kapanisi karda PROFIT_TRAIL, zararda LOSS sonucu
# alir; ayrica t["time_exit"]=True isaretlenir (rapor "zaman cikisi" ayirt eder).
PARTIAL_TP_TIME_EXIT_BARS = 0
# DISABLE_FVG_TRAIL=True iken FVG-based retrace trailing komple kapatilir
# (SL yalnizca kismi TP/scale-out kademeleriyle hareket eder, 1R sabit baslar).
# FALLBACK_LADDER ile birlikte calismaz (bu flag onceliklidir).
DISABLE_FVG_TRAIL = False

# ─── KAR MERDIVENI (Fallback Ladder, 2026-08-16 LUNA direktif) ────────────
# Mevcut FVG-based trailing FVG bulamadiginda SL'yi hareket ettiremiyor — fiyat
# duz ilerleyip geri dondugu senaryolarda kar kaciriliyor. Fallback mekanizmasi:
# fiyat entry'den ne kadar uzaksa (unrealized R), SL o kadar yuksek bir basamaga
# kilitlenir (ratchet, geri dusmez). FVG varsa FVG KAZANIR: FVG dongusu once
# islenir ve csl zaten FVG seviyesine tasinir; bu blok yalnizca merdivenin FVG'nin
# ulasmadigi (daha yuksek) seviyeyi verdigi durumda devreye girer (long: max,
# short: min = ortak koruyucu kural).
# KAPALI (ENABLE_FALLBACK_LADDER=False): baseline ile bit-bit ayni davranis.
ENABLE_FALLBACK_LADDER = False
# Basamaklar: tetikleyici (unrealized R) -> SL konumu (R, entry uzeri/alti).
# LADDER_STEP_X_R = 0 ise o basamak devre disi (SHALLOW varyanti).
LADDER_STEP_1_R = 0.5
LADDER_STEP_1_SL_R = 0.1
LADDER_STEP_2_R = 1.0
LADDER_STEP_2_SL_R = 0.5
LADDER_STEP_3_R = 1.5
LADDER_STEP_3_SL_R = 1.0
LADDER_STEP_4_R = 2.0
LADDER_STEP_4_SL_R = 1.5

# DENEYSEL (kullanilmiyor): continuation far-side SL tamponu ATR_TRAIL_MULT*ATR
# (canli: ATR_TRAIL_MULT_CONTINUATION=0.50). Continuation geri cekildi.
CONT_TRAIL_MULT = getattr(cfg, "ATR_TRAIL_MULT_CONTINUATION", 0.5)

# DENEYSEL (kullanilmiyor): continuation onay penceresi N-bar teyit (canli:
# CONTINUATION_CONFIRM_BARS=2). Continuation geri cekildi (2026-08-08).
CONT_CONFIRM_BARS = getattr(cfg, "CONTINUATION_CONFIRM_BARS", 2)


# ─── FVG retrace-only confirm helper (orijinal davranis, birebir) ──
# Retrace modu (default) bu fonksiyonu kullanir: yalnizca gap ici kapanis
# onaylar; pozisyon lehine far-side kapanis (bullish: close > top) FVG'yi
# ELIMINE ETMEZ, donguye devam eder (sonraki gap ici kapanis onay verebilir).
# Aksi yon (bullish: close < bottom) invalidation = False.
def compute_fallback_ladder_sl(side, cur_close, risk_pts, entry_price):
    """KAR MERDIVENI (Profit Ladder) — FVG trailing'in yedek mekanizmasi.

    Fiyat entry'den belirli R mesafelerindeyse SL'yi kademeli olarak
    entry +/- SL_R*R konumuna tasi (ratchet). SADECE oneri uretir; cagiran
    taraf max/min ile mevcut SL'yi korur (FVG once islenmis olabilir).
    Basamaklar LADDER_STEP_*_R / LADDER_STEP_*_SL_R sabitlerinden gelir.
    LADDER_STEP_X_R=0 olan basamak atlanir (SHALLOW gibi 2 basamakli varyant).
    risk_pts <= 0 ise None (hesaplanamaz).
    """
    if risk_pts <= 0:
        return None
    if side == "long":
        unrealized_r = (cur_close - entry_price) / risk_pts
        if LADDER_STEP_4_R > 0 and unrealized_r >= LADDER_STEP_4_R:
            return entry_price + risk_pts * LADDER_STEP_4_SL_R
        if LADDER_STEP_3_R > 0 and unrealized_r >= LADDER_STEP_3_R:
            return entry_price + risk_pts * LADDER_STEP_3_SL_R
        if LADDER_STEP_2_R > 0 and unrealized_r >= LADDER_STEP_2_R:
            return entry_price + risk_pts * LADDER_STEP_2_SL_R
        if LADDER_STEP_1_R > 0 and unrealized_r >= LADDER_STEP_1_R:
            return entry_price + risk_pts * LADDER_STEP_1_SL_R
    else:  # short
        unrealized_r = (entry_price - cur_close) / risk_pts
        if LADDER_STEP_4_R > 0 and unrealized_r >= LADDER_STEP_4_R:
            return entry_price - risk_pts * LADDER_STEP_4_SL_R
        if LADDER_STEP_3_R > 0 and unrealized_r >= LADDER_STEP_3_R:
            return entry_price - risk_pts * LADDER_STEP_3_SL_R
        if LADDER_STEP_2_R > 0 and unrealized_r >= LADDER_STEP_2_R:
            return entry_price - risk_pts * LADDER_STEP_2_SL_R
        if LADDER_STEP_1_R > 0 and unrealized_r >= LADDER_STEP_1_R:
            return entry_price - risk_pts * LADDER_STEP_1_SL_R
    return None  # degisiklik onerisi yok


def fvg_close_confirmed(fvg, all_bars):
    scan_from = fvg.real_index + 2
    for b in all_bars:
        if b.index < scan_from:
            continue
        if fvg.direction == "bullish":
            if b.close < fvg.bottom:
                return False
            if fvg.bottom <= b.close <= fvg.top:
                return True
        else:
            if b.close > fvg.top:
                return False
            if fvg.bottom <= b.close <= fvg.top:
                return True
    return False


# ─── FVG confirm-mode helper (trailing için) ─────────
# Continuation/atr_chase modlari icin: 'retrace' | 'continuation' | None.
# Dikkat: far-side kapanis hemen 'continuation' doner (sonraki barlara
# bakmaz); retrace modu bu fonksiyonu KULLANMAZ, fvg_close_confirmed kullanir.
def fvg_confirm_mode(fvg, all_bars, continuation_confirm_bars: int = 1):
    """FVG icin onay modunu dondurur: "retrace" veya "continuation".

    - "retrace": fiyat gap icinde kapandi (mevcut davranis).
    - "continuation": fiyat pozisyon lehine far-side'da ustuste
      `continuation_confirm_bars` bar kapandi (sahte kirilimlari filtreler).
    - None: invalidation veya henuz onay yok.

    trailing_manager._fvg_confirm_mode ile birebir ayni (canli paritesi).
    """
    scan_from = fvg.real_index + 2
    streak = 0
    for b in all_bars:
        if b.index < scan_from:
            continue
        if not b.is_closed:
            break
        if fvg.direction == "bullish":
            if b.close > fvg.top:
                streak += 1
                if streak >= continuation_confirm_bars:
                    return "continuation"
                continue
            streak = 0
            if b.close < fvg.bottom:
                return None
            if fvg.bottom <= b.close <= fvg.top:
                return "retrace"
        else:
            if b.close < fvg.bottom:
                streak += 1
                if streak >= continuation_confirm_bars:
                    return "continuation"
                continue
            streak = 0
            if b.close > fvg.top:
                return None
            if fvg.bottom <= b.close <= fvg.top:
                return "retrace"
    return None


_LOGGER = None


# ─── E varyanti yardimcilari (CHoCH tabanli giris) ──────────────
def _latest_choch(bars_15m):
    """Son 32 bar (8 saat, CHOCH_MAX_AGE_HOURS) icindeki en guncel CHoCH.

    An-bazli: bars_15m gecmise kirpilmis segmenttir; en son bar teyit
    (sfp_n=1 onay bari) bekledigi icin canli davranisla birebir yalnizca
    onaylanmis CHoCH'lar gorulur. CHoCH yoksa None -> E, A ile birebir.
    """
    if bars_15m is None or len(bars_15m) < 4:
        return None
    mgr = SwingStateManager()
    mgr.ingest(bars_15m)
    try:
        chochs = detect_mss(
            bars_15m,
            mgr,
            lookback=None,
            timeframe="15m",
            atr_mult=getattr(cfg, "CHOCH_ATR_OVERSHOOT", 0.15),
        )
    except Exception:
        return None
    if not chochs:
        return None
    return max(chochs, key=lambda c: c.bar_index)


def _pick_overlap_fvg(bars_15m, level, direction, atr_val, symbol):
    """CHoCH.level'a en yakin, ayni yonlu FVG'yi secer.

    Tolerans: |FVG_orta - CHoCH.level| <= max(band_genisligi,
    atr * CHOCH_FVG_OVERLAP_ATR_MULT). Uygun FVG yoksa None dondurur;
    cagiran A'nin trigger_fvg'sine duser (sadece tercih, zorunluluk degil).
    """
    if bars_15m is None or len(bars_15m) < 4:
        return None
    try:
        atr_mult = getattr(cfg, "CHOCH_FVG_OVERLAP_ATR_MULT", 1.0)
        size_mult = getattr(cfg, "FVG_SIZE_MAP", {}).get(
            symbol, getattr(cfg, "FVG_MIN_SIZE_ATR_MULT", 0.06)
        )
        min_size = max(atr_val * size_mult, 1e-8) if atr_val > 0 else 1e-8
        fvgs = detect_fvgs(
            bars_15m,
            lookback=50,
            timeframe="15m",
            min_fvg_size=min_size,
            since_index=0,
        )
    except Exception:
        return None
    cands = [f for f in fvgs if f.direction == direction]
    if not cands:
        return None
    best = min(cands, key=lambda f: abs((f.top + f.bottom) / 2 - level))
    bw = best.top - best.bottom
    tol = max(bw, atr_val * atr_mult) if atr_val > 0 else bw
    if abs((best.top + best.bottom) / 2 - level) <= tol:
        return best
    return None


def collect_fvg_profile(symbol: str):
    """V4 engine (live-identical) + captures every trigger-ready FVG with profiling data."""
    try:
        return _collect_fvg_profile_impl(symbol)
    except Exception as e:
        import traceback

        print(f"    [{symbol}] collect_fvg_profile CRASH: {e}")
        traceback.print_exc()
        return None, None, None, None, None


def _collect_fvg_profile_impl(symbol: str):
    # --- (coin bazli FVG expiry kalkti — yerini is_fvg_alive aldi) ---
    feather_path = os.path.join(
        os.path.dirname(__file__), "data", "daily", f"{symbol}_1m_raw.feather"
    )
    if not os.path.isfile(feather_path):
        return None, None, None, None, None

    ic = cfg.INITIAL_BALANCE
    rpt = cfg.RISK_PER_TRADE
    sam = cfg.SL_ATR_MULT
    tpr = cfg.TP_RR
    TP_FIXED = getattr(cfg, "TRAIL_TP_FIXED", False)
    fbm = cfg.FVG_BUFFER_MULT
    ATM = cfg.ATR_TRAIL_MULT
    TMM = cfg.TRAIL_MIN_MOVE_MULT
    FVG_MIN_SIZE_ATR_MULT = cfg.FVG_MIN_SIZE_ATR_MULT

    b1 = load_data(feather_path)
    b15 = resample_15m(b1)
    if not b15:
        print(f"    [{symbol}] resample_15m bos dondu")
        return None, None, None, None, None

    print(f"    [{symbol}] {len(b1)} bar 1m -> {len(b15)} bar 15m")
    # Per-coin session from config (CBDR_RISK_MATRIX)
    _profile = cfg.CBDR_RISK_MATRIX.get(symbol, {})
    _sname = _profile.get("session", "DEFAULT")
    _sh_info = get_session_hours(symbol)
    sh = _sh_info["start"]
    eh = _sh_info["end"]
    spans_midnight = sh > eh
    ss = SessionState(start_hour=sh, end_hour=eh)
    rsm = RetraceStateMachine(max_wick_ratio=cfg.FVG_WICK_RATIO_MAX)

    # ── LUNA Profit Protection: confirmed swing low/high lookup tables ──────
    # No-lookahead: find_swing_* fraktal sinyali bar_index + right (3) bar
    # sonra DOGRULANIR. Burada tüm serinin fraktallari bir kez cikarilir, ama
    # trailing degerlendirmesinde sadece sb - right <= sb'de "onaylanmis" olan
    # swing kullanilir (ileriye bakis yok). last_swl_bar[sb] = sb'de bilinen son
    # onayli swing low'un bar_index'i (yoksa -1).
    last_swl_price = None
    last_swl_bar = None
    last_swh_price = None
    last_swh_bar = None
    if PROFIT_PROTECT_GATE_R > 0:
        _swl = find_swing_lows(b15)
        _swh = find_swing_highs(b15)
        _nb = len(b15)
        last_swl_price = [0.0] * _nb
        last_swl_bar = [-1] * _nb
        last_swh_price = [0.0] * _nb
        last_swh_bar = [-1] * _nb
        _i = 0
        for sb in range(_nb):
            while _i < len(_swl) and _swl[_i].bar_index + 3 <= sb:
                last_swl_price[sb] = _swl[_i].price
                last_swl_bar[sb] = _swl[_i].bar_index
                _i += 1
        _i = 0
        for sb in range(_nb):
            while _i < len(_swh) and _swh[_i].bar_index + 3 <= sb:
                last_swh_price[sb] = _swh[_i].price
                last_swh_bar[sb] = _swh[_i].bar_index
                _i += 1

    day_cbdr = {}
    day_trades = defaultdict(list)
    active: list = []
    wins = []
    losses = []
    trade_records = []

    # ── HTF (1D) BIAS Alignment: no-lookahead bias tablosu ──────────────
    # Sadece HTF_BIAS_ALIGN=True iken hesaplanir. d1_bias_at[sb] = sb 15m
    # barinda "bilinen" 1D bias ("LONG"/"SHORT"/None=natural).
    d1_bias_at = None
    if HTF_BIAS_ALIGN:
        _d1, _de, _bias = _d1_bias_lookup(b15)
        d1_bias_at = _d1_bias_for_15m(b15, _de, _bias)

    fvg_by_uid = {}
    rejection_counts: dict = defaultdict(int)

    atr_val = 0.0
    prev_close = b15[0].open
    for bar in b15[1:500]:
        tr = calculate_true_range(bar, prev_close)
        if atr_val == 0.0:
            atr_val = tr  # BUG 14 FIX: İlk değer için update_atr(None) kullanma, TR ile seed et
        else:
            atr_val = update_atr(atr_val, tr)
        prev_close = bar.close

    total_bars = len(b15)
    for sb in range(500, total_bars):
        if (sb - 500) % 5000 == 0:
            pct = (sb - 500) / (total_bars - 500) * 100
            print(
                f"\r    [{_sname}] %{pct:.0f} ({sb}/{total_bars})", end="", flush=True
            )
        chunk = b15[sb - 500 : sb + 1]
        cur = b15[sb]
        tr = calculate_true_range(cur, prev_close)
        atr_val = update_atr(atr_val if atr_val > 0 else None, tr)
        prev_close = cur.close
        atr = atr_val

        try:
            edt = datetime.fromtimestamp(cur.timestamp / 1000, tz=timezone.utc)
        except Exception:
            continue

        locked_before = ss.cbdr_locked
        ss.update(edt, cur.open, cur.high, cur.low, cur.close, atr)
        just_locked = ss.cbdr_locked and not locked_before

        if just_locked and ss.cbdr_body_high > 0 and ss.cbdr_body_low > 0:
            w = ((ss.cbdr_body_high - ss.cbdr_body_low) / ss.cbdr_body_low) * 100
            day_cbdr[ss.cbdr_day] = round(w, 4)

        # Canlı bot.py:490-495 parity: pozisyon açıkken progress_rsm ÇALIŞMAZ.
        # RSM state'i trade süresince donar; kapanış sonrası BIAS_LOCKED'de
        # on_bias_fvg kaldığı yerden sürer (sweep beklenmez).
        if not active:
            process_sweep(rsm, ss, chunk, cur, atr, symbol)

        if rsm.can_trigger() and not active:
            sd = rsm.direction
            db = ss.daily_bias
            if HTF_BIAS_ALIGN:
                # Kullanici cikarimi: CBDR ve 1D ayni ya da natural ise gir.
                #   - sweep yonu (sd) vs CBDR zit  -> reddet (canli parity, korunur)
                #   - daily_bias NEUTRAL (natural) -> bu filtrede serbest
                #   - 1D bias None (natural)       -> serbest
                #   - ikisi de yonlu ve zit        -> REDDET (HTF_BIAS_CONTRA)
                if (sd == "bullish" and db == DailyBias.BEARISH) or (
                    sd == "bearish" and db == DailyBias.BULLISH
                ):
                    rsm.reset()
                    continue
                d1b = d1_bias_at[sb]
                if d1b is not None and db != DailyBias.NEUTRAL:
                    cbdr_dir = "LONG" if db == DailyBias.BULLISH else "SHORT"
                    if d1b != cbdr_dir:
                        rejection_counts["HTF_BIAS_CONTRA"] += 1
                        rsm.reset()
                        continue
            else:
                bias_reject = (
                    (sd == "bullish" and db == DailyBias.BEARISH)
                    or (sd == "bearish" and db == DailyBias.BULLISH)
                    or db == DailyBias.NEUTRAL
                )
                if bias_reject:
                    rsm.reset()
                    continue

            # ── E varyanti: CHoCH yon filtresi (config.ENTRY_VARIANT) ──
            v4_fvg = rsm.trigger_fvg
            if ENTRY_VARIANT in ("E1", "E2"):
                choch = _latest_choch(chunk)
                if choch is not None and choch.direction != sd:
                    if ENTRY_VARIANT == "E2":
                        rejection_counts["CHOCH_CONTRA"] += 1
                        rsm.reset()
                        continue
                elif choch is not None:
                    ofvg = _pick_overlap_fvg(chunk, choch.level, sd, atr, symbol)
                    if ofvg is not None:
                        v4_fvg = ofvg

            classic_fvg = {
                "direction": v4_fvg.direction if v4_fvg else "bullish",
                "top": v4_fvg.top if v4_fvg else 0,
                "bottom": v4_fvg.bottom if v4_fvg else 0,
                "size": (v4_fvg.top - v4_fvg.bottom) if v4_fvg else 0,
                "bar_index": None,
                "atr": atr,
                "v4_rejected": None,
            }
            classic_fvg["v4_fvg_top"] = v4_fvg.top if v4_fvg else None
            classic_fvg["v4_fvg_bottom"] = v4_fvg.bottom if v4_fvg else None

            # ── Session hours filter (CBDR hesaplanirken trade yasak) ──
            h = edt.hour
            if (h >= sh or h < eh) if spans_midnight else (sh <= h < eh):
                rsm.reset()
                continue

            # ── FIX #3: Next-bar-open entry (look-ahead bias giderildi) ──
            if sb + 1 >= total_bars:
                rsm.reset()
                continue
            next_bar = b15[sb + 1]
            side = "long" if sd == "bullish" else "short"
            ep = next_bar.open
            rp2 = atr * sam
            tf = v4_fvg

            if side == "long":
                if tf:
                    fh = tf.top - tf.bottom
                    if fh <= 0:
                        sl = ep - rp2 * 2
                    else:
                        ab = max(
                            fh * cfg.FVG_BUFFER_MIN_FACTOR,
                            max(rp2 * 0.1, min(fh * 0.25, rp2 * fbm)),
                        )
                        sl = tf.bottom - ab
                else:
                    sl = ep - rp2 * 2
                rd = abs(sl - ep)
                if rd <= 0:
                    sl = ep - rp2 * 2
                    rd = abs(sl - ep)
                tp = ep + rd * tpr
            else:
                if tf:
                    fh = tf.top - tf.bottom
                    if fh <= 0:
                        sl = ep + rp2 * 2
                    else:
                        ab = max(
                            fh * cfg.FVG_BUFFER_MIN_FACTOR,
                            max(rp2 * 0.1, min(fh * 0.25, rp2 * fbm)),
                        )
                        sl = tf.top + ab
                else:
                    sl = ep + rp2 * 2
                rd = abs(sl - ep)
                if rd <= 0:
                    sl = ep + rp2 * 2
                    rd = abs(sl - ep)
                tp = ep - rd * tpr

            quality_mult = 1.0
            if tf is not None:
                fvg_status = get_fvg_status(tf.top, tf.bottom, tf.direction, cur)
                if fvg_status == "INVALIDATED":
                    quality_mult = 0.0
                    classic_fvg["v4_rejected"] = "FVG_SWEPT"
                else:
                    classic_fvg["v4_rejected"] = None

            # ── Min risk dist ──
            if rd < atr * cfg.MIN_RISK_DIST_ATR_MULT:
                quality_mult = 0.0
                if classic_fvg.get("v4_rejected") is None:
                    classic_fvg["v4_rejected"] = "MIN_RISK_DIST"

            # ── CBDR + should_trade ──
            cbdr_w = None
            if ss.cbdr_body_low > 0 and not math.isinf(ss.cbdr_body_low):
                cbdr_w = (
                    (ss.cbdr_body_high - ss.cbdr_body_low) / ss.cbdr_body_low
                ) * 100
            cbdr_mult = (
                get_cbdr_multiplier(symbol, cbdr_w) if cbdr_w is not None else 1.0
            )
            if cbdr_mult == 0.0:
                quality_mult = 0.0
                if classic_fvg.get("v4_rejected") is None:
                    classic_fvg["v4_rejected"] = "CBDR_MULT_ZERO"

            # ── Haftasonu çarpani (config'den) ──
            _wprofile = cfg.CBDR_RISK_MATRIX.get(symbol, {})
            if quality_mult > 0 and _wprofile.get("weekend_bonus", False):
                if edt.weekday() >= 5:
                    cbdr_mult *= _wprofile.get("weekend_mult", 1.5)

            allowed, reason = should_trade(symbol, cbdr_width_pct=cbdr_w)
            if not allowed:
                quality_mult = 0.0
                if classic_fvg.get("v4_rejected") is None:
                    classic_fvg["v4_rejected"] = f"SHOULD_TRADE_{reason}"

            # ── Risk carpani: EL (1.5x) + CBDR Matrix ──
            h = edt.hour
            el_mult = cfg.EARLY_LONDON_RISK_MULT if 2 <= h < 8 else 1.0
            final_mult = el_mult * cbdr_mult * quality_mult

            qty = (ic * rpt * final_mult) / rd if rd > 0 else 0

            # --- FIX: Only enter if quality/validity checks passed (qty > 0)
            # Do NOT reset RSM if we just failed a quality filter,
            # allow RSM to continue hunting for the next FVG in this sweep.
            if qty > 0:
                # ── ENTERED ──
                classic_fvg["v4_rejected"] = "ENTERED"
                classic_fvg["v4_entry_price"] = ep
                classic_fvg["v4_sl"] = sl
                classic_fvg["v4_tp"] = tp
                classic_fvg["v4_qty"] = qty
                classic_fvg["v4_side"] = side
                trade_uid = f"{symbol}_{sb}_{side}"
                classic_fvg["trade_uid"] = trade_uid
                classic_fvg["v4_cbdr_mult"] = cbdr_mult
                classic_fvg["v4_final_mult"] = final_mult
                rejection_counts[classic_fvg["v4_rejected"]] += 1
                fvg_by_uid[trade_uid] = classic_fvg

                entry_day = ss.cbdr_day
                active.append(
                    {
                        "entry_bar": sb + 1,
                        "entry_price": ep,
                        "sl": sl,
                        "tp": tp,
                        "qty": qty,
                        "entry_qty": qty,
                        "side": side,
                        "trigger_fvg": tf,
                        "initial_sl": sl,
                        "initial_tp": tp,
                        "trailing_count": 0,
                        "be_triggered": False,
                        "day_key": entry_day,
                        "trade_uid": trade_uid,
                        "cbdr_body_high": ss.cbdr_body_high,
                        "cbdr_body_low": ss.cbdr_body_low,
                        "partial_taken": False,
                        "locked_pnl": 0.0,
                    }
                )
                # Canlı bot.py:1167 parity: entry sonrası BIAS_LOCKED — yön
                # korunur, yeni sweep beklemeden BIAS yönlü taze FVG aranır
                # (on_bias_fvg). Bias tersine dönerse / nötrleşirse sweep_sync
                # BIAS_LOCKED dalı resetler.
                rsm.lock_bias(bar_index=cur.index)
                continue  # ayni-bar trailing/exit calistirma
            else:
                # Filtered setup: record as rejected, reset RSM to avoid duplicate FVGs from same sweep.
                if classic_fvg["v4_rejected"] is None:
                    classic_fvg["v4_rejected"] = "QTY_ZERO"
                rejection_counts[classic_fvg["v4_rejected"]] += 1
                rsm.reset()
                continue

        # ── Trailing (unchanged) ──
        if active and cur.is_closed:
            for t in active:
                if t.get("closed"):
                    continue

            tc = chunk[:-1]
            min_mult = cfg.FVG_SIZE_MAP.get(symbol, FVG_MIN_SIZE_ATR_MULT)
            min_fvg_size = max(atr * min_mult, 1e-8)
            cfvgs = detect_fvgs(
                tc,
                lookback=min(50, len(tc)),
                timeframe="15m",
                min_fvg_size=min_fvg_size,
            )
            for t in active:
                if t.get("closed"):
                    continue
                s2 = t["side"]
                csl = t["sl"]
                ctp = t["tp"]
                rpt2 = abs(t["initial_sl"] - t["entry_price"])
                ltc = 0
                upd = False
                # ── R-kar kapisi (LUNA Plan C madde 4): PROFIT_GATE_R > 0 ise
                # trailing yalnizca unrealized kar >= PROFIT_GATE_R * risk_pts
                # oldugunda calisir. Kapinin altinda SL/TP oldugu gibi kalir.
                # TRAIL_BE_ON_GATE: esik asilinca SL entry'ye (BE) tasinir.
                if PROFIT_GATE_R > 0 and rpt2 > 0:
                    _cpx = cur.close
                    _upnl_r = (
                        (_cpx - t["entry_price"]) / rpt2
                        if s2 == "long"
                        else (t["entry_price"] - _cpx) / rpt2
                    )
                    if _upnl_r < PROFIT_GATE_R:
                        continue  # kapi kapali → bu bar trail yok
                    if TRAIL_BE_ON_GATE and not t.get("be_triggered"):
                        _be_sl = t["entry_price"]
                        if (s2 == "long" and _be_sl > csl) or (
                            s2 == "short" and _be_sl < csl
                        ):
                            csl = _be_sl
                            t["be_triggered"] = True
                            t["trailing_count"] = t.get("trailing_count", 0) + 1
                            ltc += 1
                            upd = True
                # ── LUNA Profit Protection / Breakeven Buffer (gercek mekanizma) ──
                # 1) GATE: trade en az +PROFIT_PROTECT_GATE_R*R unrealized kar
                #    gorunce (intrabar high/low, 'gordugu' an) koruma KALICI
                #    aktiflesir (latch). 2) ILK KORUMA: SL = entry + fees + 0.1R
                #    (round-trip komisyon dahil, tam formül). 3) RATCHET: her bar
                #    son onayli swing low/high ∓ SWING_ATR_MULT*ATR ile (long max,
                #    short min). FVG retrace DEVAM eder; carpisma yok — daha
                #    korumaci seviye kazanir (long max, short min zaten ortak kural).
                if PROFIT_PROTECT_GATE_R > 0 and rpt2 > 0:
                    if not t.get("protect_latched"):
                        _best = cur.high if s2 == "long" else cur.low
                        _upnl_r = (
                            (_best - t["entry_price"]) / rpt2
                            if s2 == "long"
                            else (t["entry_price"] - _best) / rpt2
                        )
                        if _upnl_r >= PROFIT_PROTECT_GATE_R:
                            t["protect_latched"] = True
                            _be_sl = (
                                (
                                    t["entry_price"] * (1 + COMMISSION_RATE)
                                    + PROFIT_PROTECT_BE_R * rpt2
                                )
                                / (1 - COMMISSION_RATE)
                                if s2 == "long"
                                else (
                                    t["entry_price"] * (1 - COMMISSION_RATE)
                                    - PROFIT_PROTECT_BE_R * rpt2
                                )
                                / (1 + COMMISSION_RATE)
                            )
                            if (s2 == "long" and _be_sl > csl) or (
                                s2 == "short" and _be_sl < csl
                            ):
                                csl = _be_sl
                                ltc += 1
                                upd = True
                    if t.get("protect_latched"):
                        _swb = PROFIT_PROTECT_SWING_ATR_MULT * atr
                        if s2 == "long" and last_swl_bar is not None:
                            _slb = last_swl_bar[sb]
                            if _slb >= t.get("entry_bar", 0):
                                _ns = last_swl_price[sb] - _swb
                                if _ns > csl:
                                    csl = _ns
                                    ltc += 1
                                    upd = True
                        elif s2 == "short" and last_swh_bar is not None:
                            _shb = last_swh_bar[sb]
                            if _shb >= t.get("entry_bar", 0):
                                _ns = last_swh_price[sb] + _swb
                                if _ns < csl:
                                    csl = _ns
                                    ltc += 1
                                    upd = True
                # DISABLE_FVG_TRAIL=True: FVG-based retrace trailing komple
                # kapatilir (yalnizca kismi TP/scale-out kademeleri SL'yi
                # hareket ettirir, SL giris 1R'de sabit baslar).
                for fvg in [] if DISABLE_FVG_TRAIL else cfvgs:
                    if s2 == "long" and fvg.direction != "bullish":
                        continue
                    if s2 == "short" and fvg.direction != "bearish":
                        continue
                    if TRAIL_MODE in ("retrace", "activation"):
                        # Orijinal davranis (1469454 oncesi): far-side kapanis
                        # FVG'yi elemez, sonraki gap ici kapanis onay verebilir.
                        # activation modunda FVG yolu retrace ile BIREBIR.
                        # KAPANIS (2026-08-08): canli TRAIL_MODE=retrace oldugu
                        # icin retrace dali tek aktif yol; activation geri cekildi.
                        if not fvg_close_confirmed(fvg, tc):
                            continue
                        mode = "retrace"
                    else:
                        # DENEYSEL: continuation/atr_chase (geri cekildi)
                        mode = fvg_confirm_mode(fvg, tc, CONT_CONFIRM_BARS)
                        if mode is None:
                            continue
                    # Continuation/atr-chase SL tamponu: continuation icin
                    # CONT_TRAIL_MULT*ATR (canli ATR_TRAIL_MULT_CONTINUATION),
                    # retrace icin ATR_TRAIL_MULT*ATR. Kapsam: far-side hop'u
                    # fiyatin yeni gectigi sinirin hemen yanina SL koyar; genis K,
                    # trend-ici noise'a karsi retrace'in dogal mesafesine yakinlasir.
                    ab2 = atr * (CONT_TRAIL_MULT if mode == "continuation" else ATM)
                    # is_placeable yalnizca continuation/atr_chase'te uygulanir
                    # (retrace modu eski davranisi aynen korur). cur = son kapanis.
                    placeable = TRAIL_MODE not in ("retrace", "activation")
                    cur_price = cur.close
                    if s2 == "long":
                        ns = (
                            (fvg.top - ab2)
                            if mode == "continuation"
                            else (fvg.bottom - ab2)
                        )
                        if (
                            ns > csl
                            and (ns - csl) > rpt2 * TMM
                            and (not placeable or ns < cur_price)
                        ):
                            sd2 = ns - csl
                            csl = ns
                            if not TP_FIXED:
                                ctp += sd2
                            ltc += 1
                            upd = True
                    else:
                        ns = (
                            (fvg.bottom + ab2)
                            if mode == "continuation"
                            else (fvg.top + ab2)
                        )
                        if (
                            ns < csl
                            and (csl - ns) > rpt2 * TMM
                            and (not placeable or ns > cur_price)
                        ):
                            sd2 = csl - ns
                            csl = ns
                            if not TP_FIXED:
                                ctp -= sd2
                            ltc += 1
                            upd = True
                # ── KAR MERDIVENI (Fallback Ladder, 2026-08-16) ──
                # FVG yolu bittikten SONRA devreye girer. csl bu noktada FVG'nin
                # ulastigi seviyededir (varsa); merdiven sadece daha koruyucu bir
                # seviye veriyorsa kazanir (long: max, short: min). Ratchet +
                # min-move filtresi diger trailing yollariyla ayni kuraldir.
                if ENABLE_FALLBACK_LADDER:
                    _ladder_sl = compute_fallback_ladder_sl(
                        s2, cur.close, rpt2, t["entry_price"]
                    )
                    if _ladder_sl is not None:
                        if s2 == "long" and _ladder_sl > csl:
                            if (_ladder_sl - csl) > rpt2 * TMM:
                                sd2 = _ladder_sl - csl
                                csl = _ladder_sl
                                if not TP_FIXED:
                                    ctp += sd2
                                ltc += 1
                                upd = True
                        elif s2 == "short" and _ladder_sl < csl:
                            if (csl - _ladder_sl) > rpt2 * TMM:
                                sd2 = csl - _ladder_sl
                                csl = _ladder_sl
                                if not TP_FIXED:
                                    ctp -= sd2
                                ltc += 1
                                upd = True
                if TRAIL_MODE in ("atr_chase", "activation") and not upd:
                    # DENEYSEL (geri cekildi 2026-08-08): ATR-chase fallback —
                    # FVG aday kullanilamadiginda SL = close ∓ K*ATR ile chase.
                    # activation modunda YALNIZCA unrealized kar >=
                    # TRAIL_ACTIVATION_R_MULT * risk_pts iken devreye girer.
                    # TRAIL_MODE=retrace iken bu blok HIC calismaz.
                    cur_price = cur.close
                    if TRAIL_MODE == "activation":
                        entry = t["entry_price"]
                        risk_pts = abs(entry - t["initial_sl"])
                        upnl_pts = (
                            cur_price - entry if s2 == "long" else entry - cur_price
                        )
                        if upnl_pts < TRAIL_ACTIVATION_R_MULT * risk_pts:
                            cur_price = None  # esik altinda fallback'i devre disi birak
                    if cur_price is not None:
                        ab2 = atr * CONT_BUFFER_MULT
                        if s2 == "long":
                            ns = cur_price - ab2
                            if ns > csl and (ns - csl) > rpt2 * TMM and ns < cur_price:
                                sd2 = ns - csl
                                csl = ns
                                if not TP_FIXED:
                                    ctp += sd2
                                ltc += 1
                                upd = True
                        else:
                            ns = cur_price + ab2
                            if ns < csl and (csl - ns) > rpt2 * TMM and ns > cur_price:
                                sd2 = csl - ns
                                csl = ns
                                if not TP_FIXED:
                                    ctp -= sd2
                                ltc += 1
                                upd = True
                if upd:
                    t["sl"] = csl
                    t["tp"] = ctp
                    t["trailing_count"] = t.get("trailing_count", 0) + ltc

        sa = []
        for t in active:
            if t.get("closed"):
                continue
            ex = False
            if t["side"] == "long":
                if cur.low <= t["sl"]:
                    t["exit_price"] = t["sl"]
                    t["exit_bar"] = sb
                    if t.get("trailing_count", 0) > 0 and t["sl"] > t["entry_price"]:
                        t["result"] = "PROFIT_TRAIL"
                    else:
                        t["result"] = "LOSS"
                    t["closed"] = True
                    ex = True
                else:
                    # ── KISMI TP: pozisyonun PARTIAL_TP_FRAC'i seviyede kapanir ──
                    # Seviye: PARTIAL_TP_PCT > 0 ise fiyat yuzdesi bazli
                    # (entry*(1+PCT/100)), degilse R bazli (entry + R*risk_pts).
                    _pt_level_long = None
                    if PARTIAL_TP_PCT > 0:
                        _pt_level_long = t["entry_price"] * (1 + PARTIAL_TP_PCT / 100.0)
                    elif PARTIAL_TP_R > 0:
                        _pt_level_long = t["entry_price"] + PARTIAL_TP_R * abs(
                            t["initial_sl"] - t["entry_price"]
                        )
                    # SCALE-OUT 2. kademe: ilk tetikleyiciden SCALE_STEP_PCT daha
                    # ileri fiyatta (long) kalan pozisyonun TAMAMI satilir.
                    # SCALE2_ABS_PCT > 0 ise MUTLAK seviye: giristen itibaren
                    # %SCALE2_ABS_PCT ilerleme (long: entry*(1+ABS/100)).
                    _pt_scale2_long = None
                    if (
                        (PARTIAL_TP_SCALE_STEP_PCT > 0 or PARTIAL_TP_SCALE2_ABS_PCT > 0)
                        and _pt_level_long is not None
                        and t.get("partial_taken")
                    ):
                        if PARTIAL_TP_SCALE2_ABS_PCT > 0:
                            _pt_scale2_long = t["entry_price"] * (
                                1 + PARTIAL_TP_SCALE2_ABS_PCT / 100.0
                            )
                        else:
                            _pt_scale2_long = _pt_level_long * (
                                1 + PARTIAL_TP_SCALE_STEP_PCT / 100.0
                            )
                        if cur.high >= _pt_scale2_long:
                            _pp = _pt_scale2_long
                            _pq = t["qty"]
                            _entry_fee = t["entry_price"] * _pq * COMMISSION_RATE
                            _exit_fee = _pp * _pq * COMMISSION_RATE
                            t["locked_pnl"] += (_pp - t["entry_price"]) * _pq
                            t["locked_fee"] = (
                                t.get("locked_fee", 0.0) + _entry_fee + _exit_fee
                            )
                            t["qty"] -= _pq
                            t["exit_price"] = _pp
                            t["exit_bar"] = sb
                            t["result"] = "TP"
                            t["scale2_exit"] = True
                            t["closed"] = True
                            ex = True
                    if (
                        _pt_level_long is not None
                        and not t.get("partial_taken")
                        and cur.high >= _pt_level_long
                    ):
                        _pp = _pt_level_long
                        _pq = t["qty"] * PARTIAL_TP_FRAC
                        _entry_fee = t["entry_price"] * _pq * COMMISSION_RATE
                        _exit_fee = _pp * _pq * COMMISSION_RATE
                        t["locked_pnl"] += (_pp - t["entry_price"]) * _pq
                        t["locked_fee"] = (
                            t.get("locked_fee", 0.0) + _entry_fee + _exit_fee
                        )
                        t["qty"] -= _pq
                        t["partial_taken"] = True
                        rejection_counts["PARTIAL_TP"] += 1
                        # SCALE-OUT: kalanin SL'sini entry*(1±SL_PROTECT_PCT/100)'e
                        # tasi (long), TP'yi de ayni delta kadar otele.
                        if PARTIAL_TP_SL_PROTECT_PCT > 0 and t["qty"] > 0:
                            _cur_sl = t["sl"]
                            _new_sl = t["entry_price"] * (
                                1 + PARTIAL_TP_SL_PROTECT_PCT / 100.0
                            )
                            if _new_sl > _cur_sl:
                                _sd = _new_sl - _cur_sl
                                t["sl"] = _new_sl
                                if not TP_FIXED:
                                    t["tp"] += _sd
                    if cur.high >= t["tp"]:
                        t["exit_price"] = t["tp"]
                        t["exit_bar"] = sb
                        t["result"] = "TP"
                        t["closed"] = True
                        ex = True
            else:
                if cur.high >= t["sl"]:
                    t["exit_price"] = t["sl"]
                    t["exit_bar"] = sb
                    if t.get("trailing_count", 0) > 0 and t["sl"] < t["entry_price"]:
                        t["result"] = "PROFIT_TRAIL"
                    else:
                        t["result"] = "LOSS"
                    t["closed"] = True
                    ex = True
                else:
                    # ── KISMI TP: pozisyonun PARTIAL_TP_FRAC'i seviyede kapanir ──
                    _pt_level_short = None
                    if PARTIAL_TP_PCT > 0:
                        _pt_level_short = t["entry_price"] * (
                            1 - PARTIAL_TP_PCT / 100.0
                        )
                    elif PARTIAL_TP_R > 0:
                        _pt_level_short = t["entry_price"] - PARTIAL_TP_R * abs(
                            t["initial_sl"] - t["entry_price"]
                        )
                    # SCALE-OUT 2. kademe: ilk tetikleyiciden SCALE_STEP_PCT daha
                    # ileri fiyatta (short) kalan pozisyonun TAMAMI satilir.
                    # SCALE2_ABS_PCT > 0 ise MUTLAK seviye: giristen itibaren
                    # %SCALE2_ABS_PCT ilerleme (short: entry*(1-ABS/100)).
                    _pt_scale2_short = None
                    if (
                        (PARTIAL_TP_SCALE_STEP_PCT > 0 or PARTIAL_TP_SCALE2_ABS_PCT > 0)
                        and _pt_level_short is not None
                        and t.get("partial_taken")
                    ):
                        if PARTIAL_TP_SCALE2_ABS_PCT > 0:
                            _pt_scale2_short = t["entry_price"] * (
                                1 - PARTIAL_TP_SCALE2_ABS_PCT / 100.0
                            )
                        else:
                            _pt_scale2_short = _pt_level_short * (
                                1 - PARTIAL_TP_SCALE_STEP_PCT / 100.0
                            )
                        if cur.low <= _pt_scale2_short:
                            _pp = _pt_scale2_short
                            _pq = t["qty"]
                            _entry_fee = t["entry_price"] * _pq * COMMISSION_RATE
                            _exit_fee = _pp * _pq * COMMISSION_RATE
                            t["locked_pnl"] += (t["entry_price"] - _pp) * _pq
                            t["locked_fee"] = (
                                t.get("locked_fee", 0.0) + _entry_fee + _exit_fee
                            )
                            t["qty"] -= _pq
                            t["exit_price"] = _pp
                            t["exit_bar"] = sb
                            t["result"] = "TP"
                            t["scale2_exit"] = True
                            t["closed"] = True
                            ex = True
                    if (
                        _pt_level_short is not None
                        and not t.get("partial_taken")
                        and cur.low <= _pt_level_short
                    ):
                        _pp = _pt_level_short
                        _pq = t["qty"] * PARTIAL_TP_FRAC
                        _entry_fee = t["entry_price"] * _pq * COMMISSION_RATE
                        _exit_fee = _pp * _pq * COMMISSION_RATE
                        t["locked_pnl"] += (t["entry_price"] - _pp) * _pq
                        t["locked_fee"] = (
                            t.get("locked_fee", 0.0) + _entry_fee + _exit_fee
                        )
                        t["qty"] -= _pq
                        t["partial_taken"] = True
                        rejection_counts["PARTIAL_TP"] += 1
                        # SCALE-OUT: kalanin SL'sini entry*(1±SL_PROTECT_PCT/100)'e
                        # tasi (short), TP'yi de ayni delta kadar otele.
                        if PARTIAL_TP_SL_PROTECT_PCT > 0 and t["qty"] > 0:
                            _cur_sl = t["sl"]
                            _new_sl = t["entry_price"] * (
                                1 - PARTIAL_TP_SL_PROTECT_PCT / 100.0
                            )
                            if _new_sl < _cur_sl:
                                _sd = _cur_sl - _new_sl
                                t["sl"] = _new_sl
                                if not TP_FIXED:
                                    t["tp"] -= _sd
                    if cur.low <= t["tp"]:
                        t["exit_price"] = t["tp"]
                        t["exit_bar"] = sb
                        t["result"] = "TP"
                        t["closed"] = True
                        ex = True
            # ── ZAMAN CIKISI (TIME_EXIT): kismi TP sonrasi kalan pozisyon,
            # entry barindan PARTIAL_TP_TIME_EXIT_BARS bar dolunca otomatik
            # kapanir (SL/TP onceliklidir — ex=True ise buraya dusmez). Amac:
            # FVG trailing FVG bulamadigi senaryoda kalanin surunmesini onlemek.
            # Kapanis fiyati bar kapanisi (cur.close). Result karda PROFIT_TRAIL,
            # zararda LOSS; ayrica t["time_exit"]=True isaretlenir (rapor icin).
            if (
                not ex
                and PARTIAL_TP_TIME_EXIT_BARS > 0
                and t.get("partial_taken")
                and t["qty"] > 0
                and sb - t.get("entry_bar", 0) >= PARTIAL_TP_TIME_EXIT_BARS
            ):
                _pp = cur.close
                _pq = t["qty"]
                _dir = 1 if t["side"] == "long" else -1
                _entry_fee = t["entry_price"] * _pq * COMMISSION_RATE
                _exit_fee = _pp * _pq * COMMISSION_RATE
                t["locked_pnl"] += _dir * (_pp - t["entry_price"]) * _pq
                t["locked_fee"] = t.get("locked_fee", 0.0) + _entry_fee + _exit_fee
                t["qty"] -= _pq
                t["exit_price"] = _pp
                t["exit_bar"] = sb
                t["time_exit"] = True
                _te_pnl = _dir * (_pp - t["entry_price"]) * _pq - _entry_fee - _exit_fee
                t["result"] = "PROFIT_TRAIL" if _te_pnl > 0 else "LOSS"
                t["closed"] = True
                ex = True
            if ex:
                diff = (
                    (t["exit_price"] - t["entry_price"])
                    if t["side"] == "long"
                    else (t["entry_price"] - t["exit_price"])
                )
                entry_fee = t["entry_price"] * t["qty"] * COMMISSION_RATE
                exit_fee = t["exit_price"] * t["qty"] * COMMISSION_RATE
                total_fee = entry_fee + exit_fee
                t["entry_fee"] = round(entry_fee, 2)
                t["exit_fee"] = round(exit_fee, 2)
                t["fee"] = round(total_fee + t.get("locked_fee", 0.0), 2)
                t["pnl"] = round(
                    diff * t["qty"]
                    - total_fee
                    + t.get("locked_pnl", 0.0)
                    - t.get("locked_fee", 0.0),
                    2,
                )
                day_trades[t.get("day_key", "")].append(t["pnl"])
                risk_usd_rec = (
                    abs(t["initial_sl"] - t["entry_price"])
                    * t.get("entry_qty", t["qty"])
                    if t["initial_sl"]
                    else 0
                )
                trade_records.append(
                    {
                        "result": t["result"],
                        "pnl": t["pnl"],
                        "fee": t["fee"],
                        "day_key": t.get("day_key", ""),
                        "risk_usd": risk_usd_rec,
                        "entry_bar": t.get("entry_bar"),
                        "exit_bar": t.get("exit_bar"),
                        "partial_taken": t.get("partial_taken", False),
                        "time_exit": t.get("time_exit", False),
                        "scale2_exit": t.get("scale2_exit", False),
                        "fvg_direction": t.get("trigger_fvg", {}).direction
                        if t.get("trigger_fvg")
                        else "",
                        "fvg_top": t.get("trigger_fvg", {}).top
                        if t.get("trigger_fvg")
                        else 0,
                        "fvg_bottom": t.get("trigger_fvg", {}).bottom
                        if t.get("trigger_fvg")
                        else 0,
                        "cbdr_body_high": t.get("cbdr_body_high", 0),
                        "cbdr_body_low": t.get("cbdr_body_low", 0),
                    }
                )
                if t["pnl"] > 0:
                    wins.append(t)
                else:
                    losses.append(t)
                # ── Gerçek sonucu FVG objesine geri yaz ──
                uid = t.get("trade_uid")
                if uid and uid in fvg_by_uid:
                    f_ = fvg_by_uid[uid]
                    f_["v4_real_result"] = t["result"]
                    f_["v4_real_pnl_usd"] = t["pnl"]
                    risk_usd = (
                        abs(t["initial_sl"] - t["entry_price"])
                        * t.get("entry_qty", t["qty"])
                        if t["initial_sl"]
                        else 0
                    )
                    f_["v4_real_pnl_R"] = (t["pnl"] / risk_usd) if risk_usd > 0 else 0.0
                    f_["v4_real_hit_target"] = t["result"] == "TP"
                    f_["v4_real_hit_stop"] = t["result"] in ("LOSS", "PROFIT_TRAIL")
                if _LOGGER is not None:
                    risk_usd = (
                        abs(t["initial_sl"] - t["entry_price"])
                        * t.get("entry_qty", t["qty"])
                        if t["initial_sl"]
                        else 0
                    )
                    fvg_sz = (
                        (t["trigger_fvg"].top - t["trigger_fvg"].bottom)
                        if t.get("trigger_fvg")
                        else None
                    )
                    _LOGGER.log_trade(
                        {
                            "symbol": symbol,
                            "session": _sname,
                            "side": t["side"].upper(),
                            "entry_time": edt,
                            "entry_price": round(t["entry_price"], 6),
                            "exit_price": round(t["exit_price"], 6),
                            "result": t["result"],
                            "final_pnl_usd": round(t["pnl"], 2),
                            "risk_usd": round(risk_usd, 2),
                            "r_multiple": round(t["pnl"] / risk_usd, 4)
                            if risk_usd > 0
                            else 0.0,
                            "trailing_count": t.get("trailing_count", 0),
                            "fvg_size_pips": round(fvg_sz, 6) if fvg_sz else None,
                            "atr": round(atr, 6),
                            "hold_bars": t.get("exit_bar", 0) - t.get("entry_bar", 0),
                        }
                    )
            else:
                sa.append(t)
        active = sa

    # ── Open trades ──
    if b15:
        lp = b15[-1].close
        for t in active:
            if not t.get("closed"):
                t["exit_price"] = lp
                t["exit_bar"] = len(b15) - 1
                t["result"] = "OPEN"
                t["closed"] = True
                diff = (
                    (lp - t["entry_price"])
                    if t["side"] == "long"
                    else (t["entry_price"] - lp)
                )
                entry_fee = t["entry_price"] * t["qty"] * COMMISSION_RATE
                exit_fee = lp * t["qty"] * COMMISSION_RATE
                total_fee = entry_fee + exit_fee
                t["entry_fee"] = round(entry_fee, 2)
                t["exit_fee"] = round(exit_fee, 2)
                t["fee"] = round(total_fee + t.get("locked_fee", 0.0), 2)
                t["pnl"] = round(
                    diff * t["qty"]
                    - total_fee
                    + t.get("locked_pnl", 0.0)
                    - t.get("locked_fee", 0.0),
                    2,
                )
                day_trades[t.get("day_key", "")].append(t["pnl"])
                risk_usd_rec = (
                    abs(t["initial_sl"] - t["entry_price"])
                    * t.get("entry_qty", t["qty"])
                    if t["initial_sl"]
                    else 0
                )
                trade_records.append(
                    {
                        "result": t["result"],
                        "pnl": t["pnl"],
                        "fee": t["fee"],
                        "day_key": t.get("day_key", ""),
                        "risk_usd": risk_usd_rec,
                        "entry_bar": t.get("entry_bar"),
                        "exit_bar": t.get("exit_bar"),
                        "partial_taken": t.get("partial_taken", False),
                        "time_exit": t.get("time_exit", False),
                        "scale2_exit": t.get("scale2_exit", False),
                        "fvg_direction": t.get("trigger_fvg", {}).direction
                        if t.get("trigger_fvg")
                        else "",
                        "fvg_top": t.get("trigger_fvg", {}).top
                        if t.get("trigger_fvg")
                        else 0,
                        "fvg_bottom": t.get("trigger_fvg", {}).bottom
                        if t.get("trigger_fvg")
                        else 0,
                        "cbdr_body_high": t.get("cbdr_body_high", 0),
                        "cbdr_body_low": t.get("cbdr_body_low", 0),
                    }
                )
                if t["pnl"] > 0:
                    wins.append(t)
                else:
                    losses.append(t)
                # ── Gerçek sonucu FVG objesine geri yaz ──
                uid = t.get("trade_uid")
                if uid and uid in fvg_by_uid:
                    f_ = fvg_by_uid[uid]
                    f_["v4_real_result"] = t["result"]
                    f_["v4_real_pnl_usd"] = t["pnl"]
                    risk_usd = (
                        abs(t["initial_sl"] - t["entry_price"])
                        * t.get("entry_qty", t["qty"])
                        if t["initial_sl"]
                        else 0
                    )
                    f_["v4_real_pnl_R"] = (t["pnl"] / risk_usd) if risk_usd > 0 else 0.0
                    f_["v4_real_hit_target"] = t["result"] == "TP"
                    f_["v4_real_hit_stop"] = t["result"] in ("LOSS", "PROFIT_TRAIL")
                if _LOGGER is not None:
                    risk_usd = (
                        abs(t["initial_sl"] - t["entry_price"])
                        * t.get("entry_qty", t["qty"])
                        if t["initial_sl"]
                        else 0
                    )
                    fvg_sz = (
                        (t["trigger_fvg"].top - t["trigger_fvg"].bottom)
                        if t.get("trigger_fvg")
                        else None
                    )
                    _LOGGER.log_trade(
                        {
                            "symbol": symbol,
                            "session": _sname,
                            "side": t["side"].upper(),
                            "entry_time": edt,
                            "entry_price": round(t["entry_price"], 6),
                            "exit_price": round(t["exit_price"], 6),
                            "result": "OPEN",
                            "final_pnl_usd": round(t["pnl"], 2),
                            "risk_usd": round(risk_usd, 2),
                            "r_multiple": round(t["pnl"] / risk_usd, 4)
                            if risk_usd > 0
                            else 0.0,
                            "trailing_count": t.get("trailing_count", 0),
                            "fvg_size_pips": round(fvg_sz, 6) if fvg_sz else None,
                            "atr": round(atr, 6),
                            "hold_bars": t.get("exit_bar", 0) - t.get("entry_bar", 0),
                        }
                    )

    print(f"\r    [{_sname}] %100 ({total_bars}/{total_bars})", flush=True)

    # ── Daily rows ──
    daily_rows = []
    all_keys = sorted(set(list(day_cbdr.keys()) + list(day_trades.keys())))
    print(f"    [{symbol}] Daily rows basliyor... ({len(all_keys)} key)", flush=True)
    for dk in all_keys:
        if not dk:
            continue
        w = day_cbdr.get(dk)
        tlist = day_trades.get(dk, [])
        if w is None and not tlist:
            continue
        total_pnl = sum(tlist)
        n_trades = len(tlist)
        n_wins = sum(1 for p in tlist if p > 0)
        n_be = sum(1 for p in tlist if p == 0)
        daily_rows.append(
            {
                "day_key": dk,
                "cbdr_pct": w,
                "trades": n_trades,
                "wins": n_wins,
                "be": n_be,
                "losses": n_trades - n_wins - n_be,
                "pnl": total_pnl,
            }
        )
    print(f"    [{symbol}] Daily rows tamam ({len(daily_rows)} row)", flush=True)

    day_cbdr_cnt = len(day_cbdr)
    day_trades_cnt = len(day_trades)
    trade_cnt = len(trade_records)
    print(
        f"    [{symbol}] Tamam: {day_cbdr_cnt} gun CBDR, {day_trades_cnt} gun trade, "
        f"{trade_cnt} islem, {len(daily_rows)} daily_row",
        flush=True,
    )
    rej_str = str(dict(sorted(rejection_counts.items(), key=lambda x: x[0])))
    print(f"    [{symbol}] Red: {rej_str}", flush=True)

    return daily_rows, wins, losses, trade_records, rejection_counts


# ─── Istatistik Hesaplama ────────────────────────────────────
def compute_session_stats(trade_records, initial_balance, daily_rows=None):
    n = len(trade_records)
    if n == 0:
        return {
            "total_trades": 0,
            "tp_pct": 0,
            "profit_trail_pct": 0,
            "loss_pct": 0,
            "positive_exit_pct": 0,
            "profit_factor": 0,
            "sharpe": 0,
            "max_dd_pct": 0,
            "total_pnl": 0,
            "total_fee": 0,
            "pnl_per_fee": 0,
            "expectancy": 0,
            "avg_hold": 0,
            "score": 0,
        }
    tp = sum(1 for r in trade_records if r["result"] == "TP")
    profit_trail = sum(1 for r in trade_records if r["result"] == "PROFIT_TRAIL")
    loss = sum(1 for r in trade_records if r["result"] in ("LOSS", "OPEN"))
    tp_pct = tp / n * 100
    profit_trail_pct = profit_trail / n * 100
    loss_pct = loss / n * 100
    positive_exit_pct = tp_pct + profit_trail_pct
    gross_profit = sum(r["pnl"] for r in trade_records if r["pnl"] > 0) or 0
    gross_loss = abs(sum(r["pnl"] for r in trade_records if r["pnl"] < 0))
    profit_factor = 999.0 if gross_loss == 0 else gross_profit / gross_loss
    cumulative = 0
    peak = 0
    max_dd = 0
    for r in trade_records:
        cumulative += r["pnl"]
        if cumulative > peak:
            peak = cumulative
        dd = peak - cumulative
        if dd > max_dd:
            max_dd = dd
    peak_balance = initial_balance + peak
    max_dd_pct = (max_dd / peak_balance) * 100 if peak_balance > 0 else 0
    # Trade-return based Sharpe (non-annualized, RFR=0)
    trade_returns = []
    for r in trade_records:
        ru = r.get("risk_usd", 0)
        if ru > 0:
            trade_returns.append(r["pnl"] / ru)
    if len(trade_returns) > 1:
        tr_mean = sum(trade_returns) / len(trade_returns)
        tr_std = (
            sum((x - tr_mean) ** 2 for x in trade_returns) / len(trade_returns)
        ) ** 0.5
        sharpe = tr_mean / tr_std if tr_std > 0 else 0

    else:
        sharpe = 0
    total_pnl = sum(r["pnl"] for r in trade_records)
    total_fee = sum(r.get("fee", 0) for r in trade_records)
    pnl_per_fee = total_pnl / total_fee if total_fee > 0 else 0
    # LUNA Plan C madde 4: expectancy + ortalama bar tutma suresi (direktif
    # rapor zorunlulugu). avg_hold trade_records'a islenmis entry_bar/exit_bar
    # kullanir (exit dahil, yari-open trade'ler count'lanmaz).
    expectancy = total_pnl / n if n else 0
    hold_bars = [
        (r.get("exit_bar", 0) - r.get("entry_bar", 0))
        for r in trade_records
        if r.get("entry_bar") is not None and r.get("exit_bar") is not None
    ]
    avg_hold = sum(hold_bars) / len(hold_bars) if hold_bars else 0.0
    score = (
        (profit_factor * positive_exit_pct / 100 * pnl_per_fee)
        / (1 + max_dd_pct / 100)
        * 100
        if max_dd_pct >= 0
        else 0
    )
    return {
        "total_trades": n,
        "tp_pct": tp_pct,
        "profit_trail_pct": profit_trail_pct,
        "loss_pct": loss_pct,
        "positive_exit_pct": positive_exit_pct,
        "profit_factor": profit_factor,
        "max_dd_pct": max_dd_pct,
        "sharpe": sharpe,
        "total_pnl": total_pnl,
        "total_fee": total_fee,
        "pnl_per_fee": pnl_per_fee,
        "expectancy": expectancy,
        "avg_hold": avg_hold,
        "score": round(score),
    }


# ─── Main ─────────────────────────────────────────────────────
# ─── Worker: tek sembol analizi (paralel surec) ──────────────
def _analyze_one_sym_v5(
    sym: str,
    mode: str | None = None,
    cont_k: float | None = None,
    act_r: float | None = None,
    entry_variant: str | None = None,
    profit_gate: float | None = None,
    trail_be: bool = False,
    profit_protect_gate: float | None = None,
    profit_protect_swing_atr: float | None = None,
    htf_bias_align: bool = False,
    partial_tp_r: float | None = None,
    partial_tp_frac: float | None = None,
    partial_tp_pct: float | None = None,
    partial_tp_sl_protect_pct: float | None = None,
    partial_tp_scale_step_pct: float | None = None,
    partial_tp_scale2_abs_pct: float | None = None,
    partial_tp_time_exit_bars: int | None = None,
    disable_fvg_trail: bool = False,
    enable_fallback_ladder: bool = False,
    ladder_step_1_r: float | None = None,
    ladder_step_1_sl_r: float | None = None,
    ladder_step_2_r: float | None = None,
    ladder_step_2_sl_r: float | None = None,
    ladder_step_3_r: float | None = None,
    ladder_step_3_sl_r: float | None = None,
    ladder_step_4_r: float | None = None,
    ladder_step_4_sl_r: float | None = None,
) -> dict | None:
    """Worker: collect_fvg_profile + compute_session_stats.
    Ayri ProcessPoolExecutor worker'inda calisir. mode verilirse
    trailing modu + (K, R) parametreleri worker icinde set edilir
    (spawn altinda main() global seti worker'a tasinmaz)."""
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    _SNIPER_SRC = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "sniper", "src"
    )
    if _SNIPER_SRC not in sys.path:
        sys.path.insert(0, _SNIPER_SRC)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    import config as cfg

    # Import engine from same module
    from analyzer_v5 import collect_fvg_profile, compute_session_stats
    import analyzer_v5 as _eng

    if mode is not None:
        _eng.TRAIL_MODE = mode
    if cont_k is not None:
        _eng.CONT_BUFFER_MULT = cont_k
    if act_r is not None:
        _eng.TRAIL_ACTIVATION_R_MULT = act_r
    if entry_variant is not None:
        _eng.ENTRY_VARIANT = entry_variant
    if profit_gate is not None:
        _eng.PROFIT_GATE_R = profit_gate
    if trail_be:
        _eng.TRAIL_BE_ON_GATE = True
    if profit_protect_gate is not None:
        _eng.PROFIT_PROTECT_GATE_R = profit_protect_gate
    if profit_protect_swing_atr is not None:
        _eng.PROFIT_PROTECT_SWING_ATR_MULT = profit_protect_swing_atr
    if htf_bias_align:
        _eng.HTF_BIAS_ALIGN = True
    if partial_tp_r is not None:
        _eng.PARTIAL_TP_R = partial_tp_r
    if partial_tp_frac is not None:
        _eng.PARTIAL_TP_FRAC = partial_tp_frac
    if partial_tp_pct is not None:
        _eng.PARTIAL_TP_PCT = partial_tp_pct
    if partial_tp_sl_protect_pct is not None:
        _eng.PARTIAL_TP_SL_PROTECT_PCT = partial_tp_sl_protect_pct
    if partial_tp_scale_step_pct is not None:
        _eng.PARTIAL_TP_SCALE_STEP_PCT = partial_tp_scale_step_pct
    if partial_tp_scale2_abs_pct is not None:
        _eng.PARTIAL_TP_SCALE2_ABS_PCT = partial_tp_scale2_abs_pct
    if partial_tp_time_exit_bars is not None:
        _eng.PARTIAL_TP_TIME_EXIT_BARS = partial_tp_time_exit_bars
    if disable_fvg_trail:
        _eng.DISABLE_FVG_TRAIL = True
    if enable_fallback_ladder:
        _eng.ENABLE_FALLBACK_LADDER = True
    if ladder_step_1_r is not None:
        _eng.LADDER_STEP_1_R = ladder_step_1_r
    if ladder_step_1_sl_r is not None:
        _eng.LADDER_STEP_1_SL_R = ladder_step_1_sl_r
    if ladder_step_2_r is not None:
        _eng.LADDER_STEP_2_R = ladder_step_2_r
    if ladder_step_2_sl_r is not None:
        _eng.LADDER_STEP_2_SL_R = ladder_step_2_sl_r
    if ladder_step_3_r is not None:
        _eng.LADDER_STEP_3_R = ladder_step_3_r
    if ladder_step_3_sl_r is not None:
        _eng.LADDER_STEP_3_SL_R = ladder_step_3_sl_r
    if ladder_step_4_r is not None:
        _eng.LADDER_STEP_4_R = ladder_step_4_r
    if ladder_step_4_sl_r is not None:
        _eng.LADDER_STEP_4_SL_R = ladder_step_4_sl_r

    try:
        result = collect_fvg_profile(sym)
        if result is None or (isinstance(result, tuple) and result[0] is None):
            return {"sym": sym, "error": "VERI YOK"}
        daily_rows, wins, losses, trade_records, rejection_counts = result
        if len(daily_rows) < 1:
            return {"sym": sym, "error": "YETERSIZ VERI"}
        stats = compute_session_stats(trade_records, cfg.INITIAL_BALANCE, daily_rows)
        return {
            "sym": sym,
            "stats": stats,
            "daily_rows": daily_rows,
            "rejection_counts": rejection_counts,
            "trade_records": trade_records,
        }
    except Exception as e:
        return {"sym": sym, "error": str(e)}


def run_compare_ad(symbols, workers, serial, cont_k, act_r):
    """A (retrace baseline) vs D (activation K, R) karsilastirmasi.

    Her coin icin A ve D modlarini ayri worker'da kosar, coin-bazli
    PnL / Win Rate (PE%) / MaxDD / Trade sayisi dokumunu ve D'nin A'yi
    yendigi (NetPnL bazinda outperform) coin listesini uretir.
    Rapor: reports/analyzer_v5_d_compare.md
    """
    import concurrent.futures

    syms = sorted(symbols)
    tasks = []
    for sym in syms:
        tasks.append((sym, "A", "retrace", None, None))
        tasks.append((sym, "D", "activation", cont_k, act_r))

    results = {}
    if serial or workers <= 1:
        for sym, tag, mode, k, r in tasks:
            results[(sym, tag)] = _analyze_one_sym_v5(sym, mode, k, r)
    else:
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as ex:
            fut_map = {
                ex.submit(_analyze_one_sym_v5, sym, mode, k, r): (sym, tag)
                for sym, tag, mode, k, r in tasks
            }
            for fut in concurrent.futures.as_completed(fut_map):
                key = fut_map[fut]
                try:
                    results[key] = fut.result()
                except Exception as e:
                    results[key] = {"sym": key[0], "error": str(e)}

    rows = []
    for sym in syms:
        ra = results.get((sym, "A"), {})
        rd = results.get((sym, "D"), {})
        if "error" in ra or "error" in rd:
            rows.append((sym, None, None, None, None, None, None, None, None, None))
            continue
        sa, sd = ra["stats"], rd["stats"]
        d_pnl = sd["total_pnl"] - sa["total_pnl"]
        rows.append(
            (
                sym,
                sa["total_trades"],
                sa["positive_exit_pct"],
                sa["max_dd_pct"],
                sa["total_pnl"],
                sd["total_trades"],
                sd["positive_exit_pct"],
                sd["max_dd_pct"],
                sd["total_pnl"],
                d_pnl,
            )
        )

    t_a = {"n": 0, "pe": 0.0, "dd": 0.0, "pnl": 0.0}
    t_d = {"n": 0, "pe": 0.0, "dd": 0.0, "pnl": 0.0}
    for r in rows:
        if r[1] is None:
            continue
        t_a["n"] += r[1]
        t_a["pe"] += r[2] * r[1]
        t_a["dd"] = max(t_a["dd"], r[3])
        t_a["pnl"] += r[4]
        t_d["n"] += r[5]
        t_d["pe"] += r[6] * r[5]
        t_d["dd"] = max(t_d["dd"], r[7])
        t_d["pnl"] += r[8]
    t_a["pe"] = t_a["pe"] / t_a["n"] if t_a["n"] else 0.0
    t_d["pe"] = t_d["pe"] / t_d["n"] if t_d["n"] else 0.0

    out_win = [r for r in rows if r[1] is not None and r[9] > 0]
    out_win.sort(key=lambda r: r[9], reverse=True)

    lines = []
    w = lines.append
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    w(f"# A (retrace) vs D (activation K={cont_k}, R={act_r}) — {ts}")
    w("")
    w(
        "- **A (retrace baseline)**: yalnizca FVG gap'i icinde kapanis onaylar; SL/TP eski davranis (ATR_TRAIL_MULT)."
    )
    w(
        f"- **D (activation K={cont_k}, R={act_r})**: FVG yolu retrace ile birebir; FVG adayi yoksa ATR-chase fallback `SL = close -+ K*ATR` YALNIZCA unrealized kar `>= R * risk_pts` (`risk_pts = |entry - initial_sl|`) oldugunda devreye girer; SL/TP paralel tasinir (PTrail)."
    )
    w(
        f"- Sabitler: `ATR_TRAIL_MULT={getattr(cfg, 'ATR_TRAIL_MULT', None)}`, `TRAIL_MIN_MOVE_MULT={getattr(cfg, 'TRAIL_MIN_MOVE_MULT', None)}`; entry/komisyon/TP-RR moddan etkilenmez."
    )
    w("")

    w("## Ozet (toplam)")
    w("")
    hdr = "| Mod | Trade | PE% | MaxDD% | NetPnL |"
    w(hdr)
    w("|" + "---|" * (hdr.count("|") - 1))
    w(f"| A | {t_a['n']} | {t_a['pe']:.1f}% | {t_a['dd']:.1f}% | {t_a['pnl']:+,.0f} |")
    w(f"| D | {t_d['n']} | {t_d['pe']:.1f}% | {t_d['dd']:.1f}% | {t_d['pnl']:+,.0f} |")
    w("")

    w("## Coin bazli dokum")
    w("")
    hdr2 = "| Symbol | Tr(A) | PE%(A) | DD%(A) | PnL(A) | Tr(D) | PE%(D) | DD%(D) | PnL(D) | ΔPnL(D-A) |"
    w(hdr2)
    w("|" + "---|" * (hdr2.count("|") - 1))
    for r in rows:
        if r[1] is None:
            w(f"| {r[0]} | — | — | — | — | — | — | — | — | HATA |")
            continue
        w(
            f"| {r[0]} | {r[1]} | {r[2]:.1f}% | {r[3]:.1f}% | {r[4]:+,.0f} | "
            f"{r[5]} | {r[6]:.1f}% | {r[7]:.1f}% | {r[8]:+,.0f} | {r[9]:+,.0f} |"
        )
    w("")

    w(f"## D'nin A'yi yendigi coinler ({len(out_win)}/{len(syms)})")
    w("")
    if out_win:
        w("| Symbol | PnL A | PnL D | ΔPnL |")
        w("|---|--:|--:|--:|")
        for r in out_win:
            w(f"| {r[0]} | {r[4]:+,.0f} | {r[8]:+,.0f} | {r[9]:+,.0f} |")
    else:
        w("*(Hicbir coinde D, A'yi NetPnL'de gecmedi)*")
    w("")

    w("## Sonuc")
    w("")
    verdict = (
        "D, toplam NetPnL'de A'yi geciyor"
        if t_d["pnl"] > t_a["pnl"]
        else "A, toplam NetPnL'de D'den onde"
    )
    w(
        f"- {verdict} (A: {t_a['pnl']:+,.0f} vs D: {t_d['pnl']:+,.0f}, fark {t_d['pnl'] - t_a['pnl']:+,.0f})."
    )
    w(
        f"- D, {len(out_win)}/{len(syms)} coinde A'ya ustun geldi; toplam MaxDD A: {t_a['dd']:.1f}% / D: {t_d['dd']:.1f}%."
    )

    report_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
    os.makedirs(report_dir, exist_ok=True)
    rpt_path = os.path.join(report_dir, "analyzer_v5_d_compare.md")
    with open(rpt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\n{'=' * 100}")
    print("  A vs D (K, R) KARSILASTIRMA")
    print(f"{'=' * 100}")
    print(
        f"  {'Symbol':<10} {'TrA':>5} {'PEA%':>7} {'PnLA':>10} {'TrD':>5} {'PED%':>7} {'PnLD':>10} {'ΔPnL':>10}"
    )
    for r in rows:
        if r[1] is None:
            print(f"  {r[0]:<10} HATA")
            continue
        print(
            f"  {r[0]:<10} {r[1]:>5} {r[2]:>6.1f}% {r[4]:>+10,.0f} "
            f"{r[5]:>5} {r[6]:>6.1f}% {r[8]:>+10,.0f} {r[9]:>+10,.0f}"
        )
    print(
        f"\n  TOPLAM  A: {t_a['n']} trade {t_a['pe']:.1f}% {t_a['pnl']:+,.0f} | "
        f"D: {t_d['n']} trade {t_d['pe']:.1f}% {t_d['pnl']:+,.0f}"
    )
    print(
        f"  D > A (NetPnL): {len(out_win)}/{len(syms)} coin -> {', '.join(r[0] for r in out_win)}"
    )
    print(f"\n  Rapor: {rpt_path}")


def run_compare_ae(symbols, workers, serial):
    """A vs E1 (yumusak) vs E2 (sert) CHoCH giris filtresi karsilastirmasi.

    Her coin icin A, E1 ve E2 modlarini ayri worker'da kosar; coin-bazli
    Trade / PE% / MaxDD / NetPnL / CHOCH_CONTRA dokumu ve toplam NetPnL
    bazinda kazanan varyanti belirler. Rapor: reports/analyzer_v5_ae_compare.md
    """
    import concurrent.futures

    syms = sorted(symbols)
    tasks = []
    for sym in syms:
        tasks.append((sym, "A", None))
        tasks.append((sym, "E1", "E1"))
        tasks.append((sym, "E2", "E2"))

    results = {}
    if serial or workers <= 1:
        for sym, tag, ev in tasks:
            results[(sym, tag)] = _analyze_one_sym_v5(sym, entry_variant=ev)
    else:
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as ex:
            fut_map = {
                ex.submit(_analyze_one_sym_v5, sym, None, None, None, ev): (sym, tag)
                for sym, tag, ev in tasks
            }
            for fut in concurrent.futures.as_completed(fut_map):
                key = fut_map[fut]
                try:
                    results[key] = fut.result()
                except Exception as e:
                    results[key] = {"sym": key[0], "error": str(e)}

    rows = []
    for sym in syms:
        ra = results.get((sym, "A"), {})
        re1 = results.get((sym, "E1"), {})
        re2 = results.get((sym, "E2"), {})
        if "error" in ra or "error" in re1 or "error" in re2:
            rows.append(
                (sym, None, None, None, None, None, None, None, None, None, None)
            )
            continue
        sa, se1, se2 = ra["stats"], re1["stats"], re2["stats"]
        contra = re2["rejection_counts"].get("CHOCH_CONTRA", 0)
        rows.append(
            (
                sym,
                sa["total_trades"],
                sa["positive_exit_pct"],
                sa["max_dd_pct"],
                sa["total_pnl"],
                se1["total_trades"],
                se1["positive_exit_pct"],
                se1["max_dd_pct"],
                se1["total_pnl"],
                se2["total_trades"],
                se2["positive_exit_pct"],
                se2["max_dd_pct"],
                se2["total_pnl"],
                contra,
            )
        )

    def _tot(idx):
        n = sum(r[idx] for r in rows if r[1] is not None)
        pe = sum(r[idx + 1] * r[idx] for r in rows if r[1] is not None)
        dd = max((r[idx + 2] for r in rows if r[1] is not None), default=0.0)
        pnl = sum(r[idx + 3] for r in rows if r[1] is not None)
        return {"n": n, "pe": pe / n if n else 0.0, "dd": dd, "pnl": pnl}

    t_a = _tot(1)
    t_e1 = _tot(5)
    t_e2 = _tot(9)
    contra_total = sum(r[13] for r in rows if r[1] is not None)

    best_tag, best_pnl = max(
        (("A", t_a["pnl"]), ("E1", t_e1["pnl"]), ("E2", t_e2["pnl"])),
        key=lambda x: x[1],
    )

    lines = []
    w = lines.append
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    w(f"# A vs E1 (yumusak) vs E2 (sert) — CHoCH giris filtresi — {ts}")
    w("")
    w("- **A (baseline)**: mevcut sweep-FVG mantigi, CHoCH filtresi yok.")
    w(
        "- **E1 (yumusak)**: CHoCH yoksa A ile birebir; destekleyici CHoCH varsa CHoCH.level ile ortusen FVG tercih edilir; bias'a ters CHoCH yok sayilir (A'ya dusulur, engellenmez)."
    )
    w(
        "- **E2 (sert)**: E1 ile ayni overlap-FVG tercihi; fark: bias'a ters CHoCH'ta trade atlanir (`CHOCH_CONTRA` reddi)."
    )
    w(
        f"- Sabitler: `CHOCH_FVG_OVERLAP_ATR_MULT={getattr(cfg, 'CHOCH_FVG_OVERLAP_ATR_MULT', 1.0)}`, `CHOCH_MAX_AGE_HOURS={getattr(cfg, 'CHOCH_MAX_AGE_HOURS', 8)}`; trailing/SL/TP formulu moddan etkilenmez."
    )
    w("")

    w("## Ozet (toplam)")
    w("")
    hdr = "| Mod | Trade | PE% | MaxDD% | NetPnL | CHOCH_CONTRA |"
    w(hdr)
    w("|" + "---|" * (hdr.count("|") - 1))
    w(
        f"| A  | {t_a['n']} | {t_a['pe']:.1f}% | {t_a['dd']:.1f}% | {t_a['pnl']:+,.0f} | — |"
    )
    w(
        f"| E1 | {t_e1['n']} | {t_e1['pe']:.1f}% | {t_e1['dd']:.1f}% | {t_e1['pnl']:+,.0f} | — |"
    )
    w(
        f"| E2 | {t_e2['n']} | {t_e2['pe']:.1f}% | {t_e2['dd']:.1f}% | {t_e2['pnl']:+,.0f} | {contra_total} |"
    )
    w("")

    w("## Coin bazli dokum")
    w("")
    hdr2 = "| Symbol | TrA | PEA% | PnLA | TrE1 | PEE1% | PnLE1 | TrE2 | PEE2% | PnLE2 | Contra |"
    w(hdr2)
    w("|" + "---|" * (hdr2.count("|") - 1))
    for r in rows:
        if r[1] is None:
            w(f"| {r[0]} | HATA | | | | | | | | | |")
            continue
        w(
            f"| {r[0]} | {r[1]} | {r[2]:.1f}% | {r[4]:+,.0f} | {r[5]} | {r[6]:.1f}% | {r[8]:+,.0f} | {r[9]} | {r[10]:.1f}% | {r[12]:+,.0f} | {r[13]} |"
        )
    w("")

    w("## Sonuc")
    w("")
    w(
        f"- En yuksek toplam NetPnL: **{best_tag}** (A: {t_a['pnl']:+,.0f}, E1: {t_e1['pnl']:+,.0f}, E2: {t_e2['pnl']:+,.0f})."
    )
    w(
        f"- E1 vs A: {t_e1['pnl'] - t_a['pnl']:+,.0f}; E2 vs A: {t_e2['pnl'] - t_a['pnl']:+,.0f}; E2 vs E1: {t_e2['pnl'] - t_e1['pnl']:+,.0f}."
    )
    w(
        f"- Toplam MaxDD — A: {t_a['dd']:.1f}%, E1: {t_e1['dd']:.1f}%, E2: {t_e2['dd']:.1f}%; E2 `CHOCH_CONTRA` reddi: {contra_total} trade."
    )

    rpt_path = os.path.join(
        os.path.dirname(__file__), "..", "reports", "analyzer_v5_ae_compare.md"
    )
    os.makedirs(os.path.dirname(rpt_path), exist_ok=True)
    with open(rpt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"{'=' * 100}", flush=True)
    print("  A vs E1 vs E2 — CHoCH giris filtresi karsilastirmasi", flush=True)
    print(f"{'=' * 100}", flush=True)
    print(
        f"  {'Symbol':<10} {'TrA':>6} {'PEA%':>6} {'PnLA':>10} "
        f"{'TrE1':>6} {'PEE1%':>6} {'PnLE1':>10} "
        f"{'TrE2':>6} {'PEE2%':>6} {'PnLE2':>10} {'Con':>7}",
        flush=True,
    )
    for r in rows:
        if r[1] is None:
            print(f"  {r[0]:<10} HATA", flush=True)
            continue
        print(
            f"  {r[0]:<10} {r[1]:>6} {r[2]:>5.1f}% {r[4]:>+10,.0f} "
            f"{r[5]:>6} {r[6]:>5.1f}% {r[8]:>+10,.0f} "
            f"{r[9]:>6} {r[10]:>5.1f}% {r[12]:>+10,.0f} {r[13]:>7}",
            flush=True,
        )
    print(
        f"  TOPLAM A: {t_a['n']} trade, PE={t_a['pe']:.1f}%, PnL={t_a['pnl']:+,.0f} | "
        f"E1: {t_e1['n']} trade, PE={t_e1['pe']:.1f}%, PnL={t_e1['pnl']:+,.0f} | "
        f"E2: {t_e2['n']} trade, PE={t_e2['pe']:.1f}%, PnL={t_e2['pnl']:+,.0f} | "
        f"Kazanan: {best_tag} | Rapor: {rpt_path}",
        flush=True,
    )


def _clean_backtest_state():
    """Backtest'e ait state dosyasını run başında temizle (LUNA Plan C madde 3).

    Backtest, canlıyla aynı state_manager iskeletini kullandığından
    (is_sweep_used okuma / .lock oluşturma) SNIPER_OUTPUT_DIR içindeki
    trade_state.json kalıntısı (_used_sweeps) aynı günkü ikinci koşuyu
    etkileyebilir: legacy "{direction}_{bar_index}" kayıtları bar_index'e
    göre eşleştiğinden geçmiş koşuların sweep'leri yeni koşuda "kullanıldı"
    görülüp trade sayısını değiştirir. Temizlenir ve loglanır — temiz state
    + aynı veri → aynı trade/PnL determinizmi.
    """
    _out = os.path.join(os.path.dirname(__file__), "..", "output")
    for fname in ("trade_state.json", "trade_state.json.lock", "trade_state.json.tmp"):
        p = os.path.join(_out, fname)
        try:
            if os.path.exists(p):
                os.remove(p)
                print(f"  [STATE] temizlendi: {p}", flush=True)
        except OSError as e:
            print(f"  [STATE] temizleme hatasi: {p} ({e})", flush=True)


def main():
    """V5 ana rapor: Tum sembolleri isler + summary + dosya."""
    global _LOGGER, TRAIL_MODE, CONT_BUFFER_MULT, TRAIL_ACTIVATION_R_MULT
    global PROFIT_GATE_R, TRAIL_BE_ON_GATE, TRAIL_EXP_TAG
    global PROFIT_PROTECT_GATE_R, PROFIT_PROTECT_SWING_ATR_MULT
    global HTF_BIAS_ALIGN, PARTIAL_TP_R, PARTIAL_TP_FRAC, PARTIAL_TP_PCT
    global PARTIAL_TP_SL_PROTECT_PCT, PARTIAL_TP_SCALE_STEP_PCT
    global PARTIAL_TP_SCALE2_ABS_PCT, PARTIAL_TP_TIME_EXIT_BARS
    global DISABLE_FVG_TRAIL, ENABLE_FALLBACK_LADDER
    global LADDER_STEP_1_R, LADDER_STEP_1_SL_R
    global LADDER_STEP_2_R, LADDER_STEP_2_SL_R
    global LADDER_STEP_3_R, LADDER_STEP_3_SL_R
    global LADDER_STEP_4_R, LADDER_STEP_4_SL_R
    import argparse

    parser = argparse.ArgumentParser(description="V5 backtest engine")
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Paralel worker sayisi (1=serial, default=1)",
    )
    parser.add_argument("--serial", action="store_true", help="Serial mod")
    parser.add_argument(
        "--compare-ad",
        action="store_true",
        help="A vs D (K, R) coin-bazli karsilastirma raporu uret (28 coin)",
    )
    parser.add_argument(
        "--compare-ae",
        action="store_true",
        help="A vs E1 (yumusak) vs E2 (sert) CHoCH giris filtresi karsilastirmasi (28 coin)",
    )
    parser.add_argument(
        "--trail-exp",
        type=str,
        choices=[
            "BASELINE_RETRACE_LIVE_PARITY",
            "PROFIT_GATE_0_8R",
            "PROFIT_GATE_1_0R",
            "ATR_TRAIL_0_5",
            "ATR_TRAIL_0_75",
            "HYBRID_FVG_PLUS_PROFIT_GATE",
            "PROFIT_PROTECT_0_8R_SW0_5",
            "PROFIT_PROTECT_0_8R_SW0_75",
            "PROFIT_PROTECT_1_0R_SW0_5",
            "PROFIT_PROTECT_1_0R_SW0_75",
            "PROFIT_PROTECT_2_0R_SW0_5",
            "PROFIT_PROTECT_2_0R_SW0_75",
            "HTF_BIAS_ALIGN",
            "PARTIAL_TP_1_5R",
            "PARTIAL_TP_1_2R_70PCT",
            "PARTIAL_TP_1_8R_50PCT",
            "PARTIAL_TP_2R_70PCT",
            "PARTIAL_TP_1_5_PCT_50_PCT",
            "PARTIAL_TP_2_0_PCT_50_PCT",
            "PARTIAL_TP_1_5_PCT_30_PCT",
            "SCALE_OUT_1_5_50_2_0",
            "PARTIAL_TP_1_5_PCT_50_TIME_EXIT",
            "PARTIAL_TP_3PCT_70PCT",
            "PARTIAL_TP_3PCT_SCALEOUT",
            "LADDER_DEFAULT",
            "LADDER_AGGRESSIVE",
            "LADDER_CONSERVATIVE",
            "LADDER_SHALLOW",
        ],
        default=None,
        help="LUNA Plan C madde 4 trailing deneyi. Varsayilan kosu baseline "
        "(canli config / retrace) ile aynidir; deney sadece trailing'i degistirir, "
        "entry/state'e dokunmaz.",
    )
    args = parser.parse_args()

    use_serial = args.serial or args.workers <= 1
    n_workers = args.workers if not use_serial else 1

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    # LUNA Plan C madde 3: her koşu TEMİZ state ile başlar.
    _clean_backtest_state()

    # ── Trailing deneyleri (LUNA Plan C madde 4) ──
    # Her deney BASELINE'dan AYRI: yalnizca trailing mekanigini degistirir,
    # entry/state/komisyon degismez. Report etiketi EXP_TAG ile isaretlenir.
    TRAIL_EXP_TAG = args.trail_exp or "BASELINE_RETRACE_LIVE_PARITY"
    ENABLE_FALLBACK_LADDER = False
    LADDER_STEP_1_R = 0.0
    LADDER_STEP_1_SL_R = 0.0
    LADDER_STEP_2_R = 0.0
    LADDER_STEP_2_SL_R = 0.0
    LADDER_STEP_3_R = 0.0
    LADDER_STEP_3_SL_R = 0.0
    LADDER_STEP_4_R = 0.0
    LADDER_STEP_4_SL_R = 0.0
    PARTIAL_TP_SCALE2_ABS_PCT = 0.0
    PARTIAL_TP_TIME_EXIT_BARS = 0
    DISABLE_FVG_TRAIL = False
    if args.trail_exp == "PROFIT_GATE_0_8R":
        TRAIL_MODE = "retrace"
        PROFIT_GATE_R = 0.8
        TRAIL_BE_ON_GATE = False
    elif args.trail_exp == "PROFIT_GATE_1_0R":
        TRAIL_MODE = "retrace"
        PROFIT_GATE_R = 1.0
        TRAIL_BE_ON_GATE = False
    elif args.trail_exp == "ATR_TRAIL_0_5":
        TRAIL_MODE = "atr_chase"
        CONT_BUFFER_MULT = 0.5
        PROFIT_GATE_R = 0.0
        TRAIL_BE_ON_GATE = False
    elif args.trail_exp == "ATR_TRAIL_0_75":
        TRAIL_MODE = "atr_chase"
        CONT_BUFFER_MULT = 0.75
        PROFIT_GATE_R = 0.0
        TRAIL_BE_ON_GATE = False
    elif args.trail_exp == "HYBRID_FVG_PLUS_PROFIT_GATE":
        TRAIL_MODE = "retrace"
        PROFIT_GATE_R = 1.0
        TRAIL_BE_ON_GATE = True
    elif args.trail_exp == "PROFIT_PROTECT_0_8R_SW0_5":
        TRAIL_MODE = "retrace"
        PROFIT_GATE_R = 0.0
        TRAIL_BE_ON_GATE = False
        PROFIT_PROTECT_GATE_R = 0.8
        PROFIT_PROTECT_SWING_ATR_MULT = 0.5
    elif args.trail_exp == "PROFIT_PROTECT_0_8R_SW0_75":
        TRAIL_MODE = "retrace"
        PROFIT_GATE_R = 0.0
        TRAIL_BE_ON_GATE = False
        PROFIT_PROTECT_GATE_R = 0.8
        PROFIT_PROTECT_SWING_ATR_MULT = 0.75
    elif args.trail_exp == "PROFIT_PROTECT_1_0R_SW0_5":
        TRAIL_MODE = "retrace"
        PROFIT_GATE_R = 0.0
        TRAIL_BE_ON_GATE = False
        PROFIT_PROTECT_GATE_R = 1.0
        PROFIT_PROTECT_SWING_ATR_MULT = 0.5
    elif args.trail_exp == "PROFIT_PROTECT_1_0R_SW0_75":
        TRAIL_MODE = "retrace"
        PROFIT_GATE_R = 0.0
        TRAIL_BE_ON_GATE = False
        PROFIT_PROTECT_GATE_R = 1.0
        PROFIT_PROTECT_SWING_ATR_MULT = 0.75
    elif args.trail_exp == "PROFIT_PROTECT_2_0R_SW0_5":
        TRAIL_MODE = "retrace"
        PROFIT_GATE_R = 0.0
        TRAIL_BE_ON_GATE = False
        PROFIT_PROTECT_GATE_R = 2.0
        PROFIT_PROTECT_SWING_ATR_MULT = 0.5
    elif args.trail_exp == "PROFIT_PROTECT_2_0R_SW0_75":
        TRAIL_MODE = "retrace"
        PROFIT_GATE_R = 0.0
        TRAIL_BE_ON_GATE = False
        PROFIT_PROTECT_GATE_R = 2.0
        PROFIT_PROTECT_SWING_ATR_MULT = 0.75
    elif args.trail_exp == "HTF_BIAS_ALIGN":
        TRAIL_MODE = "retrace"
        PROFIT_GATE_R = 0.0
        TRAIL_BE_ON_GATE = False
        PROFIT_PROTECT_GATE_R = 0.0
        PROFIT_PROTECT_SWING_ATR_MULT = 0.5
        HTF_BIAS_ALIGN = True
    elif args.trail_exp == "PARTIAL_TP_1_5R":
        TRAIL_MODE = "retrace"
        PROFIT_GATE_R = 0.0
        TRAIL_BE_ON_GATE = False
        PROFIT_PROTECT_GATE_R = 0.0
        PROFIT_PROTECT_SWING_ATR_MULT = 0.5
        PARTIAL_TP_R = 1.5
        PARTIAL_TP_FRAC = 0.5
    elif args.trail_exp == "PARTIAL_TP_1_2R_70PCT":
        TRAIL_MODE = "retrace"
        PROFIT_GATE_R = 0.0
        TRAIL_BE_ON_GATE = False
        PROFIT_PROTECT_GATE_R = 0.0
        PROFIT_PROTECT_SWING_ATR_MULT = 0.5
        PARTIAL_TP_R = 1.2
        PARTIAL_TP_FRAC = 0.7
    elif args.trail_exp == "PARTIAL_TP_1_8R_50PCT":
        TRAIL_MODE = "retrace"
        PROFIT_GATE_R = 0.0
        TRAIL_BE_ON_GATE = False
        PROFIT_PROTECT_GATE_R = 0.0
        PROFIT_PROTECT_SWING_ATR_MULT = 0.5
        PARTIAL_TP_R = 1.8
        PARTIAL_TP_FRAC = 0.5
    elif args.trail_exp == "PARTIAL_TP_2R_70PCT":
        TRAIL_MODE = "retrace"
        PROFIT_GATE_R = 0.0
        TRAIL_BE_ON_GATE = False
        PROFIT_PROTECT_GATE_R = 0.0
        PROFIT_PROTECT_SWING_ATR_MULT = 0.5
        PARTIAL_TP_R = 0.0
        PARTIAL_TP_FRAC = 0.5
        PARTIAL_TP_PCT = 3.0
        PARTIAL_TP_SL_PROTECT_PCT = 1.5
        PARTIAL_TP_SCALE_STEP_PCT = 2.0
    elif args.trail_exp == "PARTIAL_TP_1_5_PCT_50_PCT":
        TRAIL_MODE = "retrace"
        PROFIT_GATE_R = 0.0
        TRAIL_BE_ON_GATE = False
        PROFIT_PROTECT_GATE_R = 0.0
        PROFIT_PROTECT_SWING_ATR_MULT = 0.5
        PARTIAL_TP_R = 0.0
        PARTIAL_TP_FRAC = 0.5
        PARTIAL_TP_PCT = 1.5
    elif args.trail_exp == "PARTIAL_TP_2_0_PCT_50_PCT":
        TRAIL_MODE = "retrace"
        PROFIT_GATE_R = 0.0
        TRAIL_BE_ON_GATE = False
        PROFIT_PROTECT_GATE_R = 0.0
        PROFIT_PROTECT_SWING_ATR_MULT = 0.5
        PARTIAL_TP_R = 0.0
        PARTIAL_TP_FRAC = 0.5
        PARTIAL_TP_PCT = 2.0
    elif args.trail_exp == "PARTIAL_TP_1_5_PCT_30_PCT":
        TRAIL_MODE = "retrace"
        PROFIT_GATE_R = 0.0
        TRAIL_BE_ON_GATE = False
        PROFIT_PROTECT_GATE_R = 0.0
        PROFIT_PROTECT_SWING_ATR_MULT = 0.5
        PARTIAL_TP_R = 0.0
        PARTIAL_TP_FRAC = 0.3
        PARTIAL_TP_PCT = 1.5
    elif args.trail_exp == "SCALE_OUT_1_5_50_2_0":
        TRAIL_MODE = "retrace"
        PROFIT_GATE_R = 0.0
        TRAIL_BE_ON_GATE = False
        PROFIT_PROTECT_GATE_R = 0.0
        PROFIT_PROTECT_SWING_ATR_MULT = 0.5
        PARTIAL_TP_R = 0.0
        PARTIAL_TP_FRAC = 0.5
        PARTIAL_TP_PCT = 1.5
        PARTIAL_TP_SCALE2_ABS_PCT = 2.0
        DISABLE_FVG_TRAIL = True
    elif args.trail_exp == "PARTIAL_TP_1_5_PCT_50_TIME_EXIT":
        TRAIL_MODE = "retrace"
        PROFIT_GATE_R = 0.0
        TRAIL_BE_ON_GATE = False
        PROFIT_PROTECT_GATE_R = 0.0
        PROFIT_PROTECT_SWING_ATR_MULT = 0.5
        PARTIAL_TP_R = 0.0
        PARTIAL_TP_FRAC = 0.5
        PARTIAL_TP_PCT = 1.5
        PARTIAL_TP_TIME_EXIT_BARS = 15
        DISABLE_FVG_TRAIL = True
    elif args.trail_exp == "PARTIAL_TP_3PCT_70PCT":
        TRAIL_MODE = "retrace"
        PROFIT_GATE_R = 0.0
        TRAIL_BE_ON_GATE = False
        PROFIT_PROTECT_GATE_R = 0.0
        PROFIT_PROTECT_SWING_ATR_MULT = 0.5
        PARTIAL_TP_R = 0.0
        PARTIAL_TP_FRAC = 0.7
        PARTIAL_TP_PCT = 3.0
    elif args.trail_exp == "PARTIAL_TP_3PCT_SCALEOUT":
        TRAIL_MODE = "retrace"
        PROFIT_GATE_R = 0.0
        TRAIL_BE_ON_GATE = False
        PROFIT_PROTECT_GATE_R = 0.0
        PROFIT_PROTECT_SWING_ATR_MULT = 0.5
        PARTIAL_TP_R = 0.0
        PARTIAL_TP_FRAC = 0.5
        PARTIAL_TP_PCT = 3.0
        PARTIAL_TP_SL_PROTECT_PCT = 1.5
        PARTIAL_TP_SCALE_STEP_PCT = 2.0
    elif args.trail_exp == "LADDER_DEFAULT":
        TRAIL_MODE = "retrace"
        PROFIT_GATE_R = 0.0
        TRAIL_BE_ON_GATE = False
        PROFIT_PROTECT_GATE_R = 0.0
        PROFIT_PROTECT_SWING_ATR_MULT = 0.5
        PARTIAL_TP_R = 0.0
        PARTIAL_TP_FRAC = 0.7
        PARTIAL_TP_PCT = 0.0
        PARTIAL_TP_SL_PROTECT_PCT = 0.0
        PARTIAL_TP_SCALE_STEP_PCT = 0.0
        ENABLE_FALLBACK_LADDER = True
        LADDER_STEP_1_R = 0.5
        LADDER_STEP_1_SL_R = 0.1
        LADDER_STEP_2_R = 1.0
        LADDER_STEP_2_SL_R = 0.5
        LADDER_STEP_3_R = 1.5
        LADDER_STEP_3_SL_R = 1.0
        LADDER_STEP_4_R = 2.0
        LADDER_STEP_4_SL_R = 1.5
    elif args.trail_exp == "LADDER_AGGRESSIVE":
        TRAIL_MODE = "retrace"
        PROFIT_GATE_R = 0.0
        TRAIL_BE_ON_GATE = False
        PROFIT_PROTECT_GATE_R = 0.0
        PROFIT_PROTECT_SWING_ATR_MULT = 0.5
        PARTIAL_TP_R = 0.0
        PARTIAL_TP_FRAC = 0.7
        PARTIAL_TP_PCT = 0.0
        PARTIAL_TP_SL_PROTECT_PCT = 0.0
        PARTIAL_TP_SCALE_STEP_PCT = 0.0
        ENABLE_FALLBACK_LADDER = True
        LADDER_STEP_1_R = 0.5
        LADDER_STEP_1_SL_R = 0.05
        LADDER_STEP_2_R = 1.0
        LADDER_STEP_2_SL_R = 0.3
        LADDER_STEP_3_R = 1.5
        LADDER_STEP_3_SL_R = 0.7
        LADDER_STEP_4_R = 2.0
        LADDER_STEP_4_SL_R = 1.2
    elif args.trail_exp == "LADDER_CONSERVATIVE":
        TRAIL_MODE = "retrace"
        PROFIT_GATE_R = 0.0
        TRAIL_BE_ON_GATE = False
        PROFIT_PROTECT_GATE_R = 0.0
        PROFIT_PROTECT_SWING_ATR_MULT = 0.5
        PARTIAL_TP_R = 0.0
        PARTIAL_TP_FRAC = 0.7
        PARTIAL_TP_PCT = 0.0
        PARTIAL_TP_SL_PROTECT_PCT = 0.0
        PARTIAL_TP_SCALE_STEP_PCT = 0.0
        ENABLE_FALLBACK_LADDER = True
        LADDER_STEP_1_R = 0.5
        LADDER_STEP_1_SL_R = 0.1
        LADDER_STEP_2_R = 1.0
        LADDER_STEP_2_SL_R = 0.5
        LADDER_STEP_3_R = 2.0
        LADDER_STEP_3_SL_R = 1.0
        LADDER_STEP_4_R = 3.0
        LADDER_STEP_4_SL_R = 2.0
    elif args.trail_exp == "LADDER_SHALLOW":
        TRAIL_MODE = "retrace"
        PROFIT_GATE_R = 0.0
        TRAIL_BE_ON_GATE = False
        PROFIT_PROTECT_GATE_R = 0.0
        PROFIT_PROTECT_SWING_ATR_MULT = 0.5
        PARTIAL_TP_R = 0.0
        PARTIAL_TP_FRAC = 0.7
        PARTIAL_TP_PCT = 0.0
        PARTIAL_TP_SL_PROTECT_PCT = 0.0
        PARTIAL_TP_SCALE_STEP_PCT = 0.0
        ENABLE_FALLBACK_LADDER = True
        LADDER_STEP_1_R = 0.5
        LADDER_STEP_1_SL_R = 0.05
        LADDER_STEP_2_R = 1.0
        LADDER_STEP_2_SL_R = 0.5
        LADDER_STEP_3_R = 0.0
        LADDER_STEP_3_SL_R = 0.0
        LADDER_STEP_4_R = 0.0
        LADDER_STEP_4_SL_R = 0.0
    else:  # BASELINE_RETRACE_LIVE_PARITY (veya default kosu)
        TRAIL_MODE = getattr(cfg, "TRAIL_MODE", "retrace")
        PROFIT_GATE_R = 0.0
        TRAIL_BE_ON_GATE = False
        PROFIT_PROTECT_GATE_R = 0.0
        PROFIT_PROTECT_SWING_ATR_MULT = 0.5

    # KAPANIS (2026-08-08): D modu + continuation geri cekildi. Varsayilan kosu
    # artik modul sabitini kullanir = canli config'ten turetilir (retrace).
    # ONCEKI sabit override (TRAIL_MODE="activation", K=2.0, R=1.5) KALDIRILDI:
    # backtest'i canli config'ten ayiran son gizli kaynak da boylece bitti.
    print(
        f"  TRAIL MODU: {TRAIL_MODE} "
        f"(K={CONT_BUFFER_MULT}, R={TRAIL_ACTIVATION_R_MULT}, "
        f"Gate={PROFIT_GATE_R}, BE={TRAIL_BE_ON_GATE}) — EXP: {TRAIL_EXP_TAG}",
        flush=True,
    )
    if PROFIT_PROTECT_GATE_R > 0:
        print(
            f"  PROFIT PROTECT: gate={PROFIT_PROTECT_GATE_R}R "
            f"be={PROFIT_PROTECT_BE_R}R swing_atr={PROFIT_PROTECT_SWING_ATR_MULT}",
            flush=True,
        )
    if ENABLE_FALLBACK_LADDER:
        print(
            f"  FALLBACK LADDER: {LADDER_STEP_1_R:.1f}R->+{LADDER_STEP_1_SL_R}R "
            f"{LADDER_STEP_2_R:.1f}R->+{LADDER_STEP_2_SL_R}R "
            f"{LADDER_STEP_3_R:.1f}R->+{LADDER_STEP_3_SL_R}R "
            f"{LADDER_STEP_4_R:.1f}R->+{LADDER_STEP_4_SL_R}R (SL=entry+SL_R*R)",
            flush=True,
        )
    if PARTIAL_TP_PCT > 0 or PARTIAL_TP_R > 0:
        _pt_txt = (
            f"%{PARTIAL_TP_PCT:g} fiyat" if PARTIAL_TP_PCT > 0 else f"{PARTIAL_TP_R}R"
        )
        _pt_extra = []
        if PARTIAL_TP_SL_PROTECT_PCT > 0:
            _pt_extra.append(f"SL->%{PARTIAL_TP_SL_PROTECT_PCT:g}")
        if PARTIAL_TP_SCALE2_ABS_PCT > 0:
            _pt_extra.append(f"2.kademe->%{PARTIAL_TP_SCALE2_ABS_PCT:g} (mutlak)")
        elif PARTIAL_TP_SCALE_STEP_PCT > 0:
            _pt_extra.append(f"2.kademe->+%{PARTIAL_TP_SCALE_STEP_PCT:g}")
        if PARTIAL_TP_TIME_EXIT_BARS > 0:
            _pt_extra.append(f"TIME_EXIT={PARTIAL_TP_TIME_EXIT_BARS} bar")
        if DISABLE_FVG_TRAIL:
            _pt_extra.append("FVG_TRAIL=KAPALI")
        print(
            f"  PARTIAL TP: {_pt_txt} -> %{PARTIAL_TP_FRAC*100:.0f} kapanis"
            + (f" [{', '.join(_pt_extra)}]" if _pt_extra else ""),
            flush=True,
        )

    if args.compare_ad:
        t0c = time.time()
        run_compare_ad(
            cfg.SYMBOLS,
            n_workers,
            use_serial,
            CONT_BUFFER_MULT,
            TRAIL_ACTIVATION_R_MULT,
        )
        print(f"Sure: {time.time() - t0c:.0f}s")
        return

    if args.compare_ae:
        t0c = time.time()
        run_compare_ae(cfg.SYMBOLS, n_workers, use_serial)
        print(f"Sure: {time.time() - t0c:.0f}s")
        return

    t0 = time.time()
    results_data = []
    all_trade_records = []

    print("=" * 100)
    print("  V5 PROFIL — CBDR→Sweep→RSM→FVG→Entry→Trail→Exit")
    print("  Live-identical backtest engine")
    if not use_serial:
        print(f"  Mod: PARALEL ({n_workers} worker)")
    print("=" * 100)

    if use_serial:
        for sym in sorted(cfg.SYMBOLS):
            try:
                profile = cfg.CBDR_RISK_MATRIX.get(sym, {})
                sname = profile.get("session", "DEFAULT")
                sh_info = get_session_hours(sym)
                print(
                    f"\n  [{sym}] Session={sname} [{sh_info['start']:02d}:00-{sh_info['end']:02d}:00]",
                    flush=True,
                )
                result = collect_fvg_profile(sym)
                if result is None or (isinstance(result, tuple) and result[0] is None):
                    print(f"    [{sym}] VERI DOSYASI YOK VEYA ERKEN CIKIS", flush=True)
                    continue
                daily_rows, wins, losses, trade_records, rejection_counts = result
                if len(daily_rows) < 1:
                    print(
                        f"    [{sym}] YETERSIZ VERI (daily_rows={len(daily_rows)})",
                        flush=True,
                    )
                    continue
                stats = compute_session_stats(
                    trade_records, cfg.INITIAL_BALANCE, daily_rows
                )
                results_data.append((sym, stats, daily_rows, rejection_counts))
                all_trade_records.extend(trade_records)
                tp_c = int(stats["tp_pct"] * stats["total_trades"] / 100)
                pt_c = int(stats["profit_trail_pct"] * stats["total_trades"] / 100)
                ls_c = int(stats["loss_pct"] * stats["total_trades"] / 100)
                print(
                    f"    [{sym}] {stats['total_trades']} islem | "
                    f"TP:{tp_c} PTrail:{pt_c} LOSS:{ls_c} | "
                    f"PE={stats['positive_exit_pct']:.1f}% net PnL={stats['total_pnl']:+0f}"
                )
            except Exception as e:
                import traceback

                print(f"    [{sym}] HATA: {e}")
                traceback.print_exc()
                continue
    else:
        # ── Paralel mod ──
        import concurrent.futures

        syms = sorted(cfg.SYMBOLS)
        print(f"\n  {len(syms)} coin {n_workers} worker ile isleniyor...\n", flush=True)
        with concurrent.futures.ProcessPoolExecutor(max_workers=n_workers) as executor:
            fut_map = {
                executor.submit(
                    _analyze_one_sym_v5,
                    sym,
                    TRAIL_MODE,
                    CONT_BUFFER_MULT,
                    TRAIL_ACTIVATION_R_MULT,
                    None,
                    PROFIT_GATE_R,
                    TRAIL_BE_ON_GATE,
                    PROFIT_PROTECT_GATE_R,
                    PROFIT_PROTECT_SWING_ATR_MULT,
                    HTF_BIAS_ALIGN,
                    PARTIAL_TP_R,
                    PARTIAL_TP_FRAC,
                    PARTIAL_TP_PCT,
                    PARTIAL_TP_SL_PROTECT_PCT,
                    PARTIAL_TP_SCALE_STEP_PCT,
                    PARTIAL_TP_SCALE2_ABS_PCT,
                    PARTIAL_TP_TIME_EXIT_BARS,
                    DISABLE_FVG_TRAIL,
                    ENABLE_FALLBACK_LADDER,
                    LADDER_STEP_1_R,
                    LADDER_STEP_1_SL_R,
                    LADDER_STEP_2_R,
                    LADDER_STEP_2_SL_R,
                    LADDER_STEP_3_R,
                    LADDER_STEP_3_SL_R,
                    LADDER_STEP_4_R,
                    LADDER_STEP_4_SL_R,
                ): sym
                for sym in syms
            }
            for future in concurrent.futures.as_completed(fut_map):
                sym = fut_map[future]
                try:
                    res = future.result()
                except Exception as e:
                    print(f"  [!] {sym}: HATA - {e}", flush=True)
                    continue
                if res is None or "error" in res:
                    msg = res.get("error", "BILINMEYEN") if res else "NONE"
                    print(f"  {sym}: {msg}", flush=True)
                    continue
                stats = res["stats"]
                results_data.append(
                    (sym, stats, res["daily_rows"], res["rejection_counts"])
                )
                all_trade_records.extend(res.get("trade_records", []))
                tp_c = int(stats["tp_pct"] * stats["total_trades"] / 100)
                pt_c = int(stats["profit_trail_pct"] * stats["total_trades"] / 100)
                ls_c = int(stats["loss_pct"] * stats["total_trades"] / 100)
                print(
                    f"  {sym}: {stats['total_trades']} islem | "
                    f"TP:{tp_c} PTrail:{pt_c} LOSS:{ls_c} | "
                    f"PE={stats['positive_exit_pct']:.1f}% net PnL={stats['total_pnl']:+0f}",
                    flush=True,
                )

    # ── Parquet ──
    if _LOGGER is not None:
        _LOGGER.save_and_clear()
        _LOGGER = None

    # ── Summary ──
    print(f"\n{'=' * 100}")
    print("  SUMMARY")
    print(f"{'=' * 100}")

    def fvg_created(rej):
        total = 0
        for k, v in rej.items():
            if not k.startswith("SHOULD_TRADE_"):
                total += v
        return total

    hdr = f"  {'Symbol':<10} {'Trades':>7} {'TP%':>6} {'PTrail%':>8} {'Loss%':>7} {'PF':>6} {'Sharpe':>7} {'MaxDD%':>7} {'Fee':>10} {'NetPnL':>10} {'PnL/Fee':>8} {'FVGCr':>6} {'FVGEnt':>6} {'MinRisk':>7} {'Score':>7}"
    print(hdr)
    print(f"  {'-' * len(hdr)}")

    for sym, stats, _, rej in results_data:
        entered = rej.get("ENTERED", 0)
        fvg_c = fvg_created(rej)
        min_risk = rej.get("MIN_RISK_DIST", 0)
        row = f"  {sym:<10} {stats['total_trades']:>7} {stats['tp_pct']:>5.1f}% {stats['profit_trail_pct']:>7.1f}% {stats['loss_pct']:>6.1f}% "
        row += f"{stats['profit_factor']:>5.2f} {stats['sharpe']:>6.3f} {stats['max_dd_pct']:>6.1f}% {stats['total_fee']:>+9.0f} {stats['total_pnl']:>+9.0f} {stats['pnl_per_fee']:>7.2f} {fvg_c:>6} {entered:>6} {min_risk:>7} {stats['score']:>6.1f}"
        print(row)

    total_trades = sum(s["total_trades"] for _, s, _, _ in results_data)
    total_pnl = sum(s["total_pnl"] for _, s, _, _ in results_data)
    total_fee_sum = sum(s["total_fee"] for _, s, _, _ in results_data)
    print(
        f"\n  TOPLAM: {total_trades} trade, Fee={total_fee_sum:+.0f}, net PnL={total_pnl:+.0f} | Sure: {time.time() - t0:.0f}s"
    )
    if HTF_BIAS_ALIGN:
        _contra_total = sum(
            rej.get("HTF_BIAS_CONTRA", 0) for _, _, _, rej in results_data
        )
        print(
            f"  HTF BIAS NOT: 1D bias'a zit yon nedeniyle girilmeyen trade: {_contra_total}"
        )
    if PARTIAL_TP_R > 0 or PARTIAL_TP_PCT > 0:
        _partial_total = sum(rej.get("PARTIAL_TP", 0) for _, _, _, rej in results_data)
        if PARTIAL_TP_PCT > 0:
            _pt_level_txt = f"{PARTIAL_TP_PCT:g}% fiyat"
        else:
            _pt_level_txt = f"{PARTIAL_TP_R}R"
        print(
            f"  PARTIAL TP NOT: {_pt_level_txt}'de %{PARTIAL_TP_FRAC*100:.0f} kapanan trade: {_partial_total}"
        )

    # ── Report file ──
    rpt_path = os.path.join(
        os.path.dirname(__file__), "..", "reports", "analyzer_v5_summary.md"
    )
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(rpt_path, "a") as f:
        f.write(f"\n---\n# analyzer_v5 Summary [{TRAIL_EXP_TAG}] — {ts}\n\n")
        hdr2 = f"| {'Symbol':<10} | {'Trades':>7} | {'TP%':>6} | {'PTrail%':>8} | {'Loss%':>7} | {'PF':>6} | {'Sharpe':>7} | {'MaxDD%':>7} | {'Fee':>10} | {'NetPnL':>10} | {'Exp$':>8} | {'AvgHold':>8} | {'PnL/Fee':>8} | {'FVGCr':>6} | {'FVGEnt':>6} | {'MinRisk':>7} | {'Score':>7} |"
        f.write(hdr2 + "\n")
        sep = "|" + "---|" * (hdr2.count("|") - 1)
        f.write(sep + "\n")
        for sym, stats, _, rej in results_data:
            entered = rej.get("ENTERED", 0)
            fvg_c = fvg_created(rej)
            min_risk = rej.get("MIN_RISK_DIST", 0)
            line = f"| {sym:<10} | {stats['total_trades']:>7} | {stats['tp_pct']:>5.1f}% | {stats['profit_trail_pct']:>7.1f}% | {stats['loss_pct']:>6.1f}% | "
            line += f"{stats['profit_factor']:>5.2f} | {stats['sharpe']:>6.3f} | {stats['max_dd_pct']:>6.1f}% | {stats['total_fee']:>+9.0f} | {stats['total_pnl']:>+9.0f} | {stats['expectancy']:>8.2f} | {stats['avg_hold']:>7.1f} | {stats['pnl_per_fee']:>7.2f} | {fvg_c:>6} | {entered:>6} | {min_risk:>7} | {stats['score']:>6.1f} |"
            f.write(line + "\n")
        f.write(
            f"\n**TOPLAM:** {total_trades} trade, Fee={total_fee_sum:+.0f}, net PnL={total_pnl:+.0f}, "
            f"Expectancy={total_pnl / total_trades:+.2f}$/trade (avg_hold bar ort. "
            f"{sum(s['avg_hold'] * s['total_trades'] for _, s, _, _ in results_data) / total_trades:.1f})\n"
        )
        # ── Exit-reason dagilimi (LUNA Plan C madde 4 rapor zorunlulugu) ──
        if all_trade_records:
            n_tp = sum(1 for r in all_trade_records if r["result"] == "TP")
            n_pt = sum(1 for r in all_trade_records if r["result"] == "PROFIT_TRAIL")
            n_ls = sum(1 for r in all_trade_records if r["result"] in ("LOSS", "OPEN"))
            f.write(
                f"\n**Exit-reason:** TP={n_tp} ({n_tp / total_trades * 100:.1f}%) | "
                f"PROFIT_TRAIL={n_pt} ({n_pt / total_trades * 100:.1f}%) | "
                f"LOSS/OPEN={n_ls} ({n_ls / total_trades * 100:.1f}%)\n"
            )
        # ── HTF BIAS notu: 1D bias'a zit yon nedeniyle giris yapilmayan trade sayisi
        # (kullanici istegi: sütun degil, rapor altinda not olarak).
        if HTF_BIAS_ALIGN:
            _contra = sum(
                rej.get("HTF_BIAS_CONTRA", 0) for _, _, _, rej in results_data
            )
            f.write(
                f"\n**HTF BIAS NOT:** 1D bias'a zit yon oldugu icin giris yapilmayan trade: "
                f"{_contra} (kural: CBDR ve 1D ayni ya da natural ise gir)\n"
            )
        if PARTIAL_TP_R > 0 or PARTIAL_TP_PCT > 0:
            _partial = sum(rej.get("PARTIAL_TP", 0) for _, _, _, rej in results_data)
            if PARTIAL_TP_PCT > 0:
                _pt_level_txt = f"%{PARTIAL_TP_PCT:g} fiyat kari"
            else:
                _pt_level_txt = f"{PARTIAL_TP_R}R seviyesinde"
            f.write(
                f"\n**PARTIAL TP NOT:** {_pt_level_txt} pozisyonun "
                f"%{PARTIAL_TP_FRAC*100:.0f}'i kapatilan trade sayisi: {_partial}\n"
            )
            if all_trade_records:
                _pt_trades = [r for r in all_trade_records if r.get("partial_taken")]
                if _pt_trades:
                    _n_te = sum(1 for r in _pt_trades if r.get("time_exit"))
                    _n_s2 = sum(1 for r in _pt_trades if r.get("scale2_exit"))
                    _n_fvg = len(_pt_trades) - _n_te - _n_s2
                    _n_tp = sum(1 for r in _pt_trades if r["result"] == "TP")
                    _n_pt = sum(1 for r in _pt_trades if r["result"] == "PROFIT_TRAIL")
                    _n_ls = sum(
                        1 for r in _pt_trades if r["result"] in ("LOSS", "OPEN")
                    )
                    f.write(
                        f"\n**KALAN POZISYON KAPANISI (kismi TP alan {len(_pt_trades)} trade):** "
                        f"TP={_n_tp} ({_n_tp/len(_pt_trades)*100:.1f}%) | "
                        f"PROFIT_TRAIL/FVG={_n_pt} ({_n_pt/len(_pt_trades)*100:.1f}%) | "
                        f"LOSS/SL={_n_ls} ({_n_ls/len(_pt_trades)*100:.1f}%) | "
                        f"TIME_EXIT={_n_te} ({_n_te/len(_pt_trades)*100:.1f}%) | "
                        f"SCALE2={_n_s2} ({_n_s2/len(_pt_trades)*100:.1f}%)\n"
                    )
        f.write("\n")
    print(f"  Rapor: {rpt_path}")

    # ── FVG Zone + Fibonacci Analizi ──
    try:
        from fvg_zone_analyzer import (
            Trade,
            classify_trades,
            compute_zone_fibo_stats,
            generate_zone_fibo_report,
            run_holdout_validation,
            generate_holdout_report,
        )

        report_dir = os.path.join(os.path.dirname(__file__), "..", "reports")

        trades = []
        for rec in all_trade_records:
            result_map = {
                "TP": "TP",
                "PROFIT_TRAIL": "PTrail",
                "LOSS": "Loss",
                "OPEN": "Loss",
            }
            trades.append(
                Trade(
                    timestamp=float(rec.get("risk_usd", 0)),
                    fvg_direction=rec.get("fvg_direction", "bullish"),
                    fvg_top=rec.get("fvg_top", 0),
                    fvg_bottom=rec.get("fvg_bottom", 0),
                    swing_high=rec.get("cbdr_body_high", 0),
                    swing_low=rec.get("cbdr_body_low", 0),
                    result=result_map.get(rec.get("result", ""), "Loss"),
                    r_multiple=(
                        rec["pnl"] / rec["risk_usd"]
                        if rec.get("risk_usd", 0) > 0
                        else 0.0
                    ),
                    pnl=rec.get("pnl", 0),
                )
            )

        classify_trades(trades)
        stats = compute_zone_fibo_stats(trades)
        fibo_report = generate_zone_fibo_report(stats)
        fibo_path = os.path.join(report_dir, "fvg_zone_fibo_analysis.md")
        os.makedirs(report_dir, exist_ok=True)
        with open(fibo_path, "w", encoding="utf-8") as f:
            f.write(fibo_report)
        print("  [FVG Zone] Fiyat bölgesi + Fibonacci analizi raporu yazıldı")

        h_result = run_holdout_validation(trades)
        holdout_report = generate_holdout_report(h_result)
        holdout_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "docs",
            "fibo_zone_holdout_validation.md",
        )
        os.makedirs(os.path.dirname(holdout_path), exist_ok=True)
        with open(holdout_path, "a", encoding="utf-8") as f:
            f.write("\n" + holdout_report)
        print(
            f"  [Holdout] Doğrulama: validated={h_result.validated} "
            f"reason={h_result.reason}"
        )
    except Exception as e:
        print(f"  [FVG Zone] Rapor olusturma hatasi: {e}")


if __name__ == "__main__":
    main()
