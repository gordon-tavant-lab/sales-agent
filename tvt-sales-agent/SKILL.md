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
    invoked skill owns its own eval gate. See spec008 research-foundations.md for why the
    agent-factory piece specifically is NOT asserted safe without the T4 spike.
---

# tvt-sales-agent — Dynamic Sales Skill Dispatcher

> **Current build stage (T1-T5 of Stage 1 done; T4 gating spike + Stage 2 not yet).** This
> entry point resolves ONE capability per request: Tier-1 deterministic matching first
> (`dispatch.py`, no LLM call), then Tier-2 closed-set LLM-assisted matching if Tier 1
> returns `no_match`/`tied` (`--tier2-prompt` composes the question, the invoking agent
> answers it, `--tier2-validate` checks the answer against the finite slug list -- an
> answer outside that list is treated as `NONE`, never trusted at face value). It does
> **not yet** do multi-job requests (T6), the Agent Factory for genuine capability gaps
> (T9 -- blocked on T4's gating spike, not yet run), or promotion (T10/T11). A request
> neither tier can resolve returns `no_match` rather than guessing; there is no factory
> fallback yet, by design, so this gap is visible rather than silently absorbed.

Full architecture: `../plan.md`. Task-by-task build order: `../tasks.md`. This file is the
thin routing surface — it computes nothing itself. `dispatch.py` does the matching,
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

The full list of 22 capabilities and their trigger patterns is `references/roster.yml`.

## Dispatch Contract (current stage)

1. Run `scripts/dispatch.py "<the request text>"`.
2. If `status: matched` — invoke the named `invokes` skill (under `skills/<name>/`) via the
   `Agent` tool, `subagent_type: general-purpose`, with a thin wrapper prompt naming that
   skill and passing the original request. Return its output.
3. If `status: no_match` — run `scripts/dispatch.py --tier2-prompt "<request>"` to get the
   closed-set classification question, answer it yourself (you already have model access;
   `dispatch.py` does not), then run `scripts/dispatch.py --tier2-validate "<your answer>"`.
   If that validates to `matched`, proceed as step 2. If it's still `no_match` (including
   when your own answer wasn't one of the listed slugs -- the validator does not trust it
   at face value), say so plainly. There is no factory fallback yet (T9, blocked on T4).
4. If `status: tied` — say so plainly, naming the tied capabilities. Do not silently pick
   one. (Multi-job splitting, T6, replaces this for genuinely multi-job requests -- not
   yet built.)

## Guardrails (already load-bearing, not deferred to a later stage)

- **AI drafts, human sends.** Nothing this skill invokes ever sends, posts, or transmits
  anything — every vendored capability's own output is draft/research/analysis. See
  `references/roster.yml`: every entry is `outward_facing: false`.
- **No CRM/PII exfiltration** — enforced by the invoked skill itself (e.g. `tvt-gov-guard`
  where applicable); this router does not add or bypass that.
- **Self-contained** — every dependency is vendored inside this same repo (`../VENDORED_FROM.md`).
  A fresh install of this package needs nothing outside it to run the capabilities above.
