# `tvt-pm-grow` — Math Reference

All formulas the deterministic scripts implement. The LLM never computes these; it reads the
JSON the scripts emit. Constants are tunable defaults, documented inline.

## Table of contents
1. RICE × Kano scoring
2. Thompson Sampling — calibrated P(success)
3. MDI composition + Goodhart guard
4. Bayesian pillar reweighting (self-definition)
5. EMV ranking + tiering
6. Backtest accuracy (Brier, MAPE)
7. Forecasting (Phase 2, deferred)
8. Constants

---

## 1. RICE × Kano scoring  (`score_rice_kano.py`)

RICE core (Confidence deliberately **excluded** here — injected later as Thompson P(success)):

```
rice_core = (reach × impact) / effort        # effort > 0
```

Kano multiplier `k` classifies the *kind* of value:

| kano label | k | rationale |
|---|---|---|
| must_be | 0.8 | table stakes — capped upside, but absence causes churn |
| one_dimensional | 1.0 | linear value (more = better) — neutral |
| attractive | 1.3 | delighter — disproportionate retention/buzz |
| indifferent | 0.4 | users don't care — heavily discount |
| reverse | 0.1 | some users actively dislike — near-kill |

```
rice_kano = rice_core × k
```

**Failure mode:** Kano labels are subjective. Mitigation: the table is explicit and tunable; labels
come from the LLM/human at candidate time, never inferred by Python.

---

## 2. Thompson Sampling — calibrated P(success)  (`thompson_tracker.py`)

One Beta(α, β) posterior **per feature `category`** (categories share signal; individual features
are too sparse). Prior: Beta(1, 1) (uniform), or a weak domain-profile-informed prior.

Update from `outcomes[]`, with **exponential recency decay** so recent reception dominates:

```
w_i = exp(−λ · (cycle_now − shipped_cycle_i))         # λ = 0.3 default
α = α0 + Σ_i  w_i · success_i
β = β0 + Σ_i  w_i · (1 − success_i)
```

Outputs per category:
```
p_success      = α / (α + β)                          # posterior mean → becomes RICE Confidence
ci90           = [Beta.ppf(0.05; α,β), Beta.ppf(0.95; α,β)]   # 90% credible interval
thompson_sample= a single draw from Beta(α,β)         # for explore/exploit if needed
```

Wide `ci90` (little evidence) signals caution downstream and in sparse mode. Uncertain categories
naturally get discounted because EMV uses the posterior mean and the interval is reported.

**Failure mode:** cold start (no outcomes). Mitigation: uniform prior → p_success = 0.5; sparse mode
flags low confidence.

---

## 3. MDI composition + Goodhart guard  (`mdi_compose.py`)

**Per-metric normalization to [0,1]** against domain-profile targets:

```
norm(x) = clip( x / target , 0, 1 )                   # "+" metrics
norm(x) = clip( target / x , 0, 1 )   if x>0 else 0   # "(−)" metrics (lower is better)
rate metrics already in [0,1] use themselves (or x/target if a target<1 is set)
```

**Pillar subscore** = mean of its normalized present metrics (missing keys skipped, not zeroed):

```
subscore_pillar = mean( norm(metric) for metric present in pillar )
```

**MDI**:
```
MDI = Σ_pillar  w_pillar · subscore_pillar            # weights sum to 1
```

**Goodhart divergence guard** — over the last two cycles, flag if a value pillar rises while a
health metric falls:

```
if Δrevenue_subscore > +θ  and  (Δsentiment_subscore < −θ  OR  Δretention_d30 < −θ):
    goodhart_alert("revenue rising while sentiment/retention falling")
```
θ = 0.05 default. Generalized: any pillar up while a designated health metric (retention_d30,
sentiment_score) is down.

---

## 4. Bayesian pillar reweighting — self-definition  (`reweight_pillars.py`)

The loop **defines its own objective** by learning which pillars actually predict winning.

For each pillar, Pearson correlation `r` between that pillar's per-cycle subscore movement and the
**lead outcome** (default: next-cycle MDI; tunable to next-cycle revenue):

```
r_pillar = pearson( Δsubscore_pillar[t] , lead_outcome[t+1] )   over available cycles
```

Target weight from correlation (clip r to [−1,1]):
```
w_target_pillar ∝ w_prior_pillar · (1 + r_pillar)
```

**James-Stein shrinkage** pulls low-signal pillars toward the profile prior (more shrink when few
cycles or weak |r|):
```
shrink s = clip( 1 − (cycles − 1)/K , s_min, 1 )      # K=8, s_min=0.1
if |r_pillar| < signal_floor (0.15):  w_target = (1−s)·w_target + s·w_prior
```

**Decayed learning rate** (weights stabilize as evidence accumulates):
```
η_t = η0 · exp(−κ · cycle)                            # η0=0.5, κ=0.15
w_new = w_old + η_t · (w_target − w_old)
```

Renormalize so `Σ w_new = 1`.

**Sparse mode (cycles < 4):** skip correlation entirely; `w_new = domain-profile priors`; flag
`low_confidence: true`. Never reweight on noise.

**Failure mode:** overfitting a short series. Mitigations stacked: shrink-to-prior, decayed LR,
sparse skip, and weights bounded by renormalization.

---

## 5. EMV ranking + tiering  (`emv_rank.py`)

Inject Thompson P(success) (by category) as the missing RICE Confidence:
```
rice_final = rice_kano × p_success
```

Expected Monetary Value:
```
EMV = p_success · delta_value − cost
```

Expected MDI contribution — map the item's `pillars` to the *new* learned weights:
```
mdi_contrib = mean( w_new[p] for p in item.pillars ) · (rice_final / max_rice_final)
```

**Rank key** (descending): primary `EMV`, tiebreak `rice_final`, then `mdi_contrib`.

**Tiers** by EMV quantiles over items with EMV>0:
```
now  : EMV ≥ 66th percentile
next : 33rd ≤ EMV < 66th
later: EMV < 33rd percentile (or EMV ≤ 0 → "later", flagged negative-EMV)
```

---

## 6. Backtest accuracy  (`backtest_ledger.py --read`)

Pairing predictions ↔ realizations by `feature_id`:
```
Brier    = mean( (predicted_p_success − realized_success)^2 )
EMV_MAPE = mean( |predicted_emv − realized_delta_value| / |realized_delta_value| )   # skip denom=0
accuracy_trend = [ {cycle, brier_for_that_cycle} ... ]
```
Lower Brier / MAPE = better. `accuracy_trend` is what Phase-2 forecasting uses to *earn* confidence.

---

## 7. Forecasting — Phase 2, deferred  (`forecast.py`)

Per-pillar metric series → 90-day projection via statsmodels Holt-Winters (trend+seasonal) or ARIMA
(short series). Forecast **confidence starts LOW** and is scaled by ledger accuracy:
```
confidence = f(accuracy_trend, cycles)   # capped LOW until enough validated cycles
```
Not implemented this phase; `forecast.py` is a guarded stub (`--enable` required).

---

## 8. Constants (defaults, all tunable)

| symbol | default | used in |
|---|---|---|
| Kano k table | 0.8/1.0/1.3/0.4/0.1 | scoring |
| λ (Thompson decay) | 0.3 | thompson |
| θ (Goodhart threshold) | 0.05 | mdi |
| signal_floor | 0.15 | reweight |
| K (shrink window) | 8 | reweight |
| s_min | 0.1 | reweight |
| η0 (base LR) | 0.5 | reweight |
| κ (LR decay) | 0.15 | reweight |
| sparse cutoff | cycles < 4 | ingest/reweight |
| now/next tier quantiles | 66 / 33 | emv_rank |
