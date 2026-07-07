"""Tests for dispatch.py Tier-1 matching (T2 scope). Python 3.9 compatible."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest  # noqa: E402
from common import load_roster  # noqa: E402
from dispatch import match_tier1  # noqa: E402


@pytest.fixture(scope="module")
def roster():
    return load_roster()


# --- spec006 §4's original example intents that map onto a real, vendored roster
#     capability today (g-sales-engine's original examples, verified against tvt-sales-agent's
#     actual roster — not every example maps to a capability that exists) ---

SPEC006_EXAMPLES_THAT_MATCH = [
    ("who should I focus on this week", "prospect-score"),
    ("build a POV for Citi", "pov-synthesis"),
    ("prep for the Citi meeting", "meeting-prep-pack"),
]


@pytest.mark.parametrize("request_text,expected_slug", SPEC006_EXAMPLES_THAT_MATCH)
def test_spec006_example_intents_match(roster, request_text, expected_slug):
    result = match_tier1(request_text, roster)
    assert result["status"] == "matched", "expected a match for: {!r}, got {}".format(
        request_text, result
    )
    assert result["capability_slug"] == expected_slug


# --- Rephrased variants of the same intents — proves Tier 1 isn't just matching the
#     literal example string, and documents which rephrasings the *keyword* table still
#     catches vs. which would need Tier 2 (T5, not built yet in this stage) ---

REPHRASED_VARIANTS_THAT_MATCH = [
    ("who should I call today", "prospect-score"),
    ("give me a ranked shortlist", "prospect-score"),
    ("draft a point of view for Wells Fargo", "pov-synthesis"),
    ("get me ready for the Wells Fargo call", "meeting-prep-pack"),
]


@pytest.mark.parametrize("request_text,expected_slug", REPHRASED_VARIANTS_THAT_MATCH)
def test_rephrased_variants_match(roster, request_text, expected_slug):
    result = match_tier1(request_text, roster)
    assert result["status"] == "matched", "expected a match for: {!r}, got {}".format(
        request_text, result
    )
    assert result["capability_slug"] == expected_slug


# --- Honest gaps: spec006 §4 examples with NO real, vendored roster capability today.
#     These MUST return no_match, not a wrong guess — a false-positive match here would
#     be worse than an honest no_match, because it would silently mishandle the request
#     instead of falling through to Tier 2 / the factory (T5/T9, not built in this stage). ---

SPEC006_EXAMPLES_WITH_NO_ROSTER_CAPABILITY_YET = [
    "expand Citi",             # HUNT/EXPAND motion framing (§2 of spec006) isn't its own roster
                                # capability in this POC — the underlying scan skill exists, but
                                # "expand"-as-a-verb isn't a trigger pattern; deferred, not built here
    "draft outreach to Citi",  # no outreach-draft skill is vendored; spec006 itself never built
                                # one either (spec006 §8: "decide at build" — never resolved)
]


@pytest.mark.parametrize("request_text", SPEC006_EXAMPLES_WITH_NO_ROSTER_CAPABILITY_YET)
def test_honest_gaps_return_no_match_not_a_wrong_guess(roster, request_text):
    result = match_tier1(request_text, roster)
    assert result["status"] in ("no_match", "tied"), (
        "a request with no real roster capability must never silently return a wrong "
        "'matched' result — got {} for {!r}".format(result, request_text)
    )


def test_find_new_prospects_variant_does_match(roster):
    # "find new credit-union prospects" (without the HUNT-motion clause) DOES match —
    # the gap above is specifically the motion-tagging language, not the base request.
    result = match_tier1("find new credit-union prospects", roster)
    assert result["status"] == "matched"
    assert result["capability_slug"] == "prospect-scan"


# --- Zero-match and tied-match mechanics ---

def test_unrelated_request_returns_no_match(roster):
    result = match_tier1("what's the weather in Austin today", roster)
    assert result["status"] == "no_match"


def test_multi_capability_request_returns_tied_not_a_guess(roster):
    # Tier 1 alone (T2 scope) does not split multi-job requests — that's T6. A request
    # naming two distinct capabilities must come back "tied", never pick one arbitrarily.
    result = match_tier1("build a pov and also prep for my meeting", roster)
    assert result["status"] == "tied"
    assert set(result["candidates"]) == {"pov-synthesis", "meeting-prep-pack"}


def test_roster_has_no_duplicate_slugs(roster):
    slugs = [c["capability_slug"] for c in roster["capabilities"]]
    assert len(slugs) == len(set(slugs))


def test_roster_has_22_capabilities(roster):
    # Pinned count — if this changes, it should be a deliberate roster edit, not a
    # silent drift from a bad merge or partial vendor.
    assert len(roster["capabilities"]) == 22


def test_no_capability_is_marked_outward_facing(roster):
    # Every roster member today is draft/research/analysis output only. If this ever
    # needs to flip to true for a future capability, that's a guardrail-relevant change
    # that should be reviewed deliberately, not slip in silently.
    for cap in roster["capabilities"]:
        assert cap["outward_facing"] is False, cap["capability_slug"]


# --- T5: Tier-2 prompt composition + answer validation ---

def test_tier2_prompt_lists_every_known_slug(roster):
    from dispatch import build_tier2_prompt

    prompt = build_tier2_prompt("make Citi think we're strategic", roster)
    for cap in roster["capabilities"]:
        assert cap["capability_slug"] in prompt
    assert "NONE" in prompt


def test_tier2_prompt_includes_the_request_text(roster):
    from dispatch import build_tier2_prompt

    prompt = build_tier2_prompt("a very specific request about Wells Fargo", roster)
    assert "Wells Fargo" in prompt


def test_tier2_validate_accepts_known_slug(roster):
    from dispatch import validate_tier2_answer

    result = validate_tier2_answer("pov-synthesis", roster)
    assert result["status"] == "matched"
    assert result["capability_slug"] == "pov-synthesis"
    assert result["method"] == "llm"


def test_tier2_validate_rejects_none(roster):
    from dispatch import validate_tier2_answer

    result = validate_tier2_answer("NONE", roster)
    assert result["status"] == "no_match"


def test_tier2_validate_rejects_invented_slug(roster):
    # The core safety property: the LLM cannot invent a new slug at this step
    # (plan.md SS1.1 point 2) -- any answer outside the finite list is no_match,
    # never trusted at face value.
    from dispatch import validate_tier2_answer

    result = validate_tier2_answer("a-slug-that-does-not-exist", roster)
    assert result["status"] == "no_match"


def test_tier2_validate_is_case_and_whitespace_tolerant_for_none(roster):
    from dispatch import validate_tier2_answer

    assert validate_tier2_answer("  none  ", roster)["status"] == "no_match"
    assert validate_tier2_answer("None", roster)["status"] == "no_match"


# --- T16: JTBD-step alignment + known-gaps registration ---

VALID_JTBD_STEPS = {"S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9"}


def test_every_capability_has_a_valid_jtbd_step(roster):
    for cap in roster["capabilities"]:
        assert "jtbd_step" in cap, cap["capability_slug"]
        assert cap["jtbd_step"] in VALID_JTBD_STEPS, "{}: {}".format(
            cap["capability_slug"], cap.get("jtbd_step")
        )


def test_s7_has_zero_roster_coverage_matching_the_confirmed_gap(roster):
    # This is not a bug -- it's the confirmed finding (O13, jtbd-pipeline-gaps.md). If this
    # test ever fails because a capability WAS added under S7, that's good news worth noticing
    # explicitly, not a silent pass -- update known-gaps.yml's O13 entry when it happens.
    s7_capabilities = [c for c in roster["capabilities"] if c["jtbd_step"] == "S7"]
    assert s7_capabilities == [], "S7 gained coverage: {} -- update known-gaps.yml".format(
        s7_capabilities
    )


def test_known_gaps_file_registers_o1_and_o13():
    import os

    import yaml

    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "references",
        "known-gaps.yml",
    )
    with open(path) as fh:
        data = yaml.safe_load(fh)
    ids = {g["id"] for g in data["known_gaps"]}
    assert ids == {"O1", "O13"}

    o13 = next(g for g in data["known_gaps"] if g["id"] == "O13")
    assert o13["jtbd_step"] == "S7"
    assert o13["coverage"] == "none"

    o1 = next(g for g in data["known_gaps"] if g["id"] == "O1")
    assert o1["jtbd_step"] == "S1"
    assert o1["coverage"] == "partial"
    assert o1["covered_by"] in {c["capability_slug"] for c in yaml.safe_load(
        open(os.path.join(os.path.dirname(path), "roster.yml"))
    )["capabilities"]}
