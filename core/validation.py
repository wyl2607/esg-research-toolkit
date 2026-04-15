"""L0 physical-range validation for ESG metric values.

Catches obvious AI extraction errors **before** they enter benchmarks and
poison the percentile pipeline. This is the cheapest, most deterministic layer
in the multi-tier validation strategy:

    L0 (this file)   physical bounds           — runs every save
    L1 cross-year    delta sanity              — runs in nightly_burn.sh
    L2 cross-source  multi-PDF agreement       — runs when 2+ sources exist
    L3 AI audit      gpt-4o grading            — scripts/audit_extractions.py
    L4 outlier vs   industry percentile        — scripts/validate_benchmarks.py

Design rules:
- Pure functions, zero I/O, no DB dependency. Trivially unit-testable.
- Soft-fail by default: returns a list of issues, caller decides whether to raise.
- Bounds are intentionally loose — we want to catch hallucinations like
  "scope1 = 7,500,000,000,000" not borderline disclosure quality.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# ── Physical bounds ─────────────────────────────────────────────────────────
# Upper bounds chosen as "no single company on Earth has ever exceeded this".
# Aramco (largest single-firm scope1 emitter) ≈ 1.6 Gt CO2e; cap at 5 Gt.
# Walmart (largest electricity buyer) ≈ 23 TWh/yr; cap at 500 TWh.
METRIC_BOUNDS: dict[str, tuple[float, float]] = {
    # tonnes CO2-equivalent
    "scope1_co2e_tonnes": (0.0, 5_000_000_000.0),
    "scope2_co2e_tonnes": (0.0, 5_000_000_000.0),
    "scope3_co2e_tonnes": (0.0, 10_000_000_000.0),
    # MWh
    "energy_consumption_mwh": (0.0, 500_000_000.0),
    # m³
    "water_usage_m3": (0.0, 10_000_000_000.0),
    # percentages 0–100
    "renewable_energy_pct": (0.0, 100.0),
    "waste_recycled_pct": (0.0, 100.0),
    "taxonomy_aligned_revenue_pct": (0.0, 100.0),
    "taxonomy_aligned_capex_pct": (0.0, 100.0),
    "female_pct": (0.0, 100.0),
    # EUR — 5T cap covers Saudi Aramco scale
    "total_revenue_eur": (0.0, 5_000_000_000_000.0),
    "total_capex_eur": (0.0, 1_000_000_000_000.0),
    # headcount
    "total_employees": (0.0, 5_000_000.0),
}

# Year sanity: anything outside this window is almost certainly an extraction bug
# (e.g. AI grabbed a phone number or page count instead of a year).
YEAR_MIN = 1990
YEAR_MAX = 2030


@dataclass(frozen=True)
class ValidationIssue:
    field: str
    value: Any
    rule: str
    severity: str  # "error" | "warn"
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "value": self.value,
            "rule": self.rule,
            "severity": self.severity,
            "message": self.message,
        }


def validate_metric(field: str, value: Any) -> list[ValidationIssue]:
    """Validate a single metric against physical bounds.

    Returns empty list if value is None or passes all checks.
    """
    if value is None:
        return []
    issues: list[ValidationIssue] = []

    # type coercion
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return [
            ValidationIssue(
                field=field,
                value=value,
                rule="type",
                severity="error",
                message=f"{field} is not numeric: {value!r}",
            )
        ]

    if numeric != numeric:  # NaN check
        return [
            ValidationIssue(
                field=field, value=value, rule="nan", severity="error",
                message=f"{field} is NaN",
            )
        ]
    if numeric in (float("inf"), float("-inf")):
        return [
            ValidationIssue(
                field=field, value=value, rule="inf", severity="error",
                message=f"{field} is infinite",
            )
        ]

    bounds = METRIC_BOUNDS.get(field)
    if bounds is not None:
        lo, hi = bounds
        if numeric < lo:
            issues.append(
                ValidationIssue(
                    field=field, value=value, rule="below_min", severity="error",
                    message=f"{field}={numeric} below min {lo}",
                )
            )
        if numeric > hi:
            issues.append(
                ValidationIssue(
                    field=field, value=value, rule="above_max", severity="error",
                    message=f"{field}={numeric} above max {hi}",
                )
            )
    return issues


def validate_year(year: Any) -> list[ValidationIssue]:
    if year is None:
        return []
    try:
        y = int(year)
    except (TypeError, ValueError):
        return [
            ValidationIssue(
                field="report_year", value=year, rule="type", severity="error",
                message=f"report_year is not int: {year!r}",
            )
        ]
    if y < YEAR_MIN or y > YEAR_MAX:
        return [
            ValidationIssue(
                field="report_year", value=year, rule="range", severity="error",
                message=f"report_year={y} outside [{YEAR_MIN}, {YEAR_MAX}]",
            )
        ]
    return []


def validate_record(record: dict[str, Any]) -> list[ValidationIssue]:
    """Validate every metric field in a dict-shaped ESG record.

    `record` can be a Pydantic .model_dump() or a SQLAlchemy row dict.
    Unknown fields are ignored — only fields in METRIC_BOUNDS are checked.
    """
    issues: list[ValidationIssue] = []
    for field, bounds_value in METRIC_BOUNDS.items():
        del bounds_value  # unused, just iterating known fields
        if field in record:
            issues.extend(validate_metric(field, record[field]))
    if "report_year" in record:
        issues.extend(validate_year(record["report_year"]))

    # Cross-field sanity: scope2 should rarely exceed scope1 by 100x
    s1 = record.get("scope1_co2e_tonnes")
    s2 = record.get("scope2_co2e_tonnes")
    try:
        if s1 is not None and s2 is not None:
            s1f = float(s1)
            s2f = float(s2)
            if s1f > 0 and s2f > 0 and s2f > 100 * s1f:
                issues.append(
                    ValidationIssue(
                        field="scope2_co2e_tonnes", value=s2, rule="cross_field",
                        severity="warn",
                        message=f"scope2 ({s2f}) > 100× scope1 ({s1f}) — possible unit mix-up",
                    )
                )
    except (TypeError, ValueError):
        pass

    return issues


def has_errors(issues: list[ValidationIssue]) -> bool:
    return any(i.severity == "error" for i in issues)
