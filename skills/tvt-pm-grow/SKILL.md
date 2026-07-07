---
name: tvt-pm-grow
description: >
  Grow a product/initiative from SEED MATERIAL (init specs, docs, files) to market dominance via a
  self-refining feedback loop. Ingests the seed + a reception-stats YAML, scores the backlog
  (RICE×Kano + Thompson-calibrated P(success)), composes a Market Dominance Index across
  adoption/sentiment/revenue/competitive pillars, Bayesian-reweights those pillars against REALIZED
  outcomes (it learns which signals predict winning), ranks by Expected Monetary Value, and emits a
  synced product roadmap + public positioning. Use this whenever the user wants to grow, launch, or
  win a market with a product — "grow this product", "what to build and what to say", "market
  dominance", "corner the market", "reception stats", "MDI", "self-learning roadmap", "PM feedback
  loop", or hands you seed specs and asks how to take it to market. The numbers are deterministic
  Python (reproducible, defensible); the LLM only reads seeds and writes the narrative.
argument-hint: "<seed-dir-or-stats.yaml> [--domain fintech|saas|marketplace|media|enterprise-b2b] [--research] [--out DIR] [--ledger PATH]"
user-invocable: true
layer: utility
eval:
  mode: gate
  depth: standard
---

# tvt-pm-grow — Seed-to-Market-Dominance Engine

Take a product seed and grow it toward cornering its market, learning from how the audience
actually responds. This skill is the **instrument**; the `product-manager` dev-team agent is its
natural **owner/caller** (see "Agent wiring" below). Deferred until the core MVP's forecasting need is proven out.

## The one principle: a hard hybrid seam

> **Python owns every number. The LLM owns every sentence.** The LLM reads seed files and proposes
> feature metadata + writes the roadmap/positioning prose. The scripts compute RICE, Thompson
> P(success), MDI, pillar weights, and EMV. Never recompute a script's number in prose; never let
> the model do the math. This is what makes recommendations defensible and replayable.

## What it produces each cycle

- `roadmap.md` — inward: what to build, tiered now/next/later, EMV-ranked, with the learned pillar
  weights and Goodhart risk flags.
- `positioning.md` — outward: the public narrative/launch story, **synced** to the roadmap (every
  now-tier feature ID appears in both).
- `mdi_scorecard.{json,md}` — the Market Dominance Index, pillar subscores, learned weights, alerts.
- `self_eval.md` — the loop grading itself: what it learned, how calibrated its past predictions were.
- appends to `backtest_ledger.jsonl` — the append-only audit trail / memory.

## How to run it (the full loop)

Setup once: `pip install -r scripts/requirements.txt` (pyyaml, numpy; statsmodels only for the
deferred forecaster). Pick a working dir (`--out`, default `./tvt-pm-grow-out/`) and a persistent
ledger path that survives across cycles.

### Step 1 — Grow the seed into candidates (LLM)
Read `references/grow-engine.md` Scaffold 1. Read the files in the stats file's `seed_refs[]`, then
emit candidate `backlog[]` rows (titles, JTBD, reach/impact/effort/kano/Δvalue/cost, pillar tags) in
the `reception_stats.yaml` shape. JTBD-cluster demand signals first. If a `reception_stats.yaml`
already exists, merge candidates into its `backlog:`. **Pause for the user / product-manager agent
to review the candidate backlog before scoring** — this is the human checkpoint.

### Step 2 — Run the deterministic chain (Python; do NOT improvise the math)
```bash
SK=.claude/skills/tvt-pm-grow          # adjust to skill path
STATS=path/to/reception_stats.yaml
LEDGER=path/to/backtest_ledger.jsonl # persistent across cycles
OUT=./tvt-pm-grow-out; mkdir -p "$OUT"

python3 $SK/scripts/ingest_seed.py "$STATS" --ledger "$LEDGER" > $OUT/state.json
python3 $SK/scripts/score_rice_kano.py --state $OUT/state.json > $OUT/scored.json
python3 $SK/scripts/thompson_tracker.py --state $OUT/state.json > $OUT/thompson.json
python3 $SK/scripts/mdi_compose.py --state $OUT/state.json > $OUT/mdi.json
python3 $SK/scripts/reweight_pillars.py --state $OUT/state.json --mdi $OUT/mdi.json > $OUT/reweight.json
python3 $SK/scripts/emv_rank.py --scored $OUT/scored.json --thompson $OUT/thompson.json --reweight $OUT/reweight.json > $OUT/ranked.json

# record predictions for this cycle's now-tier, then fold in any realized outcomes
python3 $SK/scripts/backtest_ledger.py --append --state $OUT/state.json --ranked $OUT/ranked.json --ledger "$LEDGER" --tier now --ts "<ISO8601>"
python3 $SK/scripts/backtest_ledger.py --append-realizations --state $OUT/state.json --ledger "$LEDGER" --ts "<ISO8601>"
python3 $SK/scripts/backtest_ledger.py --read --ledger "$LEDGER" > $OUT/ledger.json
```
Each script prints one JSON object. A nonzero exit means a hard error (message on stderr) — read it,
fix the stats file, rerun. Don't paper over a validation failure.

### Step 3 — Write the synced artifacts (LLM)
Read `references/grow-engine.md` Scaffold 3 and `references/output-artifacts.md`. From
`ranked.json` + `mdi.json` + `reweight.json` + `ledger.json`, write `roadmap.md`, `positioning.md`,
`mdi_scorecard.md`, `self_eval.md` into `$OUT`. **Enforce the sync gate**: every now-tier feature ID
must appear in both `roadmap.md` and `positioning.md`; state the confirmed ID list in the artifact.

### Optional `--research`
Before Step 2, run web research (the `exa` / `tavily` / `context7` MCP tools, or a research skill if
installed) to pull public sentiment + competitor share-of-voice and write them into the current
cycle's `sentiment`/`competitive` metric blocks. Keeps the loop fed
with external evidence, not just self-reported numbers.

## How the loop learns (read `references/math.md` for formulas)

- **Calibrated confidence** — Thompson Beta posteriors per feature category turn realized outcomes
  into P(success), with recency decay. Replaces RICE's guessed Confidence with earned probability.
- **Self-defining objective** — the MDI pillar weights are reweighted each cycle by how well each
  pillar's movement *predicted* the next cycle's outcome (Pearson r → reweight, James-Stein
  shrink-to-prior for weak signal, decayed learning rate). The skill learns what winning means here.
- **Audit + calibration** — the append-only ledger pairs predictions with realizations and reports
  Brier + EMV MAPE, so you can see the loop getting better (and Phase-2 forecasting earns its
  confidence from this trend).

## Guardrails (do not bypass)

- **Goodhart alert** — if revenue rises while sentiment/retention falls, `mdi_compose` flags it.
  Surface it in `roadmap.md`; don't ship a top-tier monetization feature while it's unacknowledged.
- **Sparse-data mode** — with <4 cycles the reweighter refuses to learn from noise: it uses
  domain-profile priors and flags `low_confidence`. Say so in the artifacts; never fake confidence.
- **No forecasting yet** — `forecast.py` is a deferred Phase-2 stub and will hard-exit unless
  `--enable` (and it isn't implemented). Don't promise forecasts the MVP can't back.

## Agent wiring — this skill is the ENTRY POINT to the `product-manager` agent

The relationship is **skill-as-front-door, agent-as-labor** (the same pattern as `g-dev-build` →
`team-lead`). This skill is the entry point; it **dispatches into the `product-manager` agent** to do
the judgment-heavy work, rather than the agent calling the skill.

Flow when invoked:
1. The skill spawns the `product-manager` agent for **Step 1 (grow seed → candidate backlog)** and
   the **Step 3 narrative** — the agent owns the PM judgment (JTBD clustering, candidate estimates,
   roadmap + positioning prose, the human review checkpoint).
2. The skill itself owns the **deterministic Step 2 chain** (the Python scoring/learning loop) — that
   math never goes to the agent; it runs reproducibly.
3. The agent hands the resulting roadmap to `architect` for technical design, as usual.

```
Agent(subagent_type: "product-manager", prompt: "
  Run the tvt-pm-grow growth loop for {product}.
  Step 1 — read the seed_refs and produce the candidate backlog (grow-engine Scaffold 1).
  Pause for human review of the candidate backlog.
  [skill runs the deterministic Step 2 chain]
  Step 3 — author roadmap.md + positioning.md from the ranked JSON, enforce the sync gate.
  Profile: domain={domain}, out={out dir}, ledger={ledger path}.
")
```

Why this direction: a skill encodes the **process** (the phases, the deterministic chain, the sync
gate) and is the stable, discoverable front door; the agent supplies **role behavior + its own
context window** for the open-ended PM work. Making the skill the entry means every run follows the
same reproducible process, with the agent doing the labor inside it — not re-improvising the workflow
each time. (The agent still lists `tvt-pm-grow` in its `skills:` so it can also invoke the loop when
already mid-task, but the canonical entry is the skill.)

## References (load as needed)

- `references/schema.md` — the `reception_stats.yaml` input contract (versioned). ⚠ irreversible.
- `references/ledger-format.md` — the append-only ledger record schema. ⚠ irreversible.
- `references/math.md` — every formula, with constants and failure modes.
- `references/domain-profiles.md` — pillar priors + metric targets per domain; how to tune a vertical.
- `references/grow-engine.md` — the three LLM scaffolds (seed→candidates, scored→narrative).
- `references/output-artifacts.md` — exact shape of each emitted artifact + the sync gate.
- `samples/` — a 5-cycle fintech example (with a seeded Goodhart case), a 2-cycle sparse example, and
  a seeded ledger. Run the chain on `samples/reception_stats.sample.yaml` to see it end-to-end.

## Output Gate (mandatory before finishing)

Before finishing, gate the artifact: `/tvt-core-eval gate --output <artifact> --criteria ${CLAUDE_PLUGIN_ROOT}/rubrics/client-facing-doc.md`. Do not hand it off until it passes.
