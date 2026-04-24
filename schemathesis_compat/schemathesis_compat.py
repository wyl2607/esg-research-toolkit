"""Schemathesis v3 → v4 CLI compatibility shim.

Translates deprecated v3 CLI flags to their v4 equivalents so that
existing CI workflows continue to work after the schemathesis 4.x upgrade.

Removed flags (silently dropped):
  --experimental <value>               (OpenAPI 3.1 is default in v4)
  --contrib-openapi-fill-missing-examples
  --hypothesis-derandomize

Renamed flags:
  --hypothesis-max-examples → --max-examples
  --base-url                → --url
"""
from __future__ import annotations

import sys

# Flags whose next argument should also be dropped (flag + value pairs)
_DROP_WITH_VALUE: frozenset[str] = frozenset(["--experimental"])

# Standalone flags to drop (no associated value)
_DROP_STANDALONE: frozenset[str] = frozenset([
    "--contrib-openapi-fill-missing-examples",
    "--hypothesis-derandomize",
])

# Flag renames: old name → new name (value is kept unchanged)
_RENAMES: dict[str, str] = {
    "--hypothesis-max-examples": "--max-examples",
    "--base-url": "--url",
}


def _translate(argv: list[str]) -> list[str]:
    result: list[str] = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in _DROP_WITH_VALUE:
            i += 2  # drop flag and its value
            continue
        if arg in _DROP_STANDALONE:
            i += 1
            continue
        if arg in _RENAMES:
            result.append(_RENAMES[arg])
            i += 1
            continue
        result.append(arg)
        i += 1
    return result


def main() -> None:
    sys.argv = [sys.argv[0]] + _translate(sys.argv[1:])
    import re
    from schemathesis.cli import schemathesis
    sys.argv[0] = re.sub(r"(-script\.pyw|\.exe)?$", "", sys.argv[0])
    sys.exit(schemathesis())
