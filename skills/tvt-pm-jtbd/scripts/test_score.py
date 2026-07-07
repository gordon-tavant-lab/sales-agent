"""Stdlib-only tests for score.py (Ulwick ODI scoring) — no external test runner required.

Run: python3 test_score.py
"""
import unittest

from score import (
    build_grow_handoff,
    classify,
    compute_movements,
    opportunity_score,
    score_outcomes,
)


class OpportunityScoreTests(unittest.TestCase):
    def test_formula_is_importance_plus_max_zero_gap(self):
        # importance=9, satisfaction=3 -> 9 + max(0, 6) = 15
        self.assertEqual(opportunity_score(9, 3), 15)

    def test_satisfaction_exceeding_importance_does_not_go_negative(self):
        # importance=4, satisfaction=8 -> 4 + max(0, -4) = 4, not -4
        self.assertEqual(opportunity_score(4, 8), 4)

    def test_equal_importance_and_satisfaction(self):
        self.assertEqual(opportunity_score(5, 5), 5)


class ClassifyTests(unittest.TestCase):
    def test_under_served_at_1_5x_scale(self):
        self.assertEqual(classify(15, 10), "under-served")

    def test_appropriately_served_at_1x_scale(self):
        self.assertEqual(classify(10, 10), "appropriately-served")

    def test_over_served_below_1x_scale(self):
        self.assertEqual(classify(9.9, 10), "over-served")

    def test_thresholds_scale_with_rating_scale(self):
        # scale=5: hi=7.5, mid=5
        self.assertEqual(classify(8, 5), "under-served")
        self.assertEqual(classify(5, 5), "appropriately-served")
        self.assertEqual(classify(4.9, 5), "over-served")


class ScoreOutcomesTests(unittest.TestCase):
    def test_ranks_by_opportunity_descending(self):
        outcomes = [
            {"id": "a", "importance": 5, "satisfaction": 5},   # opp 5
            {"id": "b", "importance": 9, "satisfaction": 2},   # opp 16
            {"id": "c", "importance": 6, "satisfaction": 6},   # opp 6
        ]
        scored = score_outcomes(outcomes, scale=10)
        self.assertEqual([s["id"] for s in scored], ["b", "c", "a"])
        self.assertEqual([s["rank"] for s in scored], [1, 2, 3])

    def test_out_of_range_importance_raises(self):
        with self.assertRaises(ValueError):
            score_outcomes([{"id": "a", "importance": 11, "satisfaction": 5}], scale=10)

    def test_out_of_range_satisfaction_raises(self):
        with self.assertRaises(ValueError):
            score_outcomes([{"id": "a", "importance": 5, "satisfaction": -1}], scale=10)

    def test_missing_importance_and_satisfaction_default_to_zero(self):
        scored = score_outcomes([{"id": "a"}], scale=10)
        self.assertEqual(scored[0]["importance"], 0.0)
        self.assertEqual(scored[0]["satisfaction"], 0.0)
        self.assertEqual(scored[0]["opportunity"], 0.0)

    def test_carries_through_statement_job_step_and_friction(self):
        outcomes = [{"id": "a", "statement": "Minimize X", "job_step": "step1",
                     "importance": 8, "satisfaction": 4, "friction": "manual work"}]
        scored = score_outcomes(outcomes, scale=10)
        self.assertEqual(scored[0]["outcome"], "Minimize X")
        self.assertEqual(scored[0]["job_step"], "step1")
        self.assertEqual(scored[0]["friction"], "manual work")


class GrowHandoffTests(unittest.TestCase):
    def test_only_under_served_outcomes_are_handed_off(self):
        outcomes = [
            {"id": "a", "importance": 9, "satisfaction": 2},  # under-served
            {"id": "b", "importance": 5, "satisfaction": 5},  # over-served
        ]
        scored = score_outcomes(outcomes, scale=10)
        handoff = build_grow_handoff(scored)
        self.assertEqual(len(handoff), 1)
        self.assertEqual(handoff[0]["opportunity"], scored[[s["id"] for s in scored].index("a")]["opportunity"])

    def test_no_under_served_outcomes_yields_empty_handoff(self):
        outcomes = [{"id": "a", "importance": 5, "satisfaction": 5}]
        scored = score_outcomes(outcomes, scale=10)
        self.assertEqual(build_grow_handoff(scored), [])


class ComputeMovementsTests(unittest.TestCase):
    def test_detects_improvement_and_regression(self):
        prior = {"ranked_outcomes": [
            {"id": "a", "opportunity": 10, "satisfaction": 5},
            {"id": "b", "opportunity": 10, "satisfaction": 5},
        ]}
        now = [
            {"id": "a", "outcome": "A", "opportunity": 15, "satisfaction": 3},  # regressed (worse sat, higher opp)
            {"id": "b", "outcome": "B", "opportunity": 6, "satisfaction": 8},   # improved (opp dropped)
        ]
        tracking = compute_movements(now, prior)
        self.assertEqual(len(tracking["movements"]), 2)
        self.assertEqual(tracking["most_improved"]["id"], "b")
        self.assertEqual(tracking["most_regressed"]["id"], "a")

    def test_ids_absent_from_prior_are_skipped_not_errored(self):
        prior = {"ranked_outcomes": [{"id": "a", "opportunity": 10, "satisfaction": 5}]}
        now = [{"id": "new-outcome", "outcome": "New", "opportunity": 12, "satisfaction": 4}]
        tracking = compute_movements(now, prior)
        self.assertEqual(tracking["movements"], [])
        self.assertIsNone(tracking["most_improved"])

    def test_empty_prior_yields_no_movements(self):
        tracking = compute_movements([{"id": "a", "outcome": "A", "opportunity": 10, "satisfaction": 5}], {})
        self.assertEqual(tracking["movements"], [])


if __name__ == "__main__":
    unittest.main()
