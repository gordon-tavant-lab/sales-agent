# Capabilities — tvt-sales-agent

One entry-point skill dispatching across 22 capabilities in the sales/intel/pm/create family,
organized by the real 9-step JTBD pipeline model (`specs/006-g-sales-engine/docs/jtbd-pipeline-gaps.md`).

## Entry point

- **`tvt-sales-agent`** — dynamic dispatcher. Tier 1 (deterministic keyword match) → Tier 2
  (closed-set LLM-assisted match) → recombination of existing capabilities → human-reviewed
  "propose a new skill" suggestion. See `tvt-sales-agent/SKILL.md` for the full dispatch contract.

## Capabilities by JTBD step

| Step | Capabilities |
|---|---|
| S1 — Identify & prioritize | `prospect-scan`, `prospect-score` |
| S2 — Qualify & deep-research | `account-dossier`, `account-research-customer`, `account-research-deep`, `competitor-fanout`, `intel-pipeline`, `product-opportunity-scoring` |
| S3 — Verify before client-facing | `intel-factcheck` |
| S4 — Craft narrative | `pitch-content-strategy`, `pov-synthesis` |
| S5 — Assemble & present | `deck-build`, `explainer-doc`, `meeting-prep-pack`, `pptx-build`, `tavantize-brand`, `visual-design` |
| S6 — Negotiate & close | `engagement-proposal` |
| S7 — Adopt — drive usage | **none** — confirmed gap (O13), pre-registered in `known-gaps.yml` |
| S8 — Renew | `account-qbr`, `product-roadmap-grow` |
| S9 — Review — capture IP | `pattern-extraction`, `sales-distill` |

Full trigger patterns + dependency edges: `tvt-sales-agent/references/roster.yml`.

## Known gaps

`tvt-sales-agent/references/known-gaps.yml` pre-registers two pipeline steps with weak/no
coverage (O13: S7, zero coverage; O1: S1, partial coverage) as candidates for the "propose a
new skill" suggestion path, sourced from a real, separate JTBD gap-analysis document rather
than waiting for usage to rediscover them.

## Vendored skill family (24)

See `VENDORED_FROM.md` for the full list + source provenance (commit hash, per-skill). 22
roster-family skills (intel/sales/pm/create) + `tvt-tavantize` (branding) + 2 governance
dependencies (`tvt-gov-guard`, `tvt-gov-attest`) used by the dispatch/factory mechanism
itself, not as dispatch targets.

## Governance & measurement

- **Invocation Ledger** (`tvt-sales-agent/output/invocation-ledger.jsonl`) — every dispatch
  decision attested via the real, vendored `tvt-gov-attest`, tamper-evident and chain-verifiable.
- **`kpi_capture.py`** — produces a `readings.json` consumable by `g-mature-assess`'s real
  KPI gate for the sales-gtm domain (7 KPIs). Real values where data exists, honest `no_data`
  where it doesn't.
- **`promotion_check.py`** — aggregates recurring "propose a new skill" suggestions and
  escalates a gap for a human decision once it crosses a configurable threshold. Approval is
  a prioritization signal, never an automatic skill-authoring action.

## Agents

- `agents/` — empty. This narrowed build (per a real gating spike, `research-foundations.md`)
  never creates a new agent autonomously — every request is served by an existing roster
  member (directly or recombined) or routed to the human suggestion queue above.

## Architecture

This `CAPABILITIES.md` is self-contained on purpose: the full design/plan/task-history docs
(spec.md, plan.md, tasks.md, research-foundations.md) live in the outer Workspace repo's
`specs/008-sales-agent-swarm/` directory, not inside this package -- a `/plugin marketplace add`
install of this repo does not include them, so this file never links to them. If you have the
outer Workspace checkout, they're at `specs/008-sales-agent-swarm/{plan,tasks,research-foundations}.md`.
