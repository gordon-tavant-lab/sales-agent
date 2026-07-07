"""Stdlib-only tests for score.py — no external test runner required.

Run: python3 test_score.py
"""
import unittest

from score import (
    CALIBRATION_FLOOR,
    apply_display_mode,
    compute_confidence,
    confidence_band,
    expected_value,
    meddpicc_score,
    rank_shortlist,
    resolve_calibration_n,
)


class MeddpiccScoreTests(unittest.TestCase):
    def test_sums_all_eight_dimensions(self):
        self.assertEqual(meddpicc_score([3, 3, 3, 3, 3, 3, 3, 3]), 24)
        self.assertEqual(meddpicc_score([0, 0, 0, 0, 0, 0, 0, 0]), 0)

    def test_rejects_wrong_dimension_count(self):
        with self.assertRaises(ValueError):
            meddpicc_score([1, 2, 3])

    def test_rejects_out_of_range_score(self):
        with self.assertRaises(ValueError):
            meddpicc_score([4, 0, 0, 0, 0, 0, 0, 0])


class ConfidenceTests(unittest.TestCase):
    def test_uncalibrated_shows_band_not_percent(self):
        conf = compute_confidence([3, 3, 3, 3, 3, 3, 3, 3], calibration_n=0)
        self.assertEqual(conf["calibration_state"], "uncalibrated")
        self.assertIn("display_band", conf)
        self.assertNotIn("display_percent", conf)
        self.assertEqual(conf["confidence_value"], 1.0)

    def test_calibrated_shows_percent_not_band(self):
        conf = compute_confidence([3, 3, 3, 3, 3, 3, 3, 3], calibration_n=CALIBRATION_FLOOR)
        self.assertEqual(conf["calibration_state"], "calibrated(n={})".format(CALIBRATION_FLOOR))
        self.assertIn("display_percent", conf)
        self.assertNotIn("display_band", conf)

    def test_confidence_value_always_computed_regardless_of_calibration(self):
        uncal = compute_confidence([2, 2, 2, 2, 2, 2, 2, 2], calibration_n=0)
        cal = compute_confidence([2, 2, 2, 2, 2, 2, 2, 2], calibration_n=CALIBRATION_FLOOR)
        self.assertEqual(uncal["confidence_value"], cal["confidence_value"])

    def test_band_thresholds(self):
        self.assertEqual(confidence_band(0.9), "High")
        self.assertEqual(confidence_band(0.5), "Medium")
        self.assertEqual(confidence_band(0.1), "Low")


class ExpectedValueTests(unittest.TestCase):
    def test_multiplies_all_four_factors(self):
        self.assertEqual(expected_value(0.5, 0.5, 100, 0.5), 12.5)

    def test_zero_any_factor_zeroes_the_score(self):
        self.assertEqual(expected_value(0.0, 0.9, 500000, 0.8), 0.0)


class RankShortlistTests(unittest.TestCase):
    def setUp(self):
        # 3 hunt, 2 expand — deliberately gives expand the higher raw expected_value
        # to prove the floor protects hunt from being starved (spec §5 / §10 stress case).
        self.opps = [
            {"id": "h1", "motion": "hunt", "meddpicc": [1, 1, 1, 0, 1, 1, 1, 1],
             "strategic_fit": 0.5, "deal_value": 100000, "winnability_factors": 0.3},
            {"id": "h2", "motion": "hunt", "meddpicc": [1, 1, 1, 1, 1, 1, 1, 0],
             "strategic_fit": 0.4, "deal_value": 100000, "winnability_factors": 0.3},
            {"id": "h3", "motion": "hunt", "meddpicc": [0, 1, 0, 0, 1, 0, 0, 1],
             "strategic_fit": 0.3, "deal_value": 100000, "winnability_factors": 0.2},
            {"id": "e1", "motion": "expand", "meddpicc": [3, 3, 3, 3, 3, 3, 3, 3],
             "strategic_fit": 0.9, "deal_value": 500000, "winnability_factors": 0.9},
            {"id": "e2", "motion": "expand", "meddpicc": [3, 3, 3, 3, 3, 3, 3, 3],
             "strategic_fit": 0.9, "deal_value": 400000, "winnability_factors": 0.9},
        ]

    def test_floor_protects_hunt_even_when_expand_outscores_it(self):
        result = rank_shortlist(self.opps, capacity=3, floor={"hunt": 2, "expand": 0})
        shortlist_ids = {o["id"] for o in result["shortlist"]}
        hunt_in_shortlist = {i for i in shortlist_ids if i.startswith("h")}
        self.assertGreaterEqual(len(hunt_in_shortlist), 2,
                                 "hunt floor must be filled even though expand scores higher")

    def test_shortlist_size_matches_capacity_when_enough_opportunities_exist(self):
        result = rank_shortlist(self.opps, capacity=3, floor={"hunt": 1, "expand": 1})
        self.assertEqual(len(result["shortlist"]), 3)

    def test_parked_items_carry_promotion_gap(self):
        result = rank_shortlist(self.opps, capacity=2, floor={"hunt": 1, "expand": 0})
        self.assertTrue(len(result["parked"]) > 0)
        for o in result["parked"]:
            self.assertIn("promotion_gap", o)
            self.assertIn("parked_reason", o)
            self.assertGreaterEqual(o["promotion_gap"], 0)

    def test_parked_reason_flags_floor_displacement_not_score(self):
        # e1/e2 outscore h1 on raw expected_value but hunt's floor still protects h1's slot —
        # e2 should be parked for capacity, not for scoring below the cutoff.
        result = rank_shortlist(self.opps, capacity=3, floor={"hunt": 2, "expand": 0})
        parked_ids = {o["id"]: o for o in result["parked"]}
        self.assertIn("e2", parked_ids)
        self.assertEqual(parked_ids["e2"]["parked_reason"], "capacity_consumed_by_motion_floor")
        self.assertEqual(parked_ids["e2"]["promotion_gap"], 0)

    def test_warns_when_floor_exceeds_available_opportunities(self):
        result = rank_shortlist(self.opps, capacity=10, floor={"hunt": 5, "expand": 0})
        self.assertIn("warnings", result)


class DisplayModeTests(unittest.TestCase):
    """F10: a caveat label next to a raw percentage doesn't defeat anchoring — the raw value
    must be structurally absent, not just cosmetically relabeled."""

    def test_single_score_strips_raw_value_while_uncalibrated(self):
        conf = compute_confidence([2, 3, 1, 2, 3, 2, 1, 2], calibration_n=0)
        displayed = apply_display_mode(conf)
        self.assertNotIn("confidence_value", displayed)
        self.assertNotIn("meddpicc_raw", displayed)
        self.assertNotIn("meddpicc_max", displayed)
        self.assertEqual(displayed["calibration_state"], "uncalibrated")
        self.assertIn("display_band", displayed)

    def test_single_score_keeps_raw_value_once_calibrated(self):
        conf = compute_confidence([2, 3, 1, 2, 3, 2, 1, 2], calibration_n=CALIBRATION_FLOOR)
        displayed = apply_display_mode(conf)
        self.assertIn("confidence_value", displayed)
        self.assertIn("display_percent", displayed)

    def test_rank_shortlist_strips_raw_value_in_every_entry(self):
        opps = [
            {"id": "h1", "motion": "hunt", "meddpicc": [2, 2, 2, 2, 2, 2, 2, 2],
             "calibration_n": 0, "strategic_fit": 0.8, "deal_value": 100000,
             "winnability_factors": 0.5},
            {"id": "e1", "motion": "expand", "meddpicc": [1, 1, 1, 1, 1, 1, 1, 1],
             "calibration_n": 0, "strategic_fit": 0.7, "deal_value": 80000,
             "winnability_factors": 0.4},
        ]
        result = rank_shortlist(opps, capacity=2, floor={})
        displayed = apply_display_mode(result)
        for o in displayed["shortlist"] + displayed["parked"]:
            self.assertNotIn("confidence_value", o["confidence"])
        # non-confidence fields untouched
        self.assertEqual(displayed["capacity"], 2)


class ResolveCalibrationNTests(unittest.TestCase):
    """F5: calibration_n can come from the growing backtest artifact instead of being
    hand-tracked — this is what makes score.py's --calibration-n actually update as real
    outcomes accrue via close_out.py, instead of staying a manually-typed number forever."""

    def test_no_backtest_file_uses_explicit_calibration_n(self):
        self.assertEqual(resolve_calibration_n(42, None), 42)

    def test_backtest_file_overrides_with_its_own_length(self):
        import json
        import os
        import tempfile

        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            with open(path, "w") as f:
                json.dump([{"id": "a"}, {"id": "b"}, {"id": "c"}], f)
            self.assertEqual(resolve_calibration_n(0, path), 3)
        finally:
            os.remove(path)


if __name__ == "__main__":
    unittest.main()
