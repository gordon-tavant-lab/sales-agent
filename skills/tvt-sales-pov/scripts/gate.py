#!/usr/bin/env python3
"""gate.py — risk-tiered evidence-verification gate (spec 006 §7, job 5).

Deterministic. Classifies transcript-extracted claims (MEDDPICC dimension evidence, POV
validated/refuted/refined judgments) into two lanes:

  - auto_attest: unambiguous, high-confidence, doesn't contradict the existing account record.
    Safe to write to the append-only tvt-gov-attest ledger immediately.
  - queue: everything else. Must sit in a PENDING queue and wait for a one-tap human confirm
    event before the orchestrating skill calls tvt-gov-attest --append. Nothing this script
    classifies "queue" may reach the ledger without that confirm.

This script never talks to tvt-gov-attest itself — it only produces the verdict + reason_code
that the orchestrating skill (tvt-sales-pov) pairs with a decision-id/input-ref when it calls
`attest.py --append`. Keeping the boundary here means the gate is testable in isolation from
the ledger.

Rationale (spec §7): conversation-intelligence extraction hallucinates in >1/3 of cases even
under good audio. A poisoned attest ledger corrupts the §5 backtest substrate *permanently*
(the ledger is append-only), so quality is enforced at this gate, not repaired later. A flat
"confirm all" queue just relocates the friction it was built to remove (cross-family panel
finding, 2026-07-02) — so only low-confidence/contradicting claims are queued; the rest
auto-attest, keeping the queue small enough that each item is a genuine judgment call.

Two source paths, two threat models (F7, added 2026-07-06): the confidence-threshold tiering
above is the right defense against a machine EXTRACTOR that hallucinates — but the primary path
today is a human typing `claims.json` by hand (Notion auto-extraction is deferred, not built).
On that path the author IS the verifier by construction; forcing them to invent an
`extraction_confidence` number for their own typed claim adds exactly the friction §7 says the
gate must not add, while defending against a hallucination source (a machine extractor) that
isn't present. `--source manual` auto-attests with `AUTHOR_ATTESTED` and no confidence number
required; `--source extracted` (default) keeps the full tiered gate for when auto-extraction
ships. Both paths still queue on `contradicts_prior` — that's a real signal check, not an
extraction-hallucination defense, so it applies regardless of source.

Queue-state persistence (F11, added 2026-07-06): `elapsed_seconds` for the abuse-rate KPI used
to be typed in by the person being policed. `--classify --queue-file Q` now appends every queued
claim to Q with a `queued_at` timestamp; `--confirm-queue --queue-file Q --claim-ids ...` computes
elapsed time itself (now minus the oldest matched claim's `queued_at`), removes the confirmed
claims from Q, and appends the confirmation event to `--abuse-log` (JSONL) — which also reports
the accumulated abuse rate across every confirmation event ever logged, not just this one.

Usage:
  # classify one batch of hand-typed claims (primary path)
  python gate.py --classify --claims-file claims.json --source manual --queue-file queue.jsonl

  # classify one batch of machine-extracted claims (deferred path, tiered gate applies)
  python gate.py --classify --claims-file claims.json --source extracted --queue-file queue.jsonl

  # confirm queued claims — elapsed time computed from the queue, not self-reported
  python gate.py --confirm-queue --queue-file queue.jsonl --claim-ids c,d --abuse-log abuse.jsonl

  # score a confirmation event directly, given an already-known elapsed time (unit-test / composition path)
  python gate.py --confirm --n-items 5 --elapsed-seconds 4.2

  # sum confirmed MEDDPICC dimension evidence into the /24 score
  python gate.py --aggregate-meddpicc --dims-file dims.json

Claim JSON shape (see claims.example.json):
  {"claim_id": "...", "type": "meddpicc_dimension"|"pov_validation", "extraction_confidence": 0-1,
   "contradicts_prior": bool, ...free-form evidence fields}

Output: one JSON object to stdout.
"""
import argparse
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from common import emit, fail

# "Unambiguous named metric/dimension, matches existing account context" (spec §7) — the
# threshold above which an extraction auto-attests. Retune if the confirm-all-abuse-rate KPI
# climbs (spec §7 anti-rubber-stamp design note).
HIGH_CONFIDENCE_THRESHOLD = 0.85

# Plausible per-item read time for a confirmation batch. A batch confirmed faster than
# max(MIN_PLAUSIBLE_SECONDS, n_items * SECONDS_PER_ITEM) is flagged as rubber-stamping.
SECONDS_PER_ITEM = 2.0
MIN_PLAUSIBLE_SECONDS = 3.0

# MEDDPICC aggregation mirrors tvt-sales-prospect/scripts/score.py's meddpicc_score exactly.
# Spec §5 is the single source of truth for the formula; duplicated here (not cross-imported)
# per the self-contained-skill convention — see spec 007 rationale.
MEDDPICC_DIMENSIONS = (
    "metrics", "economic_buyer", "decision_criteria", "decision_process",
    "paper_process", "identify_pain", "champion", "competition",
)
MEDDPICC_MAX = 3 * len(MEDDPICC_DIMENSIONS)  # 24


SOURCES = ("manual", "extracted")


def classify_claim(claim: Dict[str, Any], source: str = "extracted") -> Dict[str, Any]:
    if source not in SOURCES:
        raise ValueError("source must be one of {}, got {!r}".format(SOURCES, source))
    contradicts = bool(claim.get("contradicts_prior", False))

    if source == "manual":
        # The author typed this claim themselves — they are the verifier. No confidence
        # number to invent. Contradiction is still a real signal, not an extraction defense.
        if contradicts:
            decision, reason_code = "queue", "CONTRADICTS_PRIOR"
        else:
            decision, reason_code = "auto_attest", "AUTHOR_ATTESTED"
        return {
            "claim_id": claim.get("claim_id"),
            "decision": decision,
            "reason_code": reason_code,
            "method": "manual",
            "contradicts_prior": contradicts,
        }

    confidence = claim.get("extraction_confidence")
    if confidence is None:
        raise ValueError(
            "claim {} missing extraction_confidence (required for source=extracted)".format(
                claim.get("claim_id", "?"))
        )
    if not (0.0 <= confidence <= 1.0):
        raise ValueError("extraction_confidence must be 0-1, got {}".format(confidence))

    if confidence >= HIGH_CONFIDENCE_THRESHOLD and not contradicts:
        decision = "auto_attest"
        reason_code = "HIGH_CONFIDENCE_NONCONTRADICTING"
    elif contradicts:
        decision = "queue"
        reason_code = "CONTRADICTS_PRIOR"
    else:
        decision = "queue"
        reason_code = "LOW_CONFIDENCE"

    return {
        "claim_id": claim.get("claim_id"),
        "decision": decision,
        "reason_code": reason_code,
        "method": "extracted",
        "extraction_confidence": confidence,
        "contradicts_prior": contradicts,
    }


def classify_batch(claims: List[Dict[str, Any]], source: str = "extracted") -> Dict[str, Any]:
    verdicts = [classify_claim(c, source=source) for c in claims]
    auto_attested = [v for v in verdicts if v["decision"] == "auto_attest"]
    queued = [v for v in verdicts if v["decision"] == "queue"]
    return {
        "auto_attested": auto_attested,
        "queued": queued,
        "counts": {
            "total": len(verdicts),
            "auto_attested": len(auto_attested),
            "queued": len(queued),
        },
    }


def plausible_min_seconds(n_items: int) -> float:
    return max(MIN_PLAUSIBLE_SECONDS, n_items * SECONDS_PER_ITEM)


def score_confirmation(n_items: int, elapsed_seconds: float) -> Dict[str, Any]:
    if n_items <= 0:
        raise ValueError("n_items must be positive")
    if elapsed_seconds < 0:
        raise ValueError("elapsed_seconds must be non-negative")
    minimum = plausible_min_seconds(n_items)
    return {
        "n_items": n_items,
        "elapsed_seconds": elapsed_seconds,
        "plausible_min_seconds": minimum,
        "abuse_flag": elapsed_seconds < minimum,
    }


def aggregate_meddpicc(confirmed_dims: Dict[str, int]) -> Dict[str, Any]:
    """Sums only CONFIRMED per-dimension evidence — never a dimension still in the queue.
    Missing dimensions score 0 (not yet evidenced); an unconfirmed claim must not inflate
    the /24 score."""
    for d, v in confirmed_dims.items():
        if d not in MEDDPICC_DIMENSIONS:
            raise ValueError("unknown MEDDPICC dimension: {}".format(d))
        if not (0 <= v <= 3):
            raise ValueError("dimension {} must score 0-3, got {}".format(d, v))
    missing = [d for d in MEDDPICC_DIMENSIONS if d not in confirmed_dims]
    raw = sum(confirmed_dims.get(d, 0) for d in MEDDPICC_DIMENSIONS)
    return {
        "meddpicc_raw": raw,
        "meddpicc_max": MEDDPICC_MAX,
        "dimensions_confirmed": len(confirmed_dims),
        "dimensions_missing": missing,
    }


def _load(path: str) -> Any:
    with open(path, "r") as fh:
        return json.load(fh)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_jsonl(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, "r") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _write_jsonl(path: str, rows: List[Dict[str, Any]]) -> None:
    with open(path, "w") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def _append_jsonl(path: str, row: Dict[str, Any]) -> None:
    with open(path, "a") as fh:
        fh.write(json.dumps(row) + "\n")


def enqueue(queue_path: str, batch: Dict[str, Any], claims_by_id: Dict[str, Dict[str, Any]]) -> int:
    """Append every queued verdict from a classify_batch() result to the queue JSONL, stamped
    with queued_at. Returns the count appended. Idempotent per claim_id is NOT guaranteed —
    callers should not re-classify the same claims-file against the same queue twice."""
    appended = 0
    for v in batch["queued"]:
        row = dict(v)
        row["queued_at"] = _now_iso()
        row["claim"] = claims_by_id.get(v["claim_id"], {})
        _append_jsonl(queue_path, row)
        appended += 1
    return appended


def confirm_queue(queue_path: str, claim_ids: List[str]) -> Dict[str, Any]:
    """Pull the named claim_ids out of the queue, compute elapsed time from the OLDEST
    matched entry's queued_at to now (not self-reported), and return the confirmation result
    plus the still-pending queue (caller persists both)."""
    rows = _read_jsonl(queue_path)
    matched = [r for r in rows if r.get("claim_id") in claim_ids]
    remaining = [r for r in rows if r.get("claim_id") not in claim_ids]
    if not matched:
        raise ValueError("none of the given claim_ids are in the queue: {}".format(claim_ids))
    missing = set(claim_ids) - {r["claim_id"] for r in matched}
    oldest = min(datetime.fromisoformat(r["queued_at"]) for r in matched)
    elapsed = (datetime.now(timezone.utc) - oldest).total_seconds()
    result = score_confirmation(len(matched), elapsed)
    result["claim_ids"] = [r["claim_id"] for r in matched]
    result["confirmed_at"] = _now_iso()
    if missing:
        result["not_in_queue"] = sorted(missing)
    return {"result": result, "remaining_queue": remaining}


def accumulated_abuse_rate(abuse_log_path: str) -> Dict[str, Any]:
    """The accumulated (all-time) confirm-all-abuse-rate KPI — the retuning signal spec §7
    names, computed from every confirmation event ever logged, not just the latest one."""
    events = _read_jsonl(abuse_log_path)
    if not events:
        return {"n_events": 0, "n_flagged": 0, "abuse_rate": None}
    flagged = sum(1 for e in events if e.get("abuse_flag"))
    return {
        "n_events": len(events),
        "n_flagged": flagged,
        "abuse_rate": round(flagged / len(events), 4),
    }


def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--classify", action="store_true")
    p.add_argument("--claims-file")
    p.add_argument("--source", choices=SOURCES, default="extracted",
                   help="manual = author-attested, no confidence number needed (F7 primary "
                   "path); extracted = the tiered confidence gate (default, deferred path)")
    p.add_argument("--queue-file", help="JSONL; --classify appends queued claims here with "
                   "a queued_at timestamp (F11)")
    p.add_argument("--confirm", action="store_true",
                   help="score a confirmation event given an already-known elapsed time "
                   "(unit-test / composition path — prefer --confirm-queue in practice)")
    p.add_argument("--n-items", type=int)
    p.add_argument("--elapsed-seconds", type=float)
    p.add_argument("--confirm-queue", action="store_true",
                   help="pull --claim-ids out of --queue-file, computing elapsed time from "
                   "the queue itself rather than a self-reported number (F11)")
    p.add_argument("--claim-ids", help="comma-separated claim_ids to confirm")
    p.add_argument("--abuse-log", help="JSONL; --confirm-queue appends here and the output "
                   "reports the accumulated all-time abuse rate")
    p.add_argument("--aggregate-meddpicc", action="store_true")
    p.add_argument("--dims-file", help="JSON object: {dimension: score(0-3), ...}, confirmed only")
    args = p.parse_args()

    try:
        if args.classify:
            if not args.claims_file:
                fail("--classify requires --claims-file")
            claims = _load(args.claims_file)
            batch = classify_batch(claims, source=args.source)
            if args.queue_file:
                claims_by_id = {c.get("claim_id"): c for c in claims}
                n = enqueue(args.queue_file, batch, claims_by_id)
                batch["queued_to_file"] = args.queue_file
                batch["n_appended_to_queue"] = n
            emit(batch)
        elif args.confirm_queue:
            if not args.queue_file or not args.claim_ids:
                fail("--confirm-queue requires --queue-file and --claim-ids")
            ids = [c.strip() for c in args.claim_ids.split(",") if c.strip()]
            outcome = confirm_queue(args.queue_file, ids)
            _write_jsonl(args.queue_file, outcome["remaining_queue"])
            result = outcome["result"]
            if args.abuse_log:
                _append_jsonl(args.abuse_log, result)
                result["accumulated"] = accumulated_abuse_rate(args.abuse_log)
            emit(result)
        elif args.confirm:
            if args.n_items is None or args.elapsed_seconds is None:
                fail("--confirm requires --n-items and --elapsed-seconds")
            emit(score_confirmation(args.n_items, args.elapsed_seconds))
        elif args.aggregate_meddpicc:
            if not args.dims_file:
                fail("--aggregate-meddpicc requires --dims-file")
            emit(aggregate_meddpicc(_load(args.dims_file)))
        else:
            fail("specify --classify, --confirm-queue, --confirm, or --aggregate-meddpicc")
    except (ValueError, KeyError, FileNotFoundError, json.JSONDecodeError) as e:
        fail(str(e))


if __name__ == "__main__":
    main()
