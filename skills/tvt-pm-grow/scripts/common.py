"""Shared helpers for the tvt-pm-grow deterministic chain. Python 3.9 compatible."""
import json
import sys
from typing import Any, Dict, Optional


def emit(obj: Any) -> None:
    """Print one JSON object to stdout — the universal script contract."""
    json.dump(obj, sys.stdout, separators=(",", ":"), default=_default)
    sys.stdout.write("\n")


def _default(o: Any) -> Any:
    # numpy scalar / array friendliness without a hard import.
    if hasattr(o, "item"):
        try:
            return o.item()
        except Exception:
            pass
    if hasattr(o, "tolist"):
        return o.tolist()
    raise TypeError("not JSON serializable: {}".format(type(o)))


def fail(msg: str, code: int = 2) -> None:
    """Hard error → JSON to stderr + nonzero exit, so callers can detect failure."""
    json.dump({"error": msg}, sys.stderr)
    sys.stderr.write("\n")
    sys.exit(code)


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r") as fh:
        return json.load(fh)


def read_stdin_json() -> Optional[Dict[str, Any]]:
    data = sys.stdin.read().strip()
    return json.loads(data) if data else None


def clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))
