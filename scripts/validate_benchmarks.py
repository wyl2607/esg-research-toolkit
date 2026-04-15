"""Validate integrity of precomputed benchmark rows stored in SQLite."""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "esg_toolkit.db"
PERCENTILE_COLUMNS = ("p10", "p25", "p50", "p75", "p90")


@dataclass(frozen=True)
class ValidationResult:
    rows_checked: int
    violations: list[dict[str, Any]]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate benchmark percentile integrity.")
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"SQLite DB path (default: {DEFAULT_DB_PATH})",
    )
    return parser.parse_args(argv)


def _to_finite_number(value: Any) -> tuple[float | None, str | None]:
    if isinstance(value, bool):
        return None, "not_numeric"

    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None, "not_numeric"

    if not math.isfinite(numeric):
        return None, "not_finite"

    return numeric, None


def validate_benchmark_rows(db_path: Path) -> ValidationResult:
    rows_checked = 0
    violations: list[dict[str, Any]] = []

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, industry_code, metric_name, period_year,
                   p10, p25, p50, p75, p90, sample_size
            FROM industry_benchmarks
            ORDER BY id ASC
            """
        ).fetchall()

    for row in rows:
        rows_checked += 1
        issues: list[str] = []

        finite_values: dict[str, float] = {}
        for column in (*PERCENTILE_COLUMNS, "sample_size"):
            value, error = _to_finite_number(row[column])
            if error is not None:
                issues.append(f"{column}_{error}")
                continue
            finite_values[column] = value

        sample_size = finite_values.get("sample_size")
        if sample_size is not None and sample_size < 1:
            issues.append("sample_size_lt_1")

        if all(column in finite_values for column in PERCENTILE_COLUMNS):
            p10 = finite_values["p10"]
            p25 = finite_values["p25"]
            p50 = finite_values["p50"]
            p75 = finite_values["p75"]
            p90 = finite_values["p90"]
            if not (p10 <= p25 <= p50 <= p75 <= p90):
                issues.append("percentile_order_invalid")

        if issues:
            violations.append(
                {
                    "id": row["id"],
                    "industry_code": row["industry_code"],
                    "metric_name": row["metric_name"],
                    "period_year": row["period_year"],
                    "issues": issues,
                    "values": {
                        "p10": row["p10"],
                        "p25": row["p25"],
                        "p50": row["p50"],
                        "p75": row["p75"],
                        "p90": row["p90"],
                        "sample_size": row["sample_size"],
                    },
                }
            )

    return ValidationResult(rows_checked=rows_checked, violations=violations)


def _print_summary(status: str, db_path: Path, rows_checked: int, violations: int, *, error: str | None = None) -> None:
    payload: dict[str, Any] = {
        "status": status,
        "db_path": str(db_path),
        "rows_checked": rows_checked,
        "violations": violations,
    }
    if error is not None:
        payload["error"] = error
    print("SUMMARY " + json.dumps(payload, sort_keys=True, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    db_path = args.db.expanduser().resolve()

    try:
        result = validate_benchmark_rows(db_path)
    except (sqlite3.Error, OSError) as exc:
        _print_summary("error", db_path, 0, 0, error=str(exc))
        return 2

    if not result.violations:
        _print_summary("ok", db_path, result.rows_checked, 0)
        return 0

    _print_summary("violations", db_path, result.rows_checked, len(result.violations))
    for violation in result.violations:
        print("VIOLATION " + json.dumps(violation, sort_keys=True, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
