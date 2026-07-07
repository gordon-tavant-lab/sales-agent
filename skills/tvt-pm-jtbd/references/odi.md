# The Opportunity Algorithm (Ulwick ODI) — why this scoring is defensible

`tvt-pm-jtbd` doesn't ask an LLM "what should we improve?" — it computes it from importance +
satisfaction ratings using Tony Ulwick's **Outcome-Driven Innovation** opportunity algorithm, the
most established quantitative method in Jobs-to-be-Done practice.

## The formula

```
opportunity = importance + max(0, importance − satisfaction)
```

Intuition: an outcome is a big opportunity when it's **important** AND **under-satisfied**. The
`max(0, …)` term means over-satisfying never *subtracts* from importance — it just stops adding. On
a 1–10 scale, scores run ~0–20.

## Classification (scale-relative; defaults for 1–10)

| opportunity | class | meaning |
|---|---|---|
| ≥ 1.5×scale (≥15) | **under-served** | high value to improve — the gold; these become tvt-pm-grow candidates |
| 1.0–1.5×scale (10–15) | appropriately-served | adequate; don't over-invest |
| < 1.0×scale (<10) | **over-served** | already better than it needs to be — candidate to *trim* cost, not add |

## Why it fits the "capture / improve / identify areas" loop

- **Capture** — the job-map records the job, its steps, and the outcomes (the process + the metrics).
- **Identify areas to improve** — the algorithm ranks outcomes by opportunity; under-served ones are
  objectively where improvement creates the most value. No vibes.
- **Improve** — under-served outcomes hand off to `tvt-pm-grow` as candidate features (solutions).
- **Track over time** — re-rate satisfaction after shipping and `--compare`; an outcome's opportunity
  dropping (e.g. 15→11) is *proof* the improvement landed. This is the same predicted-vs-realized
  discipline as tvt-pm-grow's ledger and tvt-gov-attest's chain.

## Failure modes

- **Garbage ratings → garbage scores.** Importance/satisfaction should come from the executor
  (survey/interview), not the team's guess. LLM-estimated ratings are a starting point, flagged as
  estimates. The scoring is only as good as the inputs — same eval-first truth as everywhere else.
- **Solution-shaped outcomes.** If an "outcome" is really a feature ("add a scanner"), it can't be
  stably scored or tracked. Keep outcomes solution-free (see `references/schema.md`).
- **Over-serving blindness.** Don't ignore over-served outcomes — they're where you may be
  *spending* effort that no longer moves the needle; flag them for possible simplification.
