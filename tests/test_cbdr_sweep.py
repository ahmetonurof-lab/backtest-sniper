"""
test_cbdr_sweep.py — A6-01 golden testler: sweep-tüketim (sweep_sync.process_sweep).

Senaryo: aynı gün içinde art arda iki sweep.
  - Fix öncesi (bayrak temizlenmez): ilk sweep tüketildikten sonra RSM IDLE'ye
    döndüğünde AYNI sweep yeniden beslenir (ölü sinyal döngüsü — SEIUSDT
    direction-fail) ve ikinci sweep doğru şekilde algılanamaz.
  - Fix sonrası (sweep_sync): bayrak tüketimde temizlenir; ikinci sweep RSM
    meşgulken korunur ve ilk tüketilince KENDİ yön/seviyesiyle algılanır.

Kullanim:
  python tests/test_cbdr_sweep.py               # unittest direkt
  python -m pytest tests/test_cbdr_sweep.py -v  # pytest
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
from retrace_state import RetraceStateMachine
from session import SessionState
from sweep_sync import process_sweep

_DAY_MS = 1752624000000  # 2026-08-11T00:00:00Z


def _flat_bars(n=120):
    """FVG üretmeyen düz barlar — on_sweep_confirmed SWEEP_DETECTED'de kalır."""
    return [
        Bar(
            index=i,
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.0,
            volume=1.0,
            is_closed=True,
            timestamp=_DAY_MS + i * 900000,
        )
        for i in range(n)
    ]


class SweepConsumptionGoldenTests(unittest.TestCase):
    def setUp(self):
        self.bars = _flat_bars()
        self.rsm = RetraceStateMachine(max_wick_ratio=0.3)
        self.ss = SessionState(start_hour=22, end_hour=2)
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

    def _confirm_sweep(self, direction, level, idx):
        self.ss.sweep_confirmed = True
        self.ss.sweep_direction = direction
        self.ss.sweep_level = level
        process_sweep(self.rsm, self.ss, self.bars, self.bars[idx], 0.0, "TESTUSDT")

    def test_flag_cleared_after_sweep_consumption(self):
        """Fix özü: sweep tüketildiğinde bayrak temizlenir — aynı sweep tekrar beslenemez."""
        self._confirm_sweep("bearish", 200.0, 10)
        self.assertEqual(self.rsm.state_name, "SWEEP_DETECTED")
        self.assertFalse(self.ss.sweep_confirmed)

        # İlk tüketimden sonra IDLE'ye dönülse bile bayrak False olduğundan
        # aynı sweep yeniden onaylanamaz (fix öncesi ölü sinyal döngüsü engellenir).
        self.rsm.reset()
        process_sweep(self.rsm, self.ss, self.bars, self.bars[11], 0.0, "TESTUSDT")
        self.assertEqual(self.rsm.state_name, "IDLE")
        self.assertFalse(self.ss.sweep_confirmed)

    def test_second_sweep_preserved_while_first_active(self):
        """RSM SWEEP_DETECTED'deyken gelen ikinci sweep, tüketilene kadar korunur."""
        self._confirm_sweep("bearish", 200.0, 10)
        self.assertEqual(self.rsm.state_name, "SWEEP_DETECTED")

        self._confirm_sweep("bullish", 90.0, 20)
        # RSM meşgul (SWEEP_DETECTED, düz bar'da FVG yok → reset yok):
        # ikinci sweep'in bayrağı silinmemeli — ilki tüketilince algılanacak.
        self.assertEqual(self.rsm.state_name, "SWEEP_DETECTED")
        self.assertTrue(self.ss.sweep_confirmed)

    def test_second_sweep_detected_after_first_consumed(self):
        """Aynı gün iki sweep: ilki tüketilince ikincisi KENDİ yön/seviyesiyle algılanır."""
        self._confirm_sweep("bearish", 200.0, 10)
        self.assertEqual(self.rsm.direction, "bearish")
        self.assertEqual(self.rsm.sweep_level, 200.0)

        self._confirm_sweep("bullish", 90.0, 20)
        self.assertTrue(self.ss.sweep_confirmed)  # korundu

        self.rsm.reset()  # ilk sweep tüketildi (bias reddi / entry kapanışı)
        self._confirm_sweep("bullish", 90.0, 30)  # bayrak zaten True — tüketilir
        self.assertEqual(self.rsm.state_name, "SWEEP_DETECTED")
        self.assertEqual(self.rsm.direction, "bullish")
        self.assertEqual(self.rsm.sweep_level, 90.0)
        self.assertFalse(self.ss.sweep_confirmed)

    def test_pre_fix_reconsumption_loop_emulation(self):
        """Fix öncesi davranış: bayrak temizlenmezse aynı sweep tekrar tekrar beslenir.

        sweep_sync'in reset satırı olmasaydı (fix öncesi), tüketim sonrası IDLE'de
        bayrak hâlâ True olur ve AYNI sweep (bearish/200) yeniden onaylanırdı —
        SEIUSDT direction-fail döngüsünün kaynağı. Bu test regresyonu belgeler.
        """
        self._confirm_sweep("bearish", 200.0, 10)
        # Emulate pre-fix: bayrak silinmemiş gibi tekrar set et, RSM'yi IDLE'ye al.
        self.ss.sweep_confirmed = True  # (fix olmasaydı zaten True kalırdı)
        self.rsm.reset()
        process_sweep(self.rsm, self.ss, self.bars, self.bars[11], 0.0, "TESTUSDT")
        # Aynı ölü sweep yeniden tüketildi → 2. tüketim (fix öncesi döngü kanıtı).
        self.assertEqual(self.rsm.state_name, "SWEEP_DETECTED")
        self.assertEqual(self.rsm.direction, "bearish")
        self.assertEqual(self.rsm.sweep_level, 200.0)


if __name__ == "__main__":
    unittest.main()
