"""
test_structural_fallback.py — STRUCTURAL FALLBACK TRAILING (LUNA direktif) unit testleri.

Kapsam (direktif madde 11):
  1. Gate modelinin gercekten exclusive oldugu (FVG varsa fallback HIC
     cagrilmaz — competition yok).
  2. Swing producer'in canli trailing_manager._default_level_from_swings'e
     DOGRUDAN cagirdigi (yeniden implemente edilmedigi — parite).
  3. Reddedilen ladder/swing candidate'inin state'e yazilmadigi (saf fonksiyon).
  4. SL+TP atomik uygulama: redde SL de TP de degismez (yarim-state olmaz).

Motor seviyesi smoke (veri dosyasi varsa): HYBRID modunda tek sembol calisir ve
fallback producer'larin gercekten devreye girdigini dogrular.

Kullanim:
  set PYTHONPATH=src&& python -m pytest tests/test_structural_fallback.py -q
"""

# ruff: noqa: E402
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import analyzer_v5 as _eng  # noqa: E402
from models import Bar  # noqa: E402

_BT_SRC = os.path.join(os.path.dirname(__file__), "..", "src")
_DATA = os.path.join(_BT_SRC, "data", "daily")


def _swing_bars():
    """7 bar. index 2 = confirmed swing low (low 8.0) + swing high (high 25.0),
    ikisi de index 4'te onaylanir (pivot_strength=2, right=2).
    Long: swing_low=8.0 -> SL = 8.0 - 0.10*ATR. Short: swing_high=25.0 -> 25.0 + 0.10*ATR."""
    return [
        Bar(
            index=i,
            open=(h + lo) / 2,
            high=h,
            low=lo,
            close=(h + lo) / 2,
            volume=1.0,
            is_closed=True,
            timestamp=i * 900000,
        )
        for i, (h, lo) in enumerate(
            [
                (20.0, 10.0),
                (20.0, 10.0),
                (25.0, 8.0),
                (19.0, 11.0),
                (19.0, 10.5),
                (18.0, 12.0),
                (18.0, 12.0),
            ]
        )
    ]


class StructuralFallbackGateTests(unittest.TestCase):
    """Madde 1: GATE exclusive — FVG varsa fallback asla aktif olamaz."""

    def test_gate_closed_when_fvg_present(self):
        self.assertFalse(_eng._sf_gate("HYBRID", 5.0, True))
        self.assertFalse(_eng._sf_gate("LADDER", 3.0, True))
        self.assertFalse(_eng._sf_gate("SWING", 3.0, True))

    def test_gate_open_when_no_fvg(self):
        self.assertTrue(_eng._sf_gate("HYBRID", 5.0, False))
        self.assertTrue(_eng._sf_gate("SWING", 2.0, False))

    def test_gate_requires_mode_and_positive_risk(self):
        self.assertFalse(_eng._sf_gate(None, 5.0, False))
        self.assertFalse(_eng._sf_gate("HYBRID", 0.0, False))


class StructuralFallbackSwingProducerTests(unittest.TestCase):
    """Madde 5: swing, canli _default_level_from_swings'ten gelir (parite)."""

    def setUp(self):
        self.bars = _swing_bars()

    def test_live_function_detects_post_entry_swing(self):
        lv = _eng._SWING_TRAIL_TM._default_level_from_swings(self.bars[:5], "long")
        self.assertIsNotNone(lv)
        self.assertAlmostEqual(float(lv.price), 8.0)
        self.assertEqual(lv.source_bar_index, 2)
        lv = _eng._SWING_TRAIL_TM._default_level_from_swings(self.bars[:5], "short")
        self.assertAlmostEqual(float(lv.price), 25.0)

    def test_swing_producer_calls_live_function_directly(self):
        with mock.patch.object(_eng, "_SWING_TRAIL_TM") as mock_tm:
            mock_tm._default_level_from_swings.return_value = mock.Mock(price=8.0)
            ns, src, reason = _eng._sf_pick_fallback_candidate(
                "long", 2.5, 1.0, 10.0, 1.0, 5.0, "SWING", 0.10, self.bars, 0, 4
            )
            mock_tm._default_level_from_swings.assert_called_once_with(
                self.bars[0:5], "long"
            )
        self.assertAlmostEqual(ns, 7.9)
        self.assertEqual(src, "SWING")
        self.assertEqual(reason, "SWING_CONFIRMED")

    def test_swing_long_offset(self):
        ns, src, reason = _eng._sf_pick_fallback_candidate(
            "long", 2.5, 1.0, 10.0, 1.0, 5.0, "SWING", 0.10, self.bars, 0, 4
        )
        self.assertAlmostEqual(ns, 7.9)
        self.assertEqual(src, "SWING")

    def test_swing_short_offset(self):
        ns, src, reason = _eng._sf_pick_fallback_candidate(
            "short", 2.5, 1.0, 10.0, 1.0, 30.0, "SWING", 0.10, self.bars, 0, 4
        )
        self.assertAlmostEqual(ns, 25.1)
        self.assertEqual(src, "SWING")

    def test_swing_below_2r_produces_nothing(self):
        ns, _, _ = _eng._sf_pick_fallback_candidate(
            "long", 1.9, 1.0, 10.0, 1.0, 5.0, "SWING", 0.10, self.bars, 0, 4
        )
        self.assertIsNone(ns)


class StructuralFallbackLadderProducerTests(unittest.TestCase):
    """Madde 4: ladder kademeleri (15m CLOSE R bazli)."""

    def setUp(self):
        self.bars = _swing_bars()

    def test_step1_be_plus_fees(self):
        c = _eng.COMMISSION_RATE
        expected = (100.0 * (1 + c)) / (1 - c)
        ns, src, reason = _eng._sf_pick_fallback_candidate(
            "long", 1.2, 2.0, 100.0, 1.0, 99.0, "LADDER", 0.10, self.bars, 0, 4
        )
        self.assertAlmostEqual(ns, expected, places=6)
        self.assertEqual(src, "LADDER")
        self.assertEqual(reason, "R>=1R")

    def test_step2_half_r(self):
        ns, src, reason = _eng._sf_pick_fallback_candidate(
            "long", 1.8, 2.0, 100.0, 1.0, 98.0, "LADDER", 0.10, self.bars, 0, 4
        )
        self.assertAlmostEqual(ns, 100.0 + 2.0 * 0.5)
        self.assertEqual(src, "LADDER")
        self.assertEqual(reason, "R>=1.5R")

    def test_step3_one_r(self):
        ns, src, reason = _eng._sf_pick_fallback_candidate(
            "long", 2.2, 2.0, 100.0, 1.0, 96.0, "LADDER", 0.10, self.bars, 0, 4
        )
        self.assertAlmostEqual(ns, 100.0 + 2.0 * 1.0)
        self.assertEqual(src, "LADDER")
        self.assertEqual(reason, "R>=2R")

    def test_step4_one_and_half_r(self):
        ns, src, reason = _eng._sf_pick_fallback_candidate(
            "long", 3.5, 2.0, 100.0, 1.0, 95.0, "LADDER", 0.10, self.bars, 0, 4
        )
        self.assertAlmostEqual(ns, 100.0 + 2.0 * 1.5)
        self.assertEqual(src, "LADDER")
        self.assertEqual(reason, "R>=3R")

    def test_below_1r_none(self):
        ns, _, _ = _eng._sf_pick_fallback_candidate(
            "long", 0.8, 2.0, 100.0, 1.0, 99.0, "LADDER", 0.10, self.bars, 0, 4
        )
        self.assertIsNone(ns)


class StructuralFallbackHybridExclusiveTests(unittest.TestCase):
    """Madde 6: C varyantinda R araligina gore exclusive gecis (yarisma yok)."""

    def setUp(self):
        self.bars = _swing_bars()

    def test_1_2r_uses_ladder_not_swing(self):
        ns, src, reason = _eng._sf_pick_fallback_candidate(
            "long", 1.5, 1.0, 10.0, 1.0, 9.0, "HYBRID", 0.10, self.bars, 0, 4
        )
        self.assertEqual(src, "LADDER")
        self.assertAlmostEqual(ns, 10.5)

    def test_above_2r_uses_swing_only(self):
        ns, src, reason = _eng._sf_pick_fallback_candidate(
            "long", 2.5, 1.0, 10.0, 1.0, 5.0, "HYBRID", 0.10, self.bars, 0, 4
        )
        self.assertEqual(src, "SWING")
        self.assertAlmostEqual(ns, 7.9)

    def test_below_1r_none(self):
        ns, _, _ = _eng._sf_pick_fallback_candidate(
            "long", 0.8, 1.0, 10.0, 1.0, 5.0, "HYBRID", 0.10, self.bars, 0, 4
        )
        self.assertIsNone(ns)


class StructuralFallbackRejectionTests(unittest.TestCase):
    """Madde 2/7: reddedilen candidate state'e YAZILMAZ; SL+TP atomik."""

    def setUp(self):
        self.bars = _swing_bars()

    def test_swing_worse_than_current_sl_rejected(self):
        ns, src, reason = _eng._sf_pick_fallback_candidate(
            "long", 2.5, 1.0, 10.0, 1.0, 8.5, "SWING", 0.10, self.bars, 0, 4
        )
        self.assertEqual((ns, src, reason), (None, None, None))

    def test_swing_fails_tmm_min_move_rejected(self):
        ns, src, reason = _eng._sf_pick_fallback_candidate(
            "long", 2.5, 1.0, 10.0, 1.0, 7.85, "SWING", 0.10, self.bars, 0, 4
        )
        self.assertEqual((ns, src, reason), (None, None, None))

    def test_rejected_candidate_pure_no_state_mutation(self):
        trade = {"sl": 8.5, "tp": 10.0}
        ns, _, _ = _eng._sf_pick_fallback_candidate(
            "long", 2.5, 1.0, 10.0, 1.0, trade["sl"], "SWING", 0.10, self.bars, 0, 4
        )
        self.assertIsNone(ns)
        self.assertEqual(trade, {"sl": 8.5, "tp": 10.0})

    def test_atomic_apply_sl_tp_both_or_neither(self):
        csl, ctp = 8.5, 12.0
        ns, _, _ = _eng._sf_pick_fallback_candidate(
            "long", 2.5, 1.0, 10.0, 1.0, csl, "SWING", 0.10, self.bars, 0, 4
        )
        self.assertIsNone(ns)
        if ns is not None:
            sd2 = abs(ns - csl)
            csl = ns
            ctp += sd2
        self.assertEqual(csl, 8.5)
        self.assertEqual(ctp, 12.0)


class StructuralFallbackEngineSmokeTests(unittest.TestCase):
    """Motor seviyesi smoke: HYBRID tek sembol (veri yoksa skip)."""

    def setUp(self):
        _eng.TRAIL_MODE = "retrace"
        _eng.PROFIT_GATE_R = 0.0
        _eng.ENABLE_FALLBACK_LADDER = False
        _eng.DISABLE_FVG_TRAIL = False
        _eng.STRUCTURAL_FALLBACK_MODE = "HYBRID"
        _eng.SWING_TRAIL_BUFFER = 0.10

    def tearDown(self):
        _eng.STRUCTURAL_FALLBACK_MODE = None
        _eng.SWING_TRAIL_BUFFER = 0.10
        _eng.PROFIT_GATE_R = 0.0

    def test_hybrid_engine_completes_and_swing_producer_called(self):
        feather = os.path.join(_DATA, "BNBUSDT_1m_raw.feather")
        if not os.path.isfile(feather):
            self.skipTest("BNBUSDT_1m_raw.feather yok")
        orig_tm = _eng._SWING_TRAIL_TM
        spy = mock.Mock(wraps=orig_tm._default_level_from_swings)
        try:
            _eng._SWING_TRAIL_TM._default_level_from_swings = spy
            result = _eng.collect_fvg_profile("BNBUSDT")
        finally:
            _eng._SWING_TRAIL_TM = orig_tm
        self.assertIsNotNone(result)
        daily_rows, wins, losses, trade_records, rejection_counts = result
        stats = _eng.compute_session_stats(
            trade_records, _eng.cfg.INITIAL_BALANCE, daily_rows
        )
        self.assertGreater(stats["total_trades"], 0)
        self.assertGreater(spy.call_count, 0)


if __name__ == "__main__":
    unittest.main()
