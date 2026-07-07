#!/usr/bin/env python3
"""eval_backtest.py — the method of eval for the confidence scorer (spec 006 §5, §10).

This is the code behind two promises spec 006 makes but never shipped an implementation for:
  1. Job 1's transition KPI: "shortlist precision (backtested vs outcomes)."
  2. §5's recalibration cadence: "quarterly scorer backtest against realized outcomes with a
     drift check (calibration curve / Brier trend vs prior quarter) — a worsening trend is a
     P1 on the scorer, not a shrug."

Without this, "confidence must be backtested or it's flagged unreliable" (§7 guardrail) has no
actual backtest mechanism — the anti-astrology rule was a stated rule with no enforcement code.
This module is that enforcement: given confidence scores paired with realized won/lost outcomes,
it computes Brier score (calibration accuracy), a calibration curve (predicted vs actual win rate
per confidence bucket), shortlist precision, and a drift check against a prior period's Brier score.

Labeled dataset shape:
  [{"id": str, "confidence_value": float 0-1, "was_shortlisted": bool, "outcome": "won"|"lost"}, ...]

Usage:
  python eval_backtest.py --labeled-file backtest.json --prior-brier 0.21
"""
import argparse
import json
from typing import Any, Dict, List, Optional

from common import emit, fail

# Below this many labeled outcomes, calibration is not statistically meaningful (spec §5
# small-n reality — ~100-200 closed-deal floor, documented in research-foundations.md).
MIN_N_FOR_CALIBRATION = 100

DEFAULT_BINS = 5


def brier_score(labeled: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not labeled:
        return {"value": None, "n": 0}
    total = 0.0
    for rec in labeled:
        outcome = 1.0 if rec["outcome"] == "won" else 0.0
        total += (rec["confidence_value"] - outcome) ** 2
    value = total / len(labeled)
    return {
        "value": value,
        "n": len(labeled),
        "statistically_meaningful": len(labeled) >= MIN_N_FOR_CALIBRATION,
        "min_n_floor": MIN_N_FOR_CALIBRATION,
    }


def calibration_curve(labeled: List[Dict[str, Any]], n_bins: int = DEFAULT_BINS) -> Dict[str, Any]:
    if not labeled:
        return {"bins": [], "n": 0}
    bins = [[] for _ in range(n_bins)]
    width = 1.0 / n_bins
    for rec in labeled:
        idx = min(int(rec["confidence_value"] / width), n_bins - 1)
        bins[idx].append(rec)

    out = []
    for i, records in enumerate(bins):
        lo, hi = round(i * width, 2), round((i + 1) * width, 2)
        if not records:
            out.append({"range": [lo, hi], "n": 0, "predicted_mean": None, "actual_win_rate": None})
            continue
        predicted_mean = sum(r["confidence_value"] for r in records) / len(records)
        actual = sum(1 for r in records if r["outcome"] == "won") / len(records)
        out.append({
            "range": [lo, hi],
            "n": len(records),
            "predicted_mean": round(predicted_mean, 4),
            "actual_win_rate": round(actual, 4),
            "gap": round(predicted_mean - actual, 4),
        })
    return {"bins": out, "n": len(labeled)}


def shortlist_precision(labeled: List[Dict[str, Any]]) -> Dict[str, Any]:
    shortlisted = [r for r in labeled if r.get("was_shortlisted")]
    if not shortlisted:
        return {"value": None, "n_shortlisted": 0}
    won = sum(1 for r in shortlisted if r["outcome"] == "won")
    return {
        "value": won / len(shortlisted),
        "n_shortlisted": len(shortlisted),
        "n_won": won,
    }


def drift_check(
    current_brier: float, prior_brier: Optional[float], n_labeled: int = 0
) -> Dict[str, Any]:
    if prior_brier is None:
        return {"status": "no_prior_period", "current_brier": current_brier}
    delta = current_brier - prior_brier
    # Brier score: lower is better. A rising Brier score is the scorer getting *less* calibrated.
    worsening = delta > 0
    # Below the calibration floor a quarter holds ~1-5 outcomes, so any delta is coin-flip
    # variance — a P1 that always fires trains its operator to ignore it. Informational until
    # n clears the floor.
    if worsening and n_labeled < MIN_N_FOR_CALIBRATION:
        status = (
            f"worsening_but_not_significant — n={n_labeled} is below the "
            f"{MIN_N_FOR_CALIBRATION}-outcome calibration floor; informational only, no alert"
        )
    elif worsening:
        status = "WORSENING — P1, do not silently accept"
    else:
        status = "stable_or_improving"
    return {
        "current_brier": current_brier,
        "prior_brier": prior_brier,
        "delta": round(delta, 6),
        "n_labeled": n_labeled,
        "status": status,
    }


def run_eval(labeled: List[Dict[str, Any]], prior_brier: Optional[float] = None) -> Dict[str, Any]:
    brier = brier_score(labeled)
    result = {
        "brier_score": brier,
        "calibration_curve": calibration_curve(labeled),
        "shortlist_precision": shortlist_precision(labeled),
    }
    if brier["value"] is not None:
        result["drift_check"] = drift_check(brier["value"], prior_brier, n_labeled=len(labeled))
    return result


def _load(path: str) -> List[Dict[str, Any]]:
    with open(path, "r") as fh:
        return json.load(fh)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--labeled-file", required=True)
    p.add_argument("--prior-brier", type=float, default=None)
    p.add_argument("--bins", type=int, default=DEFAULT_BINS)
    args = p.parse_args()
    try:
        labeled = _load(args.labeled_file)
        emit(run_eval(labeled, args.prior_brier))
    except (ValueError, KeyError, FileNotFoundError, json.JSONDecodeError) as e:
        fail(str(e))


if __name__ == "__main__":
    main()
