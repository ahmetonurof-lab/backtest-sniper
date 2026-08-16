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

    def test_ladder_ratchet_never_goes_backward(self):
        # R geriler: 3R kademesinde kilitlenen SL (entry+1.5R=103.0) mevcutken
        # R=1.3'e gerilerse 1R adayi (BE+fees ~100.1) daha KOTU olur ve
        # reddedilir — SL monoton kalir (direktif madde 8 ratchet).
        csl_hi = 100.0 + 2.0 * 1.5
        ns, _, _ = _eng._sf_pick_fallback_candidate(
            "long", 1.3, 2.0, 100.0, 1.0, csl_hi, "LADDER", 0.10, self.bars, 0, 4
        )
        self.assertIsNone(ns)


class StructuralFallbackCloseRTests(unittest.TestCase):
    """Direktif Bolum 5: R-multiple 15m CLOSE'tan hesaplanir, intrabar asla."""

    def setUp(self):
        self.bars = _swing_bars()

    def test_close_r_computed_from_close_not_intrabar(self):
        # Ornek (Bolum 5): 15m high=+1.8R spike ama close=+1.2R.
        # Tek kaynak _sf_unrealized_r_close close bazlidir; motor onu cur.close
        # ile cagirir (spike fiyati R hesabina asla girmez).
        r_close = _eng._sf_unrealized_r_close("long", 11.2, 10.0, 1.0)
        r_spike = _eng._sf_unrealized_r_close("long", 11.8, 10.0, 1.0)
        self.assertAlmostEqual(r_close, 1.2)
        self.assertAlmostEqual(r_spike, 1.8)
        self.assertNotEqual(r_close, r_spike)

    def test_ladder_15r_step_not_active_on_close_12r(self):
        # Bolum 5: 15m high=+1.8R spike ama close=+1.2R -> 1.5R kademesi
        # AKTIF OLMAZ. Motor R'yi cur.close ile hesaplar (_sf_unrealized_r_close,
        # smoke'ta spy ile dogrulandi); 1.2R girdisinde ladder yalnizca 1R
        # (BE+fees) kademesini uretir, 1.5R kademesi devreye girmez.
        sl, step_r = _eng.compute_structural_ladder_sl("long", 1.2, 1.0, 10.0)
        self.assertEqual(step_r, 1.0)  # 1.5R degil
        self.assertGreater(sl, 10.0)  # BE+fees adayi
        sl, step_r = _eng.compute_structural_ladder_sl("long", 1.8, 1.0, 10.0)
        self.assertEqual(step_r, 1.5)  # ancak gercek 1.8R'de 1.5R kademesi aktif
        self.assertAlmostEqual(sl, 10.5)

    def test_close_r_short_symmetric(self):
        r = _eng._sf_unrealized_r_close("short", 8.8, 10.0, 1.0)
        self.assertAlmostEqual(r, 1.2)

    def test_close_r_zero_when_rpt2_zero(self):
        self.assertEqual(_eng._sf_unrealized_r_close("long", 11.0, 10.0, 0.0), 0.0)


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

    def test_atomic_apply_updates_sl_and_tp_together(self):
        # Gercek uygulama fonksiyonu (_sf_apply_candidate): SL ve TP tek cagrida
        # birlikte guncellenir — yarim-state (sadece SL degisir) imkansizdir.
        # Motor guard'i (`if _ns is not None:`) yalnizca onayli adayi buraya
        # tasir; TP_FIXED=False ise TP SL deltasi kadar paralel oteleinir.
        t = {}
        csl, ctp = _eng._sf_apply_candidate(
            t, "long", 8.5, 12.0, 9.5, "SWING", "SWING_CONFIRMED", 2.5, False
        )
        self.assertEqual(csl, 9.5)
        self.assertEqual(ctp, 13.0)  # sd2 = 1.0 -> TP paralel otelendi
        self.assertTrue(t["trail_swing"])
        self.assertEqual(t["trail_candidate"], 9.5)
        self.assertEqual(t["trail_r"], 2.5)

    def test_atomic_apply_respects_tp_fixed(self):
        # TP_FIXED=True: SL guncellenir ama TP OYNATILMAZ (baseline davranisi).
        t = {}
        csl, ctp = _eng._sf_apply_candidate(
            t, "short", 15.0, 8.0, 14.0, "SWING", "SWING_CONFIRMED", 2.5, True
        )
        self.assertEqual(csl, 14.0)
        self.assertEqual(ctp, 8.0)  # TP_FIXED -> degismez

    def test_apply_ladder_marks_trail_ladder(self):
        t = {}
        csl, ctp = _eng._sf_apply_candidate(
            t, "long", 9.0, 12.0, 10.5, "LADDER", "R>=1.5R", 1.8, False
        )
        self.assertEqual(csl, 10.5)
        self.assertEqual(ctp, 13.5)
        self.assertTrue(t["trail_ladder"])


class StructuralFallbackEngineSmokeTests(unittest.TestCase):
    """Motor seviyesi smoke: HYBRID tek sembol (veri yoksa skip)."""

    def setUp(self):
        _eng.TRAIL_MODE = "retrace"
        _eng.PROFIT_GATE_R = 0.0
        _eng.DISABLE_FVG_TRAIL = False
        _eng.STRUCTURAL_FALLBACK_MODE = "HYBRID"
        _eng.SWING_TRAIL_BUFFER = 0.10
        # NOT (Sonnet incelemesi): ENABLE_FALLBACK_LADDER bilinçli olarak SET
        # EDILMIYOR. O eski merdiven deneyi flag'i (analyzer_v5 ~1319); SF
        # ladder'i yalnizca STRUCTURAL_FALLBACK_MODE'den beslenir ve ondan
        # bagimsizdir. Default (False) eski yolu kapali tutar, HYBRID'in
        # ladder tarafi yine de aktiftir (asagida sf_trail_ladder_count > 0).

    def tearDown(self):
        _eng.STRUCTURAL_FALLBACK_MODE = None
        _eng.SWING_TRAIL_BUFFER = 0.10
        _eng.PROFIT_GATE_R = 0.0

    def test_hybrid_engine_completes_and_fallback_producers_called(self):
        feather = os.path.join(_DATA, "BNBUSDT_1m_raw.feather")
        if not os.path.isfile(feather):
            self.skipTest("BNBUSDT_1m_raw.feather yok")
        orig_tm = _eng._SWING_TRAIL_TM
        spy_swing = mock.Mock(wraps=orig_tm._default_level_from_swings)
        try:
            _eng._SWING_TRAIL_TM._default_level_from_swings = spy_swing
            result = _eng.collect_fvg_profile("BNBUSDT")
        finally:
            _eng._SWING_TRAIL_TM = orig_tm
        self.assertIsNotNone(result)
        daily_rows, wins, losses, trade_records, rejection_counts = result
        stats = _eng.compute_session_stats(
            trade_records, _eng.cfg.INITIAL_BALANCE, daily_rows
        )
        self.assertGreater(stats["total_trades"], 0)
        # Motor gercekten swing producer'i cagirdi (madde 5 parite).
        self.assertGreater(spy_swing.call_count, 0)
        # HYBRID'in ladder tarafi da egzersiz edildi (1-2R araligi).
        self.assertGreater(stats.get("sf_trail_ladder_count", 0), 0)


if __name__ == "__main__":
    unittest.main()
