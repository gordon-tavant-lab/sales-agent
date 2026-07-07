#!/usr/bin/env python3
"""guard.py — deterministic AI guardrail: PII redaction, injection filter, schema validation,
refusal handling. Runs in the AI call path AND as a pre-commit/pre-deploy gate.

Mode-graded (spec 004 §2):
  poc  → PII redaction ON; injection/schema = warn (planned, not enforced)
  mvp  → + injection + schema enforced (fail-closed)
  prod → full enforcement, fail-closed on any block

Usage:
  # check input text (inputs get PII + injection scan)
  python scripts/guard.py --check input  --text "@infile.txt"  --mode prod
  # check output text against a schema (outputs get PII + refusal + schema)
  python scripts/guard.py --check output --text '{"verdict":"pass"}' --schema schema.json --mode mvp

Output (stdout): one JSON verdict:
  {"verdict":"pass|redacted|blocked","mode":..,"findings":[..],"redacted_text":..,"enforced":bool}
Exit: 0 = pass/redacted; 3 = blocked (fail-closed in mvp/prod). poc never exits nonzero on a block
(it warns), per the "considered and planned" rule.
"""
import argparse
import json
import os
import re
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    import sys as _s
    json.dump({"error": "pyyaml not installed; pip install -r scripts/requirements.txt"}, _s.stderr)
    _s.exit(2)

from common import emit, fail, read_text_arg

HERE = os.path.dirname(os.path.abspath(__file__))


def load_patterns() -> Dict[str, Any]:
    # workspace override wins, else bundled
    override = os.path.join(os.environ.get("CLAUDE_PROJECT_DIR", ""), ".claude", "gov-patterns.yml")
    path = override if os.path.exists(override) else os.path.join(HERE, "patterns.yml")
    with open(path, "r") as fh:
        return yaml.safe_load(fh)


def redact_pii(text: str, patterns: List[Dict]) -> (str, List[Dict]):
    findings = []
    out = text
    for p in patterns:
        rx = re.compile(p["pattern"])
        matches = list(rx.finditer(out))
        if matches:
            findings.append({"type": "pii", "id": p["id"], "category": p.get("category"),
                             "count": len(matches), "severity": p.get("severity", "redact")})
            out = rx.sub(p.get("placeholder", "<REDACTED>"), out)
    return out, findings


def scan(text: str, patterns: List[Dict], kind: str) -> List[Dict]:
    findings = []
    for p in patterns:
        if re.search(p["pattern"], text):
            findings.append({"type": kind, "id": p["id"], "severity": "block" if kind == "injection" else "info"})
    return findings


def validate_schema(text: str, schema_path: str) -> List[Dict]:
    """Minimal, dependency-free JSON-schema check: valid JSON + required keys + top-level types."""
    findings = []
    try:
        obj = json.loads(text)
    except Exception as e:
        return [{"type": "schema", "id": "invalid_json", "severity": "block", "detail": str(e)}]
    with open(schema_path) as fh:
        schema = json.load(fh)
    for key in schema.get("required", []):
        if not (isinstance(obj, dict) and key in obj):
            findings.append({"type": "schema", "id": "missing_required", "severity": "block", "field": key})
    props = schema.get("properties", {})
    if isinstance(obj, dict):
        for key, spec in props.items():
            if key in obj and "type" in spec:
                want = spec["type"]
                ok = {
                    "string": str, "number": (int, float), "integer": int,
                    "boolean": bool, "object": dict, "array": list,
                }.get(want, object)
                if not isinstance(obj[key], ok):
                    findings.append({"type": "schema", "id": "type_mismatch", "severity": "block",
                                     "field": key, "want": want})
    return findings


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", choices=["input", "output"], required=True)
    ap.add_argument("--text", required=True, help="inline text or @path")
    ap.add_argument("--schema", default="", help="JSON schema path (output checks)")
    ap.add_argument("--mode", choices=["poc", "mvp", "prod"], default="prod")
    args = ap.parse_args()

    text = read_text_arg(args.text)
    pats = load_patterns()
    enforced = args.mode in ("mvp", "prod")

    findings: List[Dict] = []
    redacted: Optional[str] = None

    # PII redaction always runs (every mode)
    redacted, pii = redact_pii(text, pats.get("pii_patterns", []))
    findings += pii

    blocking = False
    if args.check == "input":
        inj = scan(text, pats.get("injection_patterns", []), "injection")
        findings += inj
        if inj and enforced:
            blocking = True
    else:  # output
        findings += scan(text, pats.get("refusal_patterns", []), "refusal")
        if args.schema:
            sch = validate_schema(text, args.schema)
            findings += sch
            if any(f["severity"] == "block" for f in sch) and enforced:
                blocking = True

    if blocking:
        verdict = "blocked"
    elif pii:
        verdict = "redacted"
    else:
        verdict = "pass"

    emit({"verdict": verdict, "mode": args.mode, "enforced": enforced,
          "findings": findings, "redacted_text": redacted,
          "planned_not_enforced": (not enforced) and bool(
              [f for f in findings if f["severity"] == "block"])})

    # fail-closed only when enforced; poc warns (exit 0) per "considered and planned"
    if blocking and enforced:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
