#!/usr/bin/env python3
"""forecast.py — Phase 2 (DEFERRED): per-pillar 90-day projection with EARNED confidence.

Not implemented in the core MVP by design. Guarded so an
accidental call fails loudly rather than emitting fake forecasts.

Planned design (when enabled):
  - per-pillar metric series → statsmodels Holt-Winters (trend+seasonal) or ARIMA (short series),
    model selected by series length (ARIMA when < ~12 points, else Holt-Winters).
  - 90-day projection with confidence intervals.
  - forecast confidence STARTS LOW and is scaled by ledger accuracy (Brier/MAPE trend from
    backtest_ledger.py --read) — confidence is earned, never assumed.

Usage (once implemented):
    python scripts/forecast.py --state state.json --ledger LEDGER.jsonl --enable > forecast.json
"""
import argparse

from common import emit, fail


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state")
    ap.add_argument("--ledger")
    ap.add_argument("--enable", action="store_true")
    ap.add_argument("--horizon-days", type=int, default=90)
    args = ap.parse_args()

    if not args.enable:
        fail("forecast.py is a Phase-2 deferred stub; pass --enable only once implemented "
             "Core MVP does not forecast.", code=3)

    # Placeholder for the implemented forecaster.
    emit({"status": "not_implemented",
          "note": "Phase 2 — Holt-Winters/ARIMA with ledger-earned confidence. See spec 002."})


if __name__ == "__main__":
    main()
