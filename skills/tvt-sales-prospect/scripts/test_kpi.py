"""Stdlib-only tests for kpi.py. Run: python3 test_kpi.py"""
import unittest

from kpi import (
    BENCHMARK_COVERAGE_HUNT,
    BENCHMARK_WIN_RATE_MEDIAN,
    case_study_yield,
    cycle_length_days,
    pattern_reuse_rate,
    pipeline_coverage,
    scorecard,
    stage_conversion,
    win_rate,
)


def _opp(id_, motion, stage, amount, created, closed=None, pov_cites_pattern=None,
         case_study_produced=None):
    o = {"id": id_, "motion": motion, "stage": stage, "amount": amount,
         "created_date": created, "close_date": closed}
    if pov_cites_pattern is not None:
        o["pov_cites_pattern"] = pov_cites_pattern
    if case_study_produced is not None:
        o["case_study_produced"] = case_study_produced
    return o


class WinRateTests(unittest.TestCase):
    def test_computes_ratio_of_closed_won_to_all_closed(self):
        opps = [
            _opp("1", "hunt", "Closed Won", 100000, "2026-01-01", "2026-03-01"),
            _opp("2", "hunt", "Closed Lost", 50000, "2026-01-01", "2026-02-01"),
            _opp("3", "hunt", "Prospecting", 80000, "2026-04-01"),  # open, excluded
        ]
        result = win_rate(opps)
        self.assertEqual(result["n_closed"], 2)
        self.assertEqual(result["n_won"], 1)
        self.assertEqual(result["value"], 0.5)
        self.assertEqual(result["benchmark_median"], BENCHMARK_WIN_RATE_MEDIAN)

    def test_no_closed_opportunities_returns_none(self):
        result = win_rate([_opp("1", "hunt", "Prospecting", 1000, "2026-01-01")])
        self.assertIsNone(result["value"])
        self.assertEqual(result["n_closed"], 0)


class CycleLengthTests(unittest.TestCase):
    def test_median_days_from_created_to_close_for_won_only(self):
        opps = [
            _opp("1", "hunt", "Closed Won", 100000, "2026-01-01", "2026-04-01"),  # 90 days
            _opp("2", "hunt", "Closed Won", 100000, "2026-01-01", "2026-02-10"),  # 40 days
            _opp("3", "hunt", "Closed Lost", 100000, "2026-01-01", "2026-01-31"),  # excluded
        ]
        result = cycle_length_days(opps)
        self.assertEqual(result["n"], 2)
        self.assertEqual(result["median_days"], 65)


class PipelineCoverageTests(unittest.TestCase):
    def test_ratio_against_motion_specific_benchmark(self):
        result = pipeline_coverage(open_pipeline_value=1750000, quota_value=500000, motion="hunt")
        self.assertEqual(result["ratio"], 3.5)
        self.assertEqual(result["benchmark"], BENCHMARK_COVERAGE_HUNT)
        self.assertIsNone(result["flag"])

    def test_flags_loose_qualification_above_5x(self):
        result = pipeline_coverage(open_pipeline_value=3000000, quota_value=500000, motion="hunt")
        self.assertEqual(result["flag"], "coverage_too_high_loose_qualification_risk")

    def test_flags_below_benchmark(self):
        result = pipeline_coverage(open_pipeline_value=500000, quota_value=500000, motion="hunt")
        self.assertEqual(result["flag"], "below_benchmark")

    def test_zero_quota_does_not_divide_by_zero(self):
        result = pipeline_coverage(open_pipeline_value=100000, quota_value=0, motion="expand")
        self.assertIsNone(result["ratio"])
        self.assertEqual(result["flag"], "no_quota_set")


class StageConversionTests(unittest.TestCase):
    def test_funnel_counts_reached_or_passed(self):
        opps = [
            _opp("1", "hunt", "Closed Won", 100000, "2026-01-01", "2026-03-01"),
            _opp("2", "hunt", "Proposal/Price Quote", 80000, "2026-01-01"),
            _opp("3", "hunt", "Prospecting", 50000, "2026-01-01"),
        ]
        result = stage_conversion(opps)
        prospecting = next(f for f in result["funnel"] if f["stage"] == "Prospecting")
        self.assertEqual(prospecting["count"], 3)  # all 3 reached-or-passed Prospecting


class PatternReuseRateTests(unittest.TestCase):
    def test_unlabeled_opportunities_return_none(self):
        result = pattern_reuse_rate([_opp("1", "hunt", "Prospecting", 1000, "2026-01-01")])
        self.assertIsNone(result["rate"])

    def test_computes_reuse_rate(self):
        opps = [
            _opp("1", "hunt", "Closed Won", 100000, "2026-01-01", "2026-02-01", pov_cites_pattern=True),
            _opp("2", "hunt", "Closed Won", 100000, "2026-01-01", "2026-03-01", pov_cites_pattern=False),
        ]
        result = pattern_reuse_rate(opps)
        self.assertEqual(result["rate"], 0.5)
        self.assertEqual(result["n_cited"], 1)

    def test_compares_cycle_time_when_both_groups_have_closed_data(self):
        opps = [
            _opp("1", "hunt", "Closed Won", 100000, "2026-01-01", "2026-01-31", pov_cites_pattern=True),   # 30d
            _opp("2", "hunt", "Closed Won", 100000, "2026-01-01", "2026-04-01", pov_cites_pattern=False),  # 90d
        ]
        result = pattern_reuse_rate(opps)
        self.assertEqual(result["cited_median_cycle_days"], 30)
        self.assertEqual(result["cold_started_median_cycle_days"], 90)
        self.assertEqual(result["cycle_delta_days"], 60.0)


class CaseStudyYieldTests(unittest.TestCase):
    def test_no_wins_returns_none(self):
        result = case_study_yield([_opp("1", "hunt", "Prospecting", 1000, "2026-01-01")])
        self.assertIsNone(result["yield"])
        self.assertEqual(result["n_won"], 0)

    def test_wins_with_no_label_warn_instead_of_hiding(self):
        opps = [_opp("1", "hunt", "Closed Won", 100000, "2026-01-01", "2026-02-01")]
        result = case_study_yield(opps)
        self.assertIsNone(result["yield"])
        self.assertIn("warning", result)

    def test_computes_yield_and_flags_partial_labeling(self):
        opps = [
            _opp("1", "hunt", "Closed Won", 100000, "2026-01-01", "2026-02-01", case_study_produced=True),
            _opp("2", "hunt", "Closed Won", 100000, "2026-01-01", "2026-02-01", case_study_produced=False),
            _opp("3", "hunt", "Closed Won", 100000, "2026-01-01", "2026-02-01"),  # unlabeled
        ]
        result = case_study_yield(opps)
        self.assertEqual(result["yield"], 0.5)
        self.assertEqual(result["n_won"], 3)
        self.assertEqual(result["n_labeled"], 2)
        self.assertIn("warning", result)


class ScorecardTests(unittest.TestCase):
    def test_aggregates_all_six_kpis(self):
        opps = [
            _opp("1", "hunt", "Closed Won", 100000, "2026-01-01", "2026-04-01"),
            _opp("2", "expand", "Prospecting", 50000, "2026-01-01"),
        ]
        result = scorecard(opps, quota_hunt=100000, quota_expand=100000)
        self.assertIn("win_rate", result)
        self.assertIn("cycle_length", result)
        self.assertIn("pipeline_coverage", result)
        self.assertIn("stage_conversion", result)
        self.assertIn("pattern_reuse_rate", result)
        self.assertIn("case_study_yield", result)
        self.assertIn("hunt", result["pipeline_coverage"])
        self.assertIn("expand", result["pipeline_coverage"])


class ShippedFixtureTests(unittest.TestCase):
    """Regression guard for the fixture-shape bug an import-readiness judge caught:
    kpi.py needs Salesforce-shaped records (stage/amount/created_date), not
    score.py's MEDDPICC-shaped ones. This fixture must stay independently loadable
    and scorecard-able, or a fresh installer hits `{"error": "'stage'"}` on the
    skill's own documented first command."""

    def test_shipped_kpi_fixture_scorecards_cleanly(self):
        import json
        import os

        fixture = os.path.join(os.path.dirname(__file__), "kpi_opportunities.example.json")
        with open(fixture) as f:
            opps = json.load(f)
        result = scorecard(opps, quota_hunt=500000, quota_expand=300000)
        self.assertIn("win_rate", result)
        self.assertIn("pipeline_coverage", result)


if __name__ == "__main__":
    unittest.main()
