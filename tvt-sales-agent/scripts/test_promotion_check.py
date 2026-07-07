"""Tests for promotion_check.py (T10). Python 3.9 compatible."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest  # noqa: E402
from dispatch import propose_new_skill  # noqa: E402
from promotion_check import (  # noqa: E402
    build_similarity_prompt,
    check_thresholds,
    group_suggestions,
    load_escalation_state,
    normalize_request,
    run,
    validate_similarity_answer,
)


def test_normalize_request_collapses_whitespace_and_case():
    assert normalize_request("  Detect a Stalled Pilot!  ") == "detect a stalled pilot"


def test_group_suggestions_exact_match_only():
    suggestions = [
        {"request_text": "detect a stalled pilot", "reason": "r1"},
        {"request_text": "Detect a Stalled Pilot", "reason": "r2"},  # same normalized
        {"request_text": "something totally different", "reason": "r3"},
    ]
    groups = group_suggestions(suggestions)
    assert len(groups) == 2
    assert len(groups["detect a stalled pilot"]) == 2


def test_check_thresholds_below_threshold_no_escalation():
    roster = {"config": {"promotion_threshold": 3, "promotion_rejection_multiplier": 2}}
    groups = {"gap-a": [{"request_text": "x", "reason": "r"}] * 2}  # 2 < threshold 3
    assert check_thresholds(groups, roster, {}) == []


def test_check_thresholds_at_threshold_escalates():
    roster = {"config": {"promotion_threshold": 3, "promotion_rejection_multiplier": 2}}
    groups = {"gap-a": [{"request_text": "x", "reason": "r"}] * 3}
    result = check_thresholds(groups, roster, {})
    assert len(result) == 1
    assert result[0]["gap_key"] == "gap-a"
    assert result[0]["status"] == "pending"
    assert result[0]["count"] == 3


def test_check_thresholds_does_not_duplicate_an_already_pending_escalation():
    roster = {"config": {"promotion_threshold": 3, "promotion_rejection_multiplier": 2}}
    groups = {"gap-a": [{"request_text": "x", "reason": "r"}] * 5}
    existing = {"gap-a": {"gap_key": "gap-a", "status": "pending", "count": 3}}
    assert check_thresholds(groups, roster, existing) == []


def test_check_thresholds_rejected_gap_resurfaces_only_past_multiplier():
    roster = {"config": {"promotion_threshold": 3, "promotion_rejection_multiplier": 2}}
    existing = {"gap-a": {"gap_key": "gap-a", "status": "rejected", "count": 3, "rejected_at_count": 3}}

    # Still below rejected_at_count(3) * multiplier(2) = 6 -- must NOT re-surface
    below = {"gap-a": [{"request_text": "x", "reason": "r"}] * 5}
    assert check_thresholds(below, roster, existing) == []

    # At/above 6 -- must re-surface
    at_multiplier = {"gap-a": [{"request_text": "x", "reason": "r"}] * 6}
    result = check_thresholds(at_multiplier, roster, existing)
    assert len(result) == 1
    assert "re-escalated" in result[0]["note"]


def test_load_escalation_state_keeps_most_recent_record_per_gap(tmp_path):
    path = str(tmp_path / "esc.jsonl")
    with open(path, "w") as fh:
        fh.write(json.dumps({"gap_key": "gap-a", "status": "pending", "count": 3}) + "\n")
        fh.write(json.dumps({"gap_key": "gap-a", "status": "rejected", "count": 3, "rejected_at_count": 3}) + "\n")
    state = load_escalation_state(path)
    assert state["gap-a"]["status"] == "rejected"


def test_build_similarity_prompt_includes_both_requests():
    prompt = build_similarity_prompt("detect stalled pilots", "flag pilots going overdue")
    assert "detect stalled pilots" in prompt
    assert "flag pilots going overdue" in prompt
    assert "SAME" in prompt and "DIFFERENT" in prompt


def test_validate_similarity_answer_only_accepts_exact_same():
    assert validate_similarity_answer("SAME") is True
    assert validate_similarity_answer("same") is True
    assert validate_similarity_answer("  SAME  ") is True
    assert validate_similarity_answer("DIFFERENT") is False
    assert validate_similarity_answer("probably the same i think") is False  # conservative default


def test_run_end_to_end_writes_a_real_escalation(tmp_path):
    suggestions_path = str(tmp_path / "suggestions.jsonl")
    escalations_path = str(tmp_path / "escalations.jsonl")

    for _ in range(3):
        propose_new_skill("detect a stalled pilot before it jeopardizes production", "no match", suggestions_path)
    propose_new_skill("a one-off unrelated request", "no match", suggestions_path)

    result = run(suggestions_path, escalations_path)
    assert result["total_suggestions"] == 4
    assert result["distinct_groups"] == 2
    assert len(result["new_escalations"]) == 1
    assert os.path.exists(escalations_path)

    with open(escalations_path) as fh:
        record = json.loads(fh.readline())
    assert record["count"] == 3
    assert record["status"] == "pending"


def test_run_with_no_suggestions_file_is_empty_not_an_error(tmp_path):
    result = run(str(tmp_path / "nope.jsonl"), str(tmp_path / "esc.jsonl"))
    assert result["total_suggestions"] == 0
    assert result["new_escalations"] == []


# --- T11: escalation surfacing + approve/reject flow ---

def test_pending_escalations_lists_only_pending(tmp_path):
    from promotion_check import pending_escalations

    path = str(tmp_path / "esc.jsonl")
    with open(path, "w") as fh:
        fh.write(json.dumps({"gap_key": "gap-a", "status": "pending", "count": 3}) + "\n")
        fh.write(json.dumps({"gap_key": "gap-b", "status": "approved", "count": 4}) + "\n")
        fh.write(json.dumps({"gap_key": "gap-c", "status": "rejected", "count": 3, "rejected_at_count": 3}) + "\n")
    pending = pending_escalations(path)
    assert len(pending) == 1
    assert pending[0]["gap_key"] == "gap-a"


def test_resolve_escalation_approve_never_writes_an_agent_file(tmp_path):
    # The core FR-008/T11 rescoping proof: approving writes only the escalation record
    # (+ optionally an attest record) -- never an agents/*.md file, since there is no
    # ephemeral prompt to promote in T9's narrowed design.
    from promotion_check import resolve_escalation, run

    suggestions_path = str(tmp_path / "suggestions.jsonl")
    escalations_path = str(tmp_path / "escalations.jsonl")
    from dispatch import propose_new_skill
    for _ in range(3):
        propose_new_skill("detect a stalled pilot", "no match", suggestions_path)
    run(suggestions_path, escalations_path)

    result = resolve_escalation("detect a stalled pilot", "approved", escalations_path)
    assert result["status"] == "approved"

    # No agents/ directory writes anywhere near tmp_path -- proves nothing else happened.
    agents_dirs = list(tmp_path.rglob("agents"))
    assert agents_dirs == [] or all(not any(d.iterdir()) for d in agents_dirs if d.is_dir())


def test_resolve_escalation_reject_records_rejected_at_count(tmp_path):
    from promotion_check import resolve_escalation, run

    suggestions_path = str(tmp_path / "suggestions.jsonl")
    escalations_path = str(tmp_path / "escalations.jsonl")
    from dispatch import propose_new_skill
    for _ in range(3):
        propose_new_skill("detect a stalled pilot", "no match", suggestions_path)
    run(suggestions_path, escalations_path)

    result = resolve_escalation("detect a stalled pilot", "rejected", escalations_path)
    assert result["status"] == "rejected"
    assert result["rejected_at_count"] == 3


def test_resolve_escalation_rejects_invalid_decision_value(tmp_path):
    from promotion_check import resolve_escalation

    with pytest.raises(ValueError, match="must be 'approved' or 'rejected'"):
        resolve_escalation("some-gap", "maybe", str(tmp_path / "esc.jsonl"))


def test_resolve_escalation_fails_loudly_on_unknown_gap_key(tmp_path):
    from promotion_check import resolve_escalation

    with pytest.raises(ValueError, match="no pending escalation"):
        resolve_escalation("never-registered-gap", "approved", str(tmp_path / "esc.jsonl"))


def test_resolve_escalation_writes_a_real_verifiable_attest_record(tmp_path):
    import subprocess

    from dispatch import ATTEST_SCRIPT, propose_new_skill
    from promotion_check import resolve_escalation, run

    suggestions_path = str(tmp_path / "suggestions.jsonl")
    escalations_path = str(tmp_path / "escalations.jsonl")
    ledger_path = str(tmp_path / "ledger.jsonl")
    for _ in range(3):
        propose_new_skill("detect a stalled pilot", "no match", suggestions_path)
    run(suggestions_path, escalations_path)
    resolve_escalation("detect a stalled pilot", "approved", escalations_path, ledger_path=ledger_path)

    proc = subprocess.run(
        [sys.executable, ATTEST_SCRIPT, "--verify", "--ledger", ledger_path],
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    verdict = json.loads(proc.stdout)
    assert verdict["intact"] is True
    assert verdict["records"] == 1
