#!/usr/bin/env python3
"""mdi_compose.py — roll 4 pillars into the Market Dominance Index + Goodhart guard.

Normalizes each metric to [0,1] against domain-profile targets, averages within pillar,
weights by current pillar weights. Flags Goodhart divergence (a value pillar rising while a
health metric falls) over the last two cycles.

Usage:
    python scripts/mdi_compose.py --state state.json [--theta 0.05] > mdi.json
Output: {mdi, pillar_subscores, weights_used, cycle_delta, goodhart_alerts, per_cycle}
"""
import argparse
from typing import Any, Dict, List, Optional

from common import emit, clip, load_json
from profiles import PILLARS, HEALTH_METRICS


def _norm(x: float, target: float, direction: str) -> float:
    if direction == "rate":
        if target and target != 1.0:
            return clip(x / target, 0.0, 1.0)
        return clip(x, 0.0, 1.0)
    if direction == "-":
        return clip(target / x, 0.0, 1.0) if x > 0 else 0.0
    return clip(x / target, 0.0, 1.0) if target else 0.0


def _pillar_subscore(block: Dict[str, Any], targets: Dict[str, Any]) -> Optional[float]:
    vals = []
    for key, val in block.items():
        if key in targets and isinstance(val, (int, float)):
            target, direction = targets[key]
            vals.append(_norm(float(val), float(target), direction))
    if not vals:
        return None
    return sum(vals) / len(vals)


def _subscores_for_cycle(m: Dict[str, Any], metric_targets: Dict[str, Any]) -> Dict[str, float]:
    out = {}
    for pillar in PILLARS:
        block = m.get(pillar) or {}
        ss = _pillar_subscore(block, metric_targets.get(pillar, {}))
        if ss is not None:
            out[pillar] = round(ss, 6)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--theta", type=float, default=0.05)
    args = ap.parse_args()
    state = load_json(args.state)

    metric_targets = state["domain_profile"]["metric_targets"]
    weights = state["pillar_weights"]
    metrics: List[Dict[str, Any]] = sorted(state.get("metrics", []), key=lambda x: int(x.get("cycle", 0)))

    per_cycle = []
    for m in metrics:
        per_cycle.append({"cycle": int(m.get("cycle", 0)),
                          "subscores": _subscores_for_cycle(m, metric_targets)})

    current = per_cycle[-1]["subscores"] if per_cycle else {}
    mdi = sum(weights.get(p, 0.0) * current.get(p, 0.0) for p in PILLARS)

    prev_mdi = None
    if len(per_cycle) >= 2:
        prev = per_cycle[-2]["subscores"]
        prev_mdi = sum(weights.get(p, 0.0) * prev.get(p, 0.0) for p in PILLARS)
    cycle_delta = round(mdi - prev_mdi, 6) if prev_mdi is not None else None

    # Goodhart guard: revenue subscore up while a health metric subscore/value down.
    alerts: List[str] = []
    if len(per_cycle) >= 2:
        cur_ss, prev_ss = per_cycle[-1]["subscores"], per_cycle[-2]["subscores"]
        d_rev = cur_ss.get("revenue", 0.0) - prev_ss.get("revenue", 0.0)
        if d_rev > args.theta:
            for pillar, _key in HEALTH_METRICS:
                d_health = cur_ss.get(pillar, 0.0) - prev_ss.get(pillar, 0.0)
                if d_health < -args.theta:
                    alerts.append(
                        "Goodhart: revenue +{:.3f} while {} {:.3f}".format(d_rev, pillar, d_health))

    emit({
        "mdi": round(mdi, 6),
        "pillar_subscores": current,
        "weights_used": weights,
        "cycle_delta": cycle_delta,
        "goodhart_alerts": alerts,
        "per_cycle": per_cycle,
    })


if __name__ == "__main__":
    main()
