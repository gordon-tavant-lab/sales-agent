# Scoring Model — tvt-sales-prospect

Reference for the math in `../scripts/score.py` and `../scripts/eval_backtest.py`. The code is
the source of truth; this file explains it.

## MEDDPICC confidence (/24)

Eight dimensions, each scored 0–3 on evidence strength (0 = no evidence, 3 = confirmed):
`metrics` (quantified impact the buyer agreed to), `economic_buyer` (identified and engaged),
`decision_criteria` (written criteria known, shaped by us), `decision_process` (steps/dates/
owners mapped), `paper_process` (legal/procurement path known), `identify_pain` (pain admitted,
cost attached), `champion` (named, actively selling internally), `competition` (alternatives
known, win themes placed). `confidence_value = sum / 24`, a 0–1 float. A vector that isn't
exactly 8 dimensions, or a value outside 0–3, is rejected — not coerced.

## Expected value (the ranking key)

```
expected_value = confidence_value × strategic_fit × deal_value × winnability_factors
```

`strategic_fit` and `winnability_factors` are 0–1 judgments from the opportunities file;
`deal_value` is dollars. Multiplicative on purpose: a zero on any factor zeroes the deal.

## Display: ordinal band while uncalibrated

Below the calibration floor (`CALIBRATION_FLOOR = 100` realized outcomes) output carries
`display_band` — High (≥ 0.67), Medium (≥ 0.34), Low — never a raw percentage, because a caveat
label next to a precise number does not defeat anchoring (Kahneman). At `calibration_n ≥ 100` it
switches to `display_percent`. The raw value is always retained for ranking math.

## Protected-floor allocation (`rank_shortlist`)

1. Score all; sort each motion's pool by `expected_value` descending.
2. Fill each motion's declared floor first (e.g. `hunt=3,expand=2`); warn if a pool is short.
3. Allocate remaining capacity from one merged pool, best `expected_value` first.
4. Cutoff = lowest shortlisted `expected_value`. Each parked item gets
   `promotion_gap = max(0, cutoff − ev)` and a `parked_reason`: `below_cutoff`, or
   `capacity_consumed_by_motion_floor` when it outscored the cutoff but lost its slot to a
   floor-protected item from the other motion.

Rationale: HUNT and EXPAND have incommensurable risk/economics profiles; a blind merged ranking
systematically starves whichever motion scores structurally lower.

## Cold start: why MEDDPICC-as-prior beats no prior

With zero closed outcomes there is nothing to fit a model to. MEDDPICC /24 is a structured,
evidence-gated qualification checklist — a defensible prior that is auditable dimension by
dimension, unlike stage/age/rep-feel — and stays the primary confidence input until enough
outcomes accrue to calibrate against.

## Calibration & backtest path (`eval_backtest.py`)

Given labeled records `{confidence_value, was_shortlisted, outcome: won|lost}`:

- **Brier score** — mean squared error between confidence and the 0/1 outcome; lower is better.
- **Calibration curve** — predicted mean vs actual win rate per confidence bucket (default 5
  bins), with per-bin `gap`.
- **Shortlist precision** — fraction of shortlisted items that closed won (job 1's KPI).
- **Drift check** — current vs prior-period Brier. Rising Brier = the scorer is getting *less*
  calibrated: `WORSENING — P1` once `n ≥ 100`; below that floor, `worsening_but_not_significant`
  (informational — a P1 that fires on coin-flip variance trains its operator to ignore it).

The 100-outcome floor (`MIN_N_FOR_CALIBRATION`) matches `score.py`'s display switch: calibration
below ~100–200 closed deals is not statistically meaningful.
