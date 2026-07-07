#!/usr/bin/env python3
"""score.py — confidence-scored prioritization engine (spec 006 §5).

Deterministic. The LLM extracts MEDDPICC evidence and opportunity attributes from intel/notes;
this script does all the arithmetic and ranking. Nothing here is a language model.

Formula (spec §5):
    expected_value = confidence x strategic_fit x deal_value x winnability_factors

Confidence is the MEDDPICC score (8 dimensions, 0-3 each -> /24, normalized to 0-1) — "the score
is the qualification, not stage/age/rep-feel." The same value is used for ranking regardless of
calibration state; only its *display* form changes (spec §5 anchoring guard, added 2026-07-02):
while `uncalibrated` (fewer than CALIBRATION_FLOOR realized outcomes backtested), output an ordinal
band (High/Medium/Low), never a raw percentage — a caveat label next to a precise number does not
defeat anchoring (Kahneman). The raw value is always retained for ranking math.

Capacity allocation (spec §5, protected floor per motion, added 2026-07-02): HUNT and EXPAND have
incommensurable risk/economics profiles, so a single blind-merged ranking systematically starves
whichever motion scores structurally lower. `rank_shortlist` fills each motion's declared floor
first (ranked within that motion), then allocates remaining capacity from one merged pool across
both motions. Parked items carry a `promotion_gap` — the expected-value distance to the current
cutoff, clamped at 0 — plus a `parked_reason` ("below_cutoff" vs "capacity_consumed_by_motion_floor",
for the case where a parked item already scores above the nominal cutoff but lost the slot to a
lower-scoring floor-protected item from the other motion) — the single deterministic promotion
signal (spec §10 verification).

Usage:
  # score one opportunity's confidence from its MEDDPICC dimensions
  python score.py --meddpicc 2,3,1,2,3,2,1,2 --calibration-n 0

  # rank a batch under a capacity ceiling with a protected floor per motion
  python score.py --rank --opportunities-file opps.json --capacity 8 --floor hunt=3,expand=2

Opportunity JSON shape (see opportunities.example.json):
  {"id": "...", "motion": "hunt"|"expand", "meddpicc": [0-3 x8], "calibration_n": int,
   "strategic_fit": 0-1, "deal_value": float, "winnability_factors": 0-1}

Output: one JSON object to stdout.
"""
import argparse
import json
from typing import Any, Dict, List, Optional, Tuple

from common import emit, fail

MEDDPICC_DIMENSIONS = (
    "metrics", "economic_buyer", "decision_criteria", "decision_process",
    "paper_process", "identify_pain", "champion", "competition",
)
MEDDPICC_MAX = 3 * len(MEDDPICC_DIMENSIONS)  # 24

# Floor for ML-grade calibration (spec §5 small-n reality): ~100-200 closed outcomes.
# Below this, MEDDPICC /24 + heuristic prior remain the primary confidence input indefinitely.
CALIBRATION_FLOOR = 100

BAND_HIGH = 0.67
BAND_MEDIUM = 0.34


def meddpicc_score(dims: List[int]) -> int:
    if len(dims) != len(MEDDPICC_DIMENSIONS):
        raise ValueError(
            "expected {} MEDDPICC dimensions, got {}".format(len(MEDDPICC_DIMENSIONS), len(dims))
        )
    for d in dims:
        if d < 0 or d > 3:
            raise ValueError("each MEDDPICC dimension must score 0-3, got {}".format(d))
    return sum(dims)


def confidence_band(value: float) -> str:
    if value >= BAND_HIGH:
        return "High"
    if value >= BAND_MEDIUM:
        return "Medium"
    return "Low"


def compute_confidence(dims: List[int], calibration_n: int) -> Dict[str, Any]:
    raw = meddpicc_score(dims)
    value = raw / float(MEDDPICC_MAX)
    calibrated = calibration_n >= CALIBRATION_FLOOR
    out = {
        "meddpicc_raw": raw,
        "meddpicc_max": MEDDPICC_MAX,
        "confidence_value": value,
        "calibration_state": "calibrated(n={})".format(calibration_n) if calibrated else "uncalibrated",
    }
    if calibrated:
        out["display_percent"] = round(value * 100, 1)
    else:
        out["display_band"] = confidence_band(value)
    return out


def expected_value(confidence_value: float, strategic_fit: float, deal_value: float,
                    winnability_factors: float) -> float:
    return confidence_value * strategic_fit * deal_value * winnability_factors


def _score_opportunity(opp: Dict[str, Any]) -> Dict[str, Any]:
    conf = compute_confidence(opp["meddpicc"], opp.get("calibration_n", 0))
    ev = expected_value(
        conf["confidence_value"], opp["strategic_fit"], opp["deal_value"], opp["winnability_factors"]
    )
    scored = dict(opp)
    scored["confidence"] = conf
    scored["expected_value"] = ev
    return scored


def _redact_uncalibrated(conf: Dict[str, Any]) -> Dict[str, Any]:
    """--display mode (F10): while uncalibrated, the raw confidence value and its MEDDPICC
    components are structurally removed, not just formatted around — a caveat label next to a
    precise number does not defeat anchoring (Kahneman), so the number itself must not survive
    into anything shown to a human. Once calibrated, the real value is legitimate to show."""
    if conf.get("calibration_state") != "uncalibrated":
        return conf
    redacted = dict(conf)
    for key in ("confidence_value", "meddpicc_raw", "meddpicc_max"):
        redacted.pop(key, None)
    return redacted


def apply_display_mode(result: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively redact uncalibrated confidence values from a single-score or --rank result."""
    if "confidence_value" in result or "calibration_state" in result:
        return _redact_uncalibrated(result)
    out = dict(result)
    for key in ("shortlist", "parked"):
        if key in out:
            out[key] = [
                {**o, "confidence": _redact_uncalibrated(o["confidence"])} for o in out[key]
            ]
    return out


def _parse_floor(spec: str) -> Dict[str, int]:
    floor = {}
    if not spec:
        return floor
    for part in spec.split(","):
        motion, _, count = part.partition("=")
        floor[motion.strip()] = int(count)
    return floor


def rank_shortlist(opportunities: List[Dict[str, Any]], capacity: int,
                    floor: Dict[str, int]) -> Dict[str, Any]:
    scored = [_score_opportunity(o) for o in opportunities]

    by_motion: Dict[str, List[Dict[str, Any]]] = {}
    for o in scored:
        by_motion.setdefault(o["motion"], []).append(o)
    for motion in by_motion:
        by_motion[motion].sort(key=lambda o: o["expected_value"], reverse=True)

    filled_ids = set()
    shortlist: List[Dict[str, Any]] = []
    warnings: List[str] = []

    for motion, floor_count in floor.items():
        pool = by_motion.get(motion, [])
        take = pool[:floor_count]
        if len(take) < floor_count:
            warnings.append(
                "floor for motion '{}' requested {} but only {} available".format(
                    motion, floor_count, len(take)
                )
            )
        for o in take:
            shortlist.append(o)
            filled_ids.add(o["id"])

    remaining_capacity = capacity - len(shortlist)
    if remaining_capacity < 0:
        warnings.append("capacity {} is smaller than the sum of motion floors {}".format(
            capacity, sum(floor.values())
        ))
        remaining_capacity = 0

    remaining_pool = [o for o in scored if o["id"] not in filled_ids]
    remaining_pool.sort(key=lambda o: o["expected_value"], reverse=True)
    for o in remaining_pool[:remaining_capacity]:
        shortlist.append(o)
        filled_ids.add(o["id"])

    shortlist.sort(key=lambda o: o["expected_value"], reverse=True)
    cutoff = shortlist[-1]["expected_value"] if shortlist else 0.0

    # A floor-protected item can enter the shortlist with a lower expected_value than a
    # parked item from the other motion — that parked item lost to capacity, not score.
    # promotion_gap is clamped at 0 in that case; parked_reason names which happened.
    parked = [o for o in scored if o["id"] not in filled_ids]
    parked.sort(key=lambda o: o["expected_value"], reverse=True)
    for o in parked:
        raw_gap = cutoff - o["expected_value"]
        o["promotion_gap"] = round(max(0.0, raw_gap), 6)
        o["parked_reason"] = "below_cutoff" if raw_gap > 0 else "capacity_consumed_by_motion_floor"

    result = {
        "capacity": capacity,
        "floor": floor,
        "cutoff_expected_value": cutoff,
        "shortlist": shortlist,
        "parked": parked,
    }
    if warnings:
        result["warnings"] = warnings
    return result


def _load_opportunities(path: str) -> List[Dict[str, Any]]:
    with open(path, "r") as fh:
        return json.load(fh)


def resolve_calibration_n(calibration_n: int, backtest_file: Optional[str]) -> int:
    """F5: derive calibration_n from the actual growing backtest artifact (close_out.py's
    output) instead of requiring the caller to track and pass the count by hand."""
    if backtest_file:
        return len(_load_opportunities(backtest_file))
    return calibration_n


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--meddpicc", help="8 comma-separated ints 0-3: M,E,D,D,P,I,C,C")
    p.add_argument("--calibration-n", type=int, default=0)
    p.add_argument("--calibration-from-backtest-file",
                   help="derive --calibration-n from len() of this eval_backtest.py labeled "
                   "array instead of tracking the count by hand")
    p.add_argument("--rank", action="store_true")
    p.add_argument("--opportunities-file")
    p.add_argument("--capacity", type=int)
    p.add_argument("--floor", default="", help="e.g. hunt=3,expand=2")
    p.add_argument("--display", action="store_true",
                   help="strip raw confidence values while uncalibrated (F10) — the only "
                   "output mode safe to show a human directly")
    args = p.parse_args()

    try:
        if args.rank:
            if not args.opportunities_file or args.capacity is None:
                fail("--rank requires --opportunities-file and --capacity")
            opps = _load_opportunities(args.opportunities_file)
            floor = _parse_floor(args.floor)
            result = rank_shortlist(opps, args.capacity, floor)
            emit(apply_display_mode(result) if args.display else result)
        elif args.meddpicc:
            dims = [int(x) for x in args.meddpicc.split(",")]
            calibration_n = resolve_calibration_n(args.calibration_n, args.calibration_from_backtest_file)
            result = compute_confidence(dims, calibration_n)
            emit(apply_display_mode(result) if args.display else result)
        else:
            fail("specify --meddpicc for a single score, or --rank for a batch")
    except (ValueError, KeyError, FileNotFoundError, json.JSONDecodeError) as e:
        fail(str(e))


if __name__ == "__main__":
    main()
