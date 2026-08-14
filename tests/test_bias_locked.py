"""
test_bias_locked.py — LUNA Plan C test planı: BIAS_LOCKED parity + determinizm.

Senaryo (Luna_direktif.md "Test planı", madde 92-108):
  2. İki farklı symbol aynı bar_index ile birbirini engellemez.
  3. İlk sweep sonrası BIAS_LOCKED dalı yeni sweep beklemeden aynı yönlü FVG arar.
  4. BIAS tersine dönerse veya yeni CBDR döngüsü başlarsa RSM resetlenir.
  5. Son 10 ters FVG, daha eski uyumlu FVG'yi gizlemez.
  6. Touched/invalidated FVG tekrar trigger olmaz.
  7. Aynı temiz state ve aynı veriyle iki koşu aynı trade sayısı/PnL üretir.
  8. BIAS_LOCKED flow, canlı SignalEngine.progress_rsm() ile eşleşir.

Kullanim:
  python tests/test_bias_locked.py               # unittest direkt
  python -m pytest tests/test_bias_locked.py -v  # pytest
"""

# ruff: noqa: E402
import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
_SNIPER_SRC = os.path.join(os.path.dirname(__file__), "..", "..", "sniper", "src")
if _SNIPER_SRC not in sys.path:
    sys.path.insert(0, _SNIPER_SRC)

from models import Bar
from retrace_state import RetraceStateMachine, scan_htf_fvgs
from session import DailyBias, SessionState
from sweep_sync import process_sweep

_DAY_MS = 1752624000000  # 2026-08-11T00:00:00Z


def _bar(i, o, h, lo, c):
    return Bar(
        index=i,
        open=o,
        high=h,
        low=lo,
        close=c,
        volume=1.0,
        is_closed=True,
        timestamp=_DAY_MS + i * 900000,
    )


def _flat(n=60):
    """FVG üretmeyen düz barlar (on_sweep_confirmed SWEEP_DETECTED'de kalır)."""
    return [_bar(i, 100, 101, 99, 100) for i in range(n)]


def _bullish_fvg_bars(touch=False, far_close=False, n_flat=9):
    """Düz barlar + tek BIAS yönlü (bullish) FVG + wick rejection bari.

    FVG: prev(9, H=100) - impulse(10, real_index) - next(11, L=103) → [100, 103].
    Current bar (son): low=100.5 (FVG'ye wick) + close=103.5 (govde FVG icinde
    degil, far-side close degil). Current bari bar-11 FVG'si olusturmaz.
    """
    bars = _flat(n_flat)
    bars.append(_bar(n_flat, 99, 100, 98, 99))
    bars.append(_bar(n_flat + 1, 101, 101, 100.6, 101))
    bars.append(_bar(n_flat + 2, 103.5, 104, 103, 104))
    cur = n_flat + 3
    if touch:
        bars.append(_bar(cur, 103.6, 104.5, 101, 104))
        cur += 1
    elif far_close:
        bars.append(_bar(cur, 98, 99, 97, 98))
        cur += 1
    bars.append(_bar(cur, 104, 105, 100.5, 103.5))
    return bars


def _opposite_barrage():
    """11 adet ters yönlü (bearish) FVG + en sonda 1 uyumlu (bullish) FVG.

    L-06 regresyonu: direction filtresi cap'tan (son 10) ÖNCE uygulanmazsa
    ters yönlü FVG'ler tarama penceresini doldurur ve uyumlu eski FVG gizlenir.
    """
    bars, idx, P = [], 0, 200.0
    for _ in range(11):
        bars.append(_bar(idx, P, P, P, P))
        idx += 1
        bars.append(_bar(idx, P - 14, P - 13.6, P - 14, P - 14))
        idx += 1
        bars.append(_bar(idx, P - 15, P - 15, P - 15, P - 15))
        idx += 1
        P -= 15.0
    bars.append(_bar(idx, 20, 20, 20, 20))
    idx += 1
    bars.append(_bar(idx, 55, 55, 54.6, 55))
    idx += 1
    bars.append(_bar(idx, 60, 60, 60, 60))
    idx += 1
    bars.append(_bar(idx, 58, 58, 50, 58))
    return bars


class BiasLockedPlanCGoldenTests(unittest.TestCase):
    def setUp(self):
        self.bars = _flat()
        self._patchers = [
            mock.patch("state_manager.is_sweep_used", return_value=False),
            mock.patch("state_manager.mark_sweep_used"),
        ]
        for p in self._patchers:
            p.start()
        self.addCleanup(self._stop_patchers)

    def _stop_patchers(self):
        for p in self._patchers:
            p.stop()

    def _locked_rsm(self, bars, direction="bullish", lock_bar=8, daily_bias=None):
        """Sweep → lock_bias akışıyla BIAS_LOCKED RSM üret (canlı bot.py:1167 parity)."""
        rsm = RetraceStateMachine(max_wick_ratio=0.3)
        ss = SessionState(start_hour=22, end_hour=2)
        ss.daily_bias = daily_bias if daily_bias is not None else DailyBias.BULLISH
        rsm.on_sweep(direction=direction, level=99.0, bar_index=lock_bar)
        rsm.lock_bias(bar_index=lock_bar)
        self.assertEqual(rsm.state_name, "BIAS_LOCKED")
        return rsm, ss

    # ── LUNA #2: iki farklı symbol aynı bar_index ile birbirini engellemez ──
    def test_two_symbols_same_bar_index_do_not_block(self):
        """Legacy "{direction}_{bar_index}" kaydı sembol B'yi engellememeli."""
        legacy_used = {"bullish_10"}

        def fake_is_sweep_used(sweep_id):
            return sweep_id in legacy_used

        with mock.patch("state_manager.is_sweep_used", side_effect=fake_is_sweep_used):
            rsm = RetraceStateMachine(max_wick_ratio=0.3)
            ss = SessionState(start_hour=22, end_hour=2)
            ss.sweep_confirmed = True
            ss.sweep_direction = "bullish"
            ss.sweep_level = 100.0
            # Sembol adı geçilmeden (eski sweep_sync) _sweep_id("", ...)="bullish_10"
            # üretir → legacy kayıt engeller. Symbol-scoped ID ile engellenmez.
            process_sweep(rsm, ss, self.bars, self.bars[10], 0.0, "SYMB")
            self.assertEqual(rsm.state_name, "SWEEP_DETECTED")
            self.assertEqual(rsm.direction, "bullish")
            self.assertEqual(rsm.sweep_level, 100.0)

    # ── LUNA #3: BIAS_LOCKED, yeni sweep beklemeden BIAS yönlü FVG arar ──
    def test_bias_locked_fvg_without_new_sweep(self):
        bars = _bullish_fvg_bars()
        rsm, ss = self._locked_rsm(bars)
        self.assertFalse(ss.sweep_confirmed)  # yeni sweep YOK
        process_sweep(rsm, ss, bars, bars[-1], 0.0, "TESTUSDT")
        self.assertEqual(rsm.state_name, "TRIGGER_READY")
        self.assertIsNotNone(rsm.trigger_fvg)
        self.assertTrue(ss.fvg_ready)

    # ── LUNA #4a: bias tersine dönerse BIAS_LOCKED resetlenir ──
    def test_bias_conflict_bearish_resets(self):
        bars = _bullish_fvg_bars()
        rsm, ss = self._locked_rsm(bars, daily_bias=DailyBias.BEARISH)
        process_sweep(rsm, ss, bars, bars[-1], 0.0, "TESTUSDT")
        self.assertEqual(rsm.state_name, "IDLE")
        self.assertFalse(ss.fvg_ready)

    # ── LUNA #4b: nötr bias (yeni CBDR günü) BIAS_LOCKED'i resetler ──
    def test_bias_conflict_neutral_resets(self):
        bars = _bullish_fvg_bars()
        rsm, ss = self._locked_rsm(bars, daily_bias=DailyBias.NEUTRAL)
        process_sweep(rsm, ss, bars, bars[-1], 0.0, "TESTUSDT")
        self.assertEqual(rsm.state_name, "IDLE")

    # ── LUNA #4c: yeni CBDR döngüsü (update→_reset_for_new_cbdr_cycle) resetler ──
    def test_new_cbdr_cycle_resets(self):
        bars = _bullish_fvg_bars()
        rsm, ss = self._locked_rsm(bars)
        # SessionState.update() yeni CBDR döngüsünde (satır 441) bunu çağırır:
        # daily_bias → NEUTRAL, bias_locked → False, sweep_confirmed → False
        ss._reset_for_new_cbdr_cycle()
        process_sweep(rsm, ss, bars, bars[-1], 0.0, "TESTUSDT")
        self.assertEqual(rsm.state_name, "IDLE")

    # ── LUNA #5: son 10 ters FVG, daha eski uyumlu FVG'yi gizlemez ──
    def test_many_opposite_fvgs_do_not_hide_older_matching(self):
        bars = _opposite_barrage()
        bull = scan_htf_fvgs(
            bars,
            lookback=100,
            min_fvg_size=1e-8,
            max_wick_ratio=0.3,
            direction="bullish",
        )
        self.assertTrue(any(lv.direction == "bullish" for lv in bull))
        rsm, ss = self._locked_rsm(bars, lock_bar=0)
        process_sweep(rsm, ss, bars, bars[-1], 0.0, "TESTUSDT")
        self.assertEqual(rsm.state_name, "TRIGGER_READY")
        self.assertEqual(rsm.trigger_fvg.direction, "bullish")

    # ── LUNA #6a: touched (doldurulmuş) FVG tekrar trigger olmaz ──
    def test_touched_fvg_does_not_retrigger(self):
        bars = _bullish_fvg_bars(touch=True)
        rsm, ss = self._locked_rsm(bars)
        process_sweep(rsm, ss, bars, bars[-1], 0.0, "TESTUSDT")
        self.assertEqual(rsm.state_name, "BIAS_LOCKED")
        self.assertFalse(ss.fvg_ready)

    # ── LUNA #6b: invalidated (far-side close) FVG tekrar trigger olmaz ──
    def test_invalidated_fvg_does_not_retrigger(self):
        bars = _bullish_fvg_bars(far_close=True)
        rsm, ss = self._locked_rsm(bars)
        process_sweep(rsm, ss, bars, bars[-1], 0.0, "TESTUSDT")
        self.assertEqual(rsm.state_name, "BIAS_LOCKED")
        self.assertFalse(ss.fvg_ready)

    # ── LUNA #7: temiz state + aynı veri → aynı sonuç (determinizm) ──
    def _run_sweep_scenario(self):
        bars = _flat(20)
        rsm = RetraceStateMachine(max_wick_ratio=0.3)
        ss = SessionState(start_hour=22, end_hour=2)
        out = []
        for i in (5, 6, 7, 12):
            if i == 5:
                ss.sweep_confirmed = True
                ss.sweep_direction = "bearish"
                ss.sweep_level = 200.0
            process_sweep(rsm, ss, bars, bars[i], 0.0, "TESTUSDT")
            out.append((rsm.state_name, ss.sweep_confirmed))
        return tuple(out)

    def test_clean_state_determinism(self):
        """Bayat legacy trade_state.json kalıntısı koşular arası determinizmi bozmaz."""
        import analyzer_v5

        out_dir = os.path.join(os.path.dirname(__file__), "..", "output")
        state_file = os.path.join(out_dir, "trade_state.json")
        backup = None
        if os.path.exists(state_file):
            with open(state_file, "rb") as f:
                backup = f.read()
        try:
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump({"_used_sweeps": {"bullish_10": {"date": "2099-01-01"}}}, f)
            analyzer_v5._clean_backtest_state()
            self.assertFalse(os.path.exists(state_file))
            res1 = self._run_sweep_scenario()
            res2 = self._run_sweep_scenario()
            self.assertEqual(res1, res2)
        finally:
            if backup is not None:
                with open(state_file, "wb") as f:
                    f.write(backup)
            else:
                if os.path.exists(state_file):
                    os.remove(state_file)

    # ── LUNA #8: BIAS_LOCKED flow, canlı SignalEngine.progress_rsm ile eşleşir ──
    def test_bias_locked_matches_live_signal_engine(self):
        from trading.signal_engine import SignalEngine

        bars = _flat(40)

        def make():
            return RetraceStateMachine(max_wick_ratio=0.3), SessionState(
                start_hour=22, end_hour=2
            )

        r1, s1 = make()
        r2, s2 = make()
        engine = SignalEngine(r2)

        for i in range(5, 40):
            if i == 6:
                for ss in (s1, s2):
                    ss.sweep_confirmed = True
                    ss.sweep_direction = "bullish"
                    ss.sweep_level = 100.0
            if i == 20:
                r1.lock_bias(bar_index=15)
                r2.lock_bias(bar_index=15)
                for ss in (s1, s2):
                    ss.daily_bias = DailyBias.BULLISH
            if i == 30:
                for ss in (s1, s2):
                    ss.daily_bias = DailyBias.BEARISH
            process_sweep(r1, s1, bars, bars[i], 0.0, "TESTUSDT")
            engine.progress_rsm(bars, bars[i], s2, 0.0, "TESTUSDT")
            self.assertEqual(r1.state_name, r2.state_name, f"step={i}")
            self.assertEqual(s1.sweep_confirmed, s2.sweep_confirmed, f"step={i}")
            self.assertEqual(s1.fvg_ready, s2.fvg_ready, f"step={i}")
            self.assertEqual(r1.direction, r2.direction, f"step={i} (direction)")


if __name__ == "__main__":
    unittest.main()
