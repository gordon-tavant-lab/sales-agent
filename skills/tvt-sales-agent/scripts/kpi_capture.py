"""kpi_capture.py — produces a g-mature-assess-compatible readings.json (T17, FR-018).

Consumes, does not reinvent: g-mature-assess's kpi_eval.py already does deterministic
KPI-gate evaluation against the sales-gtm domain's 7 KPIs (win_rate, sales_cycle_length,
pipeline_coverage, meddpicc_score, pattern_reuse_rate, case_study_yield, rep_ramp_time).
This script's only job is to produce the `{kpi_id: value | "no_data"}` readings.json that
tool expects, sourced from tvt-sales-agent's own real operational data:

  - win_rate / sales_cycle_length / pipeline_coverage: passed through from
    tvt-sales-prospect's own kpi.py scorecard, field-renamed to match kpi-catalog.yml's
    ids exactly (kpi.py's own output shape predates this integration and uses different
    key names -- "cycle_length" not "sales_cycle_length", motion keys "hunt"/"expand" not
    "new_business"/"expansion"). Requires a real --opportunities-file; without one, these
    three report no_data.
  - meddpicc_score / pattern_reuse_rate / case_study_yield / rep_ramp_time: this system
    does not own the data these need (per-deal MEDDPICC evidence, cross-chain pattern-cite
    tracking, rep-level ramp data) -- always no_data here, honestly, per FR-018. If that
    changes, this is where the computation would be added, not silently assumed.

Per-jtbd_step invocation counts are computed from the Invocation Ledger as a separate
"activity" block -- NOT one of the 7 KPIs, so it is deliberately kept out of the
kpi_eval.py-shaped readings dict rather than conflated with it.
"""
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import emit, fail, load_roster  # noqa: E402

NO_DATA = "no_data"

# The 4 JTBD-doc candidate KPIs (jtbd-pipeline-gaps.md) are not in g-mature-assess's
# catalog yet -- reported here under a separate, clearly-labeled block so a future
# catalog addition has a real source to point at, without this script inventing an
# entry in the sales-gtm domain that doesn't exist there yet.
JTBD_CANDIDATE_KPI_IDS = [
    "target_list_coverage_rate",       # S1
    "qualified_lead_yield",            # S1
    "verification_gate_compliance_rate",  # S3
    "pilot_stall_rate",                # S7
    "poc_to_production_conversion_rate",  # S7
    "renewal_expansion_rate",          # S8
    "renewal_risk_lead_time",          # S8
]


def load_ledger(ledger_path: str) -> List[Dict[str, Any]]:
    """Read the Invocation Ledger (tvt-gov-attest JSONL). Missing file = no invocations
    yet, not an error -- this script runs before Stage 2 (T8's ledger wiring) exists."""
    if not os.path.exists(ledger_path):
        return []
    records = []
    with open(ledger_path, "r") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def activity_by_jtbd_step(ledger_records: List[Dict[str, Any]], roster: Dict[str, Any]) -> Dict[str, int]:
    """Per-jtbd_step invocation counts -- a coverage/activity leading indicator, not a
    KPI itself. AGENT:<slug> reason_codes (per research-foundations.md Decision Point 2)
    are matched back to roster.yml's jtbd_step tag."""
    slug_to_step = {c["capability_slug"]: c["jtbd_step"] for c in roster["capabilities"]}
    counts: Dict[str, int] = {step: 0 for step in ("S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9")}
    for rec in ledger_records:
        reason_code = rec.get("reason_code", "")
        if not reason_code.startswith("AGENT:"):
            continue
        slug = reason_code[len("AGENT:"):]
        step = slug_to_step.get(slug)
        if step:
            counts[step] += 1
    return counts


def _reading_or_no_data(container: Any, key: str) -> Any:
    """A missing key AND an explicit None (kpi.py's own "not enough data" signal, e.g.
    win_rate's value is None when there are zero closed deals) both mean the same thing
    here: no_data. Never pass a bare None through to kpi_eval.py -- it only understands
    a real value or the literal string "no_data"."""
    if not isinstance(container, dict):
        return NO_DATA
    value = container.get(key)
    return NO_DATA if value is None else value


def sales_prospect_readings(opportunities_file: Optional[str], quota_hunt: float, quota_expand: float) -> Dict[str, Any]:
    """Shell out to the vendored tvt-sales-prospect/scripts/kpi.py and translate its
    output to kpi-catalog.yml's id/shape. Returns no_data for all three if no real
    opportunities file is given, or if kpi.py itself had insufficient data (e.g. zero
    closed deals) -- this function never fabricates a reading."""
    if not opportunities_file or not os.path.exists(opportunities_file):
        return {
            "win_rate": NO_DATA,
            "sales_cycle_length": NO_DATA,
            "pipeline_coverage": {"new_business": NO_DATA, "expansion": NO_DATA},
        }

    kpi_script_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        "skills",
        "tvt-sales-prospect",
        "scripts",
    )
    sys.path.insert(0, kpi_script_dir)
    import importlib

    tvt_kpi = importlib.import_module("kpi")
    with open(opportunities_file) as fh:
        opportunities = json.load(fh)
    scorecard = tvt_kpi.scorecard(opportunities, quota_hunt, quota_expand)

    coverage = scorecard.get("pipeline_coverage", {})
    coverage_reading = {
        "new_business": _reading_or_no_data(coverage.get("hunt"), "ratio"),
        "expansion": _reading_or_no_data(coverage.get("expand"), "ratio"),
    }

    return {
        "win_rate": _reading_or_no_data(scorecard.get("win_rate"), "value"),
        "sales_cycle_length": _reading_or_no_data(scorecard.get("cycle_length"), "median_days"),
        "pipeline_coverage": coverage_reading,
    }


def build_readings(
    ledger_path: str,
    roster: Dict[str, Any],
    opportunities_file: Optional[str] = None,
    quota_hunt: float = 0.0,
    quota_expand: float = 0.0,
) -> Dict[str, Any]:
    prospect = sales_prospect_readings(opportunities_file, quota_hunt, quota_expand)
    readings = {
        "win_rate": prospect["win_rate"],
        "sales_cycle_length": prospect["sales_cycle_length"],
        "pipeline_coverage": prospect["pipeline_coverage"],
        # This system does not own the data these four need -- always honest no_data,
        # per FR-018. Not a placeholder for "not implemented yet"; a documented,
        # permanent boundary until a data source for these actually exists.
        "meddpicc_score": NO_DATA,
        "pattern_reuse_rate": NO_DATA,
        "case_study_yield": NO_DATA,
        "rep_ramp_time": NO_DATA,
    }

    ledger_records = load_ledger(ledger_path)
    activity = activity_by_jtbd_step(ledger_records, roster)

    jtbd_candidates = {kpi_id: NO_DATA for kpi_id in JTBD_CANDIDATE_KPI_IDS}

    return {
        "readings": readings,
        "activity_by_jtbd_step": activity,
        "jtbd_candidate_kpis_not_yet_in_catalog": jtbd_candidates,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ledger-file", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "output", "invocation-ledger.jsonl"
    ))
    p.add_argument("--opportunities-file", default=None)
    p.add_argument("--quota-hunt", type=float, default=0.0)
    p.add_argument("--quota-expand", type=float, default=0.0)
    p.add_argument("--output", default=None)
    args = p.parse_args()

    try:
        roster = load_roster()
    except (OSError, ValueError) as e:
        fail("roster load failed: {}".format(e))
        return

    result = build_readings(
        args.ledger_file, roster, args.opportunities_file, args.quota_hunt, args.quota_expand
    )

    if args.output:
        with open(args.output, "w") as fh:
            json.dump(result, fh, indent=2)
            fh.write("\n")
    emit(result)


if __name__ == "__main__":
    main()
