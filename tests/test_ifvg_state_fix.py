"""
test_ifvg_state_fix.py — IFVG state-fix regresyon testleri.

Sorun (17K normal trade bastirmasi): IFVG entry'si RSM state makinesini
kirletiyordu — trigger aninda rsm.direction IFVG yonune cekiliyor, entry
sonrasi lock_bias() ters yon kilidi yapiyor, bias_conflict -> reset ile
gunun sweep penceresi oluyordu. Fix (devir eki karari / Bas Mühendis onayi):

  - sweep_sync: IFVG trigger aninda rsm._pre_ifvg_direction = sweep/bias yonu
    saklanir (entry side hesabi icin direction yine IFVG yonune cekilir).
  - analyzer_v5 entry: IFVG kaynakli entry'de yon giris oncesi sweep/bias
    yonune geri alinir ve normal entry gibi BIAS_LOCKED'a gecilir.
  - IFVG_ENABLED=False iken hicbir yeni attribut/referans kullanilmaz
    -> davranis bit-bit bugunku ile ayni (cikis sarti 3).

Kullanim:
  python -m pytest tests/test_ifvg_state_fix.py -v
"""

# ruff: noqa: E402
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
from retrace_state import RetraceStateMachine, RetraceState
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


def _flat(n=9):
    """FVG üretmeyen düz barlar."""
    return [_bar(i, 100, 101, 99, 100) for i in range(n)]


def _ifvg_scenario_bars():
    """Bullish sweep + bullish FVG [100,103] + body-break (inverted aday) + retest.

    Bar 12: bullish FVG body-break (close 99 < 100) -> inverted bearish aday.
    Bar 13: bearish retest touch (high 104 >= 100, close 99.5 <= 103) -> IFVG hit.
    """
    bars = _flat(9)
    bars.append(_bar(9, 99, 100, 98, 99))  # FVG 1. mum
    bars.append(_bar(10, 101, 101, 100.6, 101))  # FVG 2. mum (impulse)
    bars.append(_bar(11, 103.5, 104, 103, 104))  # FVG 3. mum -> [100, 103]
    bars.append(_bar(12, 102, 102.5, 98, 99))  # body-break -> inverted
    bars.append(_bar(13, 100, 104, 99, 99.5))  # IFVG retest touch
    return bars


class IFVGStateFixTests(unittest.TestCase):
    def setUp(self):
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

    def _make_ss(self):
        ss = SessionState(start_hour=22, end_hour=2)
        ss.daily_bias = DailyBias.BULLISH
        ss.sweep_confirmed = True
        ss.sweep_direction = "bullish"
        ss.sweep_level = 98.0
        return ss

    # ── Cikis sarti 3: IFVG_ENABLED=False -> bit-bit ayni davranis ──
    def test_flag_off_no_side_effect(self):
        """Flag kapaliyken ayni senaryo: IFVG blogu hic devreye girmez;
        _pre_ifvg_direction yok, source NORMAL, state SWEEP_DETECTED kalir."""
        bars = _ifvg_scenario_bars()
        rsm = RetraceStateMachine(max_wick_ratio=0.3)
        ss = self._make_ss()
        with mock.patch("config.IFVG_ENABLED", False):
            process_sweep(rsm, ss, bars, bars[12], 0.0, "TESTUSDT")
        self.assertEqual(rsm.state_name, "SWEEP_DETECTED")
        self.assertEqual(rsm.direction, "bullish")
        self.assertEqual(rsm._last_trigger_source, "NORMAL")
        self.assertFalse(hasattr(rsm, "_pre_ifvg_direction"))
        self.assertFalse(ss.fvg_ready)

    def test_flag_off_never_enters_trigger_ready_from_ifvg(self):
        """Flag kapaliyken IFVG adayları check_ifvg_retest'i tetikleyemez."""
        bars = _ifvg_scenario_bars()
        rsm = RetraceStateMachine(max_wick_ratio=0.3)
        ss = self._make_ss()
        with mock.patch("config.IFVG_ENABLED", False):
            process_sweep(rsm, ss, bars, bars[13], 0.0, "TESTUSDT")
        self.assertEqual(rsm.state_name, "SWEEP_DETECTED")
        self.assertEqual(rsm._last_trigger_source, "NORMAL")

    # ── Fix: IFVG trigger aninda sweep/bias yonu saklanir ──
    def test_flag_on_saves_sweep_direction(self):
        """Flag acikken bar 12'de IFVG tetiklenir: direction IFVG yonune cekilir
        AMA _pre_ifvg_direction sweep yonunu (bullish) korur."""
        bars = _ifvg_scenario_bars()
        rsm = RetraceStateMachine(max_wick_ratio=0.3)
        ss = self._make_ss()
        with mock.patch("config.IFVG_ENABLED", True):
            process_sweep(rsm, ss, bars, bars[12], 0.0, "TESTUSDT")
        self.assertEqual(rsm.state_name, "TRIGGER_READY")
        self.assertEqual(rsm._last_trigger_source, "IFVG")
        self.assertEqual(rsm.direction, "bearish")  # entry side hesabi icin
        self.assertEqual(rsm._pre_ifvg_direction, "bullish")  # sweep/bias yonu
        self.assertTrue(ss.fvg_ready)

    # ── Fix: entry sonrasi restore + BIAS_LOCKED (analyzer_v5 parity snippet) ──
    def test_restore_locks_sweep_direction_not_ifvg_direction(self):
        """IFVG entry kapanisi: direction sweep/bias yonune geri alinir,
        lock_bias() normal entry gibi BIAS_LOCKED uretir (ters yon kilidi yok)."""
        bars = _ifvg_scenario_bars()
        rsm = RetraceStateMachine(max_wick_ratio=0.3)
        ss = self._make_ss()
        with mock.patch("config.IFVG_ENABLED", True):
            process_sweep(rsm, ss, bars, bars[12], 0.0, "TESTUSDT")
        self.assertEqual(rsm.state_name, "TRIGGER_READY")
        # analyzer_v5.py entry-restore snippet (birebir kopya):
        if getattr(rsm, "_last_trigger_source", None) == "IFVG":
            rsm.direction = getattr(rsm, "_pre_ifvg_direction", None) or rsm.direction
        rsm.lock_bias(bar_index=12)
        self.assertEqual(rsm.state_name, "BIAS_LOCKED")
        self.assertEqual(rsm.direction, "bullish")

    def test_normal_entry_lock_unchanged(self):
        """NORMAL kaynakli entry'de restore yapilmaz — direction ayni kalir."""
        rsm = RetraceStateMachine(max_wick_ratio=0.3)
        rsm.on_sweep("bullish", 98.0, bar_index=12)
        rsm.state = RetraceState.TRIGGER_READY
        rsm.direction = "bullish"
        rsm._last_trigger_source = "NORMAL"
        rsm.lock_bias(bar_index=12)
        self.assertEqual(rsm.state_name, "BIAS_LOCKED")
        self.assertEqual(rsm.direction, "bullish")


if __name__ == "__main__":
    unittest.main()
