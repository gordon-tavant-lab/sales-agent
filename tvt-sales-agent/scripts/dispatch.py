"""tvt-sales-agent dispatcher — deterministic Tier-1 matching (T2 scope only).

Tier 1 (this file, for now): case-insensitive substring match of the incoming request
against each roster capability's trigger_patterns (roster.yml). Exactly one match wins.
Zero or multiple matches are NOT resolved here — that is Tier 2's job (T5, LLM-assisted
fallback, closed-set only) and this module deliberately returns NO_MATCH / TIED for both
so a later caller can decide what happens next, rather than guessing here.

No multi-job splitting (T6), no LLM fallback (T5), no factory (T9) in this file yet —
see tasks.md Stage 1 for the staged build order this mirrors.
"""
import sys
from typing import Any, Dict, List

from common import emit, fail, load_roster, known_slugs


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
