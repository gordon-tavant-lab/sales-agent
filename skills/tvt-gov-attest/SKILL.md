---
name: tvt-gov-attest
description: >
  Tamper-evident decision audit trail for enterprise/regulated AI — an append-only, hash-chained
  ledger recording every AI decision as input → method → verdict → reason_code → model+version →
  cost. Produces the replayable evidence chain and adverse-action reason codes that examiners demand
  (SR 11-7 model risk, ECOA/FCRA adverse action, NIST AI RMF auditability). Verifies chain integrity
  (tamper detection) and reports attestation coverage + deterministic-resolution rate for the build
  governance gate. Use whenever an AI system makes decisions that must be audited, explained, or
  proven tamper-free — especially mortgage/fintech/lending. Trigger on "audit trail", "decision
  evidence", "reason codes", "adverse action", "SR 11-7", "model risk", "tamper-evident",
  "attestation", "evidence chain". Deterministic Python; hash chain via SHA-256.
argument-hint: "--append|--verify|--report --ledger L.jsonl [--mode poc|mvp|prod] [decision fields]"
user-invocable: true
layer: utility
eval:
  mode: exempt
  rationale: >
    deterministic hash-chained ledger writer — no LLM-generated content to grade.
---

# tvt-gov-attest — Tamper-Evident Decision Evidence Chain

The audit artifact that turns "an agent reviewed it" into "here is the replayable, tamper-proof
record of every decision." Applies `g-pm-grow`'s append-only ledger + `g-learn-determinism-proof`'s
hash chain to AI governance. Part of the governance spine (spec
`the enterprise governance spine); feeds a governance gate if you run one in your own toolkit.

## What a record captures

Every AI decision → one append-only record:
`input_ref → method (deterministic|llm|hybrid|human) → verdict → reason_code → model+version → cost`.
The `reason_code` is the regulated-industry payload: it's the adverse-action / explainability code an
examiner or a denied applicant is entitled to.

## Hash chain (tamper-evidence)

In PROD each record carries `chain_hash = sha256(prev_chain_hash + canonical(record))`. Altering any
past record changes its hash, which breaks every subsequent link — `--verify` finds the exact broken
record. This is what makes the trail *tamper-evident*, not merely *append-only*.

## Mode-graded (the "considered and planned" rule)

| Mode | Ledger | Why |
|---|---|---|
| `poc` | plain decision log (no chaining) | prove the decision path is captured; chaining deferred + planned |
| `mvp` | + reason codes + structured evidence | explainability before external release |
| `prod` | hash-chained, immutable, retention-tagged | full tamper-evident audit for regulated ship |

## Usage

```bash
# append a decision (wrap your AI decision point with this)
python scripts/attest.py --append --ledger audit.jsonl --mode prod \
  --decision-id D-001 --input-ref "loan:123" --method deterministic \
  --verdict pass --reason-code AUS_APPROVE --model claude-opus-4-8 --cost 0.0 --ts <ISO8601>

# verify the chain is intact (CI / pre-deploy / audit) — exits 3 if tampered
python scripts/attest.py --verify --ledger audit.jsonl

# coverage + deterministic-resolution report for the governance gate
python scripts/attest.py --report --ledger audit.jsonl --expected 100
```

`--report` returns `attested_decisions`, `coverage` (vs `--expected`), verdict/method breakdowns, and
`deterministic_resolution_rate` — the governance gate checks coverage ≥ threshold, and the
deterministic rate supports the "resolve ≥25% without LLM" cost-transparency target.

## In the decision path vs as a gate

- **Decision path:** call `--append` at every AI decision point, pairing with `tvt-gov-guard` (guard
  screens, attest records). Pass a fixed `--ts` in replay/test contexts for reproducibility.
- **Gate:** `--verify` (chain intact?) + `--report` (coverage met?) run pre-deploy; failure fails the
  governance gate.

## Boundaries

Deterministic only — the ledger never asks an LLM whether a record is valid; integrity is pure
SHA-256. Records *what* was decided and *why* (reason code); it does not *make* the decision. Pairs
with `tvt-gov-guard` (enforcement) and `g-gov-fairness` (bias metrics) under the `g-dev-build`
governance gate. The `compliance` agent reads the report; this skill produces it.

No external deps (stdlib `hashlib`/`json`). Python 3.9 compatible.
