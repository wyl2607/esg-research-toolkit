from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path("scripts/qa/verify_dashboard_stats.py")


def _run(payload: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )


def _empty_payload() -> dict[str, object]:
    return {
        "total_companies": 0,
        "avg_taxonomy_aligned": None,
        "avg_renewable_pct": None,
        "yearly_trend": [],
        "top_emitters": [],
        "bottom_emitters": [],
        "coverage_rates": {},
    }


def test_dashboard_stats_contract_preserves_unknown_averages() -> None:
    result = _run(_empty_payload())

    assert result.returncode == 0
    assert "OK dashboard stats shape" in result.stdout


@pytest.mark.parametrize(
    "mutator",
    [
        lambda payload: payload.pop("coverage_rates"),
        lambda payload: payload.update(total_companies=-1),
        lambda payload: payload.update(avg_renewable_pct="0"),
        lambda payload: payload.update(yearly_trend=[0]),
        lambda payload: payload.update(coverage_rates={"scope1": None}),
    ],
)
def test_dashboard_stats_contract_rejects_invalid_shapes(mutator) -> None:
    payload = _empty_payload()
    mutator(payload)

    result = _run(payload)

    assert result.returncode == 1
    assert "dashboard stats contract failed" in result.stderr
