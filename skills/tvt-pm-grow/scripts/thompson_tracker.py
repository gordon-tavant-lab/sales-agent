#!/usr/bin/env python3
"""thompson_tracker.py — Beta(alpha,beta) posterior per feature CATEGORY → P(success).

Calibrated probability of success learned from realized outcomes, with exponential recency
decay so recent market reception dominates. This p_success becomes the RICE Confidence term.

Usage:
    python scripts/thompson_tracker.py --state state.json [--lam 0.3] > thompson.json
Output: {"by_category": {cat: {alpha, beta, p_success, ci90:[lo,hi], thompson_sample, n}}}
"""
import argparse
import math
from typing import Dict, List

from common import emit, load_json


def _beta_ppf(q: float, a: float, b: float) -> float:
    """90% CI bounds via a robust bisection on the regularized incomplete beta (no scipy dep).

    Uses math.lgamma-based continued fraction for the incomplete beta CDF. Deterministic.
    """
    def betacf(x: float, a: float, b: float) -> float:
        MAXIT, EPS, FPMIN = 200, 3.0e-12, 1.0e-300
        qab, qap, qam = a + b, a + 1.0, a - 1.0
        c = 1.0
        d = 1.0 - qab * x / qap
        if abs(d) < FPMIN:
            d = FPMIN
        d = 1.0 / d
        h = d
        for m in range(1, MAXIT + 1):
            m2 = 2 * m
            aa = m * (b - m) * x / ((qam + m2) * (a + m2))
            d = 1.0 + aa * d
            if abs(d) < FPMIN:
                d = FPMIN
            c = 1.0 + aa / c
            if abs(c) < FPMIN:
                c = FPMIN
            d = 1.0 / d
            h *= d * c
            aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
            d = 1.0 + aa * d
            if abs(d) < FPMIN:
                d = FPMIN
            c = 1.0 + aa / c
            if abs(c) < FPMIN:
                c = FPMIN
            d = 1.0 / d
            de = d * c
            h *= de
            if abs(de - 1.0) < EPS:
                break
        return h

    def betai(x: float, a: float, b: float) -> float:
        if x <= 0.0:
            return 0.0
        if x >= 1.0:
            return 1.0
        lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
        bt = math.exp(lbeta + a * math.log(x) + b * math.log(1.0 - x))
        if x < (a + 1.0) / (a + b + 2.0):
            return bt * betacf(x, a, b) / a
        return 1.0 - bt * betacf(1.0 - x, b, a) / b

    lo, hi = 0.0, 1.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if betai(mid, a, b) < q:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--lam", type=float, default=0.3, help="recency decay rate")
    args = ap.parse_args()
    state = load_json(args.state)
    cycle_now = int(state.get("product", {}).get("cycle", 1))
    outcomes = state.get("outcomes", [])

    # collect categories from backlog AND outcomes so we can price unseen ones too
    cats = {i.get("category") for i in state.get("backlog", [])}
    cats |= {o.get("category") for o in outcomes}
    cats.discard(None)

    by_cat: Dict[str, Dict] = {}
    for cat in sorted(cats):
        alpha, beta, n = 1.0, 1.0, 0  # uniform Beta(1,1) prior
        for o in outcomes:
            if o.get("category") != cat:
                continue
            n += 1
            w = math.exp(-args.lam * max(0, cycle_now - int(o.get("shipped_cycle", cycle_now))))
            s = 1.0 if o.get("success") else 0.0
            alpha += w * s
            beta += w * (1.0 - s)
        p = alpha / (alpha + beta)
        ci = [round(_beta_ppf(0.05, alpha, beta), 4), round(_beta_ppf(0.95, alpha, beta), 4)]
        # deterministic "sample" surrogate = posterior mean (no RNG in replay context)
        by_cat[cat] = {
            "alpha": round(alpha, 4), "beta": round(beta, 4),
            "p_success": round(p, 4), "ci90": ci, "thompson_sample": round(p, 4), "n": n,
        }

    emit({"by_category": by_cat})


if __name__ == "__main__":
    main()
