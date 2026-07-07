"""Stdlib-only tests for gate.py — no external test runner required.

Run: python3 test_gate.py
"""
import unittest

import os
import tempfile
import time

from gate import (
    HIGH_CONFIDENCE_THRESHOLD,
    MEDDPICC_MAX,
    accumulated_abuse_rate,
    aggregate_meddpicc,
    classify_batch,
    classify_claim,
    confirm_queue,
    enqueue,
    plausible_min_seconds,
    score_confirmation,
)


class ClassifyClaimTests(unittest.TestCase):
    def test_high_confidence_nonconflicting_auto_attests(self):
        v = classify_claim({"claim_id": "a", "extraction_confidence": 0.95, "contradicts_prior": False})
        self.assertEqual(v["decision"], "auto_attest")
        self.assertEqual(v["reason_code"], "HIGH_CONFIDENCE_NONCONTRADICTING")

    def test_low_confidence_queues(self):
        v = classify_claim({"claim_id": "b", "extraction_confidence": 0.3, "contradicts_prior": False})
        self.assertEqual(v["decision"], "queue")
        self.assertEqual(v["reason_code"], "LOW_CONFIDENCE")

    def test_high_confidence_but_contradicting_still_queues(self):
        # spec §10: a deliberately planted false/contradicting claim must surface for review
        # even if the extractor was "confident" about it.
        v = classify_claim({"claim_id": "c", "extraction_confidence": 0.99, "contradicts_prior": True})
        self.assertEqual(v["decision"], "queue")
        self.assertEqual(v["reason_code"], "CONTRADICTS_PRIOR")

    def test_threshold_boundary_is_inclusive(self):
        v = classify_claim({"claim_id": "d", "extraction_confidence": HIGH_CONFIDENCE_THRESHOLD,
                             "contradicts_prior": False})
        self.assertEqual(v["decision"], "auto_attest")

    def test_missing_confidence_raises(self):
        with self.assertRaises(ValueError):
            classify_claim({"claim_id": "e"})

    def test_out_of_range_confidence_raises(self):
        with self.assertRaises(ValueError):
            classify_claim({"claim_id": "f", "extraction_confidence": 1.5})


class ClassifyBatchTests(unittest.TestCase):
    def test_mixed_batch_splits_into_both_lanes_with_no_overlap(self):
        # spec §10: (a) an unambiguous high-confidence claim auto-attests with no queue item;
        # (b) a low-confidence/contradicting claim surfaces in the PENDING queue.
        claims = [
            {"claim_id": "hi", "extraction_confidence": 0.9, "contradicts_prior": False},
            {"claim_id": "lo", "extraction_confidence": 0.2, "contradicts_prior": False},
            {"claim_id": "contra", "extraction_confidence": 0.9, "contradicts_prior": True},
        ]
        result = classify_batch(claims)
        auto_ids = {v["claim_id"] for v in result["auto_attested"]}
        queued_ids = {v["claim_id"] for v in result["queued"]}
        self.assertEqual(auto_ids, {"hi"})
        self.assertEqual(queued_ids, {"lo", "contra"})
        self.assertEqual(result["counts"], {"total": 3, "auto_attested": 1, "queued": 2})

    def test_rejected_claim_never_appears_in_auto_attested(self):
        # A queued (rejectable) claim must never land anywhere that implies it reached the
        # ledger — classify_batch's auto_attested list is the only thing safe to attest.
        claims = [{"claim_id": "false-claim", "extraction_confidence": 0.99, "contradicts_prior": True}]
        result = classify_batch(claims)
        self.assertEqual(result["auto_attested"], [])
        self.assertEqual(len(result["queued"]), 1)


class ConfirmationAbuseTests(unittest.TestCase):
    def test_plausible_read_time_scales_with_batch_size(self):
        self.assertGreater(plausible_min_seconds(10), plausible_min_seconds(2))

    def test_fast_confirm_all_flagged_as_abuse(self):
        # spec §10: a synthetic "confirm all in <1s" batch must increment the abuse-rate KPI.
        result = score_confirmation(n_items=5, elapsed_seconds=0.8)
        self.assertTrue(result["abuse_flag"])

    def test_plausible_confirm_time_not_flagged(self):
        result = score_confirmation(n_items=2, elapsed_seconds=30.0)
        self.assertFalse(result["abuse_flag"])

    def test_rejects_nonpositive_item_count(self):
        with self.assertRaises(ValueError):
            score_confirmation(n_items=0, elapsed_seconds=5.0)


class AggregateMeddpiccTests(unittest.TestCase):
    def test_full_confirmed_set_sums_to_max(self):
        dims = {"metrics": 3, "economic_buyer": 3, "decision_criteria": 3, "decision_process": 3,
                "paper_process": 3, "identify_pain": 3, "champion": 3, "competition": 3}
        result = aggregate_meddpicc(dims)
        self.assertEqual(result["meddpicc_raw"], MEDDPICC_MAX)
        self.assertEqual(result["dimensions_missing"], [])

    def test_unconfirmed_dimension_does_not_inflate_score(self):
        # only 2 of 8 dimensions confirmed — the other 6 must score 0, not be imputed.
        result = aggregate_meddpicc({"metrics": 3, "champion": 3})
        self.assertEqual(result["meddpicc_raw"], 6)
        self.assertEqual(result["dimensions_confirmed"], 2)
        self.assertEqual(len(result["dimensions_missing"]), 6)

    def test_unknown_dimension_raises(self):
        with self.assertRaises(ValueError):
            aggregate_meddpicc({"not_a_real_dimension": 1})

    def test_out_of_range_dimension_score_raises(self):
        with self.assertRaises(ValueError):
            aggregate_meddpicc({"metrics": 4})


class SourceSplitTests(unittest.TestCase):
    """F7: manual authorship doesn't need an invented confidence number; extracted still does."""

    def test_manual_auto_attests_without_confidence(self):
        v = classify_claim({"claim_id": "m1", "contradicts_prior": False}, source="manual")
        self.assertEqual(v["decision"], "auto_attest")
        self.assertEqual(v["reason_code"], "AUTHOR_ATTESTED")
        self.assertEqual(v["method"], "manual")
        self.assertNotIn("extraction_confidence", v)

    def test_manual_still_queues_on_contradiction(self):
        v = classify_claim({"claim_id": "m2", "contradicts_prior": True}, source="manual")
        self.assertEqual(v["decision"], "queue")
        self.assertEqual(v["reason_code"], "CONTRADICTS_PRIOR")

    def test_extracted_still_requires_confidence(self):
        with self.assertRaises(ValueError):
            classify_claim({"claim_id": "e1", "contradicts_prior": False}, source="extracted")

    def test_extracted_is_the_default(self):
        with self.assertRaises(ValueError):
            classify_claim({"claim_id": "e2"})

    def test_unknown_source_raises(self):
        with self.assertRaises(ValueError):
            classify_claim({"claim_id": "x"}, source="bogus")

    def test_classify_batch_passes_source_through(self):
        claims = [{"claim_id": "m3", "contradicts_prior": False}]
        result = classify_batch(claims, source="manual")
        self.assertEqual(result["counts"]["auto_attested"], 1)


class QueueStateTests(unittest.TestCase):
    """F11: elapsed time for the abuse-rate KPI is computed from real queued_at timestamps,
    not self-reported by the person being policed."""

    def setUp(self):
        fd, self.queue_path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        os.remove(self.queue_path)  # enqueue/confirm_queue create it fresh
        fd, self.abuse_path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        os.remove(self.abuse_path)

    def tearDown(self):
        for path in (self.queue_path, self.abuse_path):
            if os.path.exists(path):
                os.remove(path)

    def test_enqueue_appends_queued_claims_with_timestamp(self):
        claims = [{"claim_id": "q1", "contradicts_prior": True}]
        batch = classify_batch(claims, source="manual")
        n = enqueue(self.queue_path, batch, {"q1": claims[0]})
        self.assertEqual(n, 1)
        with open(self.queue_path) as f:
            import json
            row = json.loads(f.readline())
        self.assertEqual(row["claim_id"], "q1")
        self.assertIn("queued_at", row)

    def test_confirm_queue_computes_elapsed_not_self_reported(self):
        claims = [{"claim_id": "q2", "contradicts_prior": True}]
        batch = classify_batch(claims, source="manual")
        enqueue(self.queue_path, batch, {"q2": claims[0]})
        time.sleep(0.05)
        outcome = confirm_queue(self.queue_path, ["q2"])
        self.assertGreater(outcome["result"]["elapsed_seconds"], 0.03)
        self.assertEqual(outcome["remaining_queue"], [])

    def test_confirm_queue_leaves_unmatched_claims_pending(self):
        claims = [
            {"claim_id": "q3", "contradicts_prior": True},
            {"claim_id": "q4", "contradicts_prior": True},
        ]
        batch = classify_batch(claims, source="manual")
        enqueue(self.queue_path, batch, {c["claim_id"]: c for c in claims})
        outcome = confirm_queue(self.queue_path, ["q3"])
        self.assertEqual(len(outcome["remaining_queue"]), 1)
        self.assertEqual(outcome["remaining_queue"][0]["claim_id"], "q4")

    def test_confirm_queue_raises_when_no_claim_ids_match(self):
        with self.assertRaises(ValueError):
            confirm_queue(self.queue_path, ["nonexistent"])

    def test_accumulated_abuse_rate_empty_log(self):
        result = accumulated_abuse_rate(self.abuse_path)
        self.assertEqual(result["n_events"], 0)
        self.assertIsNone(result["abuse_rate"])

    def test_accumulated_abuse_rate_across_multiple_events(self):
        import json
        with open(self.abuse_path, "w") as f:
            f.write(json.dumps({"abuse_flag": True}) + "\n")
            f.write(json.dumps({"abuse_flag": False}) + "\n")
            f.write(json.dumps({"abuse_flag": True}) + "\n")
        result = accumulated_abuse_rate(self.abuse_path)
        self.assertEqual(result["n_events"], 3)
        self.assertEqual(result["n_flagged"], 2)
        self.assertAlmostEqual(result["abuse_rate"], 0.6667, places=3)


if __name__ == "__main__":
    unittest.main()
