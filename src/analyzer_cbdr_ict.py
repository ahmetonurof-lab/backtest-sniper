"""
analyzer_cbdr_ict.py — ICT-defined CBDR / Asia Range window tests.
Same V3 entry logic, no session phases — just range window vs open trading.
"""
import argparse
import csv
import os
import sys
import time
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coins_config import get_config, COINS
from fvg import detect_fvgs
from models import Bar
from retrace_state import RetraceStateMachine
from analyzer_v3 import load_data, resample_15m, fvg_close_confirmed
from session import DailyBias

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class IctRangeState:
    """Range window state machine with configurable UTC hours."""

    def __init__(self, range_start_hour: int, range_end_hour: int):
        self.range_start = range_start_hour
        self.range_end = range_end_hour
        self.spans_midnight = range_start_hour > range_end_hour

        self.range_high = 0.0
        self.range_low = float("inf")
        self.range_locked = False
        self.range_day = ""
        self.daily_bias = DailyBias.NEUTRAL
        self.sweep_confirmed = False
        self.sweep_direction: str | None = None
        self.sweep_level: float | None = None
        self.trades_today = 0

    def _in_window(self, h: int) -> bool:
        if self.spans_midnight:
            return h >= self.range_start or h < self.range_end
        return self.range_start <= h < self.range_end

    def _day_key(self, dt: datetime, h: int) -> str:
        today = dt.strftime("%Y-%m-%d")
        if h >= self.range_start:
            return today
        return (dt - timedelta(days=1)).strftime("%Y-%m-%d")

    def update(self, dt: datetime, open: float, high: float, low: float, close: float, atr: float = 0):
        h = dt.hour
        rk = self._day_key(dt, h)

        if rk != self.range_day:
            self._reset()
            self.range_day = rk

        if self._in_window(h) and not self.range_locked:
            self._track_body(open, close)

        if not self._in_window(h) and not self.range_locked and self.range_high > 0:
            self.range_locked = True

        if self.range_locked and not self.sweep_confirmed:
            self._check_sweep(high, low, close, atr)

    def _reset(self):
        self.range_high = 0.0
        self.range_low = float("inf")
        self.range_locked = False
        self.daily_bias = DailyBias.NEUTRAL
        self.sweep_confirmed = False
        self.sweep_direction = None
        self.sweep_level = None
        self.trades_today = 0

    def _track_body(self, open: float, close: float):
        bh = max(open, close)
        bl = min(open, close)
        if bh > self.range_high:
            self.range_high = bh
        if bl < self.range_low:
            self.range_low = bl

    def _check_sweep(self, high: float, low: float, close: float, atr: float = 0):
        tol = atr * 0.5 if atr > 0 else 10.0

        if high > self.range_high + tol:
            if close < self.range_high:
                self.sweep_confirmed = True
                self.sweep_direction = "bearish"
                self.sweep_level = self.range_high
                self.daily_bias = DailyBias.BEARISH
                return

        if low < self.range_low - tol:
            if close > self.range_low:
                self.sweep_confirmed = True
                self.sweep_direction = "bullish"
                self.sweep_level = self.range_low
                self.daily_bias = DailyBias.BULLISH


RANGE_CONFIGS = {
    "real_cbdr": {"name": "Real CBDR (14:00-20:00 NY)", "start": 19, "end": 1},
    "asia_range": {"name": "Asia Range (20:00-00:00 NY)", "start": 1, "end": 5},
}


def run_bt(symbol: str, cfg: dict, range_cfg: dict):
    csv_file = os.path.join(os.path.dirname(__file__), "data", f"{symbol}_1m.csv")
    if not os.path.isfile(csv_file):
        return None

    mfs = cfg["min_fvg_size"]
    ic = cfg["initial_capital"]
    rpt = cfg["risk_per_trade"]
    rp = cfg.get("risk_primary", rpt)
    sam = cfg["sl_atr_mult"]
    tpr = cfg["tp_rr"]
    fbm = cfg["fvg_buffer_mult"]

    ATM = cfg.get("atr_trail_mult", 0.25)
    TMM = cfg.get("trail_min_move_mult", 0.20)
    BERM = cfg.get("be_risk_mult", 1.0)
    BESP = cfg.get("be_spread_pts", 0.0)
    W = 500

    b1 = load_data(csv_file)
    b15 = resample_15m(b1)
    if not b15:
        return None

    rs = IctRangeState(range_cfg["start"], range_cfg["end"])
    rsm = RetraceStateMachine(min_fvg_size=mfs)
    trades = []
    active = []
    wins = []
    losses = []

    def _record_pnl(t):
        if t["pnl"] > 0:
            wins.append(t)
        else:
            losses.append(t)

    for sb in range(W, len(b15)):
        chunk = b15[sb - W: sb + 1]
        cur = b15[sb]
        atr = max(cur.range, cur.close * 0.0001)

        try:
            edt = datetime.fromtimestamp(cur.timestamp / 1000, tz=timezone.utc)
        except Exception:
            continue

        rs.update(edt, cur.open, cur.high, cur.low, cur.close, atr)

        if rs.sweep_confirmed and rsm.state_name == "IDLE":
            rsm.on_sweep(direction=rs.sweep_direction or "bullish",
                         level=rs.sweep_level or 0.0, bar_index=cur.index)

        if rsm.state_name == "SWEEP_DETECTED":
            rsm.on_sweep_confirmed(chunk, cur)

        if rsm.can_trigger() and not active:
            sd = rsm.direction
            db = rs.daily_bias

            if (sd == "bullish" and db == DailyBias.BEARISH) or \
               (sd == "bearish" and db == DailyBias.BULLISH) or \
               db == DailyBias.NEUTRAL:
                rsm.reset()
                continue

            h = edt.hour
            if rs._in_window(h):
                rsm.reset()
                continue

            side = "long" if sd == "bullish" else "short"
            ep = cur.close
            rp2 = atr * sam
            tf = rsm.trigger_fvg

            MSDM = 2.0
            FBF = 0.10

            if side == "long":
                if tf:
                    fh = tf.top - tf.bottom
                    if fh <= 0:
                        sl = ep - rp2 * 2
                    else:
                        ab = max(fh * FBF, max(rp2 * 0.1, min(fh * 0.25, rp2 * fbm)))
                        sl = tf.bottom - ab
                else:
                    sl = ep - rp2 * 2
                rd = abs(sl - ep)
                if tf and rd > rp2 * MSDM:
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
                        ab = max(fh * FBF, max(rp2 * 0.1, min(fh * 0.25, rp2 * fbm)))
                        sl = tf.top + ab
                else:
                    sl = ep + rp2 * 2
                rd = abs(sl - ep)
                if tf and rd > rp2 * MSDM:
                    sl = ep + rp2 * 2
                    rd = abs(sl - ep)
                if rd <= 0:
                    sl = ep + rp2 * 2
                    rd = abs(sl - ep)
                tp = ep - rd * tpr

            if rd < atr * 0.1:
                rsm.reset()
                continue
            qty = (ic * rp) / rd if rd > 0 else 0
            if qty <= 0:
                rsm.reset()
                continue

            active.append({"entry_bar": sb, "entry_price": ep, "sl": sl, "tp": tp,
                           "qty": qty, "side": side, "trigger_fvg": tf,
                           "initial_sl": sl, "initial_tp": tp, "trailing_count": 0})
            rs.trades_today += 1
            rsm.reset()

        if active and cur.is_closed:
            for t in active:
                if t.get("closed"):
                    continue
                if t.get("trailing_count", 0) == 0:
                    side2 = t["side"]
                    entry2 = t["entry_price"]
                    rpt2 = abs(t["initial_sl"] - entry2)
                    threshold2 = rpt2 * BERM
                    be_sl2 = entry2 + BESP if side2 == "long" else entry2 - BESP
                    if side2 == "long":
                        if cur.high >= entry2 + threshold2 and t["sl"] < be_sl2:
                            t["sl"] = be_sl2
                            t["trailing_count"] = 1
                    else:
                        if cur.low <= entry2 - threshold2 and t["sl"] > be_sl2:
                            t["sl"] = be_sl2
                            t["trailing_count"] = 1

            tc = chunk[:-1]
            cfvgs = detect_fvgs(tc, lookback=min(50, len(tc)), timeframe="15m", min_fvg_size=mfs)

            for t in active:
                if t.get("closed"):
                    continue
                side2 = t["side"]
                csl = t["sl"]
                ctp = t["tp"]
                rpt2 = abs(t["initial_sl"] - t["entry_price"])
                ltc = 0
                upd = False

                for fvg in cfvgs:
                    if side2 == "long" and fvg.direction != "bullish":
                        continue
                    if side2 == "short" and fvg.direction != "bearish":
                        continue
                    if not fvg_close_confirmed(fvg, tc):
                        continue
                    ab2 = atr * ATM
                    if side2 == "long":
                        ns = fvg.bottom - ab2
                        if ns > csl and (ns - csl) > rpt2 * TMM:
                            sd2 = ns - csl
                            csl = ns
                            ctp += sd2
                            ltc += 1
                            upd = True
                    else:
                        ns = fvg.top + ab2
                        if ns < csl and (csl - ns) > rpt2 * TMM:
                            sd2 = csl - ns
                            csl = ns
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
                    t["result"] = "SL"
                    t["closed"] = True
                    ex = True
                elif cur.high >= t["tp"]:
                    t["exit_price"] = t["tp"]
                    t["exit_bar"] = sb
                    t["result"] = "TP"
                    t["closed"] = True
                    ex = True
            else:
                if cur.high >= t["sl"]:
                    t["exit_price"] = t["sl"]
                    t["exit_bar"] = sb
                    t["result"] = "SL"
                    t["closed"] = True
                    ex = True
                elif cur.low <= t["tp"]:
                    t["exit_price"] = t["tp"]
                    t["exit_bar"] = sb
                    t["result"] = "TP"
                    t["closed"] = True
                    ex = True
            if ex:
                diff = (t["exit_price"] - t["entry_price"]) if t["side"] == "long" else (t["entry_price"] - t["exit_price"])
                t["pnl"] = round(diff * t["qty"], 2)
                rsk = abs(t["initial_sl"] - t["entry_price"])
                t["rr"] = round(diff / rsk if rsk > 0 else 0, 2)
                trades.append(t)
                _record_pnl(t)
            else:
                sa.append(t)
        active = sa

    if b15:
        lp = b15[-1].close
        for t in active:
            if not t.get("closed"):
                t["exit_price"] = lp
                t["exit_bar"] = len(b15) - 1
                t["result"] = "OPEN"
                t["closed"] = True
                diff = (lp - t["entry_price"]) if t["side"] == "long" else (t["entry_price"] - lp)
                t["pnl"] = round(diff * t["qty"], 2)
                rsk = abs(t["initial_sl"] - t["entry_price"])
                t["rr"] = round(diff / rsk if rsk > 0 else 0, 2)
                trades.append(t)
                _record_pnl(t)

    m = {"symbol": symbol, "total_trades": len(trades)}
    if trades:
        tp2 = sum(t["pnl"] for t in trades)
        wr = len(wins) / len(trades) * 100
        dpk = ic
        dm = 0.0
        run = ic
        for t in trades:
            run += t["pnl"]
            dpk = max(dpk, run)
            dd = (dpk - run) / dpk * 100 if dpk > 0 else 0
            dm = max(dm, dd)
        wt2 = sum(t["rr"] for t in wins) / len(wins) if wins else 0
        lt2 = sum(t["rr"] for t in losses) / len(losses) if losses else 0
        pf = abs(wt2 / lt2) if wt2 > 0 and lt2 != 0 else 0
        m.update({"total_pnl": tp2, "wr": wr, "max_dd": dm, "profit_factor": pf})

        longs = [t for t in trades if t["side"] == "long"]
        shorts = [t for t in trades if t["side"] == "short"]
        m["long_trades"] = len(longs)
        m["short_trades"] = len(shorts)
        m["long_pnl"] = sum(t["pnl"] for t in longs) if longs else 0
        m["short_pnl"] = sum(t["pnl"] for t in shorts) if shorts else 0
        m["long_wr"] = (len([t for t in longs if t["pnl"] > 0]) / len(longs) * 100) if longs else 0
        m["short_wr"] = (len([t for t in shorts if t["pnl"] > 0]) / len(shorts) * 100) if shorts else 0
        m["avg_rr"] = sum(t["rr"] for t in trades) / len(trades)
        m["tp_count"] = sum(1 for t in trades if t["result"] == "TP")
        m["sl_count"] = sum(1 for t in trades if t["result"] == "SL")
        m["open_count"] = sum(1 for t in trades if t["result"] == "OPEN")

    return m


def main():
    parser = argparse.ArgumentParser(description="ICT CBDR/Asia Range Test")
    parser.add_argument("--symbol", type=str, help="Single coin")
    parser.add_argument("--all", action="store_true", help="All configured coins")
    parser.add_argument("--mode", type=str, choices=list(RANGE_CONFIGS.keys()), default="real_cbdr",
                        help="Range configuration to test")
    args = parser.parse_args()

    symbols = [args.symbol] if args.symbol else COINS if args.all else []

    if not symbols:
        parser.print_help()
        return

    t0 = time.time()
    results = {}

    for mode_key, mode_cfg in RANGE_CONFIGS.items():
        print(f"\n{'='*120}")
        print(f"  TEST: {mode_cfg['name']}  |  Range window: {mode_cfg['start']:02d}:00-{mode_cfg['end']:02d}:00 UTC")
        print(f"{'='*120}")
        results[mode_key] = {}
        total_pnl = 0.0

        for sym in symbols:
            ts = time.time()
            cfg = get_config(sym)
            m = run_bt(sym, cfg, mode_cfg)
            if m:
                results[mode_key][sym] = m
                total_pnl += m["total_pnl"]
                print(f"  {sym:>10} | {m['total_trades']:>4} islem | PnL={m['total_pnl']:>+9.0f} | "
                      f"WR={m['wr']:>5.1f}% | DD={m['max_dd']:>4.1f}% | PF={m['profit_factor']:>4.2f} | "
                      f"{time.time()-ts:.0f}s")
            else:
                print(f"  {sym:>10} | data yok")
        print(f"  {'TOPLAM':>10} | {'':>4}      | PnL={total_pnl:>+9.0f}")

    print(f"\n{'='*130}")
    print(f"  KARSILASTIRMA: REAL CBDR vs ASIA RANGE")
    print(f"{'='*130}")
    h = f"  {'Coin':<10} {'C.Islm':>5} {'C.PnL':>10} {'C.WR':>6} {'C.DD':>5} {'C.PF':>5}"
    h += f" {'A.Islm':>5} {'A.PnL':>10} {'A.WR':>6} {'A.DD':>5} {'A.PF':>5}"
    h += f" {'PnL Fark':>9} {'WR Fark':>6}"
    print(h)
    print("  " + "-" * 110)

    total_c_pnl = 0.0
    total_a_pnl = 0.0
    for sym in sorted(symbols):
        c = results.get("real_cbdr", {}).get(sym, {})
        a = results.get("asia_range", {}).get(sym, {})
        if not c or not a:
            continue
        dpnl = c["total_pnl"] - a["total_pnl"]
        dwr = c["wr"] - a["wr"]
        print(f"  {sym:<10} {c.get('total_trades',0):>5} {c.get('total_pnl',0):>+10.0f} "
              f"{c.get('wr',0):>5.1f}% {c.get('max_dd',0):>4.1f}% {c.get('profit_factor',0):>4.2f} "
              f"{a.get('total_trades',0):>5} {a.get('total_pnl',0):>+10.0f} "
              f"{a.get('wr',0):>5.1f}% {a.get('max_dd',0):>4.1f}% {a.get('profit_factor',0):>4.2f} "
              f"{dpnl:>+9.0f} {dwr:>+5.1f}%")
        total_c_pnl += c.get("total_pnl", 0)
        total_a_pnl += a.get("total_pnl", 0)

    print("  " + "-" * 110)
    print(f"  {'TOPLAM':<10} {'':>5} {total_c_pnl:>+10.0f} {'':>6} {'':>5} {'':>5}"
          f" {'':>5} {total_a_pnl:>+10.0f} {'':>6} {'':>5} {'':>5}"
          f" {total_c_pnl - total_a_pnl:>+9.0f} {'':>6}")

    print(f"\n  Toplam sure: {time.time()-t0:.0f}s")

    # Save detailed CSV
    report_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
    os.makedirs(report_dir, exist_ok=True)
    csv_path = os.path.join(report_dir, "ict_cbdr_vs_asia.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "mode", "trades", "pnl", "wr", "max_dd", "pf",
                     "long_trades", "short_trades", "long_pnl", "short_pnl",
                     "long_wr", "short_wr", "avg_rr", "tp", "sl", "open"])
        for mode_key in RANGE_CONFIGS:
            for sym in sorted(symbols):
                m = results.get(mode_key, {}).get(sym)
                if m:
                    w.writerow([sym, mode_key,
                                m.get("total_trades", 0), round(m.get("total_pnl", 0), 2),
                                round(m.get("wr", 0), 1), round(m.get("max_dd", 0), 1),
                                round(m.get("profit_factor", 0), 2),
                                m.get("long_trades", 0), m.get("short_trades", 0),
                                round(m.get("long_pnl", 0), 2), round(m.get("short_pnl", 0), 2),
                                round(m.get("long_wr", 0), 1), round(m.get("short_wr", 0), 1),
                                round(m.get("avg_rr", 0), 2), m.get("tp_count", 0),
                                m.get("sl_count", 0), m.get("open_count", 0)])
    print(f"\n  Detayli rapor: {csv_path}")


if __name__ == "__main__":
    main()
