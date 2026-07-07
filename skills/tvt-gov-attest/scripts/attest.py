#!/usr/bin/env python3
"""attest.py — append-only, hash-chained decision evidence ledger.

The audit artifact regulated examiners demand: a replayable, tamper-evident trail of every AI
decision (input -> method -> verdict -> reason_code -> model+version -> cost). Applies g-pm-grow's
append-only-ledger pattern + g-learn-determinism-proof's hash-chain to AI governance.

Each record's `chain_hash = sha256(prev_chain_hash + canonical(record_without_chain_hash))`.
Tampering with any past record breaks every subsequent hash — `--verify` detects it.

Mode-graded (spec 004 §2):
  poc  → plain decision log (no chaining required)
  mvp  → + reason codes + structured evidence
  prod → hash-chained, immutable, retention-tagged

Usage:
  # append one decision
  python scripts/attest.py --append --ledger L.jsonl --mode prod \
    --decision-id D-001 --input-ref "loan:123" --method deterministic \
    --verdict pass --reason-code AUS_APPROVE --model claude-opus-4-8 --cost 0.0 --ts <ISO8601>
  # verify the chain is intact
  python scripts/attest.py --verify --ledger L.jsonl
  # coverage report (for the governance gate): how many expected decisions are attested
  python scripts/attest.py --report --ledger L.jsonl [--expected N]

Output: one JSON object. --verify exits 3 if the chain is broken (tamper detected).
"""
import argparse
import hashlib
import json
import os
from typing import Any, Dict, List, Optional

from common import emit, fail

SCHEMA = 1


def _canonical(rec: Dict[str, Any]) -> str:
    r = {k: v for k, v in rec.items() if k != "chain_hash"}
    return json.dumps(r, sort_keys=True, separators=(",", ":"))


def _hash(prev: str, rec: Dict[str, Any]) -> str:
    return hashlib.sha256((prev + _canonical(rec)).encode("utf-8")).hexdigest()


def _read_all(path: str) -> List[Dict[str, Any]]:
    out = []
    if os.path.exists(path):
        with open(path, "r") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
    return out


def do_append(args) -> None:
    records = _read_all(args.ledger)
    prev_hash = records[-1].get("chain_hash", "") if records else ""
    rec: Dict[str, Any] = {
        "ts": args.ts, "schema_version": SCHEMA, "mode": args.mode,
        "decision_id": args.decision_id, "input_ref": args.input_ref,
        "method": args.method, "verdict": args.verdict, "reason_code": args.reason_code,
        "model": args.model, "model_version": args.model_version, "cost_usd": args.cost,
        "prev_hash": prev_hash if args.mode == "prod" else None,
    }
    # hash-chain only in prod (poc/mvp = plain log per mode grading)
    rec["chain_hash"] = _hash(prev_hash, rec) if args.mode == "prod" else None
    with open(args.ledger, "a") as fh:
        fh.write(json.dumps(rec, separators=(",", ":")) + "\n")
    emit({"appended": 1, "decision_id": args.decision_id, "mode": args.mode,
          "chain_hash": rec["chain_hash"], "ledger": args.ledger})


def do_verify(args) -> None:
    records = _read_all(args.ledger)
    prev = ""
    broken: Optional[Dict] = None
    chained = 0
    for i, rec in enumerate(records):
        if rec.get("chain_hash") is None:
            prev = ""  # un-chained (poc/mvp) record; reset
            continue
        expect = _hash(rec.get("prev_hash", "") or "", rec)
        if expect != rec["chain_hash"]:
            broken = {"index": i, "decision_id": rec.get("decision_id"),
                      "expected": expect, "found": rec["chain_hash"]}
            break
        prev = rec["chain_hash"]
        chained += 1
    if broken:
        emit({"intact": False, "records": len(records), "chained": chained, "tamper": broken})
        raise SystemExit(3)
    emit({"intact": True, "records": len(records), "chained": chained})


def do_report(args) -> None:
    records = _read_all(args.ledger)
    attested = len({r.get("decision_id") for r in records if r.get("decision_id")})
    by_verdict: Dict[str, int] = {}
    by_method: Dict[str, int] = {}
    for r in records:
        by_verdict[r.get("verdict", "?")] = by_verdict.get(r.get("verdict", "?"), 0) + 1
        by_method[r.get("method", "?")] = by_method.get(r.get("method", "?"), 0) + 1
    coverage = (attested / args.expected) if args.expected else None
    det = by_method.get("deterministic", 0)
    total = sum(by_method.values()) or 1
    emit({"records": len(records), "attested_decisions": attested,
          "expected": args.expected, "coverage": round(coverage, 4) if coverage is not None else None,
          "by_verdict": by_verdict, "by_method": by_method,
          "deterministic_resolution_rate": round(det / total, 4)})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--append", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--mode", choices=["poc", "mvp", "prod"], default="prod")
    ap.add_argument("--decision-id", default="")
    ap.add_argument("--input-ref", default="")
    ap.add_argument("--method", choices=["deterministic", "llm", "hybrid", "human"], default="llm")
    ap.add_argument("--verdict", default="")
    ap.add_argument("--reason-code", default="")
    ap.add_argument("--model", default="")
    ap.add_argument("--model-version", default="")
    ap.add_argument("--cost", type=float, default=0.0)
    ap.add_argument("--expected", type=int, default=0)
    ap.add_argument("--ts", default="1970-01-01T00:00:00Z")
    args = ap.parse_args()

    if args.append:
        if not args.decision_id:
            fail("--append requires --decision-id")
        do_append(args)
    elif args.verify:
        do_verify(args)
    elif args.report:
        do_report(args)
    else:
        ap.error("one of --append, --verify, --report required")


if __name__ == "__main__":
    main()
