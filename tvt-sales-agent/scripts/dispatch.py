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
    result = match_tier1(request_text, roster)
    emit(result)


if __name__ == "__main__":
    main()
