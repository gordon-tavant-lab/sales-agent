#!/usr/bin/env python3
"""emv_rank.py — final ranking by Expected Monetary Value, fused with MDI contribution.

Injects Thompson P(success) (by category) as the RICE Confidence term, computes
EMV = P(success)*delta_value - cost, estimates expected MDI contribution using the NEW learned
weights, ranks, and tiers into now/next/later by EMV quantiles.

Usage:
    python scripts/emv_rank.py --scored scored.json --thompson thompson.json --reweight reweight.json \
        > ranked.json
Output: {"items": [...ranked...], "tiers": {now:[ids], next:[ids], later:[ids]}}
"""
import argparse
from typing import Dict, List

from common import emit, load_json


def _quantile(sorted_vals: List[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = q * (len(sorted_vals) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scored", required=True)
    ap.add_argument("--thompson", required=True)
    ap.add_argument("--reweight", required=True)
    args = ap.parse_args()

    scored = load_json(args.scored)["items"]
    by_cat = load_json(args.thompson)["by_category"]
    weights = load_json(args.reweight)["new_weights"]

    items = []
    max_rice_final = 0.0
    for it in scored:
        cat = it.get("category")
        p = by_cat.get(cat, {}).get("p_success", 0.5)
        rice_final = it["rice_kano"] * p
        emv = p * it["delta_value"] - it["cost"]
        items.append({**it, "p_success": p, "rice_final": round(rice_final, 6),
                      "emv": round(emv, 2)})
        max_rice_final = max(max_rice_final, rice_final)

    max_rice_final = max_rice_final or 1.0
    for it in items:
        pillars = it.get("pillars") or []
        wmean = (sum(weights.get(p, 0.0) for p in pillars) / len(pillars)) if pillars else 0.0
        it["expected_mdi_contribution"] = round(wmean * (it["rice_final"] / max_rice_final), 6)

    # rank: EMV desc, tiebreak rice_final, then mdi contribution
    items.sort(key=lambda x: (x["emv"], x["rice_final"], x["expected_mdi_contribution"]),
               reverse=True)
    for i, it in enumerate(items):
        it["rank"] = i + 1

    pos_emv = sorted([it["emv"] for it in items if it["emv"] > 0])
    p66 = _quantile(pos_emv, 0.66)
    p33 = _quantile(pos_emv, 0.33)
    tiers: Dict[str, List[str]] = {"now": [], "next": [], "later": []}
    for it in items:
        if it["emv"] <= 0:
            it["tier"] = "later"
            it["negative_emv"] = True
        elif it["emv"] >= p66:
            it["tier"] = "now"
        elif it["emv"] >= p33:
            it["tier"] = "next"
        else:
            it["tier"] = "later"
        tiers[it["tier"]].append(it["id"])

    emit({"items": items, "tiers": tiers,
          "weights_used": weights, "emv_p33": round(p33, 2), "emv_p66": round(p66, 2)})


if __name__ == "__main__":
    main()
