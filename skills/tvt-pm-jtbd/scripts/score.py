#!/usr/bin/env python3
"""score.py — deterministic Jobs-to-be-Done opportunity scoring (Ulwick ODI).

Captures a job-map (job steps → desired outcomes, each rated on importance + current
satisfaction), then scores where to improve using Outcome-Driven Innovation:

    opportunity = importance + max(0, importance - satisfaction)

On a 1-10 scale this is the standard ODI formula. Outcomes are classified:
    opportunity >= 15  -> under-served   (HIGH improvement value — the gold)
    10 <= opp < 15     -> appropriately-served
    opportunity < 10   -> over-served    (don't invest more; maybe trim)

Also supports tracking over time: --compare a prior run to see which outcomes moved.

Usage:
  python scripts/score.py --jobmap jobmap.yaml [--scale 10] > scored.json
  python scripts/score.py --jobmap now.yaml --compare prior.json > delta.json

Input: job-map YAML (see references/schema.md). Output: one JSON object — ranked
opportunities + handoff payload for tvt-pm-grow. Deterministic.
"""
import argparse
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    import json as _j, sys as _s
    _j.dump({"error": "pyyaml not installed; pip install -r scripts/requirements.txt"}, _s.stderr)
    _s.exit(2)

from common import emit, fail


def classify(opp: float, scale: float) -> str:
    # thresholds scale with the rating scale (defaults tuned for 1-10)
    hi = 1.5 * scale
    mid = 1.0 * scale
    if opp >= hi:
        return "under-served"
    if opp >= mid:
        return "appropriately-served"
    return "over-served"


def opportunity_score(importance: float, satisfaction: float) -> float:
    """Ulwick ODI formula: opportunity = importance + max(0, importance - satisfaction)."""
    return importance + max(0.0, importance - satisfaction)


def score_outcomes(outcomes: List[Dict[str, Any]], scale: float) -> List[Dict[str, Any]]:
    """Score + classify + rank every outcome in a job-map. Raises ValueError (not fail(),
    which exits the process) so this stays unit-testable without a subprocess."""
    scored = []
    for o in outcomes:
        imp = float(o.get("importance", 0))
        sat = float(o.get("satisfaction", 0))
        for nm, v in (("importance", imp), ("satisfaction", sat)):
            if not (0 <= v <= scale):
                raise ValueError(
                    "outcome '{}' {}={} out of [0,{}]".format(o.get("id"), nm, v, scale)
                )
        opp = opportunity_score(imp, sat)
        scored.append({
            "id": o.get("id"),
            "outcome": o.get("statement"),
            "job_step": o.get("job_step"),
            "importance": imp,
            "satisfaction": sat,
            "opportunity": round(opp, 2),
            "class": classify(opp, scale),
            "friction": o.get("friction", ""),
        })
    scored.sort(key=lambda x: x["opportunity"], reverse=True)
    for i, s in enumerate(scored):
        s["rank"] = i + 1
    return scored


def build_grow_handoff(scored: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    under = [s for s in scored if s["class"] == "under-served"]
    return [{
        "jtbd": s["outcome"],
        "job_step": s["job_step"],
        "opportunity": s["opportunity"],
        "source_friction": s["friction"],
    } for s in under]


def compute_movements(scored: List[Dict[str, Any]], prior: Dict[str, Any]) -> Dict[str, Any]:
    prior_by_id = {s["id"]: s for s in prior.get("ranked_outcomes", [])}
    moves = []
    for s in scored:
        p = prior_by_id.get(s["id"])
        if p:
            moves.append({
                "id": s["id"], "outcome": s["outcome"],
                "opportunity_then": p["opportunity"], "opportunity_now": s["opportunity"],
                "delta": round(s["opportunity"] - p["opportunity"], 2),
                "satisfaction_delta": round(s["satisfaction"] - p["satisfaction"], 2),
            })
    moves.sort(key=lambda m: m["delta"])
    return {
        "movements": moves,
        "most_improved": moves[0] if moves else None,
        "most_regressed": moves[-1] if moves else None,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobmap", required=True, help="job-map YAML")
    ap.add_argument("--scale", type=float, default=10.0, help="rating scale max (default 10)")
    ap.add_argument("--compare", default="", help="prior scored.json to diff against (tracking)")
    args = ap.parse_args()

    with open(args.jobmap) as fh:
        jm = yaml.safe_load(fh)
    if not isinstance(jm, dict):
        fail("job-map must be a YAML mapping")

    job = jm.get("job", {})
    steps = jm.get("job_steps", [])
    outcomes: List[Dict[str, Any]] = jm.get("outcomes", [])
    if not outcomes:
        fail("job-map has no `outcomes` to score")

    scale = float(args.scale)
    try:
        scored = score_outcomes(outcomes, scale)
    except ValueError as e:
        fail(str(e))
        return

    under = [s for s in scored if s["class"] == "under-served"]
    # handoff payload: under-served outcomes → tvt-pm-grow candidate seeds
    handoff = build_grow_handoff(scored)

    result: Dict[str, Any] = {
        "job": job.get("statement"),
        "executor": job.get("executor"),
        "scale": scale,
        "n_outcomes": len(scored),
        "summary": {
            "under_served": len(under),
            "appropriately_served": sum(1 for s in scored if s["class"] == "appropriately-served"),
            "over_served": sum(1 for s in scored if s["class"] == "over-served"),
        },
        "ranked_outcomes": scored,
        "top_opportunities": under[:10],
        "grow_handoff": handoff,
        "job_steps": steps,
    }

    if args.compare:
        import json
        with open(args.compare) as fh:
            prior = json.load(fh)
        tracking = compute_movements(scored, prior)
        tracking["compared_to"] = args.compare
        result["tracking"] = tracking

    emit(result)


if __name__ == "__main__":
    main()
