---
name: tvt-pm-jtbd
description: >
  Jobs-to-be-Done capture + opportunity scoring. Captures a job-map (the job someone is trying to get
  done, the process steps they move through, and the measurable outcomes they judge success by),
  then deterministically scores WHERE TO IMPROVE using the Ulwick Outcome-Driven Innovation
  opportunity algorithm (importance + under-satisfaction) — ranking outcomes as under-served (improve
  these), appropriately-served, or over-served (stop investing). Tracks movement over time to prove
  improvements landed. The upstream feeder to tvt-pm-grow: under-served outcomes become candidate
  features. Use to capture a process/job, identify the highest-value areas to improve, and iterate.
  Trigger on "jobs to be done", "JTBD", "job map", "opportunity scoring", "outcome-driven", "where
  should we improve", "capture this process", "find the friction", "what's underserved", "/tvt-pm-jtbd".
  Scoring is deterministic Python; the LLM only captures the job-map from interviews/notes.
argument-hint: "--jobmap jobmap.yaml [--scale 10] [--compare prior.json]   (or: capture a job-map first)"
user-invocable: true
layer: utility
eval:
  mode: gate
  depth: standard
---

# tvt-pm-jtbd — Jobs-to-be-Done Capture & Opportunity Scoring

Find the jobs worth solving *before* deciding what to build. This skill captures a Job-to-be-Done as
a structured job-map, then computes — deterministically — which outcomes are most under-served, i.e.
exactly where improvement creates the most value. It's the front of the product loop; its output
feeds `tvt-pm-grow` (which turns under-served outcomes into scored, built, grown features).

## The loop it runs (capture → identify → improve → track)

1. **Capture** (LLM) — turn interviews / support tickets / discovery notes into a `jobmap.yaml`: the
   job, its process steps, and the measurable outcomes the executor judges success by, each rated
   importance + current satisfaction. See `references/schema.md`.
2. **Score** (Python, deterministic) — `opportunity = importance + max(0, importance − satisfaction)`.
   Ranks outcomes; classifies under-/appropriately-/over-served. See `references/odi.md`.
3. **Identify areas to improve** — under-served outcomes are objectively the highest-value targets.
4. **Hand off** — those become candidate features for `tvt-pm-grow` (the `grow_handoff` payload).
5. **Track** — after shipping, re-rate satisfaction and `--compare`; a falling opportunity score is
   *proof* the improvement worked.

## Usage

```bash
pip install -r scripts/requirements.txt   # pyyaml

# score a captured job-map
python scripts/score.py --jobmap jobmap.yaml > jtbd-scored.json

# later cycle — track what moved after you shipped improvements
python scripts/score.py --jobmap jobmap-now.yaml --compare jtbd-scored.json > jtbd-delta.json
```

Output is one JSON object: `ranked_outcomes` (every outcome with its opportunity score + class),
`top_opportunities` (the under-served ones), `summary` counts, and **`grow_handoff`** — the
under-served outcomes formatted as `jtbd` candidate seeds for tvt-pm-grow. With `--compare`, adds a
`tracking` block (per-outcome movement, most improved, most regressed).

## How it feeds g-dev-build → tvt-pm-grow (the chain)

```
g-dev-build  →  product-manager agent  →  tvt-pm-jtbd  →  tvt-pm-grow
                                          (find the          (build & grow
                                           jobs worth         against the
                                           solving)           under-served
                                                              outcomes)
```

`tvt-pm-grow`'s grow-engine Scaffold 1 says "JTBD-cluster demand signals first, then emit candidates."
This skill IS that step, made rigorous: instead of the LLM guessing the jobs, `tvt-pm-jtbd` captures
and *scores* them, and its `grow_handoff` outcomes drop straight into tvt-pm-grow's `backlog[].jtbd`
fields as evidence-backed candidate seeds. The `product-manager` agent runs this before scoring a
backlog, so a regulated/enterprise build's roadmap traces to scored jobs, not opinion.

## Why deterministic scoring matters

The "where to improve" decision is computed from importance/satisfaction via a published algorithm
(Ulwick ODI), not asserted by a model — so it's reproducible, defensible, and trackable over time
(same eval-first discipline as tvt-pm-grow's ledger and tvt-gov-attest's chain). The LLM's job is the
*capture* (reading messy inputs into a clean job-map); the math is the scoring.

## Boundaries

Captures and scores *jobs and outcomes* — solution-free. It does NOT design features (that's
`tvt-pm-grow`) or write the PRD (that's the `product-manager` agent, which calls this). Keep outcomes
phrased as metrics to minimize/maximize, never as features — see `references/schema.md`. Domain-
agnostic: works on a product's user job, your own work process, or a client's business process
(swap the job-map; the algorithm is identical). Sample in `samples/jobmap.sample.yaml`.

## Output Gate (mandatory before finishing)

Before finishing, gate the artifact: `/tvt-core-eval gate --output <artifact> --criteria ${CLAUDE_PLUGIN_ROOT}/rubrics/client-facing-doc.md`. Do not hand it off until it passes.
