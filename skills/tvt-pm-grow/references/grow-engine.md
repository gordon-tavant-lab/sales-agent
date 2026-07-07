# The Grow Engine — LLM prompt scaffolds (seed → candidates → narrative)

This is where the LLM does its half of the hybrid. The deterministic scripts own every number;
the LLM owns reading the seed and writing language. Three scaffolds, invoked in order by SKILL.md.

> **Hard rule:** the LLM never computes RICE, MDI, EMV, or weights. It *proposes* feature
> metadata (reach/impact/effort/Δvalue/cost/kano) as estimates, and *narrates* the scored JSON.
> Numbers in the artifacts come from the scripts, not the model.

---

## Scaffold 1 — Seed → candidate backlog

**Input:** the files in `product.seed_refs[]` (init specs, vision docs, competitor teardown).
**Task:** read them and emit candidate `backlog[]` rows in the `reception_stats.yaml` shape.

For each candidate produce:
- `id` (stable, `F-NNN`), `title`, `category` (coarse grouping — Thompson posteriors key on this,
  so prefer ~5–12 reusable categories like `onboarding`, `pricing`, `integrations`, `trust`),
- `jtbd` ("When [situation], I want [motivation], so I can [outcome]"),
- `reach` (users/period affected — estimate from the seed's stated audience/segment sizes),
- `impact` ∈ {0.25,0.5,1,2,3} (RICE scale; reserve 3 for "massive"),
- `effort` (person-weeks; honest rough order),
- `kano` ∈ {must_be, one_dimensional, attractive, indifferent, reverse} — classify the *kind* of
  value, not its size,
- `delta_value` and `cost` (monetary; if the seed gives no economics, estimate conservatively and
  note the assumption),
- `pillars` — which of {adoption, sentiment, revenue, competitive} the feature is hypothesized to
  move.

**JTBD clustering:** group raw demand signals (support themes, churn reasons, competitor gaps in
the teardown) into named jobs before writing candidates, so the backlog reflects demand pull, not
a feature wishlist. Loud-minority requests should not dominate.

> **Preferred: run `tvt-pm-jtbd` first.** Rather than the LLM guessing the jobs here, capture a
> job-map and opportunity-score it with the `tvt-pm-jtbd` skill. Its `grow_handoff` output is a list of
> **under-served outcomes** (importance high, satisfaction low — scored by the Ulwick ODI algorithm,
> deterministically). Seed each candidate's `jtbd` field from a handoff outcome, so the backlog
> traces to *scored evidence of where value is*, not opinion. A candidate that doesn't map to an
> under-served outcome is a feature looking for a problem — drop or justify it. When no job-map
> exists, fall back to the inline clustering above and flag that the JTBD basis is unscored.

Write candidates into the product's `reception_stats.yaml` `backlog:` (or a side file the user
reviews). The `product-manager` agent reviews this list before scoring.

---

## Scaffold 2 — (handled by scripts)

The deterministic chain runs here: `ingest_seed → score_rice_kano → thompson_tracker →
mdi_compose → reweight_pillars → emv_rank → backtest_ledger`. No LLM. SKILL.md gives exact commands.

---

## Scaffold 3 — Scored JSON → synced roadmap + positioning

**Input:** `ranked.json` (emv_rank) + `mdi.json` (mdi_compose) + `reweight.json` + `ledger.json`.
**Task:** write the two prose artifacts, kept in **strict sync**.

`roadmap.md` (inward — what to build):
- Now / Next / Later from the `tiers` field. For each *now* item: title, one-line JTBD, EMV,
  P(success), RICE×Kano, expected MDI contribution, and the pillar(s) it moves.
- Lead with the current MDI, its cycle delta, and the learned pillar weights ("the market is
  rewarding X right now — here's the evidence").
- Surface every `goodhart_alert` as an explicit risk line; never bury it.

`positioning.md` (outward — what to say), **synced to the roadmap**:
- Every *now*-tier feature ID must appear in both files. Each positioning beat cites the pillar the
  feature moves and the audience it targets.
- Translate the highest-MDI-contribution features into public narrative: the headline promise,
  the proof points, the wedge against competitors (driven by the competitive pillar).
- If a Goodhart alert fired, the narrative must not over-claim on the diverging dimension.

**Sync check (state in the artifact):** list the now-tier feature IDs and confirm they appear in
both files. This is the acceptance gate.

---

## Optional `--research` mode

If invoked with `--research`, before ingestion run web searches for public sentiment and
competitor share-of-voice (dimensions D and F of `${CLAUDE_PLUGIN_ROOT}/references/research-query-library.md`
are the closest fit — competitive landscape and recent news/signals), and write the results into
the current cycle's `sentiment` / `competitive` metric blocks. This keeps the loop fed with
external evidence rather than only self-reported numbers. Without `--research`, the skill runs
purely on the supplied stats.
