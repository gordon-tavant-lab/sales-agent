# Domain Profiles

One skill, configurable priors. A profile sets (a) starting pillar weights and (b) per-metric
normalization targets. The loop **drifts away from these priors** as it accumulates evidence
(see `reweight_pillars.py`), so a profile is a *starting point*, not a cage. Canonical source of
truth is `scripts/profiles.py` — this doc explains intent.

## Choosing a profile

| Profile | Use when the product is… | Pillar bias |
|---|---|---|
| `fintech` | lending, payments, mortgage, banking (the default for this team) | revenue-led, retention-as-health |
| `saas` | subscription B2B/B2C software | adoption + revenue balanced |
| `marketplace` | two-sided, GMV-driven | adoption-led (liquidity first) |
| `media` | content/audience, ad-or-sub monetization | adoption + sentiment-led |
| `enterprise-b2b` | high-ACV, sales-led, few large accounts | revenue + competitive-led |

## What a profile contains

- **weights**: prior `{adoption, sentiment, revenue, competitive}` summing to 1.
- **metric_targets**: per metric, a `(target, direction)` pair. `target` is the value at which the
  metric's normalized subscore saturates near 1.0. `direction`:
  - `+` higher is better (`norm = x/target`)
  - `-` lower is better (`norm = target/x`) — e.g. churn_rate, category_rank
  - `rate` already in [0,1], used directly (or `x/target` if a sub-1 target is set)

## Tuning a vertical (e.g. mortgage specifically)

Edit the relevant profile in `scripts/profiles.py`. For a mortgage lender you might lower the
`mau` target (B2B2C volumes are smaller than consumer SaaS) and raise the `revenue.mrr` target.
Because targets only affect normalization, changing them rescales subscores but never breaks the
contract. Add a brand-new vertical by adding a key to `PROFILES`.

## Sparse-data behavior

With `cycle < 4`, the reweighter ignores correlation and uses these priors verbatim, flagging
`low_confidence`. This is deliberate: with too little history, the profile prior is more
trustworthy than a correlation estimated on 1–2 points. The skill says so out loud rather than
pretending to have learned.
