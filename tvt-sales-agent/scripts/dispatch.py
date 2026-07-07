"""tvt-sales-agent dispatcher — deterministic Tier-1 matching (T2 scope only).

Tier 1 (this file, for now): case-insensitive substring match of the incoming request
against each roster capability's trigger_patterns (roster.yml). Exactly one match wins.
Zero or multiple matches are NOT resolved here — that is Tier 2's job (T5, LLM-assisted
fallback, closed-set only) and this module deliberately returns NO_MATCH / TIED for both
so a later caller can decide what happens next, rather than guessing here.

No multi-job splitting (T6), no LLM fallback (T5), no factory (T9) in this file yet —
see tasks.md Stage 1 for the staged build order this mirrors.
"""
import hashlib
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from common import emit, fail, load_roster, known_slugs

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
_PACKAGE_ROOT = os.path.dirname(os.path.dirname(_SCRIPTS_DIR))  # .../src
ATTEST_SCRIPT = os.path.join(_PACKAGE_ROOT, "skills", "tvt-gov-attest", "scripts", "attest.py")
DEFAULT_LEDGER = os.path.join(_SCRIPTS_DIR, "..", "output", "invocation-ledger.jsonl")


def match_tier1(request_text: str, roster: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic Tier-1 match. Returns one of:
      {"status": "matched", "capability_slug": "...", "invokes": "..."}
      {"status": "no_match"}
      {"status": "tied", "candidates": ["slug-a", "slug-b", ...]}
    """
    text = request_text.lower()
    hits: List[Dict[str, str]] = []
    for cap in roster["capabilities"]:
        for pattern in cap["trigger_patterns"]:
            if pattern.lower() in text:
                hits.append(cap)
                break  # one hit per capability is enough; don't double-count

    if len(hits) == 0:
        return {"status": "no_match"}
    if len(hits) == 1:
        return {
            "status": "matched",
            "capability_slug": hits[0]["capability_slug"],
            "invokes": hits[0]["invokes"],
        }
    return {
        "status": "tied",
        "candidates": [h["capability_slug"] for h in hits],
    }


def split_multi_job(matched_slugs: List[str], roster: Dict[str, Any]) -> List[List[str]]:
    """Deterministic multi-job splitter (T6, plan.md S1.2). Given a set of capability
    slugs that ALL matched within a single request (a Tier-1 "tied" result, or a Tier-2
    equivalent), sequence them into execution stages: a capability with a depends_on edge
    to another slug ALSO in this matched set runs after it; everything else runs in the
    same parallel stage. Returns a list of stages (each stage a list of slugs that can run
    concurrently), stages in execution order.

    Only edges where BOTH endpoints are in the matched set count -- a capability's
    depends_on may name something this particular request never asked for (e.g.
    pov-synthesis always declares depends_on: [account-research-deep], but a request that
    only names pov-synthesis and meeting-prep-pack has no reason to also run research).
    """
    matched_set = set(matched_slugs)
    depends_on = {
        c["capability_slug"]: [d for d in c.get("depends_on", []) if d in matched_set]
        for c in roster["capabilities"]
        if c["capability_slug"] in matched_set
    }

    stages: List[List[str]] = []
    remaining = set(matched_slugs)
    placed: List[str] = []
    while remaining:
        # A slug is ready for this stage once every one of its (in-set) dependencies has
        # already been placed in an earlier stage.
        ready = sorted(s for s in remaining if all(d in placed for d in depends_on[s]))
        if not ready:
            # A cycle in depends_on among the matched set -- should never happen with a
            # well-formed roster.yml, but fail loudly rather than infinite-loop or guess.
            raise ValueError(
                "circular depends_on among matched capabilities: {}".format(sorted(remaining))
            )
        stages.append(ready)
        placed.extend(ready)
        remaining -= set(ready)
    return stages


def assemble_envelope(individual_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """T7, plan.md S1.3: fixed response-envelope assembly. Every specialist invocation
    (pre-existing wrapper, ephemeral factory agent, or promoted agent alike) returns
    {status: ok|failed, capability_slug, output, notes} -- this function splits that list
    into {results: [...], failures: [...]} BEFORE any LLM synthesis runs, so a failure can
    never be silently dropped by an LLM that "forgot" to mention it. Every result must
    already be in the fixed contract shape -- this function does not invent or coerce a
    missing field, it fails loudly on a malformed result instead of passing it through.
    """
    results, failures = [], []
    for r in individual_results:
        for field in ("status", "capability_slug", "output", "notes"):
            if field not in r:
                raise ValueError(
                    "result missing required field {!r} (contract: status/capability_slug/"
                    "output/notes): {}".format(field, r)
                )
        if r["status"] == "failed":
            failures.append(r)
        else:
            results.append(r)
    return {"results": results, "failures": failures}


def attest_dispatch(
    result: Dict[str, Any],
    request_text: str,
    ledger_path: str = DEFAULT_LEDGER,
    mode: str = "poc",
) -> Optional[Dict[str, Any]]:
    """T8: the deterministic orchestrator itself writes the ledger entry via the vendored
    tvt-gov-attest -- never left to an agent to remember to self-report (plan.md S3.5).
    Only a real dispatch decision ("matched") gets attested; no_match/tied/multi_job
    carry nothing to attribute a capability_slug to yet. Returns the attest.py output, or
    None if there was nothing to attest for this result.
    """
    if result.get("status") != "matched":
        return None

    reason_code = "AGENT:{}".format(result["capability_slug"])
    method = "llm" if result.get("method") == "llm" else "deterministic"
    decision_id = str(uuid.uuid4())
    input_ref = hashlib.sha256(request_text.encode("utf-8")).hexdigest()[:16]
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    os.makedirs(os.path.dirname(os.path.abspath(ledger_path)), exist_ok=True)
    proc = subprocess.run(
        [sys.executable, ATTEST_SCRIPT, "--append", "--ledger", ledger_path,
         "--mode", mode, "--decision-id", decision_id, "--input-ref", input_ref,
         "--method", method, "--verdict", "dispatched", "--reason-code", reason_code,
         "--model", "tier1" if method == "deterministic" else "tier2-llm-assisted",
         "--cost", "0.0", "--ts", ts],
        capture_output=True, text=True, timeout=30,
    )
    if proc.returncode != 0:
        fail("attest --append failed: {}".format(proc.stderr))
        return None
    return json.loads(proc.stdout)


def dispatch(
    request_text: str,
    roster: Dict[str, Any],
    ledger_path: str = DEFAULT_LEDGER,
    attest: bool = True,
) -> Dict[str, Any]:
    """The real top-level entry point (T8): resolve_tier1(), then attest the decision if
    one was actually made. attest=False exists only for tests that want to check
    resolution without writing to a real ledger file.
    """
    result = resolve_tier1(request_text, roster)
    if attest:
        attest_dispatch(result, request_text, ledger_path)
    return result


def resolve_tier1(request_text: str, roster: Dict[str, Any]) -> Dict[str, Any]:
    """Tier-1 match, then apply T6's tied-to-multi_job transform. This is what callers
    (the CLI, tests) should use instead of match_tier1() directly when they want the full
    current-stage behavior; match_tier1() itself stays a pure single-purpose matcher.
    """
    result = match_tier1(request_text, roster)
    if result["status"] == "tied":
        return {"status": "multi_job", "stages": split_multi_job(result["candidates"], roster)}
    return result


def build_tier2_prompt(request_text: str, roster: Dict[str, Any]) -> str:
    """Deterministically compose the Tier-2 closed-set classification prompt (plan.md
    S1.1). This function does NOT call an LLM -- dispatch.py has no model access. The
    prompt is composed here (testable, reproducible) and answered by the calling agent
    (the Claude Code session already running this skill), then checked back through
    validate_tier2_answer() below. The LLM cannot invent a new slug: any answer outside
    the finite list, or an explicit NONE, is treated as no-match by the validator.
    """
    slugs = known_slugs(roster)
    lines = [
        "Which of these known job/capability slugs -- or NONE -- best fits this request?",
        "",
        "Request: {!r}".format(request_text),
        "",
        "Known slugs:",
    ]
    lines.extend("  - {}".format(s) for s in slugs)
    lines.append("")
    lines.append("Answer with exactly one slug from the list above, or the literal word NONE.")
    return "\n".join(lines)


def validate_tier2_answer(answer: str, roster: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic validation of a Tier-2 LLM answer against the finite slug list.
    Never trusts the answer at face value -- an answer outside the known list, or NONE,
    is no_match, exactly like an unresolved Tier-1 request. This is what keeps Tier 2
    "constrained to a closed set, never open-ended" (plan.md S1.1 point 3).
    """
    slugs = known_slugs(roster)
    cleaned = answer.strip()
    if cleaned.upper() == "NONE":
        return {"status": "no_match", "method": "llm"}
    if cleaned not in slugs:
        return {"status": "no_match", "method": "llm", "note": "answer not in known slug list, treated as NONE"}
    invokes = next(c["invokes"] for c in roster["capabilities"] if c["capability_slug"] == cleaned)
    return {"status": "matched", "capability_slug": cleaned, "invokes": invokes, "method": "llm"}


def main() -> None:
    if len(sys.argv) < 2:
        fail("usage: dispatch.py '<request text>' | dispatch.py --tier2-prompt '<text>' | dispatch.py --tier2-validate '<answer>'")

    try:
        roster = load_roster()
    except (OSError, ValueError) as e:
        fail("roster load failed: {}".format(e))
        return

    if sys.argv[1] == "--tier2-prompt":
        if len(sys.argv) < 3:
            fail("usage: dispatch.py --tier2-prompt '<request text>'")
        prompt = build_tier2_prompt(sys.argv[2], roster)
        emit({"prompt": prompt})
        return

    if sys.argv[1] == "--tier2-validate":
        if len(sys.argv) < 3:
            fail("usage: dispatch.py --tier2-validate '<llm answer>'")
        emit(validate_tier2_answer(sys.argv[2], roster))
        return

    request_text = sys.argv[1]
    emit(resolve_tier1(request_text, roster))


if __name__ == "__main__":
    main()
