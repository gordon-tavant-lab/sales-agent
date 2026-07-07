#!/usr/bin/env python3
"""close_out.py — the calibration feedback loop, closed (spec 006 §5, F5).

Before this script, the loop spec §5/§7 promise was fiction: score.py scores opportunities,
eval_backtest.py can compute Brier/calibration curves/drift *if fed labeled outcomes*, but
nothing produced those labeled outcomes from a real won/lost result — the backtest input file
had to be hand-assembled, so it never was, so the scorer never actually calibrated no matter how
many deals closed.

close_out.py is that missing link: record a real close (won or lost), and it
  1. upserts the labeled record into the growing backtest artifact (eval_backtest.py's own
     input shape — {"id","confidence_value","was_shortlisted","outcome"}), by id, so closing
     out the same opportunity twice updates rather than double-counts it;
  2. immediately re-runs eval_backtest against the regenerated artifact, so every close-out
     shows the current Brier score / calibration curve / drift check, not just records data
     for someone to remember to look at later;
  3. emits the tvt-gov-attest call the caller should make (this script never calls tvt-gov-attest
     itself — same boundary gate.py already keeps, so the ledger write is always an explicit,
     visible step, not a side effect buried in a scoring script).

Usage:
  python close_out.py --id acct-radian --outcome won --confidence-value 0.667 \
    --was-shortlisted --backtest-file backtest.json [--prior-brier 0.21]
"""
import argparse
import json
import os
from typing import Any, Dict, List, Optional

from common import emit, fail
from eval_backtest import run_eval

OUTCOMES = ("won", "lost")


def _load_backtest(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    with open(path, "r") as fh:
        return json.load(fh)


def _write_backtest(path: str, records: List[Dict[str, Any]]) -> None:
    with open(path, "w") as fh:
        json.dump(records, fh, indent=2)
        fh.write("\n")


def upsert_outcome(
    records: List[Dict[str, Any]],
    opp_id: str,
    outcome: str,
    confidence_value: float,
    was_shortlisted: bool,
) -> List[Dict[str, Any]]:
    if outcome not in OUTCOMES:
        raise ValueError("outcome must be one of {}, got {!r}".format(OUTCOMES, outcome))
    if not (0.0 <= confidence_value <= 1.0):
        raise ValueError("confidence_value must be 0-1, got {}".format(confidence_value))
    record = {
        "id": opp_id,
        "confidence_value": confidence_value,
        "was_shortlisted": was_shortlisted,
        "outcome": outcome,
    }
    out = [r for r in records if r.get("id") != opp_id]
    out.append(record)
    return out


def close_out(
    opp_id: str,
    outcome: str,
    confidence_value: float,
    was_shortlisted: bool,
    backtest_file: str,
    prior_brier: Optional[float] = None,
) -> Dict[str, Any]:
    records = _load_backtest(backtest_file)
    was_update = any(r.get("id") == opp_id for r in records)
    records = upsert_outcome(records, opp_id, outcome, confidence_value, was_shortlisted)
    _write_backtest(backtest_file, records)

    reason_code = "CLOSE_OUT_WON" if outcome == "won" else "CLOSE_OUT_LOST"
    return {
        "recorded": {
            "id": opp_id,
            "outcome": outcome,
            "was_update": was_update,
        },
        "backtest_file": backtest_file,
        "backtest_n": len(records),
        "eval": run_eval(records, prior_brier),
        "attest_call": {
            "decision_id": opp_id,
            "verdict": outcome,
            "method": "deterministic",
            "reason_code": reason_code,
            "note": "pass to `tvt-gov-attest --append` yourself — this script never calls it "
                    "directly (same boundary gate.py keeps for its own attest calls).",
        },
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--id", required=True, help="opportunity id, matching what score.py used")
    p.add_argument("--outcome", choices=OUTCOMES, required=True)
    p.add_argument("--confidence-value", type=float, required=True,
                   help="the confidence_value score.py emitted for this opportunity (0-1)")
    p.add_argument("--was-shortlisted", action="store_true")
    p.add_argument("--backtest-file", required=True,
                   help="the growing labeled-outcomes array eval_backtest.py reads; "
                        "regenerated (not appended-as-JSONL) on every close-out")
    p.add_argument("--prior-brier", type=float, default=None)
    args = p.parse_args()

    try:
        emit(close_out(
            args.id, args.outcome, args.confidence_value, args.was_shortlisted,
            args.backtest_file, args.prior_brier,
        ))
    except (ValueError, KeyError, FileNotFoundError, json.JSONDecodeError) as e:
        fail(str(e))


if __name__ == "__main__":
    main()
