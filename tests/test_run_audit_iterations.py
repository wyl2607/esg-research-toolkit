from __future__ import annotations

import datetime as dt
from argparse import Namespace

from scripts.run_audit_iterations import (
    IterationResult,
    build_audit_command,
    evaluate_iteration_result,
    parse_summary_text,
)


def test_parse_summary_text_collects_verdicts_and_errors() -> None:
    summary = parse_summary_text(
        """# Extraction Audit - Summary

Total companies: 10
Total fields audited: 90

| Verdict | Count |
|---|---|
| correct | 5 |
| incorrect | 26 |
| missed | 3 |
| not_disclosed | 56 |

## Errors
- RWE AG: dry-run
- BASF SE: openai: timeout

## Per-company reports
- [RWE AG](./rwe-2024.md) - failed (dry-run)
"""
    )

    assert summary.total_companies == 10
    assert summary.total_fields == 90
    assert summary.verdict_counts == {
        "correct": 5,
        "incorrect": 26,
        "missed": 3,
        "not_disclosed": 56,
    }
    assert summary.error_count == 2
    assert summary.non_dry_run_error_count == 1


def test_evaluate_iteration_fails_when_summary_has_non_dry_run_errors() -> None:
    summary = parse_summary_text(
        """# Extraction Audit - Summary

Total companies: 1
Total fields audited: 9

| Verdict | Count |
|---|---|
| correct | 9 |
| incorrect | 0 |
| missed | 0 |
| not_disclosed | 0 |

## Errors
- BASF SE: parse: invalid JSON
"""
    )

    result = IterationResult(
        index=1,
        command=["python", "scripts/audit_extractions.py"],
        return_code=0,
        duration_seconds=1.2,
        started_at=dt.datetime(2026, 4, 15, tzinfo=dt.timezone.utc),
        summary=summary,
    )

    evaluation = evaluate_iteration_result(result)
    assert evaluation.passed is False
    assert any("non-dry-run" in reason for reason in evaluation.reasons)


def test_evaluate_iteration_allows_dry_run_summary_errors_when_subprocess_passes() -> None:
    summary = parse_summary_text(
        """# Extraction Audit - Summary

Total companies: 2
Total fields audited: 0

| Verdict | Count |
|---|---|
| correct | 0 |
| incorrect | 0 |
| missed | 0 |
| not_disclosed | 0 |

## Errors
- RWE AG: dry-run
- BASF SE: dry-run
"""
    )

    result = IterationResult(
        index=2,
        command=["python", "scripts/audit_extractions.py", "--dry-run"],
        return_code=0,
        duration_seconds=0.7,
        started_at=dt.datetime(2026, 4, 15, tzinfo=dt.timezone.utc),
        summary=summary,
    )

    evaluation = evaluate_iteration_result(result)
    assert evaluation.passed is True
    assert evaluation.reasons == []


def test_evaluate_iteration_fails_on_non_zero_exit() -> None:
    summary = parse_summary_text(
        """# Extraction Audit - Summary

Total companies: 1
Total fields audited: 9

| Verdict | Count |
|---|---|
| correct | 9 |
| incorrect | 0 |
| missed | 0 |
| not_disclosed | 0 |
"""
    )

    result = IterationResult(
        index=3,
        command=["python", "scripts/audit_extractions.py"],
        return_code=1,
        duration_seconds=1.5,
        started_at=dt.datetime(2026, 4, 15, tzinfo=dt.timezone.utc),
        summary=summary,
    )

    evaluation = evaluate_iteration_result(result)
    assert evaluation.passed is False
    assert any("exited with code 1" in reason for reason in evaluation.reasons)


def test_build_audit_command_includes_workers_passthrough() -> None:
    args = Namespace(
        model="gpt-5.3-codex",
        max_chars=30000,
        workers=4,
        api_base="http://127.0.0.1:8000",
        company=None,
        slug=None,
        apply=True,
        dry_run=False,
    )
    command = build_audit_command(args)
    assert "--workers" in command
    idx = command.index("--workers")
    assert command[idx + 1] == "4"
