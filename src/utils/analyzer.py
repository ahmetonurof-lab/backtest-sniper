"""
analyzer.py — Parametric HTF FVG Wick Rejection + Retrade.
Coin settings read from coins_config.py.
"""

import argparse
import csv
import os
import sys
from datetime import datetime, timezone

from coins_config import get_config, COINS, RISK_PER_TRADE
from fvg import detect_fvgs
from models import Bar
from retrace_state import RetraceStateMachine
from session import DailyBias, SessionPhase, SessionState, detect_phase_from_timestamp

LONDON_RETEST_PCT = 0.003
MAX_FVG_ATTEMPTS = 3

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_data(filepath):
    bars = []
    with open(filepath, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            ts = int(
                datetime.strptime(row["open_time"], "%Y-%m-%d %H:%M:%S").timestamp()
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


def run_for_symbol(symbol: str, cfg: dict):
    csv_file = os.path.join(os.path.dirname(__file__), "data", f"{symbol}_1m.csv")
    if not os.path.isfile(csv_file):
        print(f"[SKIP] {symbol} — data file not found: {csv_file}")
        return

    min_fvg_size = cfg["min_fvg_size"]
    initial_capital = cfg["initial_capital"]
    risk_per_trade = cfg["risk_per_trade"]
    risk_primary = cfg.get("risk_primary", risk_per_trade)
    risk_retrade = cfg.get("risk_retrade", risk_per_trade)
    sl_atr_mult = cfg["sl_atr_mult"]
    tp_rr = cfg["tp_rr"]
    fvg_buffer_mult = cfg["fvg_buffer_mult"]

    print(f"\nLoading {symbol}...")
    bars_1m = load_data(csv_file)
    bars_15m = resample_15m(bars_1m)
    print(f"  {symbol} | 1m: {len(bars_1m)} bars | 15m: {len(bars_15m)} bars")

    ss = SessionState()
    rsm = RetraceStateMachine(min_fvg_size=min_fvg_size)
    rsm_retrade = RetraceStateMachine(min_fvg_size=min_fvg_size * 0.3)
    trades = []
    active_trades = []
    WINDOW = 500

    pipeline = {
        "cbdr_locked": 0,
        "sweep_detected": 0,
        "sweep_fed": 0,
        "fvg_scanned": 0,
        "wick_rejection": 0,
        "trigger_ready": 0,
        "filter_bias": 0,
        "filter_session": 0,
        "new_entry": 0,
        "trailing_sl_updates": 0,
        "trailing_tp_updates": 0,
        "closed": 0,
        "retrade_armed": 0,
        "retrade_sweep": 0,
        "retrade_sweep_fed": 0,
        "retrade_fvg_scanned": 0,
        "retrade_wick_rejection": 0,
        "retrade_trigger_ready": 0,
        "retrade_entry": 0,
        "retrade_lhr_checked": 0,
        "retrade_lhr_inzone": 0,
        "retrade_lhr_entry": 0,
    }
    total_signals = 0
    rejected_other = 0

    for scan_bar in range(WINDOW, len(bars_15m)):
        chunk = bars_15m[scan_bar - WINDOW : scan_bar + 1]
        current = bars_15m[scan_bar]
        atr_val = max(current.range, current.close * 0.0001)

        try:
            entry_dt = datetime.fromtimestamp(current.timestamp / 1000, tz=timezone.utc)
        except Exception:
            continue

        ss.update(
            entry_dt, current.open, current.high, current.low, current.close, atr_val
        )
        if ss.cbdr_locked:
            pipeline["cbdr_locked"] += 1

        if ss.sweep_confirmed:
            pipeline["sweep_detected"] += 1

        if ss.sweep_confirmed and rsm.state_name == "IDLE":
            pipeline["sweep_fed"] += 1
            rsm.on_sweep(
                direction=ss.sweep_direction or "bullish",
                level=ss.sweep_level or 0.0,
                bar_index=current.index,
            )

        if rsm.state_name == "SWEEP_DETECTED":
            pipeline["fvg_scanned"] += 1
            rsm.on_sweep_confirmed(chunk, current)
            if rsm.state_name == "TRIGGER_READY":
                pipeline["wick_rejection"] += 1

        if rsm.can_trigger() and not active_trades:
            pipeline["trigger_ready"] += 1
            total_signals += 1

            sweep_dir = rsm.direction
            daily_bias = ss.daily_bias

            if sweep_dir == "bullish" and daily_bias == DailyBias.BEARISH:
                rsm.reset()
                rejected_other += 1
                continue
            if sweep_dir == "bearish" and daily_bias == DailyBias.BULLISH:
                rsm.reset()
                rejected_other += 1
                continue
            if daily_bias == DailyBias.NEUTRAL:
                rsm.reset()
                rejected_other += 1
                continue
            pipeline["filter_bias"] += 1

            phase = detect_phase_from_timestamp(current.timestamp)
            if phase not in (SessionPhase.NEWYORK, SessionPhase.LONDON):
                pipeline["filter_session"] += 1
                rsm.reset()
                rejected_other += 1
                continue

            side = "long" if sweep_dir == "bullish" else "short"
            entry_price = current.close
            risk_pts = atr_val * sl_atr_mult
            trigger_fvg = rsm.trigger_fvg

            if side == "long":
                if trigger_fvg:
                    sl = trigger_fvg.bottom - (risk_pts * fvg_buffer_mult)
                else:
                    sl = entry_price - risk_pts * 2
                tp = (
                    ss.london_high
                    if ss.london_high > entry_price
                    else entry_price + risk_pts * tp_rr
                )
            else:
                if trigger_fvg:
                    sl = trigger_fvg.top + (risk_pts * fvg_buffer_mult)
                else:
                    sl = entry_price + risk_pts * 2
                tp = (
                    ss.london_low
                    if ss.london_low < entry_price
                    else entry_price - risk_pts * tp_rr
                )

            risk_dist = abs(sl - entry_price)
            min_risk_dist = atr_val * 0.1
            if risk_dist < min_risk_dist:
                continue
            qty = (initial_capital * risk_primary) / risk_dist if risk_dist > 0 else 0
            if qty <= 0:
                rsm.reset()
                rejected_other += 1
                continue

            new_trade = {
                "entry_bar": scan_bar,
                "entry_price": entry_price,
                "sl": sl,
                "tp": tp,
                "qty": qty,
                "side": side,
                "trigger_fvg": trigger_fvg,
                "initial_sl": sl,
                "initial_tp": tp,
                "trailing_count": 0,
                "is_retrade": False,
            }
            active_trades.append(new_trade)
            pipeline["new_entry"] += 1
            ss.trades_today += 1
            rsm.reset()

        if active_trades and current.is_closed:
            current_fvgs = detect_fvgs(
                chunk,
                lookback=min(50, len(chunk)),
                timeframe="15m",
                min_fvg_size=min_fvg_size,
            )

            for trade in active_trades:
                if trade.get("closed"):
                    continue

                for fvg in current_fvgs:
                    if trade["side"] == "long" and fvg.direction != "bullish":
                        continue
                    if trade["side"] == "short" and fvg.direction != "bearish":
                        continue
                    if fvg.filled or fvg.invalidated:
                        continue

                    buffer = (
                        abs(trade["initial_sl"] - trade["entry_price"])
                        * fvg_buffer_mult
                    )

                    if trade["side"] == "long":
                        new_sl = fvg.bottom - buffer
                        if new_sl > trade["sl"]:
                            sl_diff = new_sl - trade["sl"]
                            trade["sl"] = new_sl
                            trade["tp"] = trade["tp"] + sl_diff
                            trade["trailing_count"] += 1
                            pipeline["trailing_sl_updates"] += 1
                            pipeline["trailing_tp_updates"] += 1
                    else:
                        new_sl = fvg.top + buffer
                        if new_sl < trade["sl"]:
                            sl_diff = trade["sl"] - new_sl
                            trade["sl"] = new_sl
                            trade["tp"] = trade["tp"] - sl_diff
                            trade["trailing_count"] += 1
                            pipeline["trailing_sl_updates"] += 1
                            pipeline["trailing_tp_updates"] += 1

        still_active = []
        for trade in active_trades:
            if trade.get("closed"):
                continue

            exited = False
            if trade["side"] == "long":
                if current.low <= trade["sl"]:
                    trade["exit_price"] = trade["sl"]
                    trade["exit_bar"] = scan_bar
                    trade["result"] = "SL"
                    trade["closed"] = True
                    exited = True
                elif current.high >= trade["tp"]:
                    trade["exit_price"] = trade["tp"]
                    trade["exit_bar"] = scan_bar
                    trade["result"] = "TP"
                    trade["closed"] = True
                    exited = True
            else:
                if current.high >= trade["sl"]:
                    trade["exit_price"] = trade["sl"]
                    trade["exit_bar"] = scan_bar
                    trade["result"] = "SL"
                    trade["closed"] = True
                    exited = True
                elif current.low <= trade["tp"]:
                    trade["exit_price"] = trade["tp"]
                    trade["exit_bar"] = scan_bar
                    trade["result"] = "TP"
                    trade["closed"] = True
                    exited = True

            if exited:
                if trade["side"] == "long":
                    diff = trade["exit_price"] - trade["entry_price"]
                else:
                    diff = trade["entry_price"] - trade["exit_price"]
                trade["pnl"] = round(diff * trade["qty"], 2)
                risk = abs(trade["initial_sl"] - trade["entry_price"])
                trade["rr"] = round(diff / risk if risk > 0 else 0, 2)
                trades.append(trade)
                pipeline["closed"] += 1

                if (
                    not trade.get("is_retrade", False)
                    and ss.trades_today == 1
                    and not ss.retrade_armed
                ):
                    ss.retrade_armed = True
                    ss.retrade_side = "short" if trade["side"] == "long" else "long"
                    ss.retrade_sweep_level = 0.0
                    ss.retrade_entry_bar = trade["entry_bar"]
                    ss.retrade_fvg_attempts = 0
                    ss.retrade_mode = "fvg"
                    pipeline["retrade_armed"] += 1
            else:
                still_active.append(trade)

        active_trades = still_active

        if ss.retrade_armed and ss.trades_today == 1 and not active_trades:
            sweep_bar_idx = None
            sweep_found = False
            lookback = min(5, scan_bar)
            for check_idx in range(max(0, scan_bar - 4), scan_bar + 1):
                if check_idx < 0 or check_idx >= len(bars_15m):
                    continue
                cb = bars_15m[check_idx]
                if check_idx - lookback < 0:
                    continue
                recent_bars = bars_15m[check_idx - lookback : check_idx]

                if ss.retrade_side == "short":
                    recent_high = max(b.high for b in recent_bars)
                    if cb.high > recent_high and cb.close < recent_high:
                        sweep_found = True
                        sweep_bar_idx = check_idx
                        break
                else:
                    recent_low = min(b.low for b in recent_bars)
                    if cb.low < recent_low and cb.close > recent_low:
                        sweep_found = True
                        sweep_bar_idx = check_idx
                        break

            if sweep_found:
                pipeline["retrade_sweep"] += 1
                sweep_dir = "bearish" if ss.retrade_side == "short" else "bullish"
                sweep_bar = bars_15m[sweep_bar_idx]
                if rsm_retrade.state_name == "IDLE":
                    rsm_retrade.on_sweep(
                        direction=sweep_dir,
                        level=ss.retrade_sweep_level,
                        bar_index=sweep_bar.index,
                    )
                    pipeline["retrade_sweep_fed"] += 1

            if sweep_found and rsm_retrade.state_name == "SWEEP_DETECTED":
                pipeline["retrade_fvg_scanned"] += 1
                sweep_bar = bars_15m[sweep_bar_idx]
                sweep_chunk = (
                    bars_15m[sweep_bar_idx - WINDOW : sweep_bar_idx + 1]
                    if sweep_bar_idx >= WINDOW
                    else chunk
                )
                rsm_retrade.on_sweep_confirmed(sweep_chunk, sweep_bar)
                if rsm_retrade.state_name == "TRIGGER_READY":
                    pipeline["retrade_wick_rejection"] += 1

            if rsm_retrade.can_trigger():
                pipeline["retrade_trigger_ready"] += 1
                if sweep_bar_idx is not None and sweep_bar_idx <= (
                    ss.retrade_entry_bar or 0
                ):
                    rsm_retrade.reset()
                elif detect_phase_from_timestamp(current.timestamp) not in (
                    SessionPhase.NEWYORK,
                    SessionPhase.LONDON,
                ):
                    rsm_retrade.reset()
                else:
                    retrade_entry_price = current.close
                    retrade_risk_pts = atr_val * sl_atr_mult
                    retrade_fvg = rsm_retrade.trigger_fvg

                    if ss.retrade_side == "long":
                        if retrade_fvg:
                            retrade_sl = retrade_fvg.bottom - (
                                retrade_risk_pts * fvg_buffer_mult
                            )
                        else:
                            retrade_sl = retrade_entry_price - retrade_risk_pts * 2
                        retrade_tp = (
                            ss.london_high
                            if ss.london_high > retrade_entry_price
                            else retrade_entry_price + retrade_risk_pts * tp_rr
                        )
                    else:
                        if retrade_fvg:
                            retrade_sl = retrade_fvg.top + (
                                retrade_risk_pts * fvg_buffer_mult
                            )
                        else:
                            retrade_sl = retrade_entry_price + retrade_risk_pts * 2
                        retrade_tp = (
                            ss.london_low
                            if ss.london_low < retrade_entry_price
                            else retrade_entry_price - retrade_risk_pts * tp_rr
                        )

                    retrade_qty = (
                        (initial_capital * risk_retrade)
                        / abs(retrade_sl - retrade_entry_price)
                        if abs(retrade_sl - retrade_entry_price) > 0
                        else 0
                    )

                    if retrade_qty > 0:
                        retrade_trade = {
                            "entry_bar": scan_bar,
                            "entry_price": retrade_entry_price,
                            "sl": retrade_sl,
                            "tp": retrade_tp,
                            "qty": retrade_qty,
                            "side": ss.retrade_side,
                            "trigger_fvg": retrade_fvg,
                            "initial_sl": retrade_sl,
                            "initial_tp": retrade_tp,
                            "trailing_count": 0,
                            "is_retrade": True,
                        }
                        active_trades.append(retrade_trade)
                        pipeline["retrade_entry"] += 1
                        ss.trades_today += 1
                        rsm_retrade.reset()
                        ss.retrade_armed = False
                    else:
                        ss.retrade_fvg_attempts += 1
                        rsm_retrade.reset()
            else:
                ss.retrade_fvg_attempts += 1

            # ── LHR fallback (FVG attempts exhausted) ──
            if ss.retrade_fvg_attempts >= MAX_FVG_ATTEMPTS:
                ss.retrade_mode = "lhr"
                pipeline["retrade_lhr_checked"] += 1
                lh = ss.london_high
                ll = ss.london_low
                if ss.retrade_side == "short" and lh > 0:
                    zone_bottom = lh * (1 - LONDON_RETEST_PCT)
                    zone_top = lh
                    if zone_bottom <= current.close <= zone_top:
                        pipeline["retrade_lhr_inzone"] += 1
                        lhr_entry_price = current.close
                        lhr_risk_pts = atr_val * 1.0
                        lhr_sl = lh + lhr_risk_pts
                        lhr_tp = (
                            ss.london_low
                            if ss.london_low < lhr_entry_price
                            else lhr_entry_price - lhr_risk_pts * tp_rr
                        )
                        lhr_risk_dist = abs(lhr_sl - lhr_entry_price)
                        lhr_min_risk_dist = atr_val * 0.1
                        if lhr_risk_dist >= lhr_min_risk_dist:
                            lhr_qty = (
                                (initial_capital * risk_retrade) / lhr_risk_dist
                                if lhr_risk_dist > 0
                                else 0
                            )
                            if lhr_qty > 0:
                                active_trades.append(
                                    {
                                        "entry_bar": scan_bar,
                                        "entry_price": lhr_entry_price,
                                        "sl": lhr_sl,
                                        "tp": lhr_tp,
                                        "qty": lhr_qty,
                                        "side": "short",
                                        "trigger_fvg": None,
                                        "initial_sl": lhr_sl,
                                        "initial_tp": lhr_tp,
                                        "trailing_count": 0,
                                        "is_retrade": True,
                                    }
                                )
                                pipeline["retrade_lhr_entry"] += 1
                                ss.trades_today += 1
                                ss.retrade_armed = False
                elif ss.retrade_side == "long" and ll < float("inf"):
                    zone_top = ll * (1 + LONDON_RETEST_PCT)
                    zone_bottom = ll
                    if zone_bottom <= current.close <= zone_top:
                        pipeline["retrade_lhr_inzone"] += 1
                        lhr_entry_price = current.close
                        lhr_risk_pts = atr_val * 1.0
                        lhr_sl = ll - lhr_risk_pts
                        lhr_tp = (
                            ss.london_high
                            if ss.london_high > lhr_entry_price
                            else lhr_entry_price + lhr_risk_pts * tp_rr
                        )
                        lhr_risk_dist = abs(lhr_sl - lhr_entry_price)
                        lhr_min_risk_dist = atr_val * 0.1
                        if lhr_risk_dist >= lhr_min_risk_dist:
                            lhr_qty = (
                                (initial_capital * risk_retrade) / lhr_risk_dist
                                if lhr_risk_dist > 0
                                else 0
                            )
                            if lhr_qty > 0:
                                active_trades.append(
                                    {
                                        "entry_bar": scan_bar,
                                        "entry_price": lhr_entry_price,
                                        "sl": lhr_sl,
                                        "tp": lhr_tp,
                                        "qty": lhr_qty,
                                        "side": "long",
                                        "trigger_fvg": None,
                                        "initial_sl": lhr_sl,
                                        "initial_tp": lhr_tp,
                                        "trailing_count": 0,
                                        "is_retrade": True,
                                    }
                                )
                                pipeline["retrade_lhr_entry"] += 1
                                ss.trades_today += 1
                                ss.retrade_armed = False

    if bars_15m:
        last_price = bars_15m[-1].close
        for trade in active_trades:
            if not trade.get("closed"):
                trade["exit_price"] = last_price
                trade["exit_bar"] = len(bars_15m) - 1
                trade["result"] = "OPEN"
                trade["closed"] = True
                if trade["side"] == "long":
                    diff = last_price - trade["entry_price"]
                else:
                    diff = trade["entry_price"] - last_price
                trade["pnl"] = round(diff * trade["qty"], 2)
                risk = abs(trade["initial_sl"] - trade["entry_price"])
                trade["rr"] = round(diff / risk if risk > 0 else 0, 2)
                trades.append(trade)
                pipeline["closed"] += 1

    # Baseline PnL (RISK_PER_TRADE=0.01 ile karsilastirma icin)
    for t in trades:
        risk_dist_t = abs(t["initial_sl"] - t["entry_price"])
        if t["side"] == "long":
            diff_t = t["exit_price"] - t["entry_price"]
        else:
            diff_t = t["entry_price"] - t["exit_price"]
        qty_base = (
            (initial_capital * RISK_PER_TRADE) / risk_dist_t if risk_dist_t > 0 else 0
        )
        t["pnl_base"] = round(diff_t * qty_base, 2)

    print(f"\n{'='*78}")
    print(f"  SNIPER BACKTEST — {symbol} | {len(trades)} Islem")
    print(f"{'='*78}")
    print(f"  Parametreler: SL=FVG edge +/- buffer | TP=London High/Low veya {tp_rr}R")
    print(
        f"                FVG buffer={fvg_buffer_mult}x risk_pts | min_fvg={min_fvg_size} | Session=NEWYORK | Retrade var"
    )
    print(
        f"  Risk: primary=%{risk_primary*100:.1f}  retrade=%{risk_retrade*100:.1f}  (baseline=%{RISK_PER_TRADE*100:.0f})"
    )

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

        dd_max = 0.0
        dd_peak = initial_capital
        running = initial_capital
        for t in trades:
            running += t["pnl"]
            if running > dd_peak:
                dd_peak = running
            dd = (dd_peak - running) / dd_peak * 100 if dd_peak > 0 else 0
            if dd > dd_max:
                dd_max = dd

        cons_loss = 0
        max_cons_loss = 0
        for t in trades:
            if t["pnl"] <= 0:
                cons_loss += 1
                if cons_loss > max_cons_loss:
                    max_cons_loss = cons_loss
            else:
                cons_loss = 0

        tp_count = sum(1 for t in trades if t["result"] == "TP")
        sl_count = sum(1 for t in trades if t["result"] == "SL")
        open_count = sum(1 for t in trades if t["result"] == "OPEN")
        avg_trailing = sum(t.get("trailing_count", 0) for t in trades) / len(trades)

        print("\n  GENEL PERFORMANS")
        print(f"  {'-'*56}")
        print(f"  {'Toplam Islem':<30}{len(trades)}")
        if trades:
            print(f"  {'Kazanan':<30}{len(wins)}  (%{len(wins)/len(trades)*100:.1f})")
            print(
                f"  {'Kaybeden':<30}{len(losses)}  (%{len(losses)/len(trades)*100:.1f})"
            )
        print(f"  {'TP ile kapanan':<30}{tp_count}  (%{tp_count/len(trades)*100:.1f})")
        print(f"  {'SL ile kapanan':<30}{sl_count}  (%{sl_count/len(trades)*100:.1f})")
        print(f"  {'Acik kalan':<30}{open_count}")
        print(f"  {'Toplam PnL (USDT)':<30}{total_pnl:+.2f}")
        print(f"  {'Max Drawdown':<30}{dd_max:.1f}%")
        print(f"  {'Max Ardisik Kayip':<30}{max_cons_loss} islem")
        print(f"  {'Ort. Trailing Sayisi':<30}{avg_trailing:.1f}")

        wt = sum(t["rr"] for t in wins) / len(wins) if wins else 0
        lt = sum(t["rr"] for t in losses) / len(losses) if losses else 0
        print("\n  R:R ANALIZI")
        print(f"  {'-'*56}")
        print(f"  {'Ort. Kazanan R:R':<30}{wt:+.2f}")
        print(f"  {'Ort. Kaybeden R:R':<30}{lt:+.2f}")
        if wt > 0 and lt != 0:
            profit_factor = abs(wt / lt)
            print(f"  {'Profit Factor (W/L)':<30}{profit_factor:.2f}")

        long_trades = [t for t in trades if t["side"] == "long"]
        short_trades = [t for t in trades if t["side"] == "short"]
        long_wins = [t for t in long_trades if t["pnl"] > 0]
        short_wins = [t for t in short_trades if t["pnl"] > 0]
        long_pnl = sum(t["pnl"] for t in long_trades)
        short_pnl = sum(t["pnl"] for t in short_trades)
        long_wr = len(long_wins) / len(long_trades) * 100 if long_trades else 0
        short_wr = len(short_wins) / len(short_trades) * 100 if short_trades else 0
        long_avg_win_rr = (
            sum(t["rr"] for t in long_wins) / len(long_wins) if long_wins else 0
        )
        short_avg_win_rr = (
            sum(t["rr"] for t in short_wins) / len(short_wins) if short_wins else 0
        )

        print("\n  LONG / SHORT KARSILASTIRMA")
        print(f"  {'-'*60}")
        print(f"  {'':<12}{'Islem':<8}{'WR':<8}{'PnL':<14}{'Avg Win RR':<12}{'Trail'}")
        print(f"  {'-'*60}")
        print(
            f"  {'LONG':<12}{len(long_trades):<8}{long_wr:<7.1f}%{long_pnl:<+14.2f}{long_avg_win_rr:<+12.2f}{sum(t.get('trailing_count',0) for t in long_trades)/max(len(long_trades),1):.1f}"
        )
        print(
            f"  {'SHORT':<12}{len(short_trades):<8}{short_wr:<7.1f}%{short_pnl:<+14.2f}{short_avg_win_rr:<+12.2f}{sum(t.get('trailing_count',0) for t in short_trades)/max(len(short_trades),1):.1f}"
        )

        primary_trades = [t for t in trades if not t.get("is_retrade", False)]
        retrade_trades = [t for t in trades if t.get("is_retrade", False)]
        rt_armed = pipeline.get("retrade_armed", 0)
        rt_sweep = pipeline.get("retrade_sweep", 0)
        rt_entry = pipeline.get("retrade_entry", 0)
        print("\n  RETRADE PIPELINE BREAKDOWN")
        print(f"  {'-'*56}")
        print(f"  {'retrade_armed':<30}{rt_armed}")
        print(f"  {'retrade_sweep':<30}{rt_sweep}")
        print(f"  {'retrade_entry':<30}{rt_entry}")
        rt_lhr_checked = pipeline.get("retrade_lhr_checked", 0)
        rt_lhr_inzone = pipeline.get("retrade_lhr_inzone", 0)
        rt_lhr_entry = pipeline.get("retrade_lhr_entry", 0)
        if rt_lhr_checked:
            print(f"  {'retrade_lhr_checked':<30}{rt_lhr_checked}")
            print(f"  {'retrade_lhr_inzone':<30}{rt_lhr_inzone}")
            print(f"  {'retrade_lhr_entry':<30}{rt_lhr_entry}")
        if rt_armed > 0:
            print(f"  {'sweep/armed ratio':<30}{rt_sweep/rt_armed*100:.1f}%")
            print(
                f"  {'entry/sweep ratio':<30}{rt_entry/rt_sweep*100:.1f}%"
                if rt_sweep > 0
                else ""
            )
            print(f"  {'armed→entry conv rate':<30}{rt_entry/rt_armed*100:.1f}%")
        if retrade_trades:
            rt_wins = [t for t in retrade_trades if t["pnl"] > 0]
            rt_pnl = sum(t["pnl"] for t in retrade_trades)
            rt_wr = len(rt_wins) / len(retrade_trades) * 100
            rt_tp = sum(1 for t in retrade_trades if t["result"] == "TP")
            rt_sl = sum(1 for t in retrade_trades if t["result"] == "SL")
            rt_open = sum(1 for t in retrade_trades if t["result"] == "OPEN")
            rt_trail = sum(t.get("trailing_count", 0) for t in retrade_trades) / len(
                retrade_trades
            )
            print("\n  RETRADE (2. ENTRY) ANALIZI")
            print(f"  {'-'*56}")
            print(f"  {'1. Entry (primary)':<30}{len(primary_trades)}")
            print(f"  {'Primary PnL':<30}{sum(t['pnl'] for t in primary_trades):+.2f}")
            print(f"  {'2. Entry (retrade)':<30}{len(retrade_trades)}")
            print(f"  {'Retrade PnL':<30}{rt_pnl:+.2f}")
            print(f"  {'Retrade WR':<30}{rt_wr:.1f}%")
            if total_pnl:
                print(f"  {'Retrade PnL/total':<30}%{rt_pnl/total_pnl*100:.1f}")
            print(f"  {'Retrade TP/SL/OPEN':<30}{rt_tp}/{rt_sl}/{rt_open}")
            print(f"  {'Retrade ort. trailing':<30}{rt_trail:.1f}")

        trailed = [t for t in trades if t.get("trailing_count", 0) > 0]
        not_trailed = [t for t in trades if t.get("trailing_count", 0) == 0]
        if trailed and not_trailed:
            trailed_pnl = sum(t["pnl"] for t in trailed)
            not_trailed_pnl = sum(t["pnl"] for t in not_trailed)
            trailed_wr = sum(1 for t in trailed if t["pnl"] > 0) / len(trailed) * 100
            not_trailed_wr = (
                sum(1 for t in not_trailed if t["pnl"] > 0) / len(not_trailed) * 100
            )
            print("\n  TRAILING ETKISI")
            print(f"  {'-'*56}")
            print(
                f"  {'Trailing aktif islem':<30}{len(trailed)} (PnL={trailed_pnl:+.2f}, WR={trailed_wr:.1f}%)"
            )
            print(
                f"  {'Trailing yok islem':<30}{len(not_trailed)} (PnL={not_trailed_pnl:+.2f}, WR={not_trailed_wr:.1f}%)"
            )

        print("\n  SON 10 TRADE")
        print(f"  {'-'*85}")
        print(
            f"  {'#':<4}{'Side':<7}{'Entry':<11}{'Exit':<11}{'PnL':<10}{'R:R':<8}{'Result':<6}{'Trail':<6}{'FVG'}"
        )
        print(f"  {'-'*85}")
        for i, t in enumerate(trades[-10:]):
            fvg_info = "YES" if t.get("trigger_fvg") else "NO"
            print(
                f"  {i+1:<4}{t['side']:<7}"
                f"{t['entry_price']:<11.2f}"
                f"{t.get('exit_price', 0):<11.2f}"
                f"{t['pnl']:<+10.2f}"
                f"{t['rr']:<+8.2f}"
                f"{t['result']:<6}"
                f"{t.get('trailing_count', 0):<6}"
                f"{fvg_info}"
            )
    else:
        print("\n  Sinyal bulunamadi.")

    print()
    print("=" * 78)

    metrics = {"symbol": symbol, "total_trades": len(trades)}
    if trades:
        total_pnl = sum(t["pnl"] for t in trades)
        pnl_base = sum(t.get("pnl_base", 0) for t in trades)
        wins = [t for t in trades if t["pnl"] > 0]
        wr = len(wins) / len(trades) * 100

        dd_max = 0.0
        dd_peak = initial_capital
        running = initial_capital
        for t in trades:
            running += t["pnl"]
            if running > dd_peak:
                dd_peak = running
            dd = (dd_peak - running) / dd_peak * 100 if dd_peak > 0 else 0
            if dd > dd_max:
                dd_max = dd

        wt = sum(t["rr"] for t in wins) / len(wins) if wins else 0
        lt = sum(t["rr"] for t in trades if t["pnl"] <= 0) / max(
            len([t for t in trades if t["pnl"] <= 0]), 1
        )
        pf = abs(wt / lt) if wt > 0 and lt != 0 else 0

        primary_trades = [t for t in trades if not t.get("is_retrade", False)]
        retrade_trades = [t for t in trades if t.get("is_retrade", False)]
        rt_wins = [t for t in retrade_trades if t["pnl"] > 0]

        metrics.update(
            {
                "total_pnl": total_pnl,
                "pnl_base": pnl_base,
                "wr": wr,
                "max_dd": dd_max,
                "profit_factor": pf,
                "primary_trades": len(primary_trades),
                "retrade_trades": len(retrade_trades),
                "primary_pnl": sum(t["pnl"] for t in primary_trades),
                "retrade_pnl": sum(t["pnl"] for t in retrade_trades),
                "primary_pnl_base": sum(t.get("pnl_base", 0) for t in primary_trades),
                "retrade_pnl_base": sum(t.get("pnl_base", 0) for t in retrade_trades),
                "rt_wr": len(rt_wins) / len(retrade_trades) * 100
                if retrade_trades
                else 0,
                "risk_primary": risk_primary,
                "risk_retrade": risk_retrade,
            }
        )
    return metrics


def main():
    parser = argparse.ArgumentParser(description="Parametric Sniper Backtest Analyzer")
    parser.add_argument("--symbol", type=str, help="Coin symbol (e.g. BTCUSDT)")
    parser.add_argument(
        "--all", action="store_true", help="Run for all configured coins"
    )
    args = parser.parse_args()

    if args.all:
        results = []
        for sym in COINS:
            m = run_for_symbol(sym, get_config(sym))
            if m:
                results.append(m)

        print("\n\n")
        print("=" * 110)
        print("  BASELINE (risk=1%) vs CUSTOM RISK — KARSILASTIRMA")
        print("=" * 110)
        header = (
            f"  {'Sembol':<10}"
            f" {'Risk P/R':<14}"
            f" {'Islem':<7}"
            f" {'PnL(base)':<12}"
            f" {'PnL(cust)':<12}"
            f" {'ΔPnL':<10}"
            f" {'WR':<7}"
            f" {'MaxDD':<8}"
            f" {'PF':<7}"
            f" {'Retrd%':<8}"
        )
        print(header)
        print("  " + "-" * 105)

        total_pnl_base = 0.0
        total_pnl_cust = 0.0
        for m in results:
            sym = m["symbol"]
            rp = m["risk_primary"]
            rr = m["risk_retrade"]
            nt = m["total_trades"]
            pb = m["pnl_base"]
            pc = m["total_pnl"]
            dp = pc - pb
            wr = m["wr"]
            dd = m["max_dd"]
            pf = m["profit_factor"]
            rt_pct = m["retrade_pnl"] / pc * 100 if pc != 0 else 0

            dp_s = f"{dp:+.1f}" + (" ⚠" if abs(dp) > 50 else "")
            print(
                f"  {sym:<10}"
                f" {rp:.1%}/{rr:.1%}   "
                f" {nt:<5}"
                f" {pb:<+11.1f}"
                f" {pc:<+11.1f}"
                f" {dp_s:<12}"
                f" {wr:<5.1f}%"
                f" {dd:<6.1f}%"
                f" {pf:<5.2f}"
                f" {rt_pct:<5.1f}%"
            )
            total_pnl_base += pb
            total_pnl_cust += pc

        print("  " + "-" * 105)
        total_dp = total_pnl_cust - total_pnl_base
        print(
            f"  {'TOPLAM':<10}"
            f" {'':<14}"
            f" {'':<5}"
            f" {total_pnl_base:<+11.1f}"
            f" {total_pnl_cust:<+11.1f}"
            f" {total_dp:<+10.1f}"
            f" {'':<7}"
            f" {'':<8}"
            f" {'':<7}"
            f" {'':<8}"
        )

        # CSV kaydet
        report_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
        os.makedirs(report_dir, exist_ok=True)
        csv_path = os.path.join(report_dir, "risk_comparison.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(
                [
                    "symbol",
                    "risk_primary",
                    "risk_retrade",
                    "trades",
                    "pnl_base",
                    "pnl_custom",
                    "delta_pnl",
                    "wr",
                    "max_dd",
                    "profit_factor",
                    "retrade_pnl_pct",
                ]
            )
            for m in results:
                rt_pct = (
                    m["retrade_pnl"] / m["total_pnl"] * 100
                    if m["total_pnl"] != 0
                    else 0
                )
                w.writerow(
                    [
                        m["symbol"],
                        m["risk_primary"],
                        m["risk_retrade"],
                        m["total_trades"],
                        round(m["pnl_base"], 2),
                        round(m["total_pnl"], 2),
                        round(m["total_pnl"] - m["pnl_base"], 2),
                        round(m["wr"], 1),
                        round(m["max_dd"], 1),
                        round(m["profit_factor"], 2),
                        round(rt_pct, 1),
                    ]
                )
        print(f"\nRapor kaydedildi: {csv_path}")
    elif args.symbol:
        cfg = get_config(args.symbol)
        run_for_symbol(args.symbol, cfg)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
