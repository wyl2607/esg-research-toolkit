from __future__ import annotations

import ast
from datetime import date
from pathlib import Path

from core.normalization.period import normalize_reporting_period


def test_reporting_period_behavior_gate_preserves_current_contract() -> None:
    cases = [
        (
            {
                "fiscal_year": 2024,
                "reporting_period_label": "FY2024 Q2",
                "reporting_period_type": "annual",
                "source_document_type": "sustainability_report",
            },
            (date(2024, 4, 1), date(2024, 6, 30), "sustainability_report"),
        ),
        (
            {
                "fiscal_year": 2024,
                "reporting_period_label": "2024 2H",
                "reporting_period_type": None,
            },
            (date(2024, 7, 1), date(2024, 12, 31), "unknown"),
        ),
        (
            {
                "fiscal_year": 2024,
                "reporting_period_label": "",
                "reporting_period_type": "quarterly",
            },
            (date(2024, 10, 1), date(2024, 12, 31), "unknown"),
        ),
        (
            {
                "fiscal_year": 2024,
                "reporting_period_label": "FY2024",
                "reporting_period_type": "yearly",
            },
            (date(2024, 1, 1), date(2024, 12, 31), "unknown"),
        ),
        (
            {
                "fiscal_year": 2024,
                "reporting_period_label": "FY2024",
                "reporting_period_type": "event",
            },
            (None, None, "unknown"),
        ),
    ]

    for kwargs, expected in cases:
        period = normalize_reporting_period(**kwargs)
        assert period.fiscal_year == kwargs["fiscal_year"]
        assert (period.period_start, period.period_end, period.reporting_standard) == expected


def test_reporting_period_quality_gate_uses_data_driven_bounds() -> None:
    source = Path("core/normalization/period.py").read_text()
    tree = ast.parse(source)

    assert "QUARTER_BOUNDS" in source
    assert "HALF_YEAR_BOUNDS" in source
    assert "ANNUAL_PERIOD_TYPES" in source
    assert "_quarter_bounds" not in source
    assert "_half_year_bounds" not in source

    function_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    assert "_resolve_period_bounds" in function_names
