"""
analyze_fvg_3rd_candle.py — FVG 3. Mum Sınıflaması Backtest.

ICT iddiası:
  1. CONSOLIDATION (3. mum doji/küçük gövdeli) → FVG yüksek ihtimal doldurulur ve tutar
  2. EXPANSION (3. mum güçlü momentum) → FVG uzun süre açık kalır, breakaway gap
  3. REJECTION (3. mum ters yönde güçlü) → 50/50 coin flip, kaçınılmalı

Kullanım:
  cd backtest-sniper/src
  python analyze_fvg_3rd_candle.py
"""

# ruff: noqa: E402
import csv
import os
import random
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

os.environ["SNIPER_OUTPUT_DIR"] = os.path.join(
    os.path.dirname(__file__), "..", "output"
)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_SNIPER_SRC = os.path.join(os.path.dirname(__file__), "..", "..", "sniper", "src")
if _SNIPER_SRC not in sys.path:
    sys.path.insert(0, _SNIPER_SRC)

from indicators import calculate_true_range, update_atr
from models import Bar

# ─── Parametreler ────────────────────────────────────────────
SESSION_NAME = "DEFAULT"
SESSION_HOURS = {"start": 22, "end": 2}
TIMEFRAME = "15m"
LOOKBACK_BARS = 200  # max bar FVG'nin açık kalabileceği
ATR_PERIOD = 14

# Sınıflama eşikleri (sonradan sensitivity analysis için değiştirilebilir)
EXPANSION_ATR_MULT = 1.5  # C3 gövdesi ATR'nin bu katından büyükse
EXPANSION_BODY_RANGE_RATIO = 0.70  # body/range oranı bu değerden büyükse
REJECTION_ATR_MULT = 1.0  # C3 ters yön gövdesi ATR'nin bu katından büyükse
INVALIDATION_ATR_MULT = 1.0  # FVG'nin ters tarafını bu ATR kadar geçme = invalidate
FEE_TAKER = 0.0004  # %0.04 taker komisyonu
N_BOOTSTRAP = 1000  # bootstrap resample sayısı
BOOTSTRAP_SEED = 42  # bootstrap rastgelelik tohumu

SYMBOLS_TO_TEST = [
    "BTCUSDT",
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
    "ETHUSDT",
    "SUIUSDT",
]


# ─── Veri Yükleme ────────────────────────────────────────────
def load_data(filepath):
    bars = []
    with open(filepath, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            ts = int(
                datetime.strptime(row["open_time"], "%Y-%m-%d %H:%M:%S")
                .replace(tzinfo=timezone.utc)
                .timestamp()
                * 1000
            )
            bars.append(
                Bar(
                    index=i,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                    is_closed=True,
                    timestamp=ts,
                )
            )
    return bars


def resample_15m(bars_1m):
    m15 = []
    for i in range(0, len(bars_1m), 15):
        c = bars_1m[i : i + 15]
        if len(c) < 15:
            break
        m15.append(
            Bar(
                index=len(m15),
                open=c[0].open,
                high=max(b.high for b in c),
                low=min(b.low for b in c),
                close=c[-1].close,
                volume=sum(b.volume for b in c),
                is_closed=True,
                timestamp=c[0].timestamp,
            )
        )
    return m15


# ─── FVG Tespiti (3 mum kuralı) ──────────────────────────────
def detect_fvg_3candle(c1: Bar, c2: Bar, c3: Bar, atr: float) -> dict | None:
    """3 ardışık mumda FVG tespit et. (C1, C2, C3)"""
    # Bullish FVG: C1.high < C3.low
    if c3.low > c1.high:
        gap = c3.low - c1.high
        return {
            "direction": "bullish",
            "top": c3.low,
            "bottom": c1.high,
            "size": gap,
            "c1": c1,
            "c2": c2,
            "c3": c3,
            "bar_index": c2.index,
            "atr": atr,
        }
    # Bearish FVG: C1.low > C3.high
    if c1.low > c3.high:
        gap = c1.low - c3.high
        return {
            "direction": "bearish",
            "top": c1.low,
            "bottom": c3.high,
            "size": gap,
            "c1": c1,
            "c2": c2,
            "c3": c3,
            "bar_index": c2.index,
            "atr": atr,
        }
    return None


# ─── 3. Mum Sınıflaması ──────────────────────────────────────
def classify_c3(fvg: dict) -> str:
    """C3 mumunu CONSOLIDATION / EXPANSION / REJECTION olarak sınıflandır."""
    c3 = fvg["c3"]
    c2 = fvg["c2"]
    atr = fvg["atr"]
    direction = fvg["direction"]

    c3_body = abs(c3.close - c3.open)
    c3_range = c3.high - c3.low
    body_range_ratio = c3_body / c3_range if c3_range > 0 else 0

    # REJECTION: C3 ters yönde güçlü
    if direction == "bullish":
        # Bullish FVG'de C3 aşağı yönlü (bearish mum)
        is_bearish_c3 = c3.close < c3.open
        rejection_body = c3_body
        # C2'nin low'unu kırdı mı?
        broke_c2_low = c3.low < c2.low
        if (
            is_bearish_c3
            and rejection_body >= atr * REJECTION_ATR_MULT
            and body_range_ratio >= EXPANSION_BODY_RANGE_RATIO
        ):
            return "REJECTION"
    else:
        # Bearish FVG'de C3 yukarı yönlü (bullish mum)
        is_bullish_c3 = c3.close > c3.open
        rejection_body = c3_body
        broke_c2_high = c3.high > c2.high
        if (
            is_bullish_c3
            and rejection_body >= atr * REJECTION_ATR_MULT
            and body_range_ratio >= EXPANSION_BODY_RANGE_RATIO
        ):
            return "REJECTION"

    # EXPANSION: C3 güçlü momentum, FVG yönünde
    if direction == "bullish":
        is_bullish_c3 = c3.close > c3.open
        expansion_body = c3_body
        broke_c2_high = c3.high > c2.high
        if (
            is_bullish_c3
            and expansion_body >= atr * EXPANSION_ATR_MULT
            and body_range_ratio >= EXPANSION_BODY_RANGE_RATIO
            and broke_c2_high
        ):
            return "EXPANSION"
    else:
        is_bearish_c3 = c3.close < c3.open
        expansion_body = c3_body
        broke_c2_low = c3.low < c2.low
        if (
            is_bearish_c3
            and expansion_body >= atr * EXPANSION_ATR_MULT
            and body_range_ratio >= EXPANSION_BODY_RANGE_RATIO
            and broke_c2_low
        ):
            return "EXPANSION"

    return "CONSOLIDATION"


# ─── Sonuç Takibi ────────────────────────────────────────────
def track_fvg_outcome(fvg: dict, bars_after: list[Bar]) -> dict:
    """FVG oluşumundan sonraki LOOKBACK_BARS boyunca sonucu izle."""
    direction = fvg["direction"]
    fvg_top = fvg["top"]
    fvg_bottom = fvg["bottom"]
    fvg_index = fvg["bar_index"]
    atr = fvg["atr"]

    result = {
        "mitigated": False,
        "mitigate_bar": None,
        "mitigate_price": None,
        "bars_to_mitigate": None,
        "continuation_10": None,  # HATA 4: 10 bar sonra continuation
        "continuation_20": None,  # 20 bar sonra continuation
        "continuation_40": None,  # 40 bar sonra continuation
        "continuation": None,  # alias = continuation_10 (geriye uyum)
        "invalidated": False,
        "invalidate_bar": None,
        "max_excursion": 0.0,
        "max_excursion_dir": None,
        "bars_tracked": 0,
        "close_price_at_end": None,
    }

    invalidate_dist = atr * INVALIDATION_ATR_MULT
    mitigated = False

    for offset, b in enumerate(bars_after):
        if b.index <= fvg_index:
            continue
        if offset >= LOOKBACK_BARS:
            break

        result["bars_tracked"] = offset + 1

        # FVG alanına giriş kontrolü (close veya wick)
        touched_fvg = False
        if direction == "bullish":
            if b.low <= fvg_top and b.high >= fvg_bottom:
                touched_fvg = True
            # Invalidation: fiyat FVG'nin altını invalidate_dist kadar geçti
            if b.close < fvg_bottom - invalidate_dist:
                result["invalidated"] = True
                result["invalidate_bar"] = offset
                if not mitigated:
                    break
        else:
            if b.high >= fvg_bottom and b.low <= fvg_top:
                touched_fvg = True
            if b.close > fvg_top + invalidate_dist:
                result["invalidated"] = True
                result["invalidate_bar"] = offset
                if not mitigated:
                    break

        # Excursion (FVG'den uzaklık)
        if direction == "bullish":
            exc = max(0, b.high - fvg_top, fvg_bottom - b.low)
        else:
            exc = max(0, fvg_top - b.low, b.high - fvg_bottom)
        if exc > result["max_excursion"]:
            result["max_excursion"] = exc
            result["max_excursion_dir"] = (
                "beyond"
                if (direction == "bullish" and b.high > fvg_top)
                or (direction == "bearish" and b.low < fvg_bottom)
                else "reverse"
            )

        # Mitigation: FVG içine close yapıldı
        if not mitigated and touched_fvg:
            if (direction == "bullish" and fvg_bottom <= b.close <= fvg_top) or (
                direction == "bearish" and fvg_bottom <= b.close <= fvg_top
            ):
                mitigated = True
                result["mitigated"] = True
                result["mitigate_bar"] = offset
                result["mitigate_price"] = b.close
                result["bars_to_mitigate"] = offset
            elif (
                direction == "bullish" and b.close >= fvg_bottom and b.low <= fvg_top
            ) or (
                direction == "bearish" and b.close <= fvg_top and b.high >= fvg_bottom
            ):
                # Wick touch (price entered FVG but close may be outside)
                # Still count as mitigated if price entered the zone
                mitigated = True
                result["mitigated"] = True
                result["mitigate_bar"] = offset
                result["mitigate_price"] = b.close
                result["bars_to_mitigate"] = offset

        # HATA 4: Continuation check — 10/20/40 bar pencerelerinde ayrı ayrı
        if mitigated and result["continuation_10"] is None:
            for win_offset, win_key in [
                (10, "continuation_10"),
                (20, "continuation_20"),
                (40, "continuation_40"),
            ]:
                future_offset = offset + win_offset
                if future_offset < len(bars_after):
                    future_bar = bars_after[future_offset]
                    if direction == "bullish":
                        result[win_key] = future_bar.close > fvg_top
                    else:
                        result[win_key] = future_bar.close < fvg_bottom

        if result["invalidated"] and mitigated:
            break

    # Eğer continuation hiç kontrol edilmediyse
    for key in ["continuation_10", "continuation_20", "continuation_40"]:
        if mitigated and result[key] is None:
            result[key] = False

    # Geriye uyum alias
    result["continuation"] = result["continuation_10"]

    return result


# ─── Risk/Reward Simülasyonu ─────────────────────────────────
def simulate_rr(fvg: dict, bars_after: list[Bar]) -> dict:
    """HATA 2 DÜZELTİLDİ: Gerçek bar-bar fiyat takibi ile R:R simülasyonu.

    Entry: FVG ortası. Stop: FVG ters ucunun 1 ATR ötesi. Target: 1:2 R:R.
    """
    direction = fvg["direction"]
    atr = fvg["atr"]
    fvg_top = fvg["top"]
    fvg_bottom = fvg["bottom"]

    entry = (fvg_top + fvg_bottom) / 2
    if direction == "bullish":
        stop = fvg_bottom - atr * 1.0
        target = entry + (entry - stop) * 2.0
    else:
        stop = fvg_top + atr * 1.0
        target = entry - (stop - entry) * 2.0

    risk = abs(entry - stop)
    reward = abs(target - entry)

    risk_pct = risk / entry if entry > 0 else 0.001
    fee_per_leg_R = FEE_TAKER / risk_pct

    result = {
        "entry": entry,
        "stop": stop,
        "target": target,
        "risk": risk,
        "reward": reward,
        "rr": reward / risk if risk > 0 else 0,
        "hit_target": False,
        "hit_stop": False,
        "no_fill": False,
        "no_outcome": False,
        "fee_per_leg_R": fee_per_leg_R,
        "net_profit_R": 0.0,
    }

    # Önce entry'nin fill olup olmadığını kontrol et
    # (fiyat FVG bölgesine hiç girmediyse trade açılmamıştır)
    entered = False
    entry_offset = 0
    for offset, b in enumerate(bars_after[:LOOKBACK_BARS]):
        if b.low <= entry <= b.high:
            entered = True
            entry_offset = offset
            break
    if not entered:
        result["no_fill"] = True
        result["net_profit_R"] = 0.0
        return result

    # Entry'den sonraki barlarda stop mu target mı önce vuruluyor
    for b in bars_after[entry_offset : entry_offset + LOOKBACK_BARS]:
        if direction == "bullish":
            hit_stop = b.low <= stop
            hit_target = b.high >= target
        else:
            hit_stop = b.high >= stop
            hit_target = b.low <= target
        # Aynı barda ikisi de tetiklenirse konservatif: stop önce vurulmuş say
        if hit_stop:
            result["hit_stop"] = True
            result["net_profit_R"] = -1.0 - 2.0 * fee_per_leg_R
            return result
        if hit_target:
            result["hit_target"] = True
            result["net_profit_R"] = 2.0 - 2.0 * fee_per_leg_R
            return result

    # LOOKBACK_BARS içinde ne stop ne target vurulmadı
    result["no_outcome"] = True
    result["net_profit_R"] = -2.0 * fee_per_leg_R  # entry + varsayılan kapanış maliyeti
    return result


# ─── Ana Döngü ───────────────────────────────────────────────
def analyze_symbol(symbol: str) -> dict:
    """Tek bir coin için FVG 3rd candle analizi yap."""
    csv_path = os.path.join(
        os.path.dirname(__file__), "data", "daily", f"{symbol}_1m_raw.csv"
    )
    if not os.path.isfile(csv_path):
        return None

    b1 = load_data(csv_path)
    b15 = resample_15m(b1)
    if not b15:
        return None

    sh, eh = SESSION_HOURS["start"], SESSION_HOURS["end"]
    spans_midnight = sh > eh

    # ATR hesapla (ilk 500 bar)
    atr_val = 0.0
    prev_close = b15[0].open
    for bar in b15[1:500]:
        tr = calculate_true_range(bar, prev_close)
        atr_val = update_atr(atr_val if atr_val > 0 else None, tr)
        prev_close = bar.close

    fvgs = []
    category_counts = defaultdict(int)
    session_hour_buckets = defaultdict(int)  # HATA 1 sanity check
    category_outcomes = defaultdict(
        lambda: {
            "total": 0,
            "mitigated": 0,
            "invalidated": 0,
            "continued": 0,
            "continued_10": 0,
            "continued_20": 0,
            "continued_40": 0,
            "bars_to_mitigate": [],
            "rr_wins": 0,
            "rr_losses": 0,
            "no_fill": 0,
            "no_outcome": 0,
            "profits": [],
            "win_flags": [],
        }
    )

    total_bars = len(b15)
    for sb in range(500, total_bars):
        if (sb - 500) % 10000 == 0:
            pct = (sb - 500) / (total_bars - 500) * 100
            print(f"\r  [{symbol}] %{pct:.0f}", end="", flush=True)

        cur = b15[sb]

        # HATA 3 DÜZELTİLDİ: Sınıflama için C3'ten ÖNCEKİ ATR'yi kullan
        # (ATR güncellemesini C3 işlendikten sonra yap)
        atr = atr_val

        tr = calculate_true_range(cur, prev_close)
        atr_val = update_atr(atr_val if atr_val > 0 else None, tr)
        prev_close = cur.close

        # Session filtresi
        try:
            edt = datetime.fromtimestamp(cur.timestamp / 1000, tz=timezone.utc)
        except Exception:
            continue
        h = edt.hour
        # HATA 1 DÜZELTİLDİ: Session içindeki barları TUT, dışındakileri atla
        in_session = (h >= sh or h < eh) if spans_midnight else (sh <= h < eh)
        if not in_session:
            continue
        session_hour_buckets[h] += 1

        # 3 ardışık mum kontrolü
        if sb < 2:
            continue
        c1 = b15[sb - 2]
        c2 = b15[sb - 1]
        c3 = b15[sb]

        fvg_data = detect_fvg_3candle(c1, c2, c3, atr)
        if fvg_data is None:
            continue

        # Skip very small FVGs
        if fvg_data["size"] < atr * 0.1:
            continue

        # ATR debug: kullanılan ATR değeri (C3 öncesi)
        fvg_data["atr_used"] = atr
        fvg_data["tr_of_c3"] = tr
        fvg_data["atr_after_c3"] = atr_val
        fvg_data["fvg_hour"] = h
        fvg_data["timestamp"] = c3.timestamp

        # Sınıflama
        category = classify_c3(fvg_data)
        fvg_data["category"] = category

        # Sonuç takibi (kalan barlar)
        bars_after = b15[sb + 1 : min(sb + LOOKBACK_BARS, total_bars)]
        outcome = track_fvg_outcome(fvg_data, bars_after)

        # R:R simülasyonu (gerçek bar-bar takibi)
        rr = simulate_rr(fvg_data, bars_after)

        fvg_data["outcome"] = outcome
        fvg_data["rr"] = rr
        fvgs.append(fvg_data)

        # İstatistik
        co = category_outcomes[category]
        co["total"] += 1
        if outcome["mitigated"]:
            co["mitigated"] += 1
            if outcome["bars_to_mitigate"] is not None:
                co["bars_to_mitigate"].append(outcome["bars_to_mitigate"])
        if outcome["invalidated"]:
            co["invalidated"] += 1
        if outcome.get("continuation"):
            co["continued"] += 1
        if outcome.get("continuation_10"):
            co["continued_10"] += 1
        if outcome.get("continuation_20"):
            co["continued_20"] += 1
        if outcome.get("continuation_40"):
            co["continued_40"] += 1
        if rr.get("hit_target"):
            co["rr_wins"] += 1
            co["profits"].append(rr["net_profit_R"])
            co["win_flags"].append(1)
        if rr.get("hit_stop"):
            co["rr_losses"] += 1
            co["profits"].append(rr["net_profit_R"])
            co["win_flags"].append(0)
        if rr.get("no_fill"):
            co["no_fill"] += 1
        if rr.get("no_outcome"):
            co["no_outcome"] += 1

    print(f"\r  [{symbol}] %100", flush=True)

    return {
        "symbol": symbol,
        "total_fvgs": len(fvgs),
        "session_hour_buckets": dict(session_hour_buckets),
        "category_counts": dict(category_counts),
        "category_outcomes": dict(category_outcomes),
        "fvgs": fvgs,
    }


# ─── Bootstrap CI ────────────────────────────────────────────
def bootstrap_ci(values, n_resamples=N_BOOTSTRAP, ci=95, seed=BOOTSTRAP_SEED):
    """Bootstrap %95 CI for the mean. Returns (lower, upper, mean)."""
    rng = random.Random(seed)
    n = len(values)
    if n < 3:
        return (None, None, sum(values) / n if n else 0)
    means = []
    for _ in range(n_resamples):
        s = 0.0
        for _ in range(n):
            s += values[rng.randint(0, n - 1)]
        means.append(s / n)
    alpha = (100 - ci) / 2
    lo = sorted(means)[int(n_resamples * alpha / 100)]
    hi = sorted(means)[int(n_resamples * (100 - alpha) / 100)]
    return (lo, hi, sum(values) / n)


# ─── ATR Self-Reference Proof ─────────────────────────────────
def print_atr_proof(all_results):
    """5 rastgele FVG seç, C3 öncesi/sonrası ATR'yi göster."""
    print("\n" + "-" * 80)
    print("  ATR SELF-REFERENCE KANITI")
    print("  C3 öncesi ATR (sınıflamada kullanılan) ≠ C3 sonrası ATR")
    print("-" * 80)
    all_fvgs = []
    for r in all_results:
        if r is None:
            continue
        all_fvgs.extend(r["fvgs"])
    if len(all_fvgs) < 5:
        print("  Yetersiz FVG — atlanıyor.")
        return
    rng = random.Random(BOOTSTRAP_SEED)
    chosen = rng.sample(all_fvgs, min(5, len(all_fvgs)))
    for i, f in enumerate(chosen, 1):
        print(
            f"  #{i} cat={f['category']:>14s} dir={f['direction']:>7s}  "
            f"atr_before_C3={f['atr_used']:.4f}  "
            f"tr_of_C3={f['tr_of_c3']:.4f}  "
            f"atr_after_C3={f['atr_after_c3']:.4f}  "
            f"diff={'SAME' if abs(f['atr_used'] - f['atr_after_c3']) < 0.0001 else 'DIFF'}"
        )


# ─── Coin Korelasyonu ─────────────────────────────────────────
def print_coin_correlation(all_results):
    """Her coin için saat dilimlerindeki FVG dağılımı ve BTC ile örtüşme."""
    print("\n" + "-" * 80)
    print("  COIN KORELASYONU & EFEKTİF ÖRNEKLEM")
    print("-" * 80)
    # Per-coin, per-hour FVG count
    coin_hour = {}
    coin_days = {}
    for r in all_results:
        if r is None:
            continue
        sym = r["symbol"]
        ch = defaultdict(int)
        cd = set()
        for f in r["fvgs"]:
            hr = f.get("fvg_hour", -1)
            ch[hr] += 1
            ts = f.get("timestamp", 0)
            if ts:
                dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).date()
                cd.add(dt)
        coin_hour[sym] = dict(ch)
        coin_days[sym] = len(cd)
    all_coins = sorted(coin_hour.keys())
    if not all_coins:
        return

    # Tablo başlığı
    hours = sorted({h for ch in coin_hour.values() for h in ch})
    header = f"  {'Coin':<10s} {'Toplam':>6s} {'Gün':>4s}"
    for h in hours:
        header += f" {h:02d}:00"
    print(header)
    print("  " + "-" * len(header))
    btc_hours = coin_hour.get("BTCUSDT", {})
    btc_total = sum(btc_hours.values())
    for sym in all_coins:
        ch = coin_hour[sym]
        total = sum(ch.values())
        days = coin_days[sym]
        row = f"  {sym:<10s} {total:>6d} {days:>4d}"
        for h in hours:
            cnt = ch.get(h, 0)
            if btc_hours.get(h, 0) > 0 and cnt > 0:
                row += f"  {cnt:>2d}*"
            else:
                row += f"  {cnt:>2d} "
        print(row)

    # BTC ile ortalama overlap
    if btc_total > 0:
        overlaps = []
        for sym in all_coins:
            if sym == "BTCUSDT":
                continue
            ch = coin_hour[sym]
            overlap_pct = 0.0
            for h in hours:
                if btc_hours.get(h, 0) > 0 and ch.get(h, 0) > 0:
                    overlap_pct += 1.0
            if hours:
                overlap_pct = overlap_pct / len(hours) * 100
            overlaps.append((overlap_pct, sym))
        avg_overlap = sum(o for o, _ in overlaps) / len(overlaps) if overlaps else 0
        print(f"\n  BTC saat dilimi örtüşme ortalaması: {avg_overlap:.1f}%")
    # Efektif örneklem: eşsiz gün sayısı ortalaması
    avg_days = sum(coin_days.values()) / len(coin_days)
    print(f"  Ortalama eşsiz gün (efektif bağımsız örneklem): {avg_days:.0f}")
    min_days = min(coin_days.values())
    print(f"  En düşük gün: {min_days}")


# ─── Raporlama ───────────────────────────────────────────────
def print_report(all_results: list[dict]):
    """Kategoriler arası karşılaştırmalı rapor bas."""
    print("\n" + "=" * 100)
    print("  FVG 3. MUM SINIFLAMASI — BACKTEST RAPORU (DÜZELTİLMİŞ)")
    print(
        f"  Session: {SESSION_NAME} [{SESSION_HOURS['start']:02d}:00-{SESSION_HOURS['end']:02d}:00]"
    )
    print(f"  Timeframe: {TIMEFRAME}")
    print(f"  Lookback: {LOOKBACK_BARS} bar")
    print(
        f"  Eşikler: EXP_ATR={EXPANSION_ATR_MULT}x, EXP_BRR={EXPANSION_BODY_RANGE_RATIO}, REJ_ATR={REJECTION_ATR_MULT}x"
    )
    print("=" * 100)

    # Session filtre sanity check
    all_hours = defaultdict(int)
    for r in all_results:
        if r is None:
            continue
        for h, cnt in r.get("session_hour_buckets", {}).items():
            all_hours[h] += cnt
    if all_hours:
        total_accepted = sum(all_hours.values())
        sorted_hours = sorted(all_hours.items())
        _sh, _eh = SESSION_HOURS["start"], SESSION_HOURS["end"]
        _spans_midnight = _sh > _eh
        in_range = 0
        for h, cnt in sorted_hours:
            if _spans_midnight:
                if h >= _sh or h < _eh:
                    in_range += cnt
            else:
                if _sh <= h < _eh:
                    in_range += cnt
        print(
            f"\n  Session Sanity Check: Kabul edilen barların saat dağılımı (toplam {total_accepted} bar)"
        )
        hour_str = ", ".join(f"{h:02d}:00={cnt}" for h, cnt in sorted_hours[:12])
        print(f"    {hour_str}")
        if len(sorted_hours) > 12:
            print(f"    ... ve {len(sorted_hours)-12} farklı saat daha")
        print(
            f"    -> Tüm barlar session penceresinde: {'✅' if total_accepted == in_range else '⚠️'}"
        )

    # Coin bazlı özet
    print(f"\n{'='*100}")
    print("  COIN BAZLI ÖZET")
    print(f"{'='*100}")
    print(f"  {'Coin':<12} {'FVG':>6} {'CONS':>6} {'EXP':>6} {'REJ':>6}")
    print(f"  {'-'*42}")
    for r in all_results:
        if r is None:
            continue
        co = r["category_outcomes"]
        c_cons = co.get("CONSOLIDATION", {}).get("total", 0)
        c_exp = co.get("EXPANSION", {}).get("total", 0)
        c_rej = co.get("REJECTION", {}).get("total", 0)
        print(
            f"  {r['symbol']:<12} {r['total_fvgs']:>6} {c_cons:>6} {c_exp:>6} {c_rej:>6}"
        )

    # Toplam istatistik
    print(f"\n{'='*100}")
    print("  TOPLU İSTATİSTİK (tüm coinler)")
    print(f"{'='*100}")

    agg = defaultdict(
        lambda: {
            "total": 0,
            "mitigated": 0,
            "invalidated": 0,
            "continued": 0,
            "continued_10": 0,
            "continued_20": 0,
            "continued_40": 0,
            "bars_to_mitigate": [],
            "rr_wins": 0,
            "rr_losses": 0,
            "no_fill": 0,
            "no_outcome": 0,
            "profits": [],
            "win_flags": [],
        }
    )
    for r in all_results:
        if r is None:
            continue
        for cat, data in r["category_outcomes"].items():
            a = agg[cat]
            a["total"] += data["total"]
            a["mitigated"] += data["mitigated"]
            a["invalidated"] += data["invalidated"]
            a["continued"] += data.get("continued", 0)
            a["continued_10"] += data.get("continued_10", 0)
            a["continued_20"] += data.get("continued_20", 0)
            a["continued_40"] += data.get("continued_40", 0)
            a["bars_to_mitigate"].extend(data["bars_to_mitigate"])
            a["rr_wins"] += data["rr_wins"]
            a["rr_losses"] += data["rr_losses"]
            a["no_fill"] += data.get("no_fill", 0)
            a["no_outcome"] += data.get("no_outcome", 0)
            a["profits"].extend(data.get("profits", []))
            a["win_flags"].extend(data.get("win_flags", []))

    header = f"  {'Kategori':<16} {'FVG':>6} {'Mit%':>7} {'Inv%':>7} {'Cont10%':>8} {'Cont40%':>8} {'AvgBar':>7} {'RR_W%':>7} {'Exp':>8} {'NoFill':>7}"
    print(f"  {'-'*len(header)}")
    print(header)
    print(f"  {'-'*len(header)}")

    for cat in ["CONSOLIDATION", "EXPANSION", "REJECTION"]:
        a = agg.get(cat, {})
        t = a.get("total", 0)
        if t == 0:
            continue
        mit_rate = a["mitigated"] / t * 100
        inv_rate = a["invalidated"] / t * 100
        cont10_rate = (
            a["continued_10"] / a["mitigated"] * 100 if a["mitigated"] > 0 else 0
        )
        cont40_rate = (
            a["continued_40"] / a["mitigated"] * 100 if a["mitigated"] > 0 else 0
        )
        avg_bar = (
            sum(a["bars_to_mitigate"]) / len(a["bars_to_mitigate"])
            if a["bars_to_mitigate"]
            else 0
        )
        rr_total = a["rr_wins"] + a["rr_losses"]
        rr_wr = a["rr_wins"] / rr_total * 100 if rr_total > 0 else 0
        expectancy = (a["rr_wins"] * 2 - a["rr_losses"] * 1) / max(
            rr_total, 1
        )  # 1:2 R:R
        nf_pct = a["no_fill"] / t * 100 if t > 0 else 0
        print(
            f"  {cat:<16} {t:>6} {mit_rate:>6.1f}% {inv_rate:>6.1f}% {cont10_rate:>7.1f}% {cont40_rate:>7.1f}% {avg_bar:>6.0f} {rr_wr:>6.1f}% {expectancy:>+7.2f} {nf_pct:>6.1f}%"
        )

    print(f"  {'-'*len(header)}")

    # İddia testi
    print(f"\n{'='*100}")
    print("  İDDİA TESTİ: CONSOLIDATION > EXPANSION > REJECTION")
    print(f"{'='*100}")

    cons = agg.get("CONSOLIDATION", {})
    exp = agg.get("EXPANSION", {})
    rej = agg.get("REJECTION", {})

    c_mit = cons.get("mitigated", 0) / max(cons.get("total", 1), 1) * 100
    e_mit = exp.get("mitigated", 0) / max(exp.get("total", 1), 1) * 100
    r_mit = rej.get("mitigated", 0) / max(rej.get("total", 1), 1) * 100

    c_cont = cons.get("continued", 0) / max(cons.get("mitigated", 1), 1) * 100
    e_cont = exp.get("continued", 0) / max(exp.get("mitigated", 1), 1) * 100
    r_cont = rej.get("continued", 0) / max(rej.get("mitigated", 1), 1) * 100

    c_cont10 = cons.get("continued_10", 0) / max(cons.get("mitigated", 1), 1) * 100
    e_cont10 = exp.get("continued_10", 0) / max(exp.get("mitigated", 1), 1) * 100
    r_cont10 = rej.get("continued_10", 0) / max(rej.get("mitigated", 1), 1) * 100

    c_cont40 = cons.get("continued_40", 0) / max(cons.get("mitigated", 1), 1) * 100
    e_cont40 = exp.get("continued_40", 0) / max(exp.get("mitigated", 1), 1) * 100
    r_cont40 = rej.get("continued_40", 0) / max(rej.get("mitigated", 1), 1) * 100

    c_nf = cons.get("no_fill", 0) / max(cons.get("total", 1), 1) * 100
    e_nf = exp.get("no_fill", 0) / max(exp.get("total", 1), 1) * 100
    r_nf = rej.get("no_fill", 0) / max(rej.get("total", 1), 1) * 100

    print("\n  Mitigation Rate (ne kadar FVG dolduruldu):")
    print(f"    CONSOLIDATION: {c_mit:.1f}%")
    print(f"    EXPANSION:     {e_mit:.1f}%")
    print(f"    REJECTION:     {r_mit:.1f}%")

    print("\n  Continuation Rate (10-bar window):")
    print(f"    CONSOLIDATION: {c_cont10:.1f}%")
    print(f"    EXPANSION:     {e_cont10:.1f}%")
    print(f"    REJECTION:     {r_cont10:.1f}%")

    print("\n  Continuation Rate (40-bar window):")
    print(f"    CONSOLIDATION: {c_cont40:.1f}%")
    print(f"    EXPANSION:     {e_cont40:.1f}%")
    print(f"    REJECTION:     {r_cont40:.1f}%")

    print("\n  No-Fill Rate (trade hiç açılamadı):")
    print(f"    CONSOLIDATION: {c_nf:.1f}%")
    print(f"    EXPANSION:     {e_nf:.1f}%")
    print(f"    REJECTION:     {r_nf:.1f}%")

    # Sonuç
    print(f"\n  {'>>'} YORUM:")
    if c_mit >= e_mit >= r_mit:
        print(
            f"  ✅ İddia TUTUYOR: Consolidation ({c_mit:.1f}%) >= Expansion ({e_mit:.1f}%) >= Rejection ({r_mit:.1f}%)"
        )
    elif c_mit >= r_mit and c_mit >= e_mit:
        print(f"  ⚠️ Kısmen: Consolidation en yüksek ({c_mit:.1f}%) ama sıralama farklı")
    else:
        print(
            "  ❌ İddia TUTMUYOR: Beklenen sıralama Consolidation > Expansion > Rejection"
        )

    print("\n  R:R Expectancy (1:2 R/R, 1 ATR stop):")
    for cat in ["CONSOLIDATION", "EXPANSION", "REJECTION"]:
        a = agg.get(cat, {})
        t = a.get("total", 0)
        if t == 0:
            continue
        rr_total = a["rr_wins"] + a["rr_losses"]
        exp_val = (a["rr_wins"] * 2 - a["rr_losses"] * 1) / max(rr_total, 1)
        print(
            f"    {cat:<16} {a['rr_wins']:>3}W / {a['rr_losses']:>3}L = {exp_val:>+.2f}R expectancy"
        )
        # Show net expectancy with commission
        profits = a.get("profits", [])
        if profits:
            net_exp = sum(profits) / len(profits)
            print(f"    {'':>16} Net (%%0.04 taker): {net_exp:>+.2f}R expectancy")

    # Bootstrap CI for REJECTION
    print(f"\n{'='*100}")
    print("  BOOTSTRAP CI (%95 GÜVEN ARALIĞI) — REJECTION")
    print(f"  {N_BOOTSTRAP} resample, seed={BOOTSTRAP_SEED}")
    print(f"{'='*100}")
    rej = agg.get("REJECTION", {})
    rej_profits = rej.get("profits", [])
    rej_wins = rej.get("win_flags", [])
    if len(rej_profits) >= 3:
        wr_lo, wr_hi, wr_mean = bootstrap_ci(rej_wins)
        exp_lo, exp_hi, exp_mean = bootstrap_ci(rej_profits)
        print(
            f"  WR bootstrap:       {wr_mean*100:.1f}%  [%95 CI: {wr_lo*100:.1f}% - {wr_hi*100:.1f}%]"
        )
        print(
            f"  Expectancy bootstrap: {exp_mean:+.2f}R [%95 CI: {exp_lo:+.2f}R - {exp_hi:+.2f}R]"
        )
        # Cont@20 non-monotonic check
        print("\n  Non-Monotonik Cont@20 Check:")
        print(
            f"    REJECTION Cont@10={rej.get('continued_10', 0)/max(rej.get('mitigated',1),1)*100:.1f}%"
        )
        print(
            f"    REJECTION Cont@20={rej.get('continued_20', 0)/max(rej.get('mitigated',1),1)*100:.1f}%"
        )
        print(
            f"    REJECTION Cont@40={rej.get('continued_40', 0)/max(rej.get('mitigated',1),1)*100:.1f}%"
        )
        wr_diff = abs(wr_hi - wr_lo)
        if wr_diff > 10:
            print(
                f"    ⚠️ WR CI genişliği {wr_diff:.1f}% — Cont@20 dalgalanma gürültüden kaynaklanıyor olabilir"
            )
        else:
            print(
                f"    ✅ WR CI genişliği {wr_diff:.1f}% — Cont@20 sapma güvenilir pattern olabilir"
            )
    else:
        print(f"  Yetersiz REJECTION örneği ({len(rej_profits)}). Bootstrap atlanıyor.")

    # ATR proof
    print_atr_proof(all_results)

    # Coin correlation
    print_coin_correlation(all_results)


def write_md_report(results, agg, all_hours=None):
    """Write MD report to file. old_agg: dict from previous buggy run for comparison."""
    cons = agg.get("CONSOLIDATION", {})
    exp = agg.get("EXPANSION", {})
    rej = agg.get("REJECTION", {})

    c_mit = cons.get("mitigated", 0) / max(cons.get("total", 1), 1) * 100
    e_mit = exp.get("mitigated", 0) / max(exp.get("total", 1), 1) * 100
    r_mit = rej.get("mitigated", 0) / max(rej.get("total", 1), 1) * 100

    c_cont10 = cons.get("continued_10", 0) / max(cons.get("mitigated", 1), 1) * 100
    e_cont10 = exp.get("continued_10", 0) / max(exp.get("mitigated", 1), 1) * 100
    r_cont10 = rej.get("continued_10", 0) / max(rej.get("mitigated", 1), 1) * 100

    c_cont40 = cons.get("continued_40", 0) / max(cons.get("mitigated", 1), 1) * 100
    e_cont40 = exp.get("continued_40", 0) / max(exp.get("mitigated", 1), 1) * 100
    r_cont40 = rej.get("continued_40", 0) / max(rej.get("mitigated", 1), 1) * 100

    c_nf = cons.get("no_fill", 0) / max(cons.get("total", 1), 1) * 100
    e_nf = exp.get("no_fill", 0) / max(exp.get("total", 1), 1) * 100
    r_nf = rej.get("no_fill", 0) / max(rej.get("total", 1), 1) * 100

    def cat_expectancy(a):
        rt = a.get("rr_wins", 0) + a.get("rr_losses", 0)
        return (
            (a.get("rr_wins", 0) * 2 - a.get("rr_losses", 0) * 1) / max(rt, 1)
            if rt > 0
            else 0.0
        )

    c_exp_val = cat_expectancy(cons)
    e_exp_val = cat_expectancy(exp)
    r_exp_val = cat_expectancy(rej)

    report_lines = []
    report_lines.append("# FVG 3. Mum Sınıflaması — Backtest Raporu (Düzeltilmiş)")
    report_lines.append("")
    report_lines.append(
        f"**Session:** {SESSION_NAME} [{SESSION_HOURS['start']:02d}:00-{SESSION_HOURS['end']:02d}:00]"
    )
    report_lines.append(f"**Timeframe:** {TIMEFRAME}")
    report_lines.append(f"**Coinler:** {', '.join(SYMBOLS_TO_TEST)}")
    report_lines.append(f"**Tarih:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report_lines.append("")
    report_lines.append("**Düzeltmeler:**")
    report_lines.append(
        "- Hata 1: Session filtresi düzeltildi (22:00-02:00 artık doğru çalışıyor)"
    )
    report_lines.append(
        "- Hata 2: R:R simülasyonu gerçek bar-bar fiyat takibi ile yeniden yazıldı"
    )
    report_lines.append(
        "- Hata 3: ATR self-referans düzeltildi (C3 kendi ATR'sini etkilemiyor)"
    )
    report_lines.append(
        "- Hata 4: Continuation 3 pencerede raporlanıyor (10/20/40 bar)"
    )
    report_lines.append("")
    report_lines.append("## Parametreler")
    report_lines.append("")
    report_lines.append("| Parametre | Değer |")
    report_lines.append("|---|---|")
    report_lines.append(f"| EXPANSION ATR Mult | {EXPANSION_ATR_MULT}x |")
    report_lines.append(f"| EXPANSION Body/Range | {EXPANSION_BODY_RANGE_RATIO} |")
    report_lines.append(f"| REJECTION ATR Mult | {REJECTION_ATR_MULT}x |")
    report_lines.append(f"| Lookback Bars | {LOOKBACK_BARS} |")
    report_lines.append("")
    report_lines.append("## Coin Bazlı Özet")
    report_lines.append("")
    report_lines.append("| Coin | FVG | CONS | EXP | REJ |")
    report_lines.append("|---|---|---|---|---|")
    for r in results:
        if r is None:
            continue
        co = r["category_outcomes"]
        c_cons = co.get("CONSOLIDATION", {}).get("total", 0)
        c_exp = co.get("EXPANSION", {}).get("total", 0)
        c_rej = co.get("REJECTION", {}).get("total", 0)
        report_lines.append(
            f"| {r['symbol']} | {r['total_fvgs']} | {c_cons} | {c_exp} | {c_rej} |"
        )
    report_lines.append("")
    report_lines.append("## Toplu İstatistik")
    report_lines.append("")
    report_lines.append(
        "| Kategori | FVG | Mit% | Inv% | Cont10% | Cont40% | AvgBar | RR_W% | Exp | NoFill% |"
    )
    report_lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for cat in ["CONSOLIDATION", "EXPANSION", "REJECTION"]:
        a = agg.get(cat, {})
        t = a.get("total", 0)
        if t == 0:
            continue
        mit_rate = a["mitigated"] / t * 100
        inv_rate = a["invalidated"] / t * 100
        cont10_rate = (
            a.get("continued_10", 0) / a["mitigated"] * 100 if a["mitigated"] > 0 else 0
        )
        cont40_rate = (
            a.get("continued_40", 0) / a["mitigated"] * 100 if a["mitigated"] > 0 else 0
        )
        avg_bar = (
            sum(a["bars_to_mitigate"]) / len(a["bars_to_mitigate"])
            if a["bars_to_mitigate"]
            else 0
        )
        rr_total = a["rr_wins"] + a["rr_losses"]
        rr_wr = a["rr_wins"] / rr_total * 100 if rr_total > 0 else 0
        exp_val = cat_expectancy(a)
        nf_pct = a["no_fill"] / t * 100 if t > 0 else 0
        report_lines.append(
            f"| {cat} | {t} | {mit_rate:.1f}% | {inv_rate:.1f}% | {cont10_rate:.1f}% | {cont40_rate:.1f}% | {avg_bar:.0f} | {rr_wr:.1f}% | {exp_val:+.2f}R | {nf_pct:.1f}% |"
        )
    report_lines.append("")
    report_lines.append("## Continuation Pencere Karşılaştırması")
    report_lines.append("")
    report_lines.append("| Kategori | Cont@10 | Cont@20 | Cont@40 |")
    report_lines.append("|---|---|---|---|")
    for cat in ["CONSOLIDATION", "EXPANSION", "REJECTION"]:
        a = agg.get(cat, {})
        m = a.get("mitigated", 0)
        if m == 0:
            continue
        c10 = a.get("continued_10", 0) / m * 100
        c20 = a.get("continued_20", 0) / m * 100
        c40 = a.get("continued_40", 0) / m * 100
        report_lines.append(f"| {cat} | {c10:.1f}% | {c20:.1f}% | {c40:.1f}% |")
    report_lines.append("")
    report_lines.append("## Trade Kalitesi (R:R Simülasyonu)")
    report_lines.append("")
    report_lines.append(
        "| Kategori | Toplam Trade | Win | Loss | NoFill | NoOutcome | WR% | Expectancy |"
    )
    report_lines.append("|---|---|---|---|---|---|---|---|")
    for cat in ["CONSOLIDATION", "EXPANSION", "REJECTION"]:
        a = agg.get(cat, {})
        t = a.get("total", 0)
        if t == 0:
            continue
        w = a["rr_wins"]
        l = a["rr_losses"]
        nf = a.get("no_fill", 0)
        no = a.get("no_outcome", 0)
        rt = w + l
        wr = w / rt * 100 if rt > 0 else 0
        exp_val = cat_expectancy(a)
        report_lines.append(
            f"| {cat} | {rt} | {w} | {l} | {nf} | {no} | {wr:.1f}% | {exp_val:+.2f}R |"
        )
    report_lines.append("")
    report_lines.append("## İddia Testi")
    report_lines.append("")
    report_lines.append(
        f"- Mitigation: CONS={c_mit:.1f}% EXP={e_mit:.1f}% REJ={r_mit:.1f}%"
    )
    report_lines.append(
        f"- Continuation 10-bar: CONS={c_cont10:.1f}% EXP={e_cont10:.1f}% REJ={r_cont10:.1f}%"
    )
    report_lines.append(
        f"- Continuation 40-bar: CONS={c_cont40:.1f}% EXP={e_cont40:.1f}% REJ={r_cont40:.1f}%"
    )
    report_lines.append(f"- No-Fill: CONS={c_nf:.1f}% EXP={e_nf:.1f}% REJ={r_nf:.1f}%")
    report_lines.append("")

    # İddia sonucu
    if c_mit >= e_mit >= r_mit and c_cont10 >= e_cont10 >= r_cont10:
        report_lines.append(
            "**✅ İddia TUTUYOR (güçlü):** Sıralama Consolidation > Expansion > Rejection tüm metriklerde korunuyor."
        )
    elif c_mit >= e_mit >= r_mit:
        report_lines.append(
            "**⚠️ Kısmen:** Mitigation sıralaması doğru ama continuation sıralaması beklendiği gibi değil."
        )
    elif c_mit >= r_mit and c_mit >= e_mit:
        report_lines.append(
            f"**⚠️ Kısmen:** Consolidation mitigasyonu en yüksek ({c_mit:.1f}%) ama Expansion/Rejection sıralaması beklendiği gibi değil."
        )
    else:
        report_lines.append(
            "**❌ İddia TUTMUYOR:** Beklenen Consolidation > Expansion > Rejection sıralaması gözlenmedi."
        )

    # Session sanity check
    report_lines.append("")
    report_lines.append("## Session Filtresi Sanity Check")
    report_lines.append("")
    if all_hours:
        total_acc = sum(all_hours.values())
        _sh, _eh = SESSION_HOURS["start"], SESSION_HOURS["end"]
        _spans_midnight = _sh > _eh
        in_range = 0
        # Only show session hours
        session_entries = []
        for h_str in sorted(all_hours.keys()):
            h = int(h_str)
            cnt = all_hours[h_str]
            if _spans_midnight:
                is_in = h >= _sh or h < _eh
            else:
                is_in = _sh <= h < _eh
            if is_in:
                in_range += cnt
                session_entries.append(f"{h:02d}:00={cnt}")
        report_lines.append(
            f"**Kabul edilen barların saat dağılımı (toplam {total_acc} bar):**"
        )
        report_lines.append("")
        report_lines.append(", ".join(session_entries[:16]))
        report_lines.append("")
        if total_acc == in_range:
            report_lines.append(
                "✅ **Tüm barlar session penceresinde.** Filtre doğru çalışıyor."
            )
        else:
            report_lines.append(f"⚠️ **{total_acc - in_range} bar session dışında!**")
    else:
        report_lines.append("*Saat verisi toplanamadı.*")

    # Bootstrap CI for REJECTION
    report_lines.append("")
    report_lines.append("## Bootstrap CI — REJECTION")
    report_lines.append("")
    report_lines.append(
        f"**{N_BOOTSTRAP} resample, %95 güven aralığı, seed={BOOTSTRAP_SEED}**"
    )
    report_lines.append("")
    rej_r = agg.get("REJECTION", {})
    rej_profits = rej_r.get("profits", [])
    rej_wins = rej_r.get("win_flags", [])
    if len(rej_profits) >= 3:
        wr_lo, wr_hi, wr_mean = bootstrap_ci(rej_wins)
        exp_lo, exp_hi, exp_mean = bootstrap_ci(rej_profits)
        report_lines.append(
            f"- WR: {wr_mean*100:.1f}% [%95 CI: {wr_lo*100:.1f}% — {wr_hi*100:.1f}%]"
        )
        report_lines.append(
            f"- Expectancy: {exp_mean:+.2f}R [%95 CI: {exp_lo:+.2f}R — {exp_hi:+.2f}R]"
        )
        # Non-monotonic
        rej_m = max(rej_r.get("mitigated", 1), 1)
        c10 = rej_r.get("continued_10", 0) / rej_m * 100
        c20 = rej_r.get("continued_20", 0) / rej_m * 100
        c40 = rej_r.get("continued_40", 0) / rej_m * 100
        report_lines.append("")
        report_lines.append("**Non-Monotonik Cont@20 Check:**")
        report_lines.append(f"- Cont@10: {c10:.1f}%")
        report_lines.append(f"- Cont@20: {c20:.1f}%")
        report_lines.append(f"- Cont@40: {c40:.1f}%")
        wr_diff = abs(wr_hi - wr_lo)
        if wr_diff > 10:
            report_lines.append(
                f"- ⚠️ WR CI genişliği {wr_diff:.1f}% — Cont@20 dalgalanma gürültüden kaynaklanıyor olabilir."
            )
        else:
            report_lines.append(
                f"- ✅ WR CI genişliği {wr_diff:.1f}% — Cont@20 sapma güvenilir pattern olabilir."
            )
    else:
        report_lines.append(
            f"Yetersiz REJECTION örneği ({len(rej_profits)}). Bootstrap atlanıyor."
        )

    # Commission section
    report_lines.append("")
    report_lines.append("## Komisyon Sonrası Expectancy")
    report_lines.append("")
    report_lines.append(
        f"**Taker fee: %{FEE_TAKER*100:.2f} (round-trip %{FEE_TAKER*200:.2f})**"
    )
    report_lines.append("")
    report_lines.append("| Kategori | Brüt Exp | Net Exp | Fark |")
    report_lines.append("|---|---|---|---|")
    for cat in ["CONSOLIDATION", "EXPANSION", "REJECTION"]:
        a = agg.get(cat, {})
        profs = a.get("profits", [])
        if not profs:
            continue
        rt = a.get("rr_wins", 0) + a.get("rr_losses", 0) + a.get("no_outcome", 0)
        gross_exp = (a.get("rr_wins", 0) * 2 - a.get("rr_losses", 0) * 1) / max(rt, 1)
        net_exp = sum(profs) / len(profs)
        report_lines.append(
            f"| {cat} | {gross_exp:+.3f}R | {net_exp:+.3f}R | {net_exp - gross_exp:+.3f}R |"
        )

    # ATR Self-Reference Proof
    report_lines.append("")
    report_lines.append("## ATR Self-Reference Kanıtı")
    report_lines.append("")
    report_lines.append("**C3 öncesi ATR (sınıflamada kullanılan) vs C3 sonrası ATR**")
    report_lines.append("")
    report_lines.append(
        "| # | Kategori | Yön | ATR (C3 öncesi) | TR(C3) | ATR (C3 sonrası) | Fark |"
    )
    report_lines.append("|---|---|---|---|---|---|---|")
    all_fvgs = [f for r in results if r for f in r["fvgs"]]
    if len(all_fvgs) >= 5:
        rng = random.Random(BOOTSTRAP_SEED)
        chosen = rng.sample(all_fvgs, min(5, len(all_fvgs)))
        for i, f in enumerate(chosen, 1):
            diff_label = (
                "SAME" if abs(f["atr_used"] - f["atr_after_c3"]) < 0.0001 else "FARKLI"
            )
            report_lines.append(
                f"| {i} | {f['category']} | {f['direction']} | {f['atr_used']:.4f} | {f['tr_of_c3']:.4f} | {f['atr_after_c3']:.4f} | {diff_label} |"
            )
    else:
        report_lines.append("| Yetersiz FVG — atlanıyor | | | | | |")

    # Coin korelasyonu
    report_lines.append("")
    report_lines.append("## Coin Korelasyonu & Efektif Örneklem")
    report_lines.append("")
    report_lines.append("| Coin | Toplam FVG | Eşsiz Gün | Saat Dilimleri |")
    report_lines.append("|---|---|---|---|")
    coin_hour = {}
    coin_days = {}
    for r in results:
        if r is None:
            continue
        sym = r["symbol"]
        ch = defaultdict(int)
        cd = set()
        for f in r["fvgs"]:
            hr = f.get("fvg_hour", -1)
            ch[hr] += 1
            ts = f.get("timestamp", 0)
            if ts:
                dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).date()
                cd.add(dt)
        coin_hour[sym] = dict(ch)
        coin_days[sym] = len(cd)
    for sym in sorted(coin_hour.keys()):
        ch = coin_hour[sym]
        total = sum(ch.values())
        days = coin_days[sym]
        hours_str = ", ".join(f"{h:02d}:00({ch[h]})" for h in sorted(ch.keys()))
        report_lines.append(f"| {sym} | {total} | {days} | {hours_str} |")
    avg_days = sum(coin_days.values()) / len(coin_days)
    report_lines.append(f"| **Ortalama** | | **{avg_days:.0f}** | |")
    min_days = min(coin_days.values())
    report_lines.append(f"| **Min** | | **{min_days}** | |")

    report_lines.append("")
    report_lines.append("---")
    report_lines.append(
        "*Auto-generated by analyze_fvg_3rd_candle.py (düzeltilmiş sürüm)*"
    )

    report_path = os.path.join(
        os.path.dirname(__file__), "..", "reports", "fvg_3rd_candle_report.md"
    )
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print(f"\n  Rapor: {report_path}")


def main():
    t0 = time.time()
    print("=" * 100)
    print("  FVG 3. MUM SINIFLAMASI — BACKTEST")
    print(
        f"  Session: {SESSION_NAME} [{SESSION_HOURS['start']:02d}:00-{SESSION_HOURS['end']:02d}:00]"
    )
    print(f"  Coinler: {', '.join(SYMBOLS_TO_TEST)}")
    print("=" * 100)

    results = []
    for sym in SYMBOLS_TO_TEST:
        print(f"\n  [{sym}] Analiz basliyor...")
        result = analyze_symbol(sym)
        if result is None:
            print(f"    [{sym}] VERI DOSYASI YOK")
            continue
        results.append(result)
        print(f"    [{sym}] {result['total_fvgs']} FVG bulundu")

    print(f"\n  Toplam sure: {time.time() - t0:.0f}s")

    # Aggregated stats (for MD report)
    from collections import defaultdict

    agg = defaultdict(
        lambda: {
            "total": 0,
            "mitigated": 0,
            "invalidated": 0,
            "continued": 0,
            "continued_10": 0,
            "continued_20": 0,
            "continued_40": 0,
            "bars_to_mitigate": [],
            "rr_wins": 0,
            "rr_losses": 0,
            "no_fill": 0,
            "no_outcome": 0,
            "profits": [],
            "win_flags": [],
        }
    )
    for r in results:
        if r is None:
            continue
        for cat, data in r["category_outcomes"].items():
            a = agg[cat]
            a["total"] += data["total"]
            a["mitigated"] += data["mitigated"]
            a["invalidated"] += data["invalidated"]
            a["continued"] += data.get("continued", 0)
            a["continued_10"] += data.get("continued_10", 0)
            a["continued_20"] += data.get("continued_20", 0)
            a["continued_40"] += data.get("continued_40", 0)
            a["bars_to_mitigate"].extend(data["bars_to_mitigate"])
            a["rr_wins"] += data["rr_wins"]
            a["rr_losses"] += data["rr_losses"]
            a["no_fill"] += data.get("no_fill", 0)
            a["no_outcome"] += data.get("no_outcome", 0)
            a["profits"].extend(data.get("profits", []))
            a["win_flags"].extend(data.get("win_flags", []))

    # Aggregate session hour data for sanity check
    all_hours = defaultdict(int)
    for r in results:
        if r is None:
            continue
        for h_str, cnt in r.get("session_hour_buckets", {}).items():
            all_hours[h_str] += cnt

    print_report(results)
    write_md_report(results, agg, dict(all_hours))


# NOTE: agg is defined in print_report scope; need to hoist for MD report
# We re-define agg in main scope after calling print_report
# Actually let me just compute agg in main as well.

if __name__ == "__main__":
    main()
