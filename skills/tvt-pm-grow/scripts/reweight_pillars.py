#!/usr/bin/env python3
"""reweight_pillars.py — Bayesian self-definition of the MDI objective.

Learns which pillars actually predict winning and reweights toward them, with James-Stein
shrink-to-prior for low-signal pillars and a decayed learning rate so weights stabilize as
evidence accumulates. In sparse mode (cycles < 4) it skips correlation entirely and uses the
domain-profile priors, flagging low_confidence.

Usage:
    python scripts/reweight_pillars.py --state state.json --mdi mdi.json \
        [--lead mdi|revenue] [--eta0 0.5] [--kappa 0.15] > reweight.json
Output: {old_weights, new_weights, per_pillar_correlation, shrinkage_applied, learning_rate, mode}
"""
import argparse
import math
from typing import Dict, List, Optional

from common import emit, clip, load_json
from profiles import PILLARS

SIGNAL_FLOOR = 0.15
K_SHRINK = 8.0
S_MIN = 0.1


def _pearson(xs: List[float], ys: List[float]) -> Optional[float]:
    n = len(xs)
    if n < 2:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return 0.0
    return num / (dx * dy)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--mdi", required=True)
    ap.add_argument("--lead", choices=["mdi", "revenue"], default="mdi")
    ap.add_argument("--eta0", type=float, default=0.5)
    ap.add_argument("--kappa", type=float, default=0.15)
    args = ap.parse_args()

    state = load_json(args.state)
    mdi = load_json(args.mdi)
    old = dict(state["pillar_weights"])
    prior = dict(state["domain_profile"]["weights"])
    cycle = int(state.get("product", {}).get("cycle", 1))
    mode = state.get("mode", "full")

    per_cycle = mdi.get("per_cycle", [])

    # Sparse mode → priors verbatim, no correlation learning.
    if mode == "sparse" or len(per_cycle) < 4:
        emit({
            "old_weights": old, "new_weights": prior,
            "per_pillar_correlation": {p: None for p in PILLARS},
            "shrinkage_applied": {p: True for p in PILLARS},
            "learning_rate": 0.0, "mode": "sparse", "low_confidence": True,
            "note": "sparse data (<4 cycles): using domain-profile priors, no reweighting",
        })
        return

    # Build per-cycle subscore series + lead outcome series (next-cycle MDI or revenue).
    subs = {p: [] for p in PILLARS}
    lead = []
    weights = old
    for i in range(len(per_cycle) - 1):
        cur = per_cycle[i]["subscores"]
        nxt = per_cycle[i + 1]["subscores"]
        for p in PILLARS:
            subs[p].append(cur.get(p, 0.0))
        if args.lead == "revenue":
            lead.append(nxt.get("revenue", 0.0))
        else:
            lead.append(sum(weights.get(q, 0.0) * nxt.get(q, 0.0) for q in PILLARS))

    # Use movement (first difference) of subscore vs lead outcome.
    corr: Dict[str, Optional[float]] = {}
    target: Dict[str, float] = {}
    shrink_applied: Dict[str, bool] = {}
    s = clip(1.0 - (len(per_cycle) - 1) / K_SHRINK, S_MIN, 1.0)
    for p in PILLARS:
        series = subs[p]
        d_series = [series[i + 1] - series[i] for i in range(len(series) - 1)]
        d_lead = [lead[i + 1] - lead[i] for i in range(len(lead) - 1)]
        r = _pearson(d_series, d_lead)
        corr[p] = round(r, 4) if r is not None else None
        rr = clip(r if r is not None else 0.0, -1.0, 1.0)
        w_t = prior[p] * (1.0 + rr)
        if r is None or abs(r) < SIGNAL_FLOOR:
            w_t = (1.0 - s) * w_t + s * prior[p]
            shrink_applied[p] = True
        else:
            shrink_applied[p] = False
        target[p] = max(w_t, 0.0)

    # normalize target
    ts = sum(target.values()) or 1.0
    target = {p: target[p] / ts for p in PILLARS}

    # decayed learning rate
    eta = args.eta0 * math.exp(-args.kappa * cycle)
    new = {p: old.get(p, 0.0) + eta * (target[p] - old.get(p, 0.0)) for p in PILLARS}
    ns = sum(new.values()) or 1.0
    new = {p: round(new[p] / ns, 6) for p in PILLARS}

    emit({
        "old_weights": old, "new_weights": new,
        "per_pillar_correlation": corr, "shrinkage_applied": shrink_applied,
        "learning_rate": round(eta, 6), "lead_outcome": args.lead, "mode": "full",
        "low_confidence": False,
    })


if __name__ == "__main__":
    main()
