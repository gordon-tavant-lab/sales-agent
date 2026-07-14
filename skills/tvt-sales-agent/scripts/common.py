"""Shared helpers for tvt-sales-agent's deterministic scripts. Python 3.9 compatible."""
import json
import os
import sys
from typing import Any, Dict, List

import yaml

ROSTER_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "references",
    "roster.yml",
)


def emit(obj: Any) -> None:
    """Print one JSON object to stdout — the universal tvt-* script contract."""
    json.dump(obj, sys.stdout, separators=(",", ":"), default=_default)
    sys.stdout.write("\n")


def _default(o: Any) -> Any:
    if hasattr(o, "item"):
        try:
            return o.item()
        except Exception:
            pass
    if hasattr(o, "tolist"):
        return o.tolist()
    raise TypeError("not JSON serializable: {}".format(type(o)))


def fail(msg: str, code: int = 2) -> None:
    json.dump({"error": msg}, sys.stderr)
    sys.stderr.write("\n")
    sys.exit(code)


def load_roster(path: str = ROSTER_PATH) -> Dict[str, Any]:
    """Load roster.yml. Raises if the file is missing or malformed — a broken roster
    must fail loudly, never dispatch against a partial/empty capability list."""
    with open(path, "r") as fh:
        data = yaml.safe_load(fh)
    if not data or "capabilities" not in data:
        raise ValueError("roster.yml missing 'capabilities' key: {}".format(path))
    slugs = [c["capability_slug"] for c in data["capabilities"]]
    if len(slugs) != len(set(slugs)):
        raise ValueError("roster.yml has duplicate capability_slug entries")
    return data


def known_slugs(roster: Dict[str, Any]) -> List[str]:
    return [c["capability_slug"] for c in roster["capabilities"]]
