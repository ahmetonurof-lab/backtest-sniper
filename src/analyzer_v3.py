"""
analyzer_v3.py — Aggressive Multi-Entry Trend Rider.
Unlimited primary entries per day. No retrade, no fallback.
All imports resolve from sniper/src via sys.path.
"""
# ruff: noqa: E402, E704, E701, E702, F401, F541 — path manipulation + legacy style
import argparse
import csv
import os
import sys
from datetime import datetime, timezone

os.environ["SNIPER_OUTPUT_DIR"] = os.path.join(os.path.dirname(__file__), "..", "output")
_SNIPER_SRC = os.path.join(os.path.dirname(__file__), "..", "..", "sniper", "src")
if _SNIPER_SRC not in sys.path:
    sys.path.insert(0, _SNIPER_SRC)

import config as cfg
from fvg import detect_fvgs
from indicators import calculate_true_range, update_atr
from models import Bar, ATR_PERIOD
from retrace_state import RetraceStateMachine
from session import DailyBias, SessionPhase, SessionState, detect_phase_from_timestamp

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_data(filepath):
    """CSV'den bar verisi yukle. UTC normalize (DST koruma)."""
    bars = []
    with open(filepath, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            ts = int(datetime.strptime(row["open_time"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp() * 1000)
            bars.append(Bar(index=i, open=float(row["open"]), high=float(row["high"]),
                            low=float(row["low"]), close=float(row["close"]),
                            volume=float(row["volume"]), is_closed=True, timestamp=ts))
    return bars


def resample_15m(bars_1m):
    m15 = []
    for i in range(0, len(bars_1m), 15):
        c = bars_1m[i: i + 15]
        if len(c) < 15: break
        m15.append(Bar(index=c[0].index, open=c[0].open,
                       high=max(b.high for b in c), low=min(b.low for b in c),
                       close=c[-1].close, volume=sum(b.volume for b in c),
                       is_closed=True, timestamp=c[0].timestamp))
    return m15


def fvg_close_confirmed(fvg, all_bars: list) -> bool:
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


def run_for_symbol(symbol: str, session_hours: dict = None):
    """
    V3 backtest for one symbol.
    session_hours: {'start': int, 'end': int} — SessionState'a parametre.
                   None = default (22-02).
    """
    data_file = os.path.join(os.path.dirname(__file__), "data", "daily", f"{symbol}_1m_raw.csv")
    if not os.path.isfile(data_file):
        print(f"[SKIP] {symbol} — data file not found: {data_file}")
        return
    csv_file = data_file

    initial_capital = cfg.INITIAL_BALANCE
    risk_per_trade = cfg.RISK_PER_TRADE
    sl_atr_mult = cfg.SL_ATR_MULT
    tp_rr = cfg.TP_RR
    fvg_buffer_mult = cfg.FVG_BUFFER_MULT
    ATR_TRAIL_MULT_V3 = cfg.ATR_TRAIL_MULT
    TRAIL_MIN_MOVE_MULT_V3 = cfg.TRAIL_MIN_MOVE_MULT
    BE_RISK_MULT_V3 = cfg.BE_RISK_MULT
    BE_SPREAD_PTS_V3 = cfg.BE_SPREAD_PTS
    FVG_WICK_RATIO_MAX = cfg.FVG_WICK_RATIO_MAX
    FVG_MIN_SIZE_ATR_MULT = cfg.FVG_MIN_SIZE_ATR_MULT

    print(f"\nLoading {symbol}...")
    bars_1m = load_data(csv_file)
    bars_15m = resample_15m(bars_1m)
    print(f"  {symbol} | 1m: {len(bars_1m):,} bars | 15m: {len(bars_15m):,} bars")

    if session_hours:
        ss = SessionState(start_hour=session_hours['start'], end_hour=session_hours['end'])
    else:
        ss = SessionState()  # default 22-02
    rsm = RetraceStateMachine(max_wick_ratio=FVG_WICK_RATIO_MAX)
    trades = []
    active_trades = []
    WINDOW = 500

    pipeline = {
        "cbdr_locked": 0, "sweep_detected": 0, "sweep_fed": 0,
        "fvg_scanned": 0, "wick_rejection": 0, "trigger_ready": 0,
        "filter_bias": 0, "filter_session": 0, "new_entry": 0,
        "trailing_sl_updates": 0, "trailing_tp_updates": 0, "closed": 0,
    }
    total_signals = 0
    rejected_other = 0

    atr_val: float = 0.0
    prev_close: float = bars_15m[0].open
    for bar in bars_15m[1:WINDOW]:
        tr = calculate_true_range(bar, prev_close)
        atr_val = update_atr(atr_val if atr_val > 0 else None, tr)
        prev_close = bar.close

    for scan_bar in range(WINDOW, len(bars_15m)):
        chunk = bars_15m[scan_bar - WINDOW: scan_bar + 1]
        current = bars_15m[scan_bar]

        tr = calculate_true_range(current, prev_close)
        atr_val = update_atr(atr_val if atr_val > 0 else None, tr)
        prev_close = current.close

        try:
            entry_dt = datetime.fromtimestamp(current.timestamp / 1000, tz=timezone.utc)
        except Exception:
            continue

        ss.update(entry_dt, current.open, current.high, current.low, current.close, atr_val)
        if ss.cbdr_locked: pipeline["cbdr_locked"] += 1
        if ss.sweep_confirmed: pipeline["sweep_detected"] += 1

        if ss.sweep_confirmed and rsm.state_name == "IDLE":
            pipeline["sweep_fed"] += 1
            rsm.on_sweep(direction=ss.sweep_direction or "bullish",
                         level=ss.sweep_level or 0.0, bar_index=None)

        if rsm.state_name == "SWEEP_DETECTED":
            pipeline["fvg_scanned"] += 1
            rsm.on_sweep_confirmed(chunk, current, atr_val)
            if rsm.state_name == "TRIGGER_READY":
                pipeline["wick_rejection"] += 1

        if rsm.can_trigger() and not active_trades:
            pipeline["trigger_ready"] += 1
            total_signals += 1

            sweep_dir = rsm.direction
            daily_bias = ss.daily_bias

            if sweep_dir == "bullish" and daily_bias == DailyBias.BEARISH:
                rsm.reset(); rejected_other += 1; continue
            if sweep_dir == "bearish" and daily_bias == DailyBias.BULLISH:
                rsm.reset(); rejected_other += 1; continue
            if daily_bias == DailyBias.NEUTRAL:
                rsm.reset(); rejected_other += 1; continue
            pipeline["filter_bias"] += 1

            phase = detect_phase_from_timestamp(current.timestamp)
            if phase not in (SessionPhase.NEWYORK, SessionPhase.LONDON):
                pipeline["filter_session"] += 1
                rsm.reset(); rejected_other += 1; continue

            side = "long" if sweep_dir == "bullish" else "short"
            entry_price = current.close
            risk_pts = atr_val * sl_atr_mult
            trigger_fvg = rsm.trigger_fvg

            MAX_SL_DIST_MULT_V3 = 2.0
            FVG_BUFFER_MIN_FACTOR_V3 = 0.10

            if side == "long":
                if trigger_fvg:
                    fvg_height = trigger_fvg.top - trigger_fvg.bottom
                    if fvg_height <= 0:
                        sl = entry_price - risk_pts * 2
                    else:
                        adaptive_buf = max(
                            fvg_height * FVG_BUFFER_MIN_FACTOR_V3,
                            max(risk_pts * 0.1, min(fvg_height * 0.25, risk_pts * fvg_buffer_mult)),
                        )
                        sl = trigger_fvg.bottom - adaptive_buf
                else:
                    sl = entry_price - risk_pts * 2
                risk_dist = abs(sl - entry_price)
                if trigger_fvg and risk_dist > risk_pts * MAX_SL_DIST_MULT_V3:
                    sl = entry_price - risk_pts * 2
                    risk_dist = abs(sl - entry_price)
                if risk_dist <= 0:
                    sl = entry_price - risk_pts * 2
                    risk_dist = abs(sl - entry_price)
                tp = entry_price + risk_dist * tp_rr
            else:
                if trigger_fvg:
                    fvg_height = trigger_fvg.top - trigger_fvg.bottom
                    if fvg_height <= 0:
                        sl = entry_price + risk_pts * 2
                    else:
                        adaptive_buf = max(
                            fvg_height * FVG_BUFFER_MIN_FACTOR_V3,
                            max(risk_pts * 0.1, min(fvg_height * 0.25, risk_pts * fvg_buffer_mult)),
                        )
                        sl = trigger_fvg.top + adaptive_buf
                else:
                    sl = entry_price + risk_pts * 2
                risk_dist = abs(sl - entry_price)
                if trigger_fvg and risk_dist > risk_pts * MAX_SL_DIST_MULT_V3:
                    sl = entry_price + risk_pts * 2
                    risk_dist = abs(sl - entry_price)
                if risk_dist <= 0:
                    sl = entry_price + risk_pts * 2
                    risk_dist = abs(sl - entry_price)
                tp = entry_price - risk_dist * tp_rr

            min_risk_dist = atr_val * 0.1
            if risk_dist < min_risk_dist: continue
            qty = (initial_capital * risk_per_trade) / risk_dist if risk_dist > 0 else 0
            if qty <= 0: rsm.reset(); rejected_other += 1; continue

            new_trade = {
                "entry_bar": scan_bar, "entry_price": entry_price, "sl": sl, "tp": tp,
                "qty": qty, "side": side, "trigger_fvg": trigger_fvg,
                "initial_sl": sl, "initial_tp": tp, "trailing_count": 0,
            }
            active_trades.append(new_trade)
            pipeline["new_entry"] += 1
            ss.trades_today += 1
            rsm.reset()

        if active_trades and current.is_closed:
            for trade in active_trades:
                if trade.get("closed"): continue
                if trade.get("trailing_count", 0) > 0: continue
                side = trade["side"]
                entry = trade["entry_price"]
                risk_pts_t = abs(trade["initial_sl"] - entry)
                threshold = risk_pts_t * BE_RISK_MULT_V3
                be_sl = entry + BE_SPREAD_PTS_V3 if side == "long" else entry - BE_SPREAD_PTS_V3
                if side == "long":
                    if current.high < entry + threshold or trade["sl"] >= be_sl: continue
                else:
                    if current.low > entry - threshold or trade["sl"] <= be_sl: continue
                trade["sl"] = be_sl
                trade["trailing_count"] = 1
                pipeline["trailing_sl_updates"] += 1

            trail_chunk = chunk[:-1]
            min_fvg_size = max(atr_val * FVG_MIN_SIZE_ATR_MULT, 1e-8)
            current_fvgs = detect_fvgs(trail_chunk, lookback=min(50, len(trail_chunk)), timeframe="15m", min_fvg_size=min_fvg_size)

            for trade in active_trades:
                if trade.get("closed"): continue
                side = trade["side"]
                current_sl = trade["sl"]
                current_tp = trade["tp"]
                risk_pts_t = abs(trade["initial_sl"] - trade["entry_price"])
                local_trail_count = 0
                updated = False

                for fvg in current_fvgs:
                    if side == "long" and fvg.direction != "bullish": continue
                    if side == "short" and fvg.direction != "bearish": continue
                    if not fvg_close_confirmed(fvg, trail_chunk): continue

                    atr_buffer = atr_val * ATR_TRAIL_MULT_V3

                    if side == "long":
                        new_sl = fvg.bottom - atr_buffer
                        if new_sl > current_sl and (new_sl - current_sl) > risk_pts_t * TRAIL_MIN_MOVE_MULT_V3:
                            sl_diff = new_sl - current_sl
                            current_sl = new_sl
                            current_tp += sl_diff
                            local_trail_count += 1
                            updated = True
                    else:
                        new_sl = fvg.top + atr_buffer
                        if new_sl < current_sl and (current_sl - new_sl) > risk_pts_t * TRAIL_MIN_MOVE_MULT_V3:
                            sl_diff = current_sl - new_sl
                            current_sl = new_sl
                            current_tp -= sl_diff
                            local_trail_count += 1
                            updated = True

                if updated:
                    trade["sl"] = current_sl
                    trade["tp"] = current_tp
                    trade["trailing_count"] = trade.get("trailing_count", 0) + local_trail_count
                    pipeline["trailing_sl_updates"] += 1
                    pipeline["trailing_tp_updates"] += 1

        still_active = []
        for trade in active_trades:
            if trade.get("closed"): continue
            exited = False
            if trade["side"] == "long":
                if current.low <= trade["sl"]:
                    trade["exit_price"] = trade["sl"]; trade["exit_bar"] = scan_bar
                    trade["result"] = "SL"; trade["closed"] = True; exited = True
                elif current.high >= trade["tp"]:
                    trade["exit_price"] = trade["tp"]; trade["exit_bar"] = scan_bar
                    trade["result"] = "TP"; trade["closed"] = True; exited = True
            else:
                if current.high >= trade["sl"]:
                    trade["exit_price"] = trade["sl"]; trade["exit_bar"] = scan_bar
                    trade["result"] = "SL"; trade["closed"] = True; exited = True
                elif current.low <= trade["tp"]:
                    trade["exit_price"] = trade["tp"]; trade["exit_bar"] = scan_bar
                    trade["result"] = "TP"; trade["closed"] = True; exited = True

            if exited:
                diff = trade["exit_price"] - trade["entry_price"] if trade["side"] == "long" else trade["entry_price"] - trade["exit_price"]
                trade["pnl"] = round(diff * trade["qty"], 2)
                risk = abs(trade["initial_sl"] - trade["entry_price"])
                trade["rr"] = round(diff / risk if risk > 0 else 0, 2)
                trades.append(trade)
                pipeline["closed"] += 1
            else:
                still_active.append(trade)

        active_trades = still_active

    if bars_15m:
        last_price = bars_15m[-1].close
        for trade in active_trades:
            if not trade.get("closed"):
                trade["exit_price"] = last_price
                trade["exit_bar"] = len(bars_15m) - 1
                trade["result"] = "OPEN"
                trade["closed"] = True
                diff = last_price - trade["entry_price"] if trade["side"] == "long" else trade["entry_price"] - last_price
                trade["pnl"] = round(diff * trade["qty"], 2)
                risk = abs(trade["initial_sl"] - trade["entry_price"])
                trade["rr"] = round(diff / risk if risk > 0 else 0, 2)
                trades.append(trade)
                pipeline["closed"] += 1

    print(f"\n{'='*78}")
    print(f"  SNIPER V3 — {symbol} | {len(trades)} Islem")
    print(f"{'='*78}")
    print(f"  Parameters: SL=FVG edge +/- buffer | TP=London High/Low veya {tp_rr}R")
    print(f"                FVG buffer={fvg_buffer_mult}x risk_pts | Session=NY+LON | Unlimited entry")

    print("\n  PIPELINE")
    print(f"  {'-'*56}")
    for k, v in pipeline.items():
        print(f"  {k:<35}{v}")
    print(f"  {'total_signals':<35}{total_signals}")
    print(f"  {'rejected_other':<35}{rejected_other}")

    if trades:
        wins = [t for t in trades if t["pnl"] > 0]
        losses = [t for t in trades if t["pnl"] <= 0]
        total_pnl = sum(t["pnl"] for t in trades)

        dd_max = 0.0; dd_peak = initial_capital; running = initial_capital
        for t in trades:
            running += t["pnl"]
            if running > dd_peak: dd_peak = running
            dd = (dd_peak - running) / dd_peak * 100 if dd_peak > 0 else 0
            if dd > dd_max: dd_max = dd

        cons_loss = 0; max_cons_loss = 0
        for t in trades:
            if t["pnl"] <= 0: cons_loss += 1; max_cons_loss = max(max_cons_loss, cons_loss)
            else: cons_loss = 0

        tp_count = sum(1 for t in trades if t["result"] == "TP")
        sl_count = sum(1 for t in trades if t["result"] == "SL")
        open_count = sum(1 for t in trades if t["result"] == "OPEN")
        avg_trailing = sum(t.get("trailing_count", 0) for t in trades) / len(trades) if trades else 0

        print("\n  GENEL PERFORMANS")
        print(f"  {'-'*56}")
        print(f"  {'Toplam Islem':<30}{len(trades)}")
        print(f"  {'Kazanan':<30}{len(wins)}  (%{len(wins)/len(trades)*100:.1f})")
        print(f"  {'Kaybeden':<30}{len(losses)}  (%{len(losses)/len(trades)*100:.1f})")
        print(f"  {'TP ile kapanan':<30}{tp_count}  (%{tp_count/len(trades)*100:.1f})")
        print(f"  {'SL ile kapanan':<30}{sl_count}  (%{sl_count/len(trades)*100:.1f})")
        print(f"  {'Acik kalan':<30}{open_count}")
        print(f"  {'Toplam PnL (USDT)':<30}{total_pnl:+.2f}")
        print(f"  {'Max Drawdown':<30}{dd_max:.1f}%")
        print(f"  {'Max Ardisik Kayip':<30}{max_cons_loss} islem")
        print(f"  {'Ort. Trailing Sayisi':<30}{avg_trailing:.1f}")

        wt = sum(t["rr"] for t in wins) / len(wins) if wins else 0
        lt = sum(t["rr"] for t in losses) / len(losses) if losses else 0
        print(f"\n  R:R ANALIZI")
        print(f"  {'-'*56}")
        print(f"  {'Ort. Kazanan R:R':<30}{wt:+.2f}")
        print(f"  {'Ort. Kaybeden R:R':<30}{lt:+.2f}")
        if wt > 0 and lt != 0: print(f"  {'Profit Factor (W/L)':<30}{abs(wt/lt):.2f}")

        long_t = [t for t in trades if t["side"] == "long"]
        short_t = [t for t in trades if t["side"] == "short"]
        lw = [t for t in long_t if t["pnl"] > 0]; sw = [t for t in short_t if t["pnl"] > 0]
        print(f"\n  LONG / SHORT")
        print(f"  {'-'*60}")
        print(f"  {'':<12}{'Islem':<8}{'WR':<8}{'PnL':<14}{'Avg Win RR':<12}")
        print(f"  {'-'*60}")
        lwr = len(lw)/len(long_t)*100 if long_t else 0
        swr = len(sw)/len(short_t)*100 if short_t else 0
        lpnl = sum(t["pnl"] for t in long_t); spnl = sum(t["pnl"] for t in short_t)
        lawr = sum(t["rr"] for t in lw)/len(lw) if lw else 0
        sawr = sum(t["rr"] for t in sw)/len(sw) if sw else 0
        print(f"  {'LONG':<12}{len(long_t):<8}{lwr:<7.1f}%{lpnl:<+14.2f}{lawr:<+12.2f}")
        print(f"  {'SHORT':<12}{len(short_t):<8}{swr:<7.1f}%{spnl:<+14.2f}{sawr:<+12.2f}")

        trailed = [t for t in trades if t.get("trailing_count", 0) > 0]
        not_trailed = [t for t in trades if t.get("trailing_count", 0) == 0]
        if trailed and not_trailed:
            print(f"\n  TRAILING ETKISI")
            print(f"  {'-'*56}")
            tpnl = sum(t["pnl"] for t in trailed); npnl = sum(t["pnl"] for t in not_trailed)
            twr = sum(1 for t in trailed if t["pnl"]>0)/len(trailed)*100
            nwr = sum(1 for t in not_trailed if t["pnl"]>0)/len(not_trailed)*100
            print(f"  {'Trailing aktif':<30}{len(trailed)} (PnL={tpnl:+.2f}, WR={twr:.1f}%)")
            print(f"  {'Trailing yok':<30}{len(not_trailed)} (PnL={npnl:+.2f}, WR={nwr:.1f}%)")

        print(f"\n  SON 10 TRADE")
        print(f"  {'-'*85}")
        print(f"  {'#':<4}{'Side':<7}{'Entry':<11}{'Exit':<11}{'PnL':<10}{'R:R':<8}{'Result':<6}{'Trail':<6}{'FVG'}")
        print(f"  {'-'*85}")
        for i, t in enumerate(trades[-10:]):
            fvg_info = "YES" if t.get("trigger_fvg") else "NO"
            print(f"  {i+1:<4}{t['side']:<7}{t['entry_price']:<11.2f}{t.get('exit_price',0):<11.2f}{t['pnl']:<+10.2f}{t['rr']:<+8.2f}{t['result']:<6}{t.get('trailing_count',0):<6}{fvg_info}")
    else:
        print("\n  Sinyal bulunamadi.")

    print(f"\n{'='*78}\n")

    metrics = {"symbol": symbol, "total_trades": len(trades)}
    if trades:
        total_pnl = sum(t["pnl"] for t in trades)
        wins = [t for t in trades if t["pnl"] > 0]
        wr = len(wins) / len(trades) * 100
        dd_max = 0.0; dd_peak = initial_capital; running = initial_capital
        for t in trades:
            running += t["pnl"]; dd_peak = max(dd_peak, running)
            dd = (dd_peak - running) / dd_peak * 100 if dd_peak > 0 else 0; dd_max = max(dd_max, dd)
        wt = sum(t["rr"] for t in wins) / len(wins) if wins else 0
        lt = sum(t["rr"] for t in trades if t["pnl"] <= 0) / max(len([t for t in trades if t["pnl"] <= 0]), 1)
        pf = abs(wt / lt) if wt > 0 and lt != 0 else 0
        metrics.update({"total_pnl": total_pnl, "wr": wr, "max_dd": dd_max, "profit_factor": pf})
    return metrics


def main():
    parser = argparse.ArgumentParser(description="Sniper V3 — Aggressive Multi-Entry")
    parser.add_argument("--symbol", type=str, help="Coin symbol (e.g. BTCUSDT)")
    parser.add_argument("--all", action="store_true", help="Run for all configured coins")
    args = parser.parse_args()

    if args.all:
        results = []
        for sym in cfg.SYMBOLS:
            m = run_for_symbol(sym)
            if m: results.append(m)

        print("\n\n")
        print("=" * 110)
        print("  SNIPER V3 — TUM COINLER KARSILASTIRMA")
        print("=" * 110)
        h = f"  {'Sembol':<10} {'Islem':<7} {'PnL':<12} {'WR':<7} {'MaxDD':<8} {'PF':<7}"
        print(h)
        print("  " + "-" * 55)
        total_pnl = 0.0
        for m in sorted(results, key=lambda x: x["symbol"]):
            print(f"  {m['symbol']:<10} {m['total_trades']:<7} {m['total_pnl']:<+12.0f} {m['wr']:<5.1f}% {m['max_dd']:<6.1f}% {m['profit_factor']:<5.2f}")
            total_pnl += m["total_pnl"]
        print("  " + "-" * 55)
        print(f"  {'TOPLAM':<10} {'':<7} {total_pnl:<+12.0f}")

        report_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
        os.makedirs(report_dir, exist_ok=True)
        csv_path = os.path.join(report_dir, "v3_comparison.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["symbol", "trades", "pnl", "wr", "max_dd", "profit_factor"])
            for m in sorted(results, key=lambda x: x["symbol"]):
                w.writerow([m["symbol"], m["total_trades"], round(m["total_pnl"], 2),
                           round(m["wr"], 1), round(m["max_dd"], 1), round(m["profit_factor"], 2)])
        print(f"\nRapor kaydedildi: {csv_path}")
    elif args.symbol:
        run_for_symbol(args.symbol)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
