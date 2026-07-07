---
name: tvt-gov-guard
description: >
  Deterministic AI guardrail for enterprise/regulated builds — PII redaction, prompt-injection
  filtering, output-schema validation, and refusal handling. Runs both in the AI call path (mask
  PII before it hits a model or a log; validate model output before it's trusted) and as a
  pre-commit/pre-deploy gate. Mode-graded: POC plans+warns, MVP/PROD enforce fail-closed. Use
  whenever an AI feature touches PII, accepts untrusted input, must return structured output, or
  ships in a regulated industry (mortgage/fintech/health). Trigger on "guardrail", "PII redaction",
  "prompt injection", "output validation", "AI safety", "redact", "enterprise AI guardrails".
  All checks are deterministic Python returning a JSON verdict — no LLM in the decision path.
argument-hint: "--check input|output --text '<text or @file>' [--schema schema.json] [--mode poc|mvp|prod]"
user-invocable: true
layer: utility
eval:
  mode: exempt
  rationale: >
    deterministic pattern-based PII/injection scrubber returning a JSON verdict — no LLM in the decision path to grade.
---

# tvt-gov-guard — Deterministic AI Guardrail

The operational guardrail behind enterprise-grade AI. Where the `prompt-engineer` and `security`
agents *describe* guardrail patterns, this skill *enforces* them as real, reproducible checks. Part
of the governance spine, invoked by a governance gate if you run one in your own toolkit
governance gate and runnable standalone.

## What it enforces

| Check | On | Behavior |
|---|---|---|
| **PII redaction** | input + output | masks SSN, email, card, loan/account #, phone, DOB → placeholders. **Always on, every mode.** |
| **Prompt-injection filter** | input | flags jailbreak/override/system-reveal patterns. Blocks when enforced. |
| **Output-schema validation** | output | asserts valid JSON + required keys + top-level types. Blocks when enforced. |
| **Refusal handling** | output | detects refusals / "cannot determine" so they don't masquerade as content. |

## Mode-graded enforcement (the "considered and planned" rule)

Governance scales with build maturity — POC is not exempt from *considering* a control, only from
*enforcing* it (spec 004 §2):

| Mode | PII | Injection / schema | On a block |
|---|---|---|---|
| `poc` | redacted | scanned, **warn only** (`planned_not_enforced: true`) | exit 0 — never blocks; the finding is logged so it's tracked, not silently skipped |
| `mvp` | redacted | **enforced** | exit 3 (fail-closed) |
| `prod` | redacted | **enforced** | exit 3 (fail-closed) |

A POC that skips enforcement still surfaces every would-be block, so the governance gate can record
it in `governance-plan.md` — deferred, not forgotten.

## Usage

```bash
# scrub + screen an input before it reaches the model (or a log)
python scripts/guard.py --check input --text "@user_input.txt" --mode prod

# validate model output against a contract before trusting it
python scripts/guard.py --check output --text '@model_out.json' --schema contract.json --mode mvp
```

Each call prints one JSON verdict: `{"verdict":"pass|redacted|blocked","mode":..,"enforced":bool,
"findings":[..],"redacted_text":..,"planned_not_enforced":bool}`. Use `redacted_text` as the safe
value to forward. A `blocked` verdict in mvp/prod exits 3 (fail-closed) — callers must treat nonzero
as "do not proceed."

## In the AI call path vs as a gate

- **Call path:** redact PII on the way *in* (before model + before logging — honors g-dev-observe's
  "never log PII"), and validate/scan on the way *out*. Wrap your model call with two guard calls.
- **Gate:** run over a batch of fixtures pre-deploy; any `blocked` fails the governance gate.

## Patterns

Pattern bank in `scripts/patterns.yml` (aligned with `g-core/data/pii-patterns.yml`). Extend per
workspace at `${CLAUDE_PROJECT_DIR}/.claude/gov-patterns.yml` (override wins). PII findings carry a
`placeholder`; injection/refusal are signature-based. Tune patterns there, not in code.

## Boundaries

Deterministic enforcement only — no LLM in the decision path (auditable, byte-identical across runs).
Pairs with `tvt-gov-attest` (logs each guarded decision to the evidence chain) and feeds the
`g-dev-build` governance gate. Threat *modeling* stays with the `security` agent; prompt *design*
with `prompt-engineer`. This skill is the runtime enforcer they point to.

Setup: `pip install -r scripts/requirements.txt` (pyyaml).
