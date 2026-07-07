# Job-Map — Input Contract

The structured capture of a Job-to-be-Done. The LLM fills this from interviews, support tickets,
meeting notes, or a discovery session; `score.py` then opportunity-scores it deterministically.

```yaml
job:
  statement: string      # the functional job, solution-agnostic ("get approved for a home loan…")
  executor: string       # who performs the job (the persona/role)
  context: string        # optional: when/where/constraints (shapes which outcomes matter)

# The process — the steps the executor moves through to get the job done.
# Capturing these is half the value: friction usually lives at step boundaries.
job_steps:
  - id: string           # S1, S2, …
    name: string

# Desired outcomes — the MEASURABLE success criteria the executor judges the job by.
# This is the heart of JTBD: outcomes are stable + solution-agnostic ("minimize the time to…",
# "minimize the likelihood of…", "increase confidence that…"). Each is rated:
outcomes:
  - id: string           # O1, O2, …
    job_step: string     # which step it belongs to (links to job_steps[].id)
    statement: string    # the outcome, phrased as a metric to minimize/maximize/increase
    importance: number   # how much the executor cares, 0–scale (default scale 10)
    satisfaction: number # how well TODAY'S solutions deliver it, 0–scale
    friction: string     # optional: what makes it hard now (the qualitative "why")
```

## How outcomes should be phrased

Good outcomes are **stable and solution-free** — they describe what the executor wants to achieve,
not a feature. Use the ODI verb forms:
- "Minimize the **time** it takes to …"
- "Minimize the **likelihood** that …"
- "Increase the **confidence** that …"

Bad (a feature in disguise): "Add a document scanner." Good (the underlying outcome): "Minimize the
time to assemble required documents." Features come later — in `tvt-pm-grow` — as *solutions* to
under-served outcomes.

## Rating scale

Default 1–10 (`--scale`). `importance` and `satisfaction` must be within `[0, scale]`. Ratings come
from the executor (surveys/interviews) where possible; LLM-estimated ratings are acceptable for a
first pass but should be flagged as estimates and refined with real data — the whole point is to
score against *evidence*, not opinion.

## What scoring produces

`opportunity = importance + max(0, importance − satisfaction)`. High-importance, low-satisfaction
outcomes score highest (under-served → where to improve). See `references/odi.md`.
