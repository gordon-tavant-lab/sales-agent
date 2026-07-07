#!/usr/bin/env python3
"""kpi.py — deterministic portfolio KPI scorecard (spec 006 §3).

Computes the Gong-class portfolio KPIs the spec names, against the sourced benchmarks
(research-foundations.md §A). Deterministic. The LLM narrates the scorecard; it never
computes a number — every value here comes from arithmetic over Salesforce-shaped records,
not a model call.

Known limitation (documented, not hidden): `stage_conversion` uses current-stage snapshots,
not stage-transition timestamps. True historical conversion (did opp X actually pass through
stage Y on date Z) needs a stage-history log this minimal opportunity record doesn't capture
yet — that's a v2 data-model addition, not a v1 scope cut made silently.

Opportunity record shape:
  {"id": str, "motion": "hunt"|"expand", "stage": str (one of STAGE_ORDER or CLOSED_WON/CLOSED_LOST),
   "amount": float, "created_date": "YYYY-MM-DD", "close_date": "YYYY-MM-DD"|null,
   "pov_cites_pattern": bool (optional, spec §1a),
   "case_study_produced": bool (optional, only meaningful once stage == CLOSED_WON, spec §1a)}

The two optional fields operationalize the value-chain framing (spec §1a — two multipliers, not
one): `pov_cites_pattern` measures whether a chain's job-3 POV reused a g-intel-flywheel pattern
from another chain (multiplier 2, the flywheel), and `case_study_produced` measures whether a win
produced the second, compounding output job 7 is supposed to capture, not just revenue.

Usage:
  python kpi.py --opportunities-file opps.json --quota-hunt 500000 --quota-expand 300000
"""
import argparse
import json
import statistics
from datetime import datetime
from typing import Any, Dict, List, Optional

from common import emit, fail

# Sourced benchmarks (research-foundations.md §A — Gong Feb 2024 n=5.6M; Gong 2025 State of
# Revenue; HubSpot State of Sales 2024; Ebsta x Pavilion 2024 n=9,338 teams/$148B pipeline;
# industry analyst Sep 2023). Cite in any narration built on top of this module.
BENCHMARK_WIN_RATE_MEDIAN = 0.21
BENCHMARK_WIN_RATE_ENTERPRISE = 0.25
BENCHMARK_CYCLE_DAYS_100K_ACV = 84
BENCHMARK_CYCLE_DAYS_250K_ACV = 192
BENCHMARK_COVERAGE_HUNT = 3.5
BENCHMARK_COVERAGE_EXPAND = 2.2
BENCHMARK_COVERAGE_TOP_QUARTILE = 4.2
BENCHMARK_COVERAGE_LOOSE_QUALIFICATION_FLOOR = 5.0

CLOSED_WON = "Closed Won"
CLOSED_LOST = "Closed Lost"

# Native Salesforce Opportunity stage order (help.salesforce.com convention, verified against
# practitioner sources 2026-07-02 — sanity-check against your org's actual picklist, orgs
# frequently customize this).
STAGE_ORDER = [
    "Prospecting", "Qualification", "Needs Analysis", "Value Proposition",
    "Id. Decision Makers", "Perception Analysis", "Proposal/Price Quote",
    "Negotiation/Review",
]


def _parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d")


def win_rate(opportunities: List[Dict[str, Any]]) -> Dict[str, Any]:
    closed = [o for o in opportunities if o["stage"] in (CLOSED_WON, CLOSED_LOST)]
    if not closed:
        return {"value": None, "n_closed": 0, "n_won": 0}
    won = [o for o in closed if o["stage"] == CLOSED_WON]
    value = len(won) / len(closed)
    return {
        "value": value,
        "n_closed": len(closed),
        "n_won": len(won),
        "benchmark_median": BENCHMARK_WIN_RATE_MEDIAN,
        "benchmark_enterprise": BENCHMARK_WIN_RATE_ENTERPRISE,
        "vs_benchmark_median": round(value - BENCHMARK_WIN_RATE_MEDIAN, 4),
    }


def cycle_length_days(opportunities: List[Dict[str, Any]]) -> Dict[str, Any]:
    won = [
        o for o in opportunities
        if o["stage"] == CLOSED_WON and o.get("close_date") and o.get("created_date")
    ]
    if not won:
        return {"median_days": None, "n": 0}
    days = [(_parse_date(o["close_date"]) - _parse_date(o["created_date"])).days for o in won]
    return {
        "median_days": statistics.median(days),
        "n": len(days),
        "benchmark_100k_acv": BENCHMARK_CYCLE_DAYS_100K_ACV,
        "benchmark_250k_acv": BENCHMARK_CYCLE_DAYS_250K_ACV,
    }


def pipeline_coverage(open_pipeline_value: float, quota_value: float, motion: str) -> Dict[str, Any]:
    benchmark = BENCHMARK_COVERAGE_HUNT if motion == "hunt" else BENCHMARK_COVERAGE_EXPAND
    if quota_value <= 0:
        return {"ratio": None, "motion": motion, "benchmark": benchmark, "flag": "no_quota_set"}
    ratio = open_pipeline_value / quota_value
    flag = None
    if ratio > BENCHMARK_COVERAGE_LOOSE_QUALIFICATION_FLOOR:
        flag = "coverage_too_high_loose_qualification_risk"
    elif ratio < benchmark:
        flag = "below_benchmark"
    return {
        "ratio": round(ratio, 3),
        "motion": motion,
        "benchmark": benchmark,
        "top_quartile": BENCHMARK_COVERAGE_TOP_QUARTILE,
        "loose_qualification_floor": BENCHMARK_COVERAGE_LOOSE_QUALIFICATION_FLOOR,
        "flag": flag,
    }


def stage_conversion(opportunities: List[Dict[str, Any]],
                      stage_order: Optional[List[str]] = None) -> Dict[str, Any]:
    """Snapshot funnel proxy — see module docstring's documented limitation."""
    order = stage_order or STAGE_ORDER
    index = {s: i for i, s in enumerate(order)}

    def reached_or_passed(o, i):
        if o["stage"] == CLOSED_WON:
            return True
        if o["stage"] == CLOSED_LOST:
            return False  # can't tell which stage it reached from a snapshot alone
        return index.get(o["stage"], -1) >= i

    funnel = []
    for i, stage in enumerate(order):
        at_or_past = sum(1 for o in opportunities if reached_or_passed(o, i))
        funnel.append({"stage": stage, "count": at_or_past})

    conversions = []
    for i in range(len(funnel) - 1):
        a, b = funnel[i]["count"], funnel[i + 1]["count"]
        rate = (b / a) if a else None
        conversions.append({"from": funnel[i]["stage"], "to": funnel[i + 1]["stage"], "rate": rate})

    return {
        "funnel": funnel,
        "conversions": conversions,
        "limitation": "snapshot-based (current stage only) — not stage-transition-timestamp-based",
    }


def pattern_reuse_rate(opportunities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Multiplier 2's own health metric (spec §1a) — is the flywheel actually compounding?

    Reports what fraction of chains reused a pattern, and — when both groups have closed-won
    data — whether pattern-reuse chains actually close faster than cold-started ones. A high
    reuse rate with no cycle-time difference would mean the flywheel isn't really multiplying
    anything; this makes that checkable instead of assumed.
    """
    labeled = [o for o in opportunities if "pov_cites_pattern" in o]
    if not labeled:
        return {"rate": None, "n": 0}

    cited = [o for o in labeled if o["pov_cites_pattern"]]
    cold_started = [o for o in labeled if not o["pov_cites_pattern"]]
    result = {"rate": len(cited) / len(labeled), "n": len(labeled), "n_cited": len(cited)}

    cited_cycle = cycle_length_days(cited)["median_days"]
    cold_cycle = cycle_length_days(cold_started)["median_days"]
    if cited_cycle is not None and cold_cycle is not None:
        result["cited_median_cycle_days"] = cited_cycle
        result["cold_started_median_cycle_days"] = cold_cycle
        result["cycle_delta_days"] = round(cold_cycle - cited_cycle, 1)
    return result


def case_study_yield(opportunities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Fraction of Job-7 wins that produced a case study — the 2nd output §1a says job 7 owes.

    A win missing the `case_study_produced` field is surfaced as unlabeled, not silently
    excluded — a portfolio full of unlabeled wins should look like a warning, not a clean 100%.
    """
    won = [o for o in opportunities if o["stage"] == CLOSED_WON]
    if not won:
        return {"yield": None, "n_won": 0, "n_labeled": 0}
    labeled = [o for o in won if "case_study_produced" in o]
    if not labeled:
        return {"yield": None, "n_won": len(won), "n_labeled": 0,
                 "warning": "no wins have case_study_produced set"}
    produced = sum(1 for o in labeled if o["case_study_produced"])
    result = {"yield": produced / len(labeled), "n_won": len(won),
              "n_labeled": len(labeled), "n_produced": produced}
    if len(labeled) < len(won):
        result["warning"] = "{} of {} wins are unlabeled".format(len(won) - len(labeled), len(won))
    return result


def scorecard(opportunities: List[Dict[str, Any]], quota_hunt: float, quota_expand: float) -> Dict[str, Any]:
    open_by_motion = {"hunt": 0.0, "expand": 0.0}
    for o in opportunities:
        if o["stage"] not in (CLOSED_WON, CLOSED_LOST):
            open_by_motion[o["motion"]] = open_by_motion.get(o["motion"], 0.0) + o["amount"]

    return {
        "win_rate": win_rate(opportunities),
        "cycle_length": cycle_length_days(opportunities),
        "pipeline_coverage": {
            "hunt": pipeline_coverage(open_by_motion.get("hunt", 0.0), quota_hunt, "hunt"),
            "expand": pipeline_coverage(open_by_motion.get("expand", 0.0), quota_expand, "expand"),
        },
        "stage_conversion": stage_conversion(opportunities),
        "pattern_reuse_rate": pattern_reuse_rate(opportunities),
        "case_study_yield": case_study_yield(opportunities),
    }


def _load(path: str) -> List[Dict[str, Any]]:
    with open(path, "r") as fh:
        return json.load(fh)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--opportunities-file", required=True)
    p.add_argument("--quota-hunt", type=float, default=0.0)
    p.add_argument("--quota-expand", type=float, default=0.0)
    args = p.parse_args()
    try:
        opps = _load(args.opportunities_file)
        emit(scorecard(opps, args.quota_hunt, args.quota_expand))
    except (ValueError, KeyError, FileNotFoundError, json.JSONDecodeError) as e:
        fail(str(e))


if __name__ == "__main__":
    main()
