"""Shared helpers for g-sales-* deterministic skills. Python 3.9 compatible."""
import json
import sys
from typing import Any


def emit(obj: Any) -> None:
    """Print one JSON object to stdout — the universal g-sales script contract."""
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
