---
name: tvt-sales-prospect
layer: utility
description: >
  Deterministic confidence-scoring and capacity-allocation engine for the sales pipeline (job 1
  of the JTBD spine — "decide who to focus on"). Scores each opportunity's confidence from
  MEDDPICC evidence (/24), ranks a shortlist under a capacity ceiling with a protected floor per
  motion (HUNT/EXPAND), and computes the portfolio KPI scorecard against sourced benchmarks.
  Every number comes from Python, never from a model call. Trigger on "score my pipeline",
  "who should I focus on", "rank my opportunities", "shortlist", "this week's focus",
  "sales KPIs", "portfolio scorecard", "win rate", "pipeline coverage".
argument-hint: "--rank --opportunities-file <opps.json> --capacity N --floor hunt=N,expand=N | kpi --opportunities-file <opps.json>"
user-invocable: true
eval:
  mode: gate
  method: deterministic
  evaluator: scripts/eval_backtest.py
status: implemented — score.py + kpi.py + eval_backtest.py, full test coverage in scripts/test_*.py.
  Fired by tvt-sales-engine for job 1, `pipeline`, and `status` intents; also directly invocable.
---

# tvt-sales-prospect — Confidence-Scored Prioritization & Portfolio KPIs

Scoring math detail: `references/scoring-model.md`. This file is the build contract for the
scorer; the sections below are the full reasoning — do not re-derive it elsewhere.

**Division of labor (non-negotiable):** the LLM extracts MEDDPICC evidence and opportunity
attributes from intel/notes and narrates the results; the Python scripts do **all** arithmetic
and ranking. Never compute, estimate, or adjust a score yourself — run the script, present its
JSON, and keep every field it emits (especially `calibration_state`) intact.

## How to Use This Skill

| You want to... | Run this |
|---|---|
| Score one opportunity's confidence | `python3 scripts/score.py --meddpicc 2,3,1,2,3,2,1,2 --calibration-n 0` |
| Rank the week's shortlist under capacity | `python3 scripts/score.py --rank --opportunities-file opps.json --capacity 8 --floor hunt=3,expand=2 --display` |
| See the portfolio KPI scorecard | `python3 scripts/kpi.py --opportunities-file kpi_opps.json --quota-hunt 500000 --quota-expand 300000` |
| Backtest the scorer against outcomes | `python3 scripts/eval_backtest.py --labeled-file backtest.json --prior-brier 0.21` |

When to use each:

- **`score.py --meddpicc`** — one opportunity, fresh MEDDPICC evidence in hand (e.g. from
  tvt-sales-pov's `gate.py --aggregate-meddpicc`), you want its confidence band.
- **`score.py --rank`** — "who should I focus on this week": a batch under a capacity ceiling,
  with `--floor` protecting a minimum slot count per motion (e.g. `hunt=3,expand=2`).
- **`kpi.py`** — "how is the portfolio doing": win rate, cycle length, pipeline coverage per
  motion vs quota, stage-conversion funnel, pattern-reuse rate, case-study yield — each against
  sourced benchmarks. `--quota-hunt` / `--quota-expand` are dollar quotas (default 0 → coverage
  flags `no_quota_set`).
- **`eval_backtest.py`** — quarterly (or whenever outcomes accrue): Brier score, calibration
  curve (`--bins`, default 5), shortlist precision, and a drift check vs `--prior-brier`.

All scripts emit one JSON object to stdout. Verified flags: `score.py` accepts `--meddpicc`,
`--calibration-n`, `--rank`, `--opportunities-file`, `--capacity`, `--floor`, `--display`; `kpi.py` accepts
`--opportunities-file` (required), `--quota-hunt`, `--quota-expand`; `eval_backtest.py` accepts
`--labeled-file` (required), `--prior-brier`, `--bins`. Nothing else.

## Data contract — the opportunities file

A **local JSON file** you author by hand or export from whatever CRM you have via CSV. This is
the primary, supported path by design, not a fallback — no CRM connection is needed or assumed.
Fixture: `scripts/opportunities.example.json` for `score.py`. `kpi.py` reads a **different**
record shape (see below) — its own fixture is `scripts/kpi_opportunities.example.json`; the two
are not interchangeable.

Shape for `score.py --rank` (array of objects):

```json
{"id": "acct-radian", "motion": "hunt"|"expand", "meddpicc": [0-3 x8], "calibration_n": 0,
 "strategic_fit": 0.9, "deal_value": 250000, "winnability_factors": 0.7}
```

`kpi.py` reads Salesforce-shaped records instead: `{"id", "motion", "stage"` (native SFDC stage
name or `Closed Won`/`Closed Lost`), `"amount", "created_date", "close_date"}` plus two optional
flywheel fields, `pov_cites_pattern` and `case_study_produced`. Annotate any output
you present with where the file came from and how stale it is — never dress an old file up as a
live number.

## The scoring model (brief — full detail in `references/scoring-model.md`)

- **Confidence = MEDDPICC /24, normalized to 0–1.** Eight dimensions scored 0–3 each. The score
  is the qualification — not stage, not age, not rep-feel.
- **Ranking key: `expected_value = confidence × strategic_fit × deal_value ×
  winnability_factors`.**
- **Ordinal band while uncalibrated.** Below the 100-outcome calibration floor, output shows
  High/Medium/Low — never a naked percentage (a caveat next to a precise number does not defeat
  anchoring). The raw value is retained internally for ranking.
- **Protected floor per motion.** HUNT and EXPAND have incommensurable economics, so a blind
  merged ranking starves one motion. `--floor` fills each motion's minimum first, then merges.
- **Parked items are explained, not dropped.** Each carries `promotion_gap` (distance to the
  cutoff, clamped at 0) and `parked_reason` — `below_cutoff` or
  `capacity_consumed_by_motion_floor`.

## Calibration state — be honest about it

The backtesting machinery exists (`eval_backtest.py` — this skill's declared evaluator) but it
only converges as real won/lost outcomes accrue. The `calibrated` label requires ~100 labeled
outcomes; until then every score is `uncalibrated` and displayed as a band. The drift check
suppresses its P1 alert below that same floor (small-n deltas are coin-flip variance). Do not
present an uncalibrated band as a probability, and do not describe the scorer as calibrated
because the eval script exists.

## Guardrails

- **No naked confidence numbers.** Always run `score.py`/`--rank` with the `--display` flag
  when the output will be shown to a human — it structurally removes `confidence_value` (and
  the raw MEDDPICC components) while `calibration_state` is `uncalibrated`, leaving only the
  band. This isn't a formatting preference to honor; the raw number is *absent from the JSON*,
  so there's nothing left to reformat, strip, or "helpfully" convert to a percentage.
- **Never fabricate a score.** An opportunity missing MEDDPICC data gets no score — say which
  dimensions are missing (tvt-sales-pov's job-5 gate is how they get filled), don't guess values.
- **This skill recommends focus; the human decides.** The shortlist is an allocation proposal,
  not a directive — you present it with its parked list and reasons, and the rep chooses.
- **CRM PII → `tvt-gov-guard`** before opportunity data reaches any log, draft, or artifact; data
  stays in-workspace.
