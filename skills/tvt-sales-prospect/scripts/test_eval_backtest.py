"""Stdlib-only tests for eval_backtest.py. Run: python3 test_eval_backtest.py"""
import unittest

from eval_backtest import (
    MIN_N_FOR_CALIBRATION,
    brier_score,
    calibration_curve,
    drift_check,
    run_eval,
    shortlist_precision,
)


def _rec(id_, conf, shortlisted, outcome):
    return {"id": id_, "confidence_value": conf, "was_shortlisted": shortlisted, "outcome": outcome}


class BrierScoreTests(unittest.TestCase):
    def test_perfect_predictions_score_zero(self):
        labeled = [_rec("1", 1.0, True, "won"), _rec("2", 0.0, False, "lost")]
        result = brier_score(labeled)
        self.assertEqual(result["value"], 0.0)

    def test_worst_case_predictions_score_one(self):
        labeled = [_rec("1", 1.0, True, "lost"), _rec("2", 0.0, False, "won")]
        result = brier_score(labeled)
        self.assertEqual(result["value"], 1.0)

    def test_flags_statistical_meaningfulness_below_floor(self):
        labeled = [_rec(str(i), 0.5, True, "won") for i in range(10)]
        result = brier_score(labeled)
        self.assertFalse(result["statistically_meaningful"])
        self.assertEqual(result["min_n_floor"], MIN_N_FOR_CALIBRATION)

    def test_empty_dataset_returns_none(self):
        result = brier_score([])
        self.assertIsNone(result["value"])


class CalibrationCurveTests(unittest.TestCase):
    def test_bins_predicted_vs_actual(self):
        labeled = [
            _rec("1", 0.85, True, "won"),
            _rec("2", 0.90, True, "lost"),
            _rec("3", 0.10, False, "lost"),
            _rec("4", 0.15, False, "lost"),
        ]
        result = calibration_curve(labeled, n_bins=5)
        self.assertEqual(len(result["bins"]), 5)
        top_bin = result["bins"][-1]
        self.assertEqual(top_bin["n"], 2)
        self.assertEqual(top_bin["actual_win_rate"], 0.5)

    def test_empty_bins_report_zero_not_crash(self):
        result = calibration_curve([_rec("1", 0.05, True, "won")], n_bins=5)
        empty_bins = [b for b in result["bins"] if b["n"] == 0]
        self.assertTrue(len(empty_bins) > 0)
        for b in empty_bins:
            self.assertIsNone(b["predicted_mean"])


class ShortlistPrecisionTests(unittest.TestCase):
    def test_only_counts_shortlisted_items(self):
        labeled = [
            _rec("1", 0.8, True, "won"),
            _rec("2", 0.8, True, "lost"),
            _rec("3", 0.1, False, "won"),  # not shortlisted — must not count
        ]
        result = shortlist_precision(labeled)
        self.assertEqual(result["n_shortlisted"], 2)
        self.assertEqual(result["value"], 0.5)

    def test_no_shortlisted_items_returns_none(self):
        result = shortlist_precision([_rec("1", 0.1, False, "lost")])
        self.assertIsNone(result["value"])


class DriftCheckTests(unittest.TestCase):
    def test_no_prior_period(self):
        result = drift_check(0.2, None)
        self.assertEqual(result["status"], "no_prior_period")

    def test_flags_worsening_brier_as_p1_above_calibration_floor(self):
        result = drift_check(current_brier=0.3, prior_brier=0.2, n_labeled=150)
        self.assertIn("WORSENING", result["status"])
        self.assertIn("P1", result["status"])

    def test_worsening_below_floor_is_informational_not_p1(self):
        # A quarter at this portfolio's n holds ~1-5 outcomes; any delta is coin-flip
        # variance. A P1 that always fires trains its operator to ignore it.
        result = drift_check(current_brier=0.3, prior_brier=0.2, n_labeled=5)
        self.assertNotIn("P1", result["status"])
        self.assertIn("not_significant", result["status"])
        self.assertEqual(result["n_labeled"], 5)

    def test_improving_brier_is_not_flagged(self):
        result = drift_check(current_brier=0.15, prior_brier=0.2, n_labeled=5)
        self.assertEqual(result["status"], "stable_or_improving")


class RunEvalTests(unittest.TestCase):
    def test_produces_all_four_sections(self):
        labeled = [_rec(str(i), 0.5 + (i % 2) * 0.3, i % 3 == 0, "won" if i % 2 == 0 else "lost")
                   for i in range(20)]
        result = run_eval(labeled, prior_brier=0.25)
        self.assertIn("brier_score", result)
        self.assertIn("calibration_curve", result)
        self.assertIn("shortlist_precision", result)
        self.assertIn("drift_check", result)


if __name__ == "__main__":
    unittest.main()
