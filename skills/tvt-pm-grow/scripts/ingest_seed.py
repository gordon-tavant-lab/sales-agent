#!/usr/bin/env python3
"""ingest_seed.py — parse + validate reception_stats.yaml → canonical state.json.

The ONLY script that reads YAML; everything downstream consumes the canonical state so the
schema is parsed exactly once. Validates against schema_version, normalizes, resolves the
domain profile, and computes data-density / mode flags.

Usage:
    python scripts/ingest_seed.py path/to/reception_stats.yaml [--ledger LEDGER.jsonl] > state.json

Output (stdout): canonical state object (see references/schema.md).
Exit nonzero on hard validation error (message on stderr as JSON).
"""
import argparse
import os
from typing import Any, Dict, List

try:
    import yaml
except ImportError:
    import json as _json
    import sys as _sys
    _json.dump({"error": "pyyaml not installed; pip install -r scripts/requirements.txt"}, _sys.stderr)
    _sys.exit(2)

from common import emit, fail, clip  # noqa: E402
from profiles import get_profile, PILLARS  # noqa: E402

KNOWN_SCHEMA = 1
SPARSE_CUTOFF = 4
VALID_IMPACT = {0.25, 0.5, 1, 2, 3}
VALID_KANO = {"must_be", "one_dimensional", "attractive", "indifferent", "reverse"}
RATE_KEYS = {"activation_rate", "retention_d30", "sentiment_score", "paid_conversion",
             "churn_rate", "share_of_voice", "win_rate"}


def _count_ledger(path: str) -> int:
    if not path or not os.path.exists(path):
        return 0
    n = 0
    with open(path, "r") as fh:
        for line in fh:
            if line.strip():
                n += 1
    return n


def _validate_rates(block: Dict[str, Any], pillar: str, cycle: int) -> None:
    for k, v in block.items():
        if k in RATE_KEYS and isinstance(v, (int, float)):
            if not (0.0 <= float(v) <= 1.0):
                fail("rate {}.{} = {} out of [0,1] (cycle {})".format(pillar, k, v, cycle))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("yaml_path")
    ap.add_argument("--ledger", default="")
    args = ap.parse_args()

    if not os.path.exists(args.yaml_path):
        fail("file not found: {}".format(args.yaml_path))
    with open(args.yaml_path, "r") as fh:
        raw = yaml.safe_load(fh)
    if not isinstance(raw, dict):
        fail("top-level YAML must be a mapping")

    sv = raw.get("schema_version")
    if sv != KNOWN_SCHEMA:
        fail("schema_version {} unsupported (this skill knows {})".format(sv, KNOWN_SCHEMA))

    product = raw.get("product") or {}
    for req in ("name", "domain_profile", "cycle"):
        if req not in product:
            fail("product.{} is required".format(req))
    profile_name = product["domain_profile"]
    try:
        profile = get_profile(profile_name)
    except ValueError as e:
        fail(str(e))
    cycle = int(product["cycle"])

    metrics: List[Dict[str, Any]] = raw.get("metrics") or []
    if not any(int(m.get("cycle", -1)) == cycle for m in metrics):
        fail("metrics has no block for current cycle {}".format(cycle))
    for m in metrics:
        c = int(m.get("cycle", -1))
        for pillar in PILLARS:
            if pillar in m and isinstance(m[pillar], dict):
                _validate_rates(m[pillar], pillar, c)

    backlog: List[Dict[str, Any]] = raw.get("backlog") or []
    for item in backlog:
        if float(item.get("effort", 0)) <= 0:
            fail("backlog item {} effort must be > 0".format(item.get("id")))
        if float(item.get("impact", -1)) not in VALID_IMPACT:
            fail("backlog item {} impact must be in {}".format(item.get("id"), sorted(VALID_IMPACT)))
        if item.get("kano") not in VALID_KANO:
            fail("backlog item {} kano '{}' invalid".format(item.get("id"), item.get("kano")))
        for p in (item.get("pillars") or []):
            if p not in PILLARS:
                fail("backlog item {} unknown pillar '{}'".format(item.get("id"), p))

    outcomes: List[Dict[str, Any]] = raw.get("outcomes") or []
    known_categories = {i.get("category") for i in backlog}
    warnings: List[str] = []
    for o in outcomes:
        if o.get("category") not in known_categories and known_categories:
            warnings.append("outcome {} category '{}' not in current backlog".format(
                o.get("id"), o.get("category")))

    # pillar weights: prior from file (normalized) or profile defaults.
    prior = raw.get("pillar_weights_prior")
    if prior:
        s = sum(float(prior.get(p, 0)) for p in PILLARS) or 1.0
        pillar_weights = {p: clip(float(prior.get(p, 0)) / s, 0.0, 1.0) for p in PILLARS}
    else:
        pillar_weights = dict(profile["weights"])

    n_cycles = len({int(m.get("cycle", -1)) for m in metrics})
    ledger_records = _count_ledger(args.ledger)
    sparse = cycle < SPARSE_CUTOFF
    mode = "sparse" if sparse else "full"

    emit({
        "schema_version": KNOWN_SCHEMA,
        "mode": mode,
        "data_density": {"cycles": n_cycles, "sparse": sparse, "ledger_records": ledger_records},
        "product": product,
        "domain_profile": {"name": profile_name, "weights": profile["weights"],
                           "metric_targets": profile["metric_targets"]},
        "metrics": metrics,
        "pillar_weights": pillar_weights,
        "backlog": backlog,
        "outcomes": outcomes,
        "warnings": warnings,
    })


if __name__ == "__main__":
    main()
