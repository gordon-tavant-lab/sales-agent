# `backtest_ledger.jsonl` — Append-Only Audit Ledger (schema_version 1)

> **Irreversible decision.** This is the skill's memory and audit trail — the thing that makes
> the loop *replayable* and the predictions *calibratable*. It is **append-only**: never edit or
> delete a record. A mistake is corrected by appending a new record, not mutating an old one.
> Format is JSON Lines (one JSON object per line, UTF-8, newline-terminated).

## Why append-only

The Bayesian reweighter and the Thompson tracker both reason over history. If records could be
mutated, the learning chain would silently change under replay and the audit trail would lie.
Append-only guarantees: (a) any past cycle can be reconstructed, (b) predicted-vs-realized
accuracy is honestly measurable, (c) corrections are themselves auditable events.

## Record kinds

Two record kinds share one schema, distinguished by `kind`:

- `prediction` — written when a feature is ranked/committed in a cycle (what we *expect*).
- `realization` — written when that feature's outcome lands (what *happened*).

A `realization` references the same `feature_id`; the reader pairs them by `feature_id` (latest
prediction before the realization's cycle wins, so re-predictions are handled).

## Record schema

```json
{
  "ts": "ISO8601 string",            // wall-clock write time (informational; not used in math)
  "schema_version": 1,
  "kind": "prediction" | "realization",
  "cycle": 5,                         // cycle this record belongs to
  "feature_id": "F-007",
  "category": "onboarding",          // Thompson posterior key

  // prediction fields (null on realization records)
  "predicted_p_success": 0.61,       // Thompson P(success) at commit
  "predicted_emv": 50000.0,          // EMV at commit
  "predicted_mdi_contrib": 0.012,    // expected MDI contribution at commit
  "weights_snapshot": { "adoption":0.3,"sentiment":0.2,"revenue":0.35,"competitive":0.15 },

  // realization fields (null on prediction records)
  "realized_success": true,          // binary label
  "realized_delta_value": 58000.0,
  "realized_mdi_delta": 0.014,

  "note": "free text, optional"
}
```

Fields not applicable to a record's `kind` are written as `null` (present, explicit) so every line
parses against the same schema.

## Reader rollups (computed by `backtest_ledger.py --read`)

Pairing predictions ↔ realizations by `feature_id`, the reader computes:

- **Brier score** on calibration of `predicted_p_success` vs `realized_success`:
  `Brier = mean( (p_success − success)^2 )` over paired records. Lower = better calibrated.
- **EMV MAPE** — mean absolute percentage error of `predicted_emv` vs `realized_delta_value`
  (guards against inflated value estimates). Uses `realized_delta_value` as denominator; skips
  pairs where it is 0.
- **accuracy_trend** — Brier per cycle (list), so improvement over time is visible and **forecast
  confidence can be earned** (Phase 2 reads this).

Read-mode output:
```json
{"records": N, "predictions": P, "realizations": R, "paired": K,
 "brier": 0.0..1.0, "emv_mape": float, "accuracy_trend": [{"cycle":c,"brier":b}, ...]}
```

## Append rules (enforced by `backtest_ledger.py --append`)

1. Open the file in append mode (`"a"`); create if missing. Never truncate.
2. One compact JSON object per line, `\n`-terminated.
3. Stamp `ts` from the caller (passed in) — scripts must not call `Date.now()`-style nondeterminism
   in test/replay contexts; a fixed timestamp may be supplied for reproducible runs.
4. A prediction batch for a cycle appends one `prediction` record per ranked top-tier feature.
5. Realizations are appended from `outcomes[]` in the stats file as they arrive.
6. Idempotency is the caller's responsibility (re-appending duplicates a record) — the reader
   tolerates duplicates by treating the latest prediction per `(feature_id, cycle)` as canonical.
