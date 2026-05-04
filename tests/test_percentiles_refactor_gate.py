from __future__ import annotations

import ast
from pathlib import Path

from benchmark.percentiles import clean_numeric_values, five_point_summary, percentile


def test_percentile_summary_behavior_gate_preserves_current_contract() -> None:
    assert percentile([], 0.5) is None
    assert percentile([5.0], 0.5) == 5.0
    assert percentile([1.0, 2.0, 3.0, 4.0, 5.0], 0.25) == 2.0
    assert percentile([1.0, 2.0, 3.0, 4.0, 5.0], 0.50) == 3.0
    assert percentile([1.0, 2.0, 3.0, 4.0, 5.0], 0.75) == 4.0

    summary = five_point_summary([10, None, 20, float("nan"), 30, 40, 50])
    assert summary == {
        "p10": 14.0,
        "p25": 20.0,
        "p50": 30.0,
        "p75": 40.0,
        "p90": 46.0,
    }


def test_percentile_summary_quality_gate_is_table_driven() -> None:
    source = Path("benchmark/percentiles.py").read_text()
    tree = ast.parse(source)

    assert "SUMMARY_QUANTILES" in source

    function = next(
        node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "five_point_summary"
    )
    dict_nodes = [node for node in ast.walk(function) if isinstance(node, ast.Dict)]
    assert len(dict_nodes) == 0, "five_point_summary should build from SUMMARY_QUANTILES, not a hand-written dict"


def test_percentile_summary_quality_gate_centralizes_numeric_cleaning() -> None:
    assert clean_numeric_values([10, None, "20.5", "bad", float("nan")]) == [
        10.0,
        20.5,
    ]

    source = Path("benchmark/percentiles.py").read_text()
    tree = ast.parse(source)

    function_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    assert "clean_numeric_values" in function_names

    summary = next(
        node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "five_point_summary"
    )
    summary_calls = {
        node.func.id
        for node in ast.walk(summary)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "clean_numeric_values" in summary_calls
