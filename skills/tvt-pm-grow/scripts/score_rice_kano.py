#!/usr/bin/env python3
"""score_rice_kano.py — RICE core × Kano multiplier per backlog item.

Confidence is deliberately EXCLUDED here; it is injected later as Thompson P(success) in
emv_rank.py. This keeps the calibrated-probability source single and auditable.

Usage:
    python scripts/score_rice_kano.py --state state.json > scored.json
Output: {"items": [{id, category, rice_core, kano_multiplier, rice_kano, ...}, ...]}
"""
import argparse
from typing import Dict

from common import emit, fail, load_json

KANO_K: Dict[str, float] = {
    "must_be": 0.8,
    "one_dimensional": 1.0,
    "attractive": 1.3,
    "indifferent": 0.4,
    "reverse": 0.1,
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    args = ap.parse_args()
    state = load_json(args.state)

    items = []
    for it in state.get("backlog", []):
        effort = float(it.get("effort", 0))
        if effort <= 0:
            fail("item {} effort must be > 0".format(it.get("id")))
        reach = float(it.get("reach", 0))
        impact = float(it.get("impact", 0))
        rice_core = (reach * impact) / effort
        k = KANO_K.get(it.get("kano", "one_dimensional"), 1.0)
        items.append({
            "id": it.get("id"),
            "title": it.get("title"),
            "category": it.get("category"),
            "pillars": it.get("pillars", []),
            "reach": reach, "impact": impact, "effort": effort,
            "kano": it.get("kano"),
            "delta_value": float(it.get("delta_value", 0)),
            "cost": float(it.get("cost", 0)),
            "rice_core": round(rice_core, 6),
            "kano_multiplier": k,
            "rice_kano": round(rice_core * k, 6),
        })

    emit({"items": items})


if __name__ == "__main__":
    main()
