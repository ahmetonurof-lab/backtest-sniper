"""
bar_replay.py — Canli bot karar mekanizmasini backtestle karsilastir.

Hiçbir orijinal dosyaya dokunmaz. Sadece sniper/src modüllerini import eder,
1m CSV data'larini 15m'e resample eder, her bar icin kararlari kaydeder.

Kullanim:
    python bar_replay.py                          # tum semboller
    python bar_replay.py --symbols LINKUSDT,DOTUSDT  # secili semboller
    python bar_replay.py --window 500              # lookback penceresi
    python bar_replay.py --output sonuc.jsonl      # cikti dosyasi

Cikti: test-sniper/output/replay_result.jsonl
    Her bar icin bir satir:
    {"sym":"LINKUSDT","bar":145,"time":"2026-06-15 12:00",
     "session":"LONDON","bias":"BULLISH","cbdr_locked":true,
     "sweep_confirmed":true,"rsm_state":"SWEEP_DETECTED",
     "entry":false,"reason":"bias_bearish"}
"""

from __future__ import annotations

import csv
import json
import os
import sys
from argparse import ArgumentParser
from datetime import UTC, datetime

# ── Path: sniper/src modullerini goruntule ──
_SNIPER_SRC = os.path.join(os.path.dirname(__file__), "..", "..", "sniper", "src")
sys.path.insert(0, os.path.abspath(_SNIPER_SRC))

# ── Import live bot modulleri (pure logic) ──
import config as cfg  # noqa: E402
from models import Bar  # noqa: E402
from session import (  # noqa: E402
    DailyBias,
    SessionPhase,
    SessionState,
    detect_phase_from_timestamp,
)
from retrace_state import RetraceStateMachine  # noqa: E402
from trading.signal_engine import SignalEngine  # noqa: E402

# ── Constants ──
_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")
_DATA_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "backtest-sniper", "src", "data"
)
_DEFAULT_WINDOW = 500

# ── Data loading helpers (backtest'ten bagimsiz kopya) ──


def load_data(filepath: str) -> list[Bar]:
    bars: list[Bar] = []
    with open(filepath, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            ts_str = row["open_time"]
            try:
                ts = int(
                    datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").timestamp() * 1000
                )
            except ValueError:
                ts = int(
                    datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").timestamp() * 1000
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


def resample_15m(bars_1m: list[Bar]) -> list[Bar]:
    m15: list[Bar] = []
    for i in range(0, len(bars_1m), 15):
        chunk = bars_1m[i : i + 15]
        if len(chunk) < 15:
            break
        m15.append(
            Bar(
                index=chunk[0].index,
                open=chunk[0].open,
                high=max(b.high for b in chunk),
                low=min(b.low for b in chunk),
                close=chunk[-1].close,
                volume=sum(b.volume for b in chunk),
                is_closed=True,
                timestamp=chunk[0].timestamp,
            )
        )
    return m15


def build_symbol_configs() -> dict[str, dict]:
    cfgs: dict[str, dict] = {}
    for sym in cfg.SYMBOLS:
        min_fvg = cfg.FVG_SIZE_MAP.get(sym, 0.5)
        cfgs[sym] = {
            "MIN_FVG_SIZE": min_fvg,
            "SL_ATR_MULT": cfg.SL_ATR_MULT,
            "TP_RR": cfg.TP_RR,
            "FVG_BUFFER_MULT": cfg.FVG_BUFFER_MULT,
        }
    return cfgs


# ── Replay engine ──


class BarReplay:
    def __init__(self, window: int = _DEFAULT_WINDOW):
        self.window = window
        self.cfgs = build_symbol_configs()
        self.results: list[dict] = []

    def run_symbol(self, sym: str) -> tuple[int, int]:
        csv_file = os.path.join(_DATA_DIR, f"{sym}_1m.csv")
        if not os.path.isfile(csv_file):
            print(f"  [SKIP] {sym} — data file not found")
            return 0, 0

        bars_1m = load_data(csv_file)
        bars_15m = resample_15m(bars_1m)
        if len(bars_15m) < self.window + 5:
            print(
                f"  [SKIP] {sym} — yetersiz bar ({len(bars_15m)} < {self.window + 5})"
            )
            return 0, 0

        sym_cfg = self.cfgs[sym]
        min_fvg = sym_cfg["MIN_FVG_SIZE"]

        # ── Live bot state (canli karar mekanizmasi) ──
        live_ss = SessionState()
        live_rsm = RetraceStateMachine(min_fvg_size=min_fvg)
        live_engine = SignalEngine(live_rsm)

        # ── Backtest state (backtest'teki karar mekanizmasi) ──
        bt_ss = SessionState()
        bt_rsm = RetraceStateMachine(min_fvg_size=min_fvg)

        total_signals_live = 0
        total_signals_bt = 0
        match_count = 0
        mismatch_count = 0
        skipped_reasons: dict[str, int] = {}

        for scan_bar in range(self.window, len(bars_15m)):
            chunk = bars_15m[scan_bar - self.window : scan_bar + 1]
            current = bars_15m[scan_bar]
            atr_val = max(current.range, current.close * cfg.DEFAULT_ATR_FALLBACK_PCT)

            try:
                dt = datetime.fromtimestamp(current.timestamp / 1000, tz=UTC)
            except Exception:
                continue
            hour = dt.hour

            if hour >= 22 or hour < 2:
                session = "ASIA"
            elif 2 <= hour < 13:
                session = "LONDON"
            else:
                session = "NEWYORK"

            # ── Live bot pipeline ──
            live_ss.update(
                dt, current.open, current.high, current.low, current.close, atr_val
            )
            live_decision = self._replay_bar_live(
                sym,
                scan_bar,
                current,
                chunk,
                live_ss,
                live_rsm,
                live_engine,
                session,
                sym_cfg,
                bars_15m,
            )

            # ── Backtest pipeline ──
            bt_ss.update(
                dt, current.open, current.high, current.low, current.close, atr_val
            )
            bt_decision = self._replay_bar_backtest(
                sym, scan_bar, current, chunk, bt_ss, bt_rsm, session, sym_cfg, bars_15m
            )

            live_entry = live_decision["entry"]
            bt_entry = bt_decision["entry"]

            if live_entry == bt_entry:
                match_count += 1
            else:
                mismatch_count += 1

            if live_entry:
                total_signals_live += 1
            else:
                reason = live_decision.get("reason", "unknown")
                skipped_reasons[reason] = skipped_reasons.get(reason, 0) + 1

            if bt_entry:
                total_signals_bt += 1

            record = {
                "sym": sym,
                "bar": scan_bar,
                "time": dt.strftime("%Y-%m-%d %H:%M"),
                "close": round(current.close, 6),
                "session": session,
                "bias": live_ss.daily_bias.value if live_ss.daily_bias else "NONE",
                "cbdr_locked": live_ss.cbdr_locked,
                "sweep_confirmed": live_ss.sweep_confirmed,
                "live_entry": live_entry,
                "live_reason": live_decision.get("reason"),
                "live_side": live_decision.get("side"),
                "live_rsm": live_rsm.state_name,
                "bt_entry": bt_entry,
                "bt_reason": bt_decision.get("reason"),
                "bt_side": bt_decision.get("side"),
                "bt_rsm": bt_rsm.state_name,
                "match": live_entry == bt_entry,
            }

            self.results.append(record)

        print(
            f"    -> bars={len(bars_15m) - self.window} "
            f"live_entries={total_signals_live} "
            f"bt_entries={total_signals_bt} "
            f"match={match_count} mismatch={mismatch_count}"
        )

        return total_signals_live, len(bars_15m) - self.window

    def _replay_bar_live(
        self,
        sym: str,
        scan_bar: int,
        current: Bar,
        chunk: list[Bar],
        ss: SessionState,
        rsm: RetraceStateMachine,
        engine: SignalEngine,
        session: str,
        sym_cfg: dict,
        bars_15m: list[Bar],
    ) -> dict:
        """Live bot'un _on_15m_close() akisini birebir tekrarlar."""

        # ── 1. ASIA filtresi ──
        if session == "ASIA":
            return {"entry": False, "reason": "session_asia"}

        # ── 2. CBDR kilidi ──
        if not ss.cbdr_locked:
            return {"entry": False, "reason": "cbdr_not_locked"}

        # ── 3. Sweep status ──
        if not ss.sweep_confirmed:
            return {"entry": False, "reason": "no_sweep"}

        # ── 4. RSM progression ──
        engine.progress_rsm(chunk, current, ss)

        if rsm.state_name not in ("SWEEP_DETECTED", "TRIGGER_READY"):
            return {"entry": False, "reason": f"rsm_{rsm.state_name}"}

        # ── 5. Trigger evaluate (bias + session filter) ──
        result = engine.evaluate_trigger(current, ss)

        if result.decision == "TRIGGER":
            return {
                "entry": True,
                "side": result.direction,
                "entry_price": current.close,
                "sl": None,
                "tp": None,
                "reason": None,
            }
        elif result.decision == "SKIP":
            return {"entry": False, "reason": result.reason or "filter_skip"}

        return {"entry": False, "reason": "wait"}

    def _replay_bar_backtest(
        self,
        sym: str,
        scan_bar: int,
        current: Bar,
        chunk: list[Bar],
        ss: SessionState,
        rsm: RetraceStateMachine,
        session: str,
        sym_cfg: dict,
        bars_15m: list[Bar],
    ) -> dict:
        """Backtest (analyzer_v3.py) karar mantigini tekrarlar."""
        # CBDR locked degilse atla
        if not ss.cbdr_locked:
            return {"entry": False, "reason": "cbdr_not_locked"}

        # Sweep → RSM feed (backtest'te ss.sweep_confirmed kontrolu yok, direkt bar_index ile feed eder)
        if rsm.state_name == "IDLE" and ss.sweep_confirmed:
            rsm.on_sweep(
                direction=ss.sweep_direction or "bullish",
                level=ss.sweep_level or 0.0,
                bar_index=current.index,
            )

        # Sweep confirmed → FVG + wick
        if rsm.state_name == "SWEEP_DETECTED":
            rsm.on_sweep_confirmed(chunk, current)

        # Trigger check (backtest'te overlap guard: not active_trades)
        if not rsm.can_trigger():
            return {"entry": False, "reason": f"rsm_{rsm.state_name}"}

        # Bias filter (backtest ile ayni)
        sweep_dir = rsm.direction
        daily_bias = ss.daily_bias
        if sweep_dir == "bullish" and daily_bias == DailyBias.BEARISH:
            rsm.reset()
            return {"entry": False, "reason": "bias_bearish"}
        if sweep_dir == "bearish" and daily_bias == DailyBias.BULLISH:
            rsm.reset()
            return {"entry": False, "reason": "bias_bullish"}
        if daily_bias == DailyBias.NEUTRAL:
            rsm.reset()
            return {"entry": False, "reason": "bias_neutral"}

        # Session filter (backtest ile ayni)
        phase = detect_phase_from_timestamp(current.timestamp)
        if phase not in (SessionPhase.NEWYORK, SessionPhase.LONDON):
            rsm.reset()
            return {"entry": False, "reason": "session_filter"}

        return {
            "entry": True,
            "side": "long" if sweep_dir == "bullish" else "short",
            "reason": None,
        }

    def write_results(self, filepath: str) -> None:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            for r in self.results:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"\n[OUTPUT] {len(self.results)} kayit -> {filepath}")

    def print_summary(self) -> None:
        sym_stats: dict[str, dict] = {}
        for r in self.results:
            sym = r["sym"]
            if sym not in sym_stats:
                sym_stats[sym] = {
                    "total": 0,
                    "live_entries": 0,
                    "bt_entries": 0,
                    "match": 0,
                    "mismatch": 0,
                    "reasons": {},
                }
            sym_stats[sym]["total"] += 1
            if r["live_entry"]:
                sym_stats[sym]["live_entries"] += 1
            else:
                reason = r.get("live_reason", "unknown")
                sym_stats[sym]["reasons"][reason] = (
                    sym_stats[sym]["reasons"].get(reason, 0) + 1
                )
            if r["bt_entry"]:
                sym_stats[sym]["bt_entries"] += 1
            if r["match"]:
                sym_stats[sym]["match"] += 1
            else:
                sym_stats[sym]["mismatch"] += 1

        print("\n" + "=" * 90)
        header = f"{'SEMBOL':<12} {'TOPLAM':<8} {'LIVE':<8} {'BT':<8} {'MATCH%':<8} {'EN COK RED (LIVE)':<30}"
        print(header)
        print("-" * 90)
        for sym, st in sorted(sym_stats.items()):
            match_pct = st["match"] / max(st["total"], 1) * 100
            top_reason = (
                max(st["reasons"], key=st["reasons"].get) if st["reasons"] else "-"
            )
            top_count = st["reasons"].get(top_reason, 0) if st["reasons"] else 0
            print(
                f"{sym:<12} {st['total']:<8} "
                f"{st['live_entries']:<8} {st['bt_entries']:<8} "
                f"{match_pct:<8.2f} {top_reason}:{top_count}"
            )
        print("=" * 90)

        # Overall comparison
        total = sum(st["total"] for st in sym_stats.values())
        total_live = sum(st["live_entries"] for st in sym_stats.values())
        total_bt = sum(st["bt_entries"] for st in sym_stats.values())
        total_match = sum(st["match"] for st in sym_stats.values())
        print(
            f"\n  GENEL: bars={total} live_entry={total_live} bt_entry={total_bt} "
            f"match={total_match}/{total} ({total_match/max(total,1)*100:.2f}%)"
        )


def main():
    parser = ArgumentParser(description="Bar replay — live bot decisions vs backtest")
    parser.add_argument(
        "--symbols",
        default="",
        help="Semboller (virgulle ayir,ornek: LINKUSDT,BTCUSDT)",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=_DEFAULT_WINDOW,
        help="Lookback pencere (default: 500)",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Cikti dosyasi (default: test-sniper/output/replay_result.jsonl)",
    )
    args = parser.parse_args()

    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    else:
        symbols = list(cfg.SYMBOLS)

    output_file = args.output or os.path.join(_OUTPUT_DIR, "replay_result.jsonl")

    print(f"\n{'='*70}")
    print("  Bar Replay — Live Bot Decision Pipeline")
    print(f"  Window: {args.window} | Symbols: {len(symbols)}")
    print(f"{'='*70}\n")

    replay = BarReplay(window=args.window)

    for sym in symbols:
        print(f"  [{sym}] Processing...")
        replay.run_symbol(sym)

    replay.write_results(output_file)
    replay.print_summary()


if __name__ == "__main__":
    main()
