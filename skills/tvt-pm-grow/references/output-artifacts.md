# Output Artifacts

Written to the run working dir (default `./tvt-pm-grow-out/`). Scripts emit JSON to stdout; the LLM
writes the two prose files. The ledger persists across runs (not in the working dir — its path is
supplied so it survives cycles).

| Artifact | Author | Source | Purpose |
|---|---|---|---|
| `roadmap.md` | LLM | `ranked.json` + `mdi.json` + `reweight.json` | inward: what to build, now/next/later |
| `positioning.md` | LLM | same, synced by feature ID | outward: what to say, the public narrative |
| `mdi_scorecard.json` | script | `mdi_compose.py` | machine record of MDI + pillar subscores + weights + alerts |
| `mdi_scorecard.md` | LLM | `mdi.json` | human render of the scorecard |
| `self_eval.md` | LLM | `reweight.json` + `ledger.json` | the loop grading itself: what it learned + how calibrated it is |
| `backtest_ledger.jsonl` | script | `backtest_ledger.py --append*` | persistent audit trail (NOT in working dir) |

## `roadmap.md` shape
1. **Header** — product, cycle, current MDI + cycle delta, learned pillar weights (with a one-line
   "what the market is rewarding now").
2. **Now** — top-tier features: title, JTBD, EMV, P(success), RICE×Kano, expected MDI contribution,
   pillars moved.
3. **Next / Later** — condensed.
4. **Risk flags** — every Goodhart alert + sparse-data caveat, verbatim.

## `positioning.md` shape
1. **Headline promise** — the wedge, driven by the highest-MDI-contribution features.
2. **Audience messages** — per target segment, the beat + the proof point + the pillar it moves.
3. **Competitive wedge** — from the competitive pillar (share of voice, win rate, category rank).
4. **Sync block** — list of now-tier feature IDs confirmed present in both roadmap and positioning.

## `self_eval.md` shape
1. **What changed** — old vs new pillar weights, per-pillar correlation, what got shrunk and why.
2. **Calibration** — ledger Brier + EMV MAPE + accuracy trend; are predictions getting better?
3. **Mode** — full vs sparse; low-confidence flags.
4. **Next-cycle instrumentation** — which metrics to watch (highest predictive correlation).

## Sync rule (acceptance gate)
Every **now**-tier feature ID appears in BOTH `roadmap.md` and `positioning.md`. The build-the-thing
and tell-the-story halves are never allowed to drift.
