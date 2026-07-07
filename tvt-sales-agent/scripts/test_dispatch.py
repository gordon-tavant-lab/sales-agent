"""Tests for dispatch.py Tier-1 matching (T2 scope). Python 3.9 compatible."""
import json
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


# --- T6: multi-job splitter ---

def test_split_multi_job_sequences_a_dependent_pair(roster):
    from dispatch import split_multi_job

    stages = split_multi_job(["account-research-deep", "pov-synthesis"], roster)
    assert stages == [["account-research-deep"], ["pov-synthesis"]]


def test_split_multi_job_parallelizes_an_independent_pair(roster):
    from dispatch import split_multi_job

    stages = split_multi_job(["deck-build", "visual-design"], roster)
    assert len(stages) == 1
    assert set(stages[0]) == {"deck-build", "visual-design"}


def test_split_multi_job_ignores_out_of_set_dependencies(roster):
    # pov-synthesis depends_on account-research-deep, but if THIS request only names
    # pov-synthesis + meeting-prep-pack, account-research-deep isn't part of the matched
    # set and must not appear in the sequencing at all.
    from dispatch import split_multi_job

    stages = split_multi_job(["pov-synthesis", "meeting-prep-pack"], roster)
    all_slugs = [s for stage in stages for s in stage]
    assert "account-research-deep" not in all_slugs
    assert stages == [["pov-synthesis"], ["meeting-prep-pack"]]


def test_resolve_tier1_transforms_tied_into_multi_job(roster):
    from dispatch import resolve_tier1

    result = resolve_tier1("build a pov and also prep for my meeting", roster)
    assert result["status"] == "multi_job"
    assert result["stages"] == [["pov-synthesis"], ["meeting-prep-pack"]]


def test_resolve_tier1_passes_through_single_match_unchanged(roster):
    from dispatch import resolve_tier1

    result = resolve_tier1("who should I focus on this week", roster)
    assert result["status"] == "matched"
    assert result["capability_slug"] == "prospect-score"


# --- T7: response-envelope assembly ---

def test_assemble_envelope_splits_ok_and_failed():
    from dispatch import assemble_envelope

    individual = [
        {"status": "ok", "capability_slug": "account-research-deep", "output": "dossier text", "notes": ""},
        {"status": "failed", "capability_slug": "pov-synthesis", "output": None, "notes": "upstream research incomplete"},
    ]
    envelope = assemble_envelope(individual)
    assert len(envelope["results"]) == 1
    assert envelope["results"][0]["capability_slug"] == "account-research-deep"
    assert len(envelope["failures"]) == 1
    assert envelope["failures"][0]["capability_slug"] == "pov-synthesis"


def test_assemble_envelope_all_ok_has_empty_failures():
    from dispatch import assemble_envelope

    individual = [{"status": "ok", "capability_slug": "deck-build", "output": "deck.pptx", "notes": ""}]
    envelope = assemble_envelope(individual)
    assert envelope["failures"] == []
    assert len(envelope["results"]) == 1


def test_assemble_envelope_rejects_malformed_result_loudly():
    from dispatch import assemble_envelope

    with pytest.raises(ValueError, match="missing required field"):
        assemble_envelope([{"status": "ok", "capability_slug": "deck-build"}])  # missing output/notes


def test_assemble_envelope_a_failure_can_never_silently_disappear():
    # The whole point of T7: a failure mixed into a multi-job result must survive the
    # envelope split, never get dropped.
    from dispatch import assemble_envelope

    individual = [
        {"status": "ok", "capability_slug": "pov-synthesis", "output": "pov text", "notes": ""},
        {"status": "failed", "capability_slug": "meeting-prep-pack", "output": None, "notes": "tool error"},
        {"status": "ok", "capability_slug": "deck-build", "output": "deck.pptx", "notes": ""},
    ]
    envelope = assemble_envelope(individual)
    assert len(envelope["failures"]) == 1
    assert len(envelope["results"]) == 2
    assert sum(len(v) for v in envelope.values()) == len(individual)


# --- T8: ledger wiring via real tvt-gov-attest ---

def test_dispatch_writes_a_real_ledger_entry_for_a_matched_request(roster, tmp_path):
    from dispatch import dispatch as run_dispatch

    ledger_path = str(tmp_path / "ledger.jsonl")
    result = run_dispatch("who should I focus on this week", roster, ledger_path=ledger_path)
    assert result["status"] == "matched"

    with open(ledger_path) as fh:
        records = [json.loads(line) for line in fh]
    assert len(records) == 1
    assert records[0]["reason_code"] == "AGENT:prospect-score"
    assert records[0]["method"] == "deterministic"
    assert records[0]["verdict"] == "dispatched"


def test_dispatch_writes_nothing_for_no_match(roster, tmp_path):
    from dispatch import dispatch as run_dispatch

    ledger_path = str(tmp_path / "ledger.jsonl")
    result = run_dispatch("what's the weather in Austin today", roster, ledger_path=ledger_path)
    assert result["status"] == "no_match"
    assert not os.path.exists(ledger_path)


def test_dispatch_writes_nothing_for_multi_job_at_the_top_level(roster, tmp_path):
    # The top-level "multi_job" result itself isn't a single capability dispatch -- each
    # STAGE's actual invocation (once T9/orchestration runs them) attests individually.
    # dispatch() itself has no single capability_slug to attribute here.
    from dispatch import dispatch as run_dispatch

    ledger_path = str(tmp_path / "ledger.jsonl")
    result = run_dispatch("build a pov and also prep for my meeting", roster, ledger_path=ledger_path)
    assert result["status"] == "multi_job"
    assert not os.path.exists(ledger_path)


def test_ledger_entries_are_chain_verifiable_by_real_tvt_gov_attest(roster, tmp_path):
    import subprocess

    from dispatch import ATTEST_SCRIPT
    from dispatch import dispatch as run_dispatch

    ledger_path = str(tmp_path / "ledger.jsonl")
    run_dispatch("who should I focus on this week", roster, ledger_path=ledger_path)
    run_dispatch("build a POV for Citi", roster, ledger_path=ledger_path)

    proc = subprocess.run(
        [sys.executable, ATTEST_SCRIPT, "--verify", "--ledger", ledger_path],
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    verdict = json.loads(proc.stdout)
    assert verdict["intact"] is True
    assert verdict["records"] == 2


def test_attest_dispatch_uses_agent_prefixed_reason_code(roster, tmp_path):
    from dispatch import attest_dispatch, resolve_tier1

    ledger_path = str(tmp_path / "ledger.jsonl")
    result = resolve_tier1("build a POV for Citi", roster)
    attest_result = attest_dispatch(result, "build a POV for Citi", ledger_path=ledger_path)
    assert attest_result is not None
    assert attest_result["appended"] == 1

    with open(ledger_path) as fh:
        record = json.loads(fh.readline())
    assert record["reason_code"] == "AGENT:pov-synthesis"


# --- T9: narrowed (recombination-only) Agent Factory ---

def test_recombination_prompt_lists_every_known_slug(roster):
    from dispatch import build_recombination_prompt

    prompt = build_recombination_prompt("a request nothing single-matches", roster)
    for cap in roster["capabilities"]:
        assert cap["capability_slug"] in prompt
    assert "NONE" in prompt


def test_validate_recombination_accepts_two_valid_slugs_and_sequences_them(roster):
    from dispatch import validate_recombination_answer

    result = validate_recombination_answer("account-research-deep,pov-synthesis", roster)
    assert result["status"] == "recombination"
    assert result["stages"] == [["account-research-deep"], ["pov-synthesis"]]


def test_validate_recombination_rejects_none():
    from dispatch import validate_recombination_answer
    import yaml

    roster = yaml.safe_load(open(os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "references", "roster.yml"
    )))
    assert validate_recombination_answer("NONE", roster)["status"] == "no_recombination"


def test_validate_recombination_rejects_a_single_slug(roster):
    # A single valid slug isn't recombination -- Tier 1/2 would already have caught that.
    from dispatch import validate_recombination_answer

    result = validate_recombination_answer("pov-synthesis", roster)
    assert result["status"] == "no_recombination"


def test_validate_recombination_rejects_the_whole_answer_if_any_slug_is_invented(roster):
    # The core safety property, same as Tier 2: one invented slug invalidates the WHOLE
    # answer, never partial-trust a mix of real + fabricated slugs.
    from dispatch import validate_recombination_answer

    result = validate_recombination_answer("pov-synthesis,a-slug-that-does-not-exist", roster)
    assert result["status"] == "no_recombination"


def test_propose_new_skill_writes_a_pending_suggestion(tmp_path):
    from dispatch import propose_new_skill

    path = str(tmp_path / "suggestions.jsonl")
    record = propose_new_skill("detect a stalled pilot before it jeopardizes production", "no match", path)
    assert record["status"] == "pending"
    assert "stalled pilot" in record["request_text"]

    with open(path) as fh:
        lines = fh.readlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["status"] == "pending"


def test_factory_dispatch_with_valid_recombination_never_writes_a_suggestion(roster, tmp_path):
    from dispatch import factory_dispatch

    suggestions_path = str(tmp_path / "suggestions.jsonl")
    result = factory_dispatch(
        "research and then form a pov", roster,
        recombination_answer="account-research-deep,pov-synthesis",
        suggestions_path=suggestions_path,
    )
    assert result["status"] == "recombination"
    assert not os.path.exists(suggestions_path)


def test_factory_dispatch_with_no_recombination_suggests_instead_of_running_anything(roster, tmp_path):
    from dispatch import factory_dispatch

    suggestions_path = str(tmp_path / "suggestions.jsonl")
    result = factory_dispatch(
        "detect a stalled pilot before it jeopardizes production", roster,
        recombination_answer="NONE",
        suggestions_path=suggestions_path,
    )
    assert result["status"] == "suggested"
    assert os.path.exists(suggestions_path)


def test_factory_dispatch_genuine_gap_never_triggers_an_autonomous_ephemeral_run(roster, tmp_path):
    # T9's explicit requirement: a genuine from-scratch gap (T4 measured this unreliable,
    # 66/24/70%, never 90%) routes to the human suggestion path, NEVER an autonomous run.
    # There is no code path in factory_dispatch() that invokes the Agent tool at all --
    # this test proves the function's only possible outcomes are "recombination" (existing,
    # already-vetted skills) or "suggested" (human queue). Nothing else exists to call.
    from dispatch import factory_dispatch

    suggestions_path = str(tmp_path / "suggestions.jsonl")
    result = factory_dispatch(
        "detect a stalled pilot before it jeopardizes production", roster,
        recombination_answer=None,  # not yet asked -- the "haven't even tried recombination" path
        suggestions_path=suggestions_path,
    )
    assert result["status"] == "suggested"
    assert result["suggestion"]["status"] == "pending"


def test_factory_dispatch_guardrail_outward_facing_request_never_gets_a_send_capable_path(roster, tmp_path):
    # FR-010: agent creation must never become a side door around the "AI drafts, human
    # sends" guardrail. Structural proof, not a keyword filter: every roster capability is
    # outward_facing:false (T1's own invariant, tested separately), and factory_dispatch's
    # only two outcomes are (a) recombine EXISTING roster members -- all outward_facing:
    # false -- or (b) suggest to a human. There is no third outcome where a request like
    # this reaches a tool capable of sending anything.
    from dispatch import factory_dispatch

    suggestions_path = str(tmp_path / "suggestions.jsonl")
    result = factory_dispatch(
        "send an email to Citi telling them we're raising prices", roster,
        recombination_answer="NONE",  # no existing capability sends anything -- honest NONE
        suggestions_path=suggestions_path,
    )
    assert result["status"] == "suggested"
    for cap in roster["capabilities"]:
        assert cap["outward_facing"] is False
