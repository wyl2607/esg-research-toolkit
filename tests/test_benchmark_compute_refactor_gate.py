from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

from benchmark.compute import BENCHMARK_METRICS, recompute_industry_benchmarks
from benchmark.models import IndustryBenchmark
from report_parser.storage import CompanyReport


class _RowsQuery:
    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self._rows = rows

    def filter(self, *_args, **_kwargs):
        return self

    def all(self) -> list[SimpleNamespace]:
        return self._rows


class _DeleteQuery:
    def filter(self, *_args, **_kwargs):
        return self

    def delete(self, *_args, **_kwargs):
        return None


class _FakeSession:
    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self._rows = rows
        self.added: list[IndustryBenchmark] = []

    def query(self, model):
        if model is CompanyReport:
            return _RowsQuery(self._rows)
        if model is IndustryBenchmark:
            return _DeleteQuery()
        raise AssertionError(f"Unexpected model query: {model}")

    def add_all(self, rows) -> None:
        self.added = list(rows)

    def commit(self) -> None:
        return None


def _row(**overrides) -> SimpleNamespace:
    values = {metric: None for metric in BENCHMARK_METRICS}
    values.update(
        {
            "company_name": "Benchmark Co",
            "report_year": 2024,
            "industry_code": "D35.11",
        }
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def test_recompute_benchmark_behavior_gate_filters_invalid_metric_values() -> None:
    fake_db = _FakeSession(
        [
            _row(company_name="Valid", scope1_co2e_tonnes=100.0),
            _row(company_name="NumericString", scope1_co2e_tonnes="200.0"),
            _row(company_name="NoneValue", scope1_co2e_tonnes=None),
            _row(company_name="BadString", scope1_co2e_tonnes="not-a-number"),
            _row(company_name="NanValue", scope1_co2e_tonnes=float("nan")),
            _row(company_name="NoIndustry", industry_code=None, scope1_co2e_tonnes=300.0),
            _row(company_name="NoYear", report_year=None, scope1_co2e_tonnes=400.0),
        ]
    )

    summary = recompute_industry_benchmarks(fake_db)

    assert summary == {"industries": 1, "metric_rows": 1}
    assert len(fake_db.added) == 1
    row = fake_db.added[0]
    assert row.metric_name == "scope1_co2e_tonnes"
    assert row.sample_size == 2
    assert row.p50 == 150.0


def test_recompute_benchmark_quality_gate_extracts_metric_coercion_helper() -> None:
    source = Path("benchmark/compute.py").read_text()
    tree = ast.parse(source)

    function_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    assert "_coerce_benchmark_value" in function_names

    recompute = next(
        node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "recompute_industry_benchmarks"
    )
    recompute_calls = {
        node.func.id
        for node in ast.walk(recompute)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "_coerce_benchmark_value" in recompute_calls
    assert "float" not in recompute_calls
