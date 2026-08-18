"""
diag_ifvg_normal_suppression.py — IFVG paper-deploy direktifi GÖREV 2 teşhisi.

ÜRETİM KODUNA DOKUNMAZ (sadece teşhis): analyzer_v5._collect_fvg_profile_impl
içindeki process_sweep çağrısını monkeypatch ile sarmalayıp her 15m bar için
RSM state izini (state_prev -> state_after, trigger source, inverted aday
sayısı, trigger/reddet olayı) kaydeder. Aynı coin'i IFVG KAPALI ve AÇIK
koşar, iki izi bar-bazlı karşılaştırır:

  - "SUPPRESSED"   : IFVG kapalıda o bar TRIGGER_READY (NORMAL trigger) iken
                     açıkta TRIGGER_READY DEĞİL (NORMAL sinyal bastırıldı).
  - "USURPED"      : IFVG kapalıda NORMAL trigger varken açıkta IFVG trigger'ı
                     onun yerine geçti (aynı bar, kaynak IFVG).
  - "STATE_DIVERGE": ikisinde de trigger yok ama RSM state'i farklı ilerledi
                     (BIAS_LOCKED/SWEEP_DETECTED kilidi — NORMAL taraması
                     gecikebilir/engellenebilir).

Kullanım:  cd backtest-sniper && python tools/diag_ifvg_normal_suppression.py
"""

from __future__ import annotations

import os
import sys
import time
from collections import Counter


def _reconfigure_io() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


_reconfigure_io()

BACKTEST_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
sys.path.insert(0, BACKTEST_SRC)

import analyzer_v5 as A  # noqa: E402
import config as cfg  # noqa: E402

SAMPLE_COINS = ["ARBUSDT", "SEIUSDT", "XRPUSDT"]


def _state_name(s) -> str:
    return s.name if s is not None else "None"


def run_trace(sym: str, ifvg_on: bool) -> dict:
    """collect_fvg_profile'u IFVG on/off ile koş, per-bar RSM izini döndür."""

    cfg.IFVG_ENABLED = ifvg_on
    if ifvg_on:
        os.environ["SNIPER_IFVG_ENABLED"] = "true"
    else:
        os.environ.pop("SNIPER_IFVG_ENABLED", None)

    trace: dict[int, dict] = {}

    # Orijinal process_sweep'i sarmala: çağrı öncesi/sonrası RSM durumunu yakala.
    orig_ps = A.process_sweep

    def wrapped_ps(rsm, ss, bars_15m, current, atr_val=0.0, symbol=""):
        pre_state = _state_name(rsm.state)
        pre_n = len(getattr(rsm, "_inverted_candidates", []))
        pre_dir = getattr(rsm, "direction", None)
        pre_sweep = getattr(rsm, "sweep_level", None)
        pre_lock_bar = getattr(rsm, "_locked_from_bar", None)
        ret = orig_ps(rsm, ss, bars_15m, current, atr_val, symbol)
        ev = trace.setdefault(current.index, {})
        ev["ts"] = current.timestamp
        ev["state_prev"] = pre_state
        ev["state_after"] = _state_name(rsm.state)
        ev["src"] = getattr(rsm, "_last_trigger_source", None)
        ev["n_inv_prev"] = pre_n
        ev["n_inv_after"] = len(getattr(rsm, "_inverted_candidates", []))
        ev["dir_prev"] = pre_dir
        ev["dir_after"] = getattr(rsm, "direction", None)
        ev["sweep_prev"] = pre_sweep
        ev["sweep_after"] = getattr(rsm, "sweep_level", None)
        ev["lock_bar"] = getattr(rsm, "_locked_from_bar", None)
        ev["pre_sweep_prev"] = pre_lock_bar
        return ret

    A.process_sweep = wrapped_ps
    try:
        result = A.collect_fvg_profile(sym)
    finally:
        A.process_sweep = orig_ps

    if result is None or result[0] is None:
        return {"trace": {}, "stats": None, "records": [], "rej": {}}
    daily_rows, wins, losses, trade_records, rej = result
    stats = A.compute_session_stats(trade_records, cfg.INITIAL_BALANCE, daily_rows)
    return {"trace": trace, "stats": stats, "records": trade_records, "rej": rej}


def classify(off: dict, on: dict) -> tuple[Counter, list[dict]]:
    toff, ton = off["trace"], on["trace"]
    counts: Counter = Counter()
    examples: list[dict] = []
    blocked_bars: Counter = Counter()  # IFVG-on RSM'in meşgul kaldığı bar sayısı
    for idx in sorted(set(toff) | set(ton)):
        e_off = toff.get(idx)
        e_on = ton.get(idx)
        if e_off is None or e_on is None:
            continue
        # IFVG-on'da RSM IDLE değil ama IFVG-off'ta IDLE: NORMAL yeni sweep'i
        # (IDLE -> on_sweep) göremiyor demektir -> blokaj penceresi.
        if e_off["state_after"] == "IDLE" and e_on["state_after"] != "IDLE":
            blocked_bars[e_on["state_after"]] += 1
        off_trig = e_off["state_after"] == "TRIGGER_READY"
        on_trig = e_on["state_after"] == "TRIGGER_READY"
        if off_trig and not on_trig:
            kind = "SUPPRESSED"
            counts[kind] += 1
            if len(examples) < 15:
                examples.append(
                    {
                        "bar": idx,
                        "kind": kind,
                        "ts": e_off["ts"],
                        "off_state_prev": e_off["state_prev"],
                        "on_state_prev": e_on["state_prev"],
                        "on_state_after": e_on["state_after"],
                        "on_src": e_on["src"],
                        "n_inv": e_on["n_inv_after"],
                    }
                )
            continue
        elif off_trig and on_trig:
            if e_on["src"] == "IFVG" and e_off["src"] != "IFVG":
                kind = "USURPED"
                counts[kind] += 1
                if len(examples) < 15:
                    examples.append(
                        {
                            "bar": idx,
                            "kind": kind,
                            "ts": e_off["ts"],
                            "off_src": e_off["src"],
                            "on_src": e_on["src"],
                            "off_state_prev": e_off["state_prev"],
                            "on_state_prev": e_on["state_prev"],
                            "n_inv": e_on["n_inv_prev"],
                        }
                    )
                continue
            else:
                kind = "BOTH_TRIGGER"
                counts[kind] += 1
                continue
        elif not off_trig and on_trig:
            kind = "NEW_IFVG_ONLY"
            counts[kind] += 1
        else:
            if (
                e_off["state_after"] != e_on["state_after"]
                or e_off["state_prev"] != e_on["state_prev"]
            ):
                kind = "STATE_DIVERGE"
                counts[kind] += 1
                if len(examples) < 15:
                    examples.append(
                        {
                            "bar": idx,
                            "kind": kind,
                            "ts": e_off["ts"],
                            "off": f"{e_off['state_prev']}->{e_off['state_after']} ({e_off['dir_prev']}->{e_off['dir_after']})",
                            "on": f"{e_on['state_prev']}->{e_on['state_after']} ({e_on['dir_prev']}->{e_on['dir_after']})",
                            "n_inv": e_on["n_inv_prev"],
                            "off_src": e_off["src"],
                            "on_src": e_on["src"],
                        }
                    )
                continue
            else:
                counts["SAME"] += 1
    counts["BLOCKED_BARS_TOTAL"] = sum(blocked_bars.values())
    counts["BLOCKED_BARS_BIAS_LOCKED"] = blocked_bars.get("BIAS_LOCKED", 0)
    counts["BLOCKED_BARS_SWEEP_DETECTED"] = blocked_bars.get("SWEEP_DETECTED", 0)
    counts["BLOCKED_BARS_TRIGGER_READY"] = blocked_bars.get("TRIGGER_READY", 0)
    return counts, examples


def main() -> None:
    print("=" * 90)
    print("  GÖREV 2 — NORMAL suppression kök neden teşhisi (IFVG off vs on)")
    print("  coins:", ", ".join(SAMPLE_COINS))
    print("=" * 90)
    summary = {}
    for sym in SAMPLE_COINS:
        print(f"\n--- {sym} ---", flush=True)
        t0 = time.time()
        off = run_trace(sym, ifvg_on=False)
        print(f"  IFVG KAPALI: {time.time()-t0:.0f}s", flush=True)
        t0 = time.time()
        on = run_trace(sym, ifvg_on=True)
        print(f"  IFVG AÇIK:   {time.time()-t0:.0f}s", flush=True)

        counts, examples = classify(off, on)
        summary[sym] = {"counts": counts, "examples": examples}
        s_off = off["stats"]
        s_on = on["stats"]
        print(
            f"\n  [{sym}] stats  off: {s_off['total_trades']} trade / net {s_off['total_pnl']:+,.0f}"
        )
        print(
            f"  [{sym}] stats  on:  {s_on['total_trades']} trade / net {s_on['total_pnl']:+,.0f}"
        )
        print(
            f"  [{sym}] NORMAL trades off={sum(1 for r in off['records'] if r.get('entry_source') != 'IFVG')} "
            f"on={sum(1 for r in on['records'] if r.get('entry_source') != 'IFVG')}"
        )
        print(
            f"  [{sym}] IFVG trades on={sum(1 for r in on['records'] if r.get('entry_source') == 'IFVG')}"
        )
        print(f"  [{sym}] bar-bazlı sınıflandırma: {dict(counts)}")
        for ex in examples[:10]:
            print(
                f"    {ex['kind']:<16} bar={ex['bar']} ts={ex['ts']} "
                f"n_inv={ex['n_inv']} src_off={ex.get('off_src')} src_on={ex.get('on_src')} "
                f"{ex.get('off','')} | {ex.get('on','')}"
            )

    print("\n" + "=" * 90)
    print("  ÖZET (bar-bazlı suppression/divergence + blokaj penceresi)")

    def fmt(c: Counter) -> str:
        return ", ".join(f"{k}={v}" for k, v in sorted(c.items()))

    for sym, d in summary.items():
        print(f"  {sym:<10} {fmt(d['counts'])}")
    print("=" * 90)


if __name__ == "__main__":
    main()
