"""Unit tests for core/validation.py — L0 physical bounds checks."""
from __future__ import annotations

from core.validation import (
    METRIC_BOUNDS,
    has_errors,
    validate_metric,
    validate_record,
    validate_year,
)


def test_none_passes() -> None:
    assert validate_metric("scope1_co2e_tonnes", None) == []


def test_within_bounds_passes() -> None:
    assert validate_metric("scope1_co2e_tonnes", 1_000_000) == []
    assert validate_metric("renewable_energy_pct", 42.5) == []


def test_above_max_fails() -> None:
    issues = validate_metric("scope1_co2e_tonnes", 9e12)
    assert has_errors(issues)
    assert any(i.rule == "above_max" for i in issues)


def test_below_min_fails() -> None:
    issues = validate_metric("renewable_energy_pct", -5)
    assert has_errors(issues)
    assert any(i.rule == "below_min" for i in issues)


def test_pct_above_100_fails() -> None:
    issues = validate_metric("waste_recycled_pct", 250)
    assert has_errors(issues)


def test_string_numeric_value_fails() -> None:
    issues = validate_metric("scope1_co2e_tonnes", "not-a-number")
    assert has_errors(issues)
    assert issues[0].rule == "type"


def test_string_numeric_value_coerced() -> None:
    # JSON sometimes gives us "1234.5" — accept it
    assert validate_metric("scope1_co2e_tonnes", "1234.5") == []


def test_nan_fails() -> None:
    issues = validate_metric("scope1_co2e_tonnes", float("nan"))
    assert has_errors(issues)


def test_inf_fails() -> None:
    issues = validate_metric("scope1_co2e_tonnes", float("inf"))
    assert has_errors(issues)


def test_year_in_range() -> None:
    assert validate_year(2024) == []
    assert validate_year("2024") == []


def test_year_out_of_range() -> None:
    assert has_errors(validate_year(1900))
    assert has_errors(validate_year(2099))


def test_validate_record_clean() -> None:
    record = {
        "report_year": 2024,
        "scope1_co2e_tonnes": 1_000_000,
        "scope2_co2e_tonnes": 500_000,
        "renewable_energy_pct": 33,
    }
    assert validate_record(record) == []


def test_validate_record_catches_multiple_issues() -> None:
    record = {
        "report_year": 1800,
        "scope1_co2e_tonnes": 9e12,
        "renewable_energy_pct": 250,
    }
    issues = validate_record(record)
    assert len(issues) >= 3
    assert has_errors(issues)


def test_cross_field_scope2_dominance_warns() -> None:
    record = {
        "scope1_co2e_tonnes": 100,
        "scope2_co2e_tonnes": 100_000,  # 1000× scope1
    }
    issues = validate_record(record)
    assert any(i.rule == "cross_field" and i.severity == "warn" for i in issues)


def test_metric_bounds_table_complete() -> None:
    """Sentinel: every bound must be (low, high) with low < high."""
    for field, (lo, hi) in METRIC_BOUNDS.items():
        assert lo < hi, f"{field} has invalid bounds {lo}..{hi}"
