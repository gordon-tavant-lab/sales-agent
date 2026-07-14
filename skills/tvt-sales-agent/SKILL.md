---
name: tvt-sales-agent
layer: orchestrator
description: >
  Dynamic entry-point dispatcher for the sales/intel/pm/create skill family. Ask in plain
  language; a deterministic Tier-1 matcher (dispatch.py) routes the request to the right
  vendored tvt-* skill and returns its output. No fixed job table — new phrasings just need
  a roster.yml trigger pattern, not a code change.
  Trigger on any sales/research/product-strategy intent: "who should I focus on", "build a
  POV for <target>", "prep for <meeting>", "research <company>", "build a deck", or any
  request naming a capability listed in references/roster.yml.
argument-hint: "<intent>"
user-invocable: true
eval:
  mode: gate
  depth: standard
  note: this router computes nothing itself -- routing is deterministic (dispatch.py), the
    invoked skill owns its own eval gate. T4's gating spike (run 2026-07-07, see
    research-foundations.md) found the from-scratch factory concept does NOT meet the bar
    (66/24/70%, none reached 90%) -- the factory is narrowed to recombination-only, not
    asserted safe as originally scoped.
---

# tvt-sales-agent — Dynamic Sales Skill Dispatcher

> **Current build stage (2026-07-07): T0-T9 + T16-T17 done; T10-T15 (promotion + ops
> polish) not yet.** Dispatch is 3-tier: Tier 1 deterministic keyword match (no LLM call),
> Tier 2 closed-set LLM-assisted match (only if Tier 1 finds nothing), and the narrowed
> Agent Factory (T9, only if Tier 2 also finds nothing) — which recombines 2+ EXISTING
> roster capabilities via the same closed-set discipline, or, failing that, writes a
> human-facing "propose a new skill" suggestion. **There is no path anywhere in this build
> that invents a new agent on the spot and runs it autonomously** — T4's spike measured
> that approach unreliable (66%/24%/70% against real skills' rubrics, never the 90% bar),
> so it was never built; a genuine capability gap always becomes a human-reviewed
> suggestion, never an autonomous action. Multi-job requests (T6) sequence via
> `roster.yml`'s `depends_on` edges (dependent jobs run in order, independent jobs in
> parallel) and always assemble a `{results, failures}` envelope (T7) so a partial failure
> can never silently disappear. Every dispatch decision is attested via the real,
> vendored `tvt-gov-attest` (T8) — you never need to log anything yourself. Every
> capability is tagged with its real JTBD pipeline step (`jtbd_step`, T16) and
> `scripts/kpi_capture.py` (T17) reports real progress against `g-mature-assess`'s KPI
> gate. **Not yet built:** promotion of a factory-created ephemeral agent to a permanent
> one (T10/T11 — moot for now anyway, since the narrowed factory never creates an
> ephemeral agent to begin with; T10/T11 would apply to a future from-scratch factory if
> one is ever built), manifest finalization (T12), guardrail regression check (T13),
> Hermes registration (T14), install-completeness check (T15).

Full architecture, task-by-task build order, and research foundations live in the outer
Workspace repo's `specs/008-sales-agent-swarm/{plan,tasks,research-foundations}.md` -- not
inside this package (a marketplace install of this repo alone doesn't include them; see
`../CAPABILITIES.md`). This file is the thin routing surface — it computes nothing itself. `dispatch.py` does the matching,
`references/roster.yml` is the capability manifest, and every capability it dispatches to
is a vendored copy under `skills/` (see `../VENDORED_FROM.md`) — never a reference to
`sales-skills.git` or any `g-*` original (hard rule, `plan.md` §1).

## How to Use This Skill

Just ask, in plain language. Examples that resolve today (Tier 1, exact or near-exact
phrasing — see `scripts/test_dispatch.py` for the full covered/uncovered list):

| You want to... | Say this |
|---|---|
| Rank this week's focus | `tvt-sales-agent "who should I focus on this week"` |
| Research an account | `tvt-sales-agent "research Citi"` |
| Form a point of view on a target | `tvt-sales-agent "build a POV for <target>"` |
| Prep for a meeting | `tvt-sales-agent "prep for the <target> meeting"` |
| Build a deck | `tvt-sales-agent "build a deck for <target>"` |
| Score product opportunities | `tvt-sales-agent "what's underserved for <client>'s process"` |

The full list of 22 capabilities and their trigger patterns is `references/roster.yml` --
each tagged with the real JTBD pipeline step (S1-S9) it serves, per
`specs/006-g-sales-engine/docs/jtbd-pipeline-gaps.md`'s scoring. `references/known-gaps.yml`
registers the two steps with weak/no coverage (S7 Adopt: none; S1 signal-scan: partial) as
pre-registered candidates for the eventual factory's "propose a new skill" path.
`scripts/kpi_capture.py` produces a `readings.json` consumable by `g-mature-assess`'s
existing KPI gate -- real values where data exists, honest `no_data` where it doesn't.

## Dispatch Contract

1. Run `python3 scripts/dispatch.py "<the request text>"` (this attests the decision
   automatically via `tvt-gov-attest`, T8 -- you don't need to log anything yourself).
2. If `status: matched` — invoke the named `invokes` skill (under `skills/<name>/`) via the
   `Agent` tool, `subagent_type: general-purpose`, with a thin wrapper prompt naming that
   skill and passing the original request. Return its output.
3. If `status: multi_job` — the request named 2+ distinct capabilities (T6). `stages` is a
   list of execution stages in order; within a stage, dispatch all listed capabilities as
   parallel `Agent` calls (step 2's wrapper pattern, once each); wait for a stage to finish
   before starting the next. Collect every individual result (each already in `{status,
   capability_slug, output, notes}` shape) and assemble via `scripts/dispatch.py`'s
   `assemble_envelope()` (T7) before synthesizing one final answer — a `failures` entry, if
   any, is a **mandatory rendered section** of your response, never silently dropped.
4. If `status: no_match` — first try Tier 2: run `scripts/dispatch.py --tier2-prompt
   "<request>"`, answer the closed-set question yourself, then `--tier2-validate "<your
   answer>"`. If that validates to `matched`, proceed as step 2.
5. If Tier 2 also returns `no_match` — try recombination (T9, narrowed per the T4 spike
   result): run the equivalent recombination prompt (`dispatch.py`'s
   `build_recombination_prompt()`), answer it yourself, validate via
   `validate_recombination_answer()`. If it validates to `status: recombination`, treat the
   returned `stages` exactly like step 3 (multi-job) — every stage still only invokes
   **existing, already-vetted roster members**, never a newly-invented agent.
6. If recombination also finds nothing (`no_recombination`) — call `propose_new_skill()`
   (T9) and say so plainly to the user. **This is the only outcome for a genuine capability
   gap.** There is no path in this build that invents a new agent on the spot and runs it —
   T4 measured that approach unreliable (66%/24%/70% against real skills' rubrics, never
   90%), so it was never built. A gap becomes a human-reviewed suggestion, not an
   autonomous action.

## Guardrails (already load-bearing, not deferred to a later stage)

- **AI drafts, human sends.** Nothing this skill invokes ever sends, posts, or transmits
  anything — every vendored capability's own output is draft/research/analysis. See
  `references/roster.yml`: every entry is `outward_facing: false`.
- **No CRM/PII exfiltration** — enforced by the invoked skill itself (e.g. `tvt-gov-guard`
  where applicable); this router does not add or bypass that.
- **Self-contained** — every dependency is vendored inside this same repo (`../VENDORED_FROM.md`).
  A fresh install of this package needs nothing outside it to run the capabilities above.
