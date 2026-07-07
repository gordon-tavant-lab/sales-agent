"""Stdlib-only tests for close_out.py — no external test runner required.

Run: python3 test_close_out.py
"""
import json
import os
import tempfile
import unittest

from close_out import close_out, upsert_outcome


class UpsertOutcomeTests(unittest.TestCase):
    def test_new_id_appended(self):
        result = upsert_outcome([], "a", "won", 0.6, True)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "a")
        self.assertEqual(result[0]["outcome"], "won")

    def test_existing_id_replaced_not_duplicated(self):
        existing = [{"id": "a", "confidence_value": 0.5, "was_shortlisted": False, "outcome": "lost"}]
        result = upsert_outcome(existing, "a", "won", 0.7, True)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["outcome"], "won")
        self.assertEqual(result[0]["confidence_value"], 0.7)

    def test_invalid_outcome_raises(self):
        with self.assertRaises(ValueError):
            upsert_outcome([], "a", "maybe", 0.5, False)

    def test_out_of_range_confidence_raises(self):
        with self.assertRaises(ValueError):
            upsert_outcome([], "a", "won", 1.5, False)


class CloseOutTests(unittest.TestCase):
    def setUp(self):
        fd, self.backtest_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.remove(self.backtest_path)  # close_out creates it fresh

    def tearDown(self):
        if os.path.exists(self.backtest_path):
            os.remove(self.backtest_path)

    def test_first_close_out_creates_backtest_file(self):
        result = close_out("acct-1", "won", 0.6, True, self.backtest_path)
        self.assertEqual(result["backtest_n"], 1)
        self.assertFalse(result["recorded"]["was_update"])
        with open(self.backtest_path) as f:
            records = json.load(f)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["id"], "acct-1")

    def test_second_distinct_close_out_appends(self):
        close_out("acct-1", "won", 0.6, True, self.backtest_path)
        result = close_out("acct-2", "lost", 0.3, False, self.backtest_path)
        self.assertEqual(result["backtest_n"], 2)

    def test_reclosing_same_id_updates_not_duplicates(self):
        close_out("acct-1", "lost", 0.6, True, self.backtest_path)
        result = close_out("acct-1", "won", 0.65, True, self.backtest_path)
        self.assertEqual(result["backtest_n"], 1)
        self.assertTrue(result["recorded"]["was_update"])
        with open(self.backtest_path) as f:
            records = json.load(f)
        self.assertEqual(records[0]["outcome"], "won")

    def test_result_includes_rerun_eval(self):
        result = close_out("acct-1", "won", 0.6, True, self.backtest_path)
        self.assertIn("eval", result)
        self.assertIn("brier_score", result["eval"])
        self.assertEqual(result["eval"]["brier_score"]["n"], 1)

    def test_result_includes_attest_call_but_does_not_call_attest(self):
        result = close_out("acct-1", "won", 0.6, True, self.backtest_path)
        call = result["attest_call"]
        self.assertEqual(call["decision_id"], "acct-1")
        self.assertEqual(call["verdict"], "won")
        self.assertEqual(call["reason_code"], "CLOSE_OUT_WON")

    def test_lost_outcome_reason_code(self):
        result = close_out("acct-1", "lost", 0.3, False, self.backtest_path)
        self.assertEqual(result["attest_call"]["reason_code"], "CLOSE_OUT_LOST")

    def test_invalid_outcome_raises(self):
        with self.assertRaises(ValueError):
            close_out("acct-1", "pending", 0.5, False, self.backtest_path)

    def test_prior_brier_feeds_drift_check(self):
        close_out("acct-1", "won", 0.6, True, self.backtest_path)
        result = close_out("acct-2", "lost", 0.3, False, self.backtest_path, prior_brier=0.5)
        self.assertIn("drift_check", result["eval"])
        self.assertEqual(result["eval"]["drift_check"]["prior_brier"], 0.5)


if __name__ == "__main__":
    unittest.main()
