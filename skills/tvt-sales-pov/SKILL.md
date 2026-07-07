---
name: tvt-sales-pov
layer: compound
description: >
  Synthesizes a testable Point-of-View / Business Value Hypothesis ("Problem we see → Impact we
  anticipate → Change we propose") from fact-checked research and cross-client patterns. Owns
  POV validation-tracking: records each claim as validated/refuted/refined from a manually-authored
  claims batch (Notion auto-capture deferred — see below). Ships in two build stages — see below.
  Trigger on "build a POV for <target>", "form a point of view", "what's our differentiator for
  <account>", "prep for <meeting>" (job 5 validation half).
argument-hint: "\"<target/account>\" | validate --claims-file <claims.json> | confirm --batch <id>"
user-invocable: true
status: build in progress — Stage 1 authoring workflow + job-5 verification gate (scripts/gate.py,
  28/28 tests passing) implemented and usable end-to-end on a manually-authored claims.json. Notion
  transcript auto-extraction and Stage 2 synthesis are deliberately deferred, not blocked on MCP
  approval (design decision — see docs/ in this repo)
eval:
  mode: gate
  depth: standard
---

# tvt-sales-pov — Point-of-View / Business Value Hypothesis Synthesis

Full design: see docs/ in this repo (job 3, the discovery → AI-opportunity bridge, and the
verification gate). This file is the build contract; do not re-derive the reasoning here.

## How to Use This Skill

| You want to... | Say this |
|---|---|
| Form a POV for a target | `tvt-sales-pov "build a POV for <target>"` |
| Capture validation from a call | `tvt-sales-pov validate --claims-file <claims.json>` (manually authored — see below) |
| Confirm a batch of queued claims | `tvt-sales-pov confirm --batch <batch-id>` |
| See what's queued for review | `tvt-sales-pov queue` |

## Two-stage build (do not skip to Stage 2)

- **Stage 1 (build first, implemented):** a thin authoring aid over 3-5 hand-curated
  mortgage/fintech-specific provocations (see `provocations/`) + the discovery-call blueprint.
  Given a target, this stage:
  1. Reads every `provocations/*.md` (or `<slug>/problem_we_see.md` + `impact_we_anticipate.md`
     + `change_we_propose.md`) in the library.
  2. Picks the provocation(s) whose named problem best matches the target's known context
     (from whatever job-2 dossier exists — `tvt-intel-dossier`/`tvt-intel-customer` output).
  3. Tailors the wording to the target (account name, specific numbers where the dossier
     supports them — never invents a number the dossier doesn't back) without inventing a new
     provocation from scratch. If no provocation fits, say so rather than forcing a weak match —
     an empty library or a bad fit is a signal to write a new curated provocation, not to
     synthesize one on the fly (that's Stage 2's job, gated below).
  4. Emits the discovery-call blueprint: the agenda built around "here's what we believe is
     happening — where are we off?" (co-creation framing, not extraction — see the
     insight-saturation caveat in docs/).
  - Validates the POV-led motion converts in real conversations before automating pattern
    discovery. **The provocations library itself is empty until you write the first 3-5** —
    that's content work, not a code dependency, and can start immediately (see
    `provocations/README.md`).
- **Stage 2 (only after Stage 1 shows validated/refuted signal — do not build early):**
  synthesizes a POV by orchestrating `tvt-intel-flywheel` (cross-client patterns) + `tvt-pm-jtbd`
  (scored under-served outcomes) + `tvt-intel-dossier`/`tvt-intel-customer` (account research) +
  `tvt-intel-fanout` (named competitor/vendor entities feeding MEDDPICC Competition). Synthesis
  reasoning follows the `ai-solution-thinker` agent's existing pain-point → solution-hypothesis →
  accelerator-pattern methodology — do not invent new reasoning logic for this job. **Gate:**
  check whether Stage 1 provocations have accumulated validated/refuted outcomes (job 5) before
  starting Stage 2 work; if Stage 1 hasn't been used in a real conversation yet, that's the
  blocker, not a missing Stage 2 feature.

## Hard gate — do not violate

**Input research must clear `tvt-intel-factcheck` before synthesis.** No unverified claim reaches a
client-facing POV — a hallucinated claim reaching the pitch is worse than a bad ledger entry.
This is the upstream twin of the verification gate below and applies to both stages,
though it is load-bearing mainly for Stage 2 (Stage 1 draws only from hand-curated, already-vetted
provocation text, not freshly synthesized research claims).

## Validation-tracking (job 5) — implemented via `scripts/gate.py`

Records each POV claim (MEDDPICC dimension evidence, or a validated/refuted/refined judgment) from
a **manually-authored `claims.json`** — one small batch per call, not a form (design decision:
Notion auto-extraction is deliberately deferred, not blocked on MCP approval —
most sales-team members this skill is meant to reach don't have a Notion workspace wired up, so
auto-capture can't be the assumed path yet). The gate below is source-agnostic: everything
downstream of "a claims.json exists" is implemented and tested, whether that file was typed by hand
or (if ever built) extracted automatically from a transcript:

```bash
cd scripts
# 1. classify a batch of hand-typed claims. --source manual means no invented confidence
#    number (author is the verifier by construction) — --queue-file persists queued claims
#    with a real timestamp instead of losing track of when they entered the queue
python3 gate.py --classify --claims-file claims.json --source manual --queue-file queue.jsonl
#    → {"auto_attested": [...], "queued": [...], "counts": {...}, "n_appended_to_queue": N}
#    (if claims ever come from an automated extractor instead, use --source extracted — that
#    keeps the full confidence-threshold tiering, the defense that path actually needs)

# 2. auto_attested claims: pair each with tvt-gov-attest directly, no human step (invoke the vendored
#    tvt-gov-attest skill — its copy ships in this repo at tvt-gov-attest/,
#    installed with the same plugin; "consume, don't duplicate governance" — see docs/)
tvt-gov-attest --append --ledger pov.jsonl --mode mvp --decision-id <claim_id> \
  --input-ref "account:<id>" --method manual --verdict auto_attest \
  --reason-code AUTHOR_ATTESTED

# 3. queued claims: surface for a one-tap batch confirm. --confirm-queue computes elapsed time
#    itself from the queue's own timestamps — nothing is self-reported by the person being
#    policed — and removes confirmed claims from the queue file
python3 gate.py --confirm-queue --queue-file queue.jsonl --claim-ids <id1,id2> \
  --abuse-log abuse.jsonl
#    → {"abuse_flag": true|false, "elapsed_seconds": <computed>, "accumulated": {...}}
#    then attest the confirmed ones the same way as step 2 (reason_code from the confirmed
#    claim, not a synthetic one). "accumulated" is the all-time abuse rate across every
#    confirm event ever logged — a rising rate means retune HIGH_CONFIDENCE_THRESHOLD in
#    gate.py, not add more friction

# 4. once all 8 MEDDPICC dimensions have been confirmed (auto or one-tap) for an account,
#    aggregate into the /24 score tvt-sales-prospect's score.py consumes for job-1 confidence
python3 gate.py --aggregate-meddpicc --dims-file confirmed_dims.json
#    → {"meddpicc_raw": N, "meddpicc_max": 24, "dimensions_missing": [...]}
```

**Never** call `tvt-gov-attest --append` for a claim `gate.py` classified `"queue"` until a real
confirm event happened — that is the entire point of the gate ("confirm nothing writes
to attest without a confirm event").

## Build status

- **Implemented:** `scripts/gate.py` — risk-tiered classify/queue split (`--source manual|extracted`,
  manual = author-attested with no invented confidence number), persistent queue-state JSONL
  with computed (not self-reported) elapsed time and an accumulated abuse-rate KPI, MEDDPICC /24
  aggregation from confirmed dimensions only. 28/28 tests passing (`scripts/test_gate.py`). CLI
  verified end-to-end against `scripts/claims.example.json`. Usable today on a manually-authored
  `claims.json` — this is the complete, supported path, not a stopgap.
- **Implemented:** Stage 1 authoring workflow (provocation matching + discovery-call blueprint
  generation), described above — this is markdown-driven orchestration, no script needed.
- **Deliberately deferred, not scheduled (design decision — see docs/ in this repo):** Notion MCP
  transcript → claim-JSON extraction. Most sales-team members won't have Notion access wired up, so
  this was never the right thing to build first; if it's ever built, it only needs to target the
  same `claims.json` shape `gate.py` already consumes — nothing else changes. The `tvt-gov-attest`
  wiring above is a documented CLI call, not yet scripted into one command.
- **Blocked by design, not an oversight:** Stage 2 synthesis, gated behind Stage 1 field signal.
- **Content dependency:** the provocations library (`provocations/`) is still empty — write the
  first 3-5 hand-curated mortgage/fintech provocations before Stage 1 has anything to match
  against. This has no code dependency and can happen in parallel with anything else in this file.

## Output Gate (mandatory before finishing)

Before finishing, gate the artifact: `/tvt-core-eval gate --output <artifact> --criteria ${CLAUDE_PLUGIN_ROOT}/rubrics/pov.md`. Do not hand it off until it passes.
