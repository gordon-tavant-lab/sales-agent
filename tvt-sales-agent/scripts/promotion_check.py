"""promotion_check.py — suggestion-recurrence aggregation -> escalations (T10, FR-006/FR-007).

Rescoped 2026-07-07 (plan.md S5): T9's narrowed factory never creates an ephemeral agent, so
there is no AGENT:<slug> invocation count to aggregate from the ledger. This instead reads
output/skill-suggestions.jsonl -- T9's propose_new_skill() queue -- and groups suggestions by
underlying gap, deterministic-first (exact normalized-text match), an LLM-assisted similarity
call only for genuinely ambiguous near-matches (research-foundations.md Decision Point 2's
discipline, reused not reinvented -- same two-step prompt/validate pattern as Tier 2 and the
recombination factory: this script composes the question, the invoking agent answers it, this
script validates the answer, never trusts an answer at face value).

Once a group's recurrence count crosses roster.yml's promotion_threshold, this writes a pending
escalation record to output/promotion-escalations.jsonl -- a prioritization signal for a human
decision, never an automatic file-write (there is no ephemeral agent to promote).
"""
import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import emit, fail, load_roster  # noqa: E402

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SUGGESTIONS_PATH = os.path.join(_SCRIPTS_DIR, "..", "output", "skill-suggestions.jsonl")
DEFAULT_ESCALATIONS_PATH = os.path.join(_SCRIPTS_DIR, "..", "output", "promotion-escalations.jsonl")


def normalize_request(text: str) -> str:
    """Deterministic normalization for exact-match grouping: lowercase, collapse
    whitespace, strip punctuation at the edges. Two suggestions that normalize to the
    same string are the same underlying gap with high confidence -- no LLM call needed.
    """
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = text.strip(".,!?;:")
    return text


def load_suggestions(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    records = []
    with open(path, "r") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def group_suggestions(suggestions: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Deterministic-first grouping: exact match on normalized request_text. Suggestions
    that are genuinely the same gap but phrased differently will land in separate groups
    here -- that's the ambiguous case build_similarity_prompt()/validate_similarity_answer()
    below exist for, not something this function guesses at.
    """
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for s in suggestions:
        key = normalize_request(s["request_text"])
        groups.setdefault(key, []).append(s)
    return groups


def build_similarity_prompt(text_a: str, text_b: str) -> str:
    """T10's ambiguous case (Decision Point 2): two suggestions that don't normalize to
    an exact match, but might be the same underlying gap phrased differently. Composed
    here, answered by the invoking agent (this script has no model access), validated by
    validate_similarity_answer() below -- same two-step discipline as Tier 2 / T9.
    """
    return (
        "Are these two requests the same underlying capability gap, just phrased "
        "differently, or genuinely different gaps?\n\n"
        "Request A: {!r}\n"
        "Request B: {!r}\n\n"
        "Answer with exactly one word: SAME or DIFFERENT.".format(text_a, text_b)
    )


def validate_similarity_answer(answer: str) -> bool:
    """Never trust an answer outside the closed set -- anything that isn't exactly SAME
    is treated as DIFFERENT (the conservative default: under-grouping just means slower
    promotion, not a wrong one; over-grouping could wrongly conflate two real gaps)."""
    return answer.strip().upper() == "SAME"


def load_escalation_state(path: str) -> Dict[str, Dict[str, Any]]:
    """Keyed by normalized request_text -> the most recent escalation record for that
    gap, so we know whether it's already pending/approved/rejected and (if rejected) what
    count it was rejected at, for the re-surface-only-past-multiplier policy."""
    if not os.path.exists(path):
        return {}
    state: Dict[str, Dict[str, Any]] = {}
    with open(path, "r") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rec = json.loads(line)
                state[rec["gap_key"]] = rec  # later records overwrite earlier ones
    return state


def check_thresholds(
    groups: Dict[str, List[Dict[str, Any]]],
    roster: Dict[str, Any],
    existing_state: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """For each group, decide whether a NEW escalation record should be written:
      - count < threshold: not yet, no record.
      - count >= threshold, no prior record (or prior was 'pending'/'approved'): escalate.
      - count >= threshold, prior was 'rejected' at count N: only re-escalate once the
        current count reaches N * promotion_rejection_multiplier (FR-008's "unless the
        recurrence pattern changes materially" -- a deterministic rule, not a judgment call).
    """
    threshold = roster["config"]["promotion_threshold"]
    multiplier = roster["config"]["promotion_rejection_multiplier"]
    new_escalations = []

    for gap_key, suggestions in groups.items():
        count = len(suggestions)
        if count < threshold:
            continue

        prior = existing_state.get(gap_key)
        if prior is None or prior["status"] in ("pending", "approved"):
            if prior is not None and prior["status"] == "pending":
                continue  # already escalated and awaiting a decision, don't duplicate
            new_escalations.append({
                "gap_key": gap_key,
                "status": "pending",
                "count": count,
                "sample_request_text": suggestions[0]["request_text"],
                "reasons": sorted(set(s["reason"] for s in suggestions)),
            })
        elif prior["status"] == "rejected":
            rejected_at = prior.get("rejected_at_count", prior["count"])
            if count >= rejected_at * multiplier:
                new_escalations.append({
                    "gap_key": gap_key,
                    "status": "pending",
                    "count": count,
                    "sample_request_text": suggestions[0]["request_text"],
                    "reasons": sorted(set(s["reason"] for s in suggestions)),
                    "note": "re-escalated: count {} reached {}x the rejected-at count {}".format(
                        count, multiplier, rejected_at
                    ),
                })

    return new_escalations


def write_escalations(escalations: List[Dict[str, Any]], path: str) -> None:
    if not escalations:
        return
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a") as fh:
        for esc in escalations:
            fh.write(json.dumps(esc, separators=(",", ":")) + "\n")


def run(
    suggestions_path: str = DEFAULT_SUGGESTIONS_PATH,
    escalations_path: str = DEFAULT_ESCALATIONS_PATH,
) -> Dict[str, Any]:
    roster = load_roster()
    suggestions = load_suggestions(suggestions_path)
    groups = group_suggestions(suggestions)
    existing_state = load_escalation_state(escalations_path)
    new_escalations = check_thresholds(groups, roster, existing_state)
    write_escalations(new_escalations, escalations_path)
    return {
        "total_suggestions": len(suggestions),
        "distinct_groups": len(groups),
        "new_escalations": new_escalations,
    }


def resolve_escalation(
    gap_key: str,
    decision: str,
    escalations_path: str = DEFAULT_ESCALATIONS_PATH,
    ledger_path: Optional[str] = None,
    mode: str = "poc",
) -> Dict[str, Any]:
    """T11: approve or reject a pending escalation. Rescoped 2026-07-07 (plan.md S5) --
    approval is a PRIORITIZATION signal only. It writes an attest record marking the
    decision to pursue building a real skill for this gap; it does NOT write any
    agents/*.md file, because the narrowed factory (T9) never created an ephemeral prompt
    to promote in the first place. Building the actual skill is a separate, manual,
    future task through the normal vendoring process.

    decision must be exactly "approved" or "rejected" -- anything else fails loudly
    rather than silently defaulting to one or the other.
    """
    if decision not in ("approved", "rejected"):
        raise ValueError("decision must be 'approved' or 'rejected', got {!r}".format(decision))

    state = load_escalation_state(escalations_path)
    current = state.get(gap_key)
    if current is None or current["status"] != "pending":
        raise ValueError(
            "no pending escalation for gap_key {!r} (current state: {})".format(
                gap_key, current["status"] if current else "none"
            )
        )

    updated = dict(current)
    updated["status"] = decision
    if decision == "rejected":
        updated["rejected_at_count"] = current["count"]

    os.makedirs(os.path.dirname(os.path.abspath(escalations_path)), exist_ok=True)
    with open(escalations_path, "a") as fh:
        fh.write(json.dumps(updated, separators=(",", ":")) + "\n")

    if ledger_path is not None:
        import hashlib
        import subprocess
        import uuid
        from datetime import datetime, timezone

        package_root = os.path.dirname(os.path.dirname(_SCRIPTS_DIR))  # .../src
        attest_script = os.path.join(package_root, "skills", "tvt-gov-attest", "scripts", "attest.py")
        reason_code = "AGENT:{}".format(gap_key.replace(" ", "-")[:60])
        proc = subprocess.run(
            [sys.executable, attest_script, "--append", "--ledger", ledger_path,
             "--mode", mode, "--decision-id", str(uuid.uuid4()),
             "--input-ref", hashlib.sha256(gap_key.encode("utf-8")).hexdigest()[:16],
             "--method", "human", "--verdict", decision, "--reason-code", reason_code,
             "--ts", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")],
            capture_output=True, text=True, timeout=30,
        )
        if proc.returncode != 0:
            fail("attest --append failed while resolving {!r}: {}".format(gap_key, proc.stderr))
            return updated

    return updated


def pending_escalations(escalations_path: str = DEFAULT_ESCALATIONS_PATH) -> List[Dict[str, Any]]:
    """T11: what tvt-sales-agent's `status` command surfaces -- every gap_key whose most
    recent record is still "pending" (not yet approved or rejected)."""
    state = load_escalation_state(escalations_path)
    return [rec for rec in state.values() if rec["status"] == "pending"]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--suggestions-file", default=DEFAULT_SUGGESTIONS_PATH)
    p.add_argument("--escalations-file", default=DEFAULT_ESCALATIONS_PATH)
    p.add_argument("--status", action="store_true", help="list pending escalations instead of running aggregation")
    p.add_argument("--resolve", choices=["approved", "rejected"], default=None)
    p.add_argument("--gap-key", default=None)
    p.add_argument("--ledger-file", default=None)
    args = p.parse_args()

    if args.status:
        emit({"pending": pending_escalations(args.escalations_file)})
        return
    if args.resolve:
        if not args.gap_key:
            fail("--resolve requires --gap-key")
            return
        emit(resolve_escalation(args.gap_key, args.resolve, args.escalations_file, args.ledger_file))
        return

    emit(run(args.suggestions_file, args.escalations_file))


if __name__ == "__main__":
    main()
