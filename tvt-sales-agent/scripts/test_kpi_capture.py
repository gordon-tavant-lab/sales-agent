"""Tests for kpi_capture.py (T17). Python 3.9 compatible."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest  # noqa: E402
from common import load_roster  # noqa: E402
from kpi_capture import activity_by_jtbd_step, build_readings, load_ledger  # noqa: E402

FIXTURES_DIR = os.path.dirname(os.path.abspath(__file__))
EXAMPLE_LEDGER = os.path.join(
    os.path.dirname(FIXTURES_DIR), "output", "invocation-ledger.example.jsonl"
)
EXAMPLE_OPPORTUNITIES = os.path.join(
    os.path.dirname(os.path.dirname(FIXTURES_DIR)),
    "skills",
    "tvt-sales-prospect",
    "scripts",
    "kpi_opportunities.example.json",
)


@pytest.fixture(scope="module")
def roster():
    return load_roster()


def test_missing_ledger_file_is_empty_not_an_error():
    assert load_ledger("/tmp/definitely-does-not-exist-12345.jsonl") == []


def test_example_ledger_loads_5_records():
    records = load_ledger(EXAMPLE_LEDGER)
    assert len(records) == 5


def test_activity_by_jtbd_step_counts_correctly(roster):
    records = load_ledger(EXAMPLE_LEDGER)
    activity = activity_by_jtbd_step(records, roster)
    # req-001 prospect-score (S1), req-002+req-004 account-research-deep (S2, x2),
    # req-003 pov-synthesis (S4), req-005 deck-build (S5)
    assert activity["S1"] == 1
    assert activity["S2"] == 2
    assert activity["S4"] == 1
    assert activity["S5"] == 1
    assert activity["S7"] == 0  # confirmed gap, T16
    assert sum(activity.values()) == 5


def test_no_ledger_no_opportunities_is_all_honest_no_data(roster):
    result = build_readings("/tmp/definitely-does-not-exist-12345.jsonl", roster)
    for kpi_id, value in result["readings"].items():
        if kpi_id == "pipeline_coverage":
            assert value == {"new_business": "no_data", "expansion": "no_data"}
        else:
            assert value == "no_data", kpi_id
    assert sum(result["activity_by_jtbd_step"].values()) == 0
    for value in result["jtbd_candidate_kpis_not_yet_in_catalog"].values():
        assert value == "no_data"


def test_real_opportunities_file_produces_real_readings(roster):
    result = build_readings(
        EXAMPLE_LEDGER, roster, EXAMPLE_OPPORTUNITIES, quota_hunt=500000, quota_expand=300000
    )
    readings = result["readings"]
    assert readings["win_rate"] not in ("no_data", None)
    assert 0.0 <= readings["win_rate"] <= 1.0
    assert readings["sales_cycle_length"] not in ("no_data", None)
    assert readings["pipeline_coverage"]["new_business"] not in ("no_data", None)
    # These four this system genuinely does not have data for -- must stay no_data
    # even when real opportunity data IS available for the other three.
    assert readings["meddpicc_score"] == "no_data"
    assert readings["pattern_reuse_rate"] == "no_data"
    assert readings["case_study_yield"] == "no_data"
    assert readings["rep_ramp_time"] == "no_data"


def test_zero_quota_reports_pipeline_coverage_no_data_not_a_crash(roster):
    # kpi.py itself returns {"ratio": None, ...} when quota is 0 -- proves the None-vs-
    # missing-key bug (caught during T17 build) stays fixed.
    result = build_readings(EXAMPLE_LEDGER, roster, EXAMPLE_OPPORTUNITIES)
    assert result["readings"]["pipeline_coverage"] == {"new_business": "no_data", "expansion": "no_data"}


def test_readings_shape_matches_g_mature_assess_kpi_ids(roster):
    result = build_readings(EXAMPLE_LEDGER, roster, EXAMPLE_OPPORTUNITIES, 500000, 300000)
    expected_ids = {
        "win_rate", "sales_cycle_length", "pipeline_coverage",
        "meddpicc_score", "pattern_reuse_rate", "case_study_yield", "rep_ramp_time",
    }
    assert set(result["readings"].keys()) == expected_ids


def test_readings_json_is_serializable(roster):
    result = build_readings(EXAMPLE_LEDGER, roster, EXAMPLE_OPPORTUNITIES, 500000, 300000)
    json.dumps(result)  # must not raise


def test_readings_are_genuinely_consumable_by_g_mature_assess_kpi_eval(roster, tmp_path):
    """End-to-end proof, not just structural similarity: feed kpi_capture.py's real
    output through g-mature-assess's real kpi_eval.py as a subprocess and confirm it
    produces a real verdict, not an error. This is the actual point of FR-018 --
    consuming the existing KPI gate, not just producing JSON that looks like its shape.
    """
    import subprocess
    import sys as _sys

    result = build_readings(EXAMPLE_LEDGER, roster, EXAMPLE_OPPORTUNITIES, 500000, 300000)
    readings_path = tmp_path / "readings.json"
    readings_path.write_text(json.dumps(result["readings"]))

    kpi_eval_path = os.path.expanduser(
        "~/Workspace/.claude/skills/g-mature-assess/scripts/kpi_eval.py"
    )
    if not os.path.exists(kpi_eval_path):
        pytest.skip("g-mature-assess not present in this environment")

    proc = subprocess.run(
        [_sys.executable, kpi_eval_path, "--domain", "sales-gtm", "--stage", "2",
         "--readings", str(readings_path)],
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    verdict = json.loads(proc.stdout)
    assert verdict["domain"] == "sales-gtm"
    assert verdict["total_count"] == 7
    assert verdict["gate"] in ("PASS", "FAIL")
    # 4 KPIs (meddpicc/pattern_reuse/case_study/rep_ramp) are honestly no_data in this
    # fixture -- proves the no_data path round-trips correctly, not just the happy path.
    assert verdict["no_data_count"] == 4
