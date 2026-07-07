# `reception_stats.yaml` — Input Contract (schema_version 1)

> **Irreversible decision.** Every script and every future phase depends on these field
> meanings. Changes require bumping `schema_version` and a migration note here. Treat as
> the single source of truth for a product's seed + reception.

## Top-level shape

```yaml
schema_version: 1                 # int, required. Lock for the migration chain.

product:
  name: string                    # required
  domain_profile: enum            # required: fintech|saas|marketplace|media|enterprise-b2b
  cycle: int                      # required. Nth feedback cycle (1-based). cycle < 4 → sparse mode.
  seed_refs:                      # optional list. The SEED MATERIAL the grow-engine LLM reads.
    - path: string                #   relative/abs path to a spec/doc/file
    - path: string

metrics:                          # required, list of per-cycle blocks (append over time)
  - cycle: int
    adoption:    { ... }          # see pillar metric tables below
    sentiment:   { ... }
    revenue:     { ... }
    competitive: { ... }

pillar_weights_prior:             # optional. Seed weights; reweighter learns from here.
  adoption: float                 #   if omitted, domain_profile defaults are used.
  sentiment: float                #   need not sum to 1 (ingest normalizes).
  revenue: float
  competitive: float

backlog:                          # required (may be empty on cycle 1). Candidate features.
  - id: string                    #   stable id, e.g. "F-012"
    title: string
    category: string              #   Thompson posterior is keyed on this (e.g. "onboarding")
    jtbd: string                  #   job-to-be-done statement
    reach: number                 #   RICE reach (users/period affected)
    impact: number                #   RICE impact: one of 0.25, 0.5, 1, 2, 3
    effort: number                #   person-weeks (>0). RICE denominator + EMV cost basis.
    kano: enum                    #   must_be|one_dimensional|attractive|indifferent|reverse
    delta_value: number           #   Δvalue (monetary) if the feature succeeds — EMV term
    cost: number                  #   fully-loaded cost (monetary) — EMV term
    pillars: [enum]               #   which MDI pillars this hypothesizes to move

outcomes:                         # optional. SHIPPED items → feeds Thompson + ledger + reweighter.
  - id: string
    category: string              #   must match the backlog category it shipped from
    shipped_cycle: int
    success: bool                 #   binary success label → Beta update
    predicted_delta_value: number #   what EMV predicted at commit time
    realized_delta_value: number  #   what actually happened
    pillar_deltas:                #   realized per-pillar movement (reweighter correlation input)
      adoption: float
      sentiment: float
      revenue: float
      competitive: float
```

## Pillar metric tables

All **rates ∈ [0,1]**. `sentiment_score` normalized to **[0,1]** (0.5 = neutral). Monetary fields in
the account's single currency. Metrics marked **(−)** are "lower is better" — the normalizer
inverts them. Unknown metric → omit the key (normalizer skips missing keys, does not assume 0).

### adoption
| key | meaning | direction |
|---|---|---|
| mau | monthly active users | + |
| wau | weekly active users | + |
| new_signups | new signups this cycle | + |
| activation_rate | % new users reaching activation | + (rate) |
| retention_d30 | day-30 retention | + (rate) — also a **health guard** |

### sentiment
| key | meaning | direction |
|---|---|---|
| nps | Net Promoter Score (−100..100) | + |
| review_avg | avg public review (1..5) | + |
| social_mentions | mentions this cycle | + |
| sentiment_score | normalized sentiment | + (rate) — also a **health guard** |

### revenue
| key | meaning | direction |
|---|---|---|
| mrr | monthly recurring revenue | + |
| arpu | avg revenue per user | + |
| paid_conversion | free→paid rate | + (rate) |
| churn_rate | customer churn | (−) (rate) |

### competitive
| key | meaning | direction |
|---|---|---|
| share_of_voice | category share of voice | + (rate) |
| win_rate | competitive win rate | + (rate) |
| category_rank | rank in category (1=best) | (−) |

## Validation rules (enforced by `ingest_seed.py`)

1. `schema_version` must equal a version this skill knows (currently `1`); else hard error.
2. `product.domain_profile` must be a known profile.
3. Every `backlog[].effort > 0`; `impact ∈ {0.25,0.5,1,2,3}`; `kano` in the enum.
4. Every `outcomes[].category` should match some historical backlog category (warn if not).
5. Rates outside [0,1] → hard error (catches un-normalized input early).
6. `metrics` must contain at least the current `cycle`'s block.
7. Normalization is **idempotent**: re-ingesting canonical output yields the same canonical output.

## Normalization → canonical `state.json`

`ingest_seed.py` emits a canonical object the rest of the chain consumes (YAML parsed exactly once):

```json
{
  "schema_version": 1,
  "mode": "full" | "sparse",
  "data_density": {"cycles": N, "sparse": bool, "ledger_records": M},
  "product": {...},
  "domain_profile": {"weights": {...}, "metric_targets": {...}},
  "metrics": [ ... per-cycle, validated ... ],
  "pillar_weights": {...},
  "backlog": [ ... validated ... ],
  "outcomes": [ ... validated ... ]
}
```
