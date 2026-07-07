#!/usr/bin/env python3
"""backtest_ledger.py — append-only audit ledger writer/reader.

The skill's memory: predictions (what we expected at commit) and realizations (what happened),
paired by feature_id to compute calibration (Brier) and value accuracy (MAPE). Append-only —
corrections are new records, never mutations. See references/ledger-format.md.

Usage:
    # append predictions for the now-tier from a ranked.json
    python scripts/backtest_ledger.py --append --state state.json --ranked ranked.json \
        --ledger LEDGER.jsonl [--ts ISO8601] [--tier now]
    # append realizations from the stats outcomes (already in state)
    python scripts/backtest_ledger.py --append-realizations --state state.json \
        --ledger LEDGER.jsonl [--ts ISO8601]
    # read rollups
    python scripts/backtest_ledger.py --read --ledger LEDGER.jsonl > ledger.json
"""
import argparse
import json
import os
from typing import Any, Dict, List

from common import emit, load_json

SCHEMA = 1


def _append(path: str, records: List[Dict[str, Any]]) -> None:
    with open(path, "a") as fh:
        for r in records:
            fh.write(json.dumps(r, separators=(",", ":")) + "\n")


def _read_all(path: str) -> List[Dict[str, Any]]:
    out = []
    if not os.path.exists(path):
        return out
    with open(path, "r") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def do_append_predictions(args) -> None:
    state = load_json(args.state)
    ranked = load_json(args.ranked)
    cycle = int(state.get("product", {}).get("cycle", 1))
    weights = ranked.get("weights_used", {})
    recs = []
    for it in ranked["items"]:
        if args.tier and it.get("tier") != args.tier:
            continue
        recs.append({
            "ts": args.ts, "schema_version": SCHEMA, "kind": "prediction", "cycle": cycle,
            "feature_id": it["id"], "category": it.get("category"),
            "predicted_p_success": it.get("p_success"), "predicted_emv": it.get("emv"),
            "predicted_mdi_contrib": it.get("expected_mdi_contribution"),
            "weights_snapshot": weights,
            "realized_success": None, "realized_delta_value": None, "realized_mdi_delta": None,
            "note": args.note,
        })
    _append(args.ledger, recs)
    emit({"appended": len(recs), "kind": "prediction", "ledger": args.ledger})


def do_append_realizations(args) -> None:
    state = load_json(args.state)
    recs = []
    for o in state.get("outcomes", []):
        recs.append({
            "ts": args.ts, "schema_version": SCHEMA, "kind": "realization",
            "cycle": int(o.get("shipped_cycle", state.get("product", {}).get("cycle", 1))),
            "feature_id": o.get("id"), "category": o.get("category"),
            "predicted_p_success": None, "predicted_emv": None, "predicted_mdi_contrib": None,
            "weights_snapshot": None,
            "realized_success": bool(o.get("success")),
            "realized_delta_value": o.get("realized_delta_value"),
            "realized_mdi_delta": sum((o.get("pillar_deltas") or {}).values()) or None,
            "note": args.note,
        })
    _append(args.ledger, recs)
    emit({"appended": len(recs), "kind": "realization", "ledger": args.ledger})


def do_read(args) -> None:
    records = _read_all(args.ledger)
    preds: Dict[str, Dict] = {}   # latest prediction per feature_id
    reals: Dict[str, Dict] = {}
    npred = nreal = 0
    for r in records:
        if r.get("kind") == "prediction":
            npred += 1
            preds[r["feature_id"]] = r  # latest wins
        elif r.get("kind") == "realization":
            nreal += 1
            reals[r["feature_id"]] = r

    brier_terms, mape_terms = [], []
    per_cycle: Dict[int, List[float]] = {}
    paired = 0
    for fid, real in reals.items():
        pred = preds.get(fid)
        if not pred:
            continue
        paired += 1
        if pred.get("predicted_p_success") is not None and real.get("realized_success") is not None:
            s = 1.0 if real["realized_success"] else 0.0
            term = (pred["predicted_p_success"] - s) ** 2
            brier_terms.append(term)
            per_cycle.setdefault(int(real.get("cycle", 0)), []).append(term)
        pe, rv = pred.get("predicted_emv"), real.get("realized_delta_value")
        if pe is not None and rv:
            mape_terms.append(abs(pe - rv) / abs(rv))

    brier = round(sum(brier_terms) / len(brier_terms), 6) if brier_terms else None
    mape = round(sum(mape_terms) / len(mape_terms), 6) if mape_terms else None
    trend = [{"cycle": c, "brier": round(sum(v) / len(v), 6)} for c, v in sorted(per_cycle.items())]

    emit({"records": len(records), "predictions": npred, "realizations": nreal, "paired": paired,
          "brier": brier, "emv_mape": mape, "accuracy_trend": trend})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--append", action="store_true")
    ap.add_argument("--append-realizations", dest="append_real", action="store_true")
    ap.add_argument("--read", action="store_true")
    ap.add_argument("--state")
    ap.add_argument("--ranked")
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--tier", default="now")
    ap.add_argument("--ts", default="1970-01-01T00:00:00Z", help="fixed ts for reproducible runs")
    ap.add_argument("--note", default="")
    args = ap.parse_args()

    if args.append:
        do_append_predictions(args)
    elif args.append_real:
        do_append_realizations(args)
    elif args.read:
        do_read(args)
    else:
        ap.error("one of --append, --append-realizations, --read required")


if __name__ == "__main__":
    main()
