#!/usr/bin/env python3
"""Validate the dashboard stats response without coercing unknown values to zero."""

from __future__ import annotations

import json
import math
import sys
from collections.abc import Mapping
from typing import Any

_REQUIRED_KEYS = {
    "total_companies",
    "avg_taxonomy_aligned",
    "avg_renewable_pct",
    "yearly_trend",
    "top_emitters",
    "bottom_emitters",
    "coverage_rates",
}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate_payload(payload: Any) -> None:
    if not isinstance(payload, Mapping):
        raise ValueError("dashboard stats payload must be a JSON object")

    missing = sorted(_REQUIRED_KEYS.difference(payload))
    if missing:
        raise ValueError(f"dashboard stats payload missing keys: {', '.join(missing)}")

    total_companies = payload["total_companies"]
    if not isinstance(total_companies, int) or isinstance(total_companies, bool) or total_companies < 0:
        raise ValueError("total_companies must be a non-negative integer")

    # None means the average is undefined for an empty or incomplete dataset.
    # It must remain distinct from a measured 0.0.
    for key in ("avg_taxonomy_aligned", "avg_renewable_pct"):
        value = payload[key]
        if value is not None and not _is_number(value):
            raise ValueError(f"{key} must be a finite number or null")

    for key in ("yearly_trend", "top_emitters", "bottom_emitters"):
        value = payload[key]
        if not isinstance(value, list) or any(not isinstance(item, Mapping) for item in value):
            raise ValueError(f"{key} must be a list of objects")

    coverage_rates = payload["coverage_rates"]
    if not isinstance(coverage_rates, Mapping):
        raise ValueError("coverage_rates must be an object")
    if any(not isinstance(key, str) or not _is_number(value) for key, value in coverage_rates.items()):
        raise ValueError("coverage_rates values must be finite numbers")


def main() -> int:
    try:
        validate_payload(json.load(sys.stdin))
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"dashboard stats contract failed: {exc}", file=sys.stderr)
        return 1
    print("OK dashboard stats shape")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
