"""Run audit_extractions.py repeatedly and track run history.

This utility executes scripts/audit_extractions.py for multiple iterations,
cleans old per-company markdown reports between runs, parses SUMMARY.md after
each iteration, and writes an aggregated RUN_HISTORY.md report.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIT_SCRIPT = ROOT / "scripts" / "audit_extractions.py"
AUDIT_DIR = ROOT / "scripts" / "seed_data" / "audit_reports"
SUMMARY_PATH = AUDIT_DIR / "SUMMARY.md"
RUN_HISTORY_PATH = AUDIT_DIR / "RUN_HISTORY.md"


@dataclass(frozen=True)
class SummaryStats:
    total_companies: int
    total_fields: int
    verdict_counts: dict[str, int]
    error_entries: list[str]

    @property
    def error_count(self) -> int:
        return len(self.error_entries)

    @property
    def non_dry_run_error_count(self) -> int:
        count = 0
        for entry in self.error_entries:
            _, _, raw_message = entry.partition(":")
            message = raw_message.strip().lower() if raw_message else entry.strip().lower()
            if message != "dry-run":
                count += 1
        return count


@dataclass(frozen=True)
class IterationResult:
    index: int
    command: list[str]
    return_code: int
    duration_seconds: float
    started_at: dt.datetime
    summary: SummaryStats | None
    summary_parse_error: str | None = None


@dataclass(frozen=True)
class IterationEvaluation:
    passed: bool
    reasons: list[str] = field(default_factory=list)


def parse_summary_text(text: str) -> SummaryStats:
    total_companies_match = re.search(r"^Total companies:\s*(\d+)\s*$", text, flags=re.MULTILINE)
    total_fields_match = re.search(r"^Total fields audited:\s*(\d+)\s*$", text, flags=re.MULTILINE)

    if not total_companies_match or not total_fields_match:
        raise ValueError("missing required totals in SUMMARY.md")

    verdict_counts: dict[str, int] = {}
    for verdict in ("correct", "incorrect", "missed", "not_disclosed"):
        match = re.search(rf"^\|\s*{verdict}\s*\|\s*(\d+)\s*\|\s*$", text, flags=re.MULTILINE)
        if not match:
            raise ValueError(f"missing verdict count for '{verdict}'")
        verdict_counts[verdict] = int(match.group(1))

    error_entries: list[str] = []
    lines = text.splitlines()
    in_errors = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            in_errors = stripped == "## Errors"
            continue
        if not in_errors:
            continue
        if stripped.startswith("- "):
            error_entries.append(stripped[2:].strip())

    return SummaryStats(
        total_companies=int(total_companies_match.group(1)),
        total_fields=int(total_fields_match.group(1)),
        verdict_counts=verdict_counts,
        error_entries=error_entries,
    )


def parse_summary_file(path: Path) -> SummaryStats:
    return parse_summary_text(path.read_text(encoding="utf-8"))


def evaluate_iteration_result(result: IterationResult) -> IterationEvaluation:
    reasons: list[str] = []
    if result.return_code != 0:
        reasons.append(f"audit subprocess exited with code {result.return_code}")
    if result.summary_parse_error:
        reasons.append(f"summary parse error: {result.summary_parse_error}")
    if result.summary and result.summary.non_dry_run_error_count > 0:
        reasons.append(f"summary has {result.summary.non_dry_run_error_count} non-dry-run error(s)")
    if result.summary is None and not result.summary_parse_error:
        reasons.append("summary missing")
    return IterationEvaluation(passed=not reasons, reasons=reasons)


def clean_previous_markdown_reports(audit_dir: Path) -> int:
    audit_dir.mkdir(parents=True, exist_ok=True)
    removed = 0
    for path in audit_dir.glob("*.md"):
        if path.name in {".gitkeep", "RUN_HISTORY.md"}:
            continue
        path.unlink(missing_ok=True)
        removed += 1
    return removed


def build_audit_command(args: argparse.Namespace) -> list[str]:
    cmd = [sys.executable, str(AUDIT_SCRIPT)]
    if args.model:
        cmd.extend(["--model", args.model])
    if args.max_chars is not None:
        cmd.extend(["--max-chars", str(args.max_chars)])
    if args.api_base:
        cmd.extend(["--api-base", args.api_base])
    if args.company:
        cmd.extend(["--company", args.company])
    if args.slug:
        cmd.extend(["--slug", args.slug])
    if args.apply:
        cmd.append("--apply")
    if args.dry_run:
        cmd.append("--dry-run")
    return cmd


def run_single_iteration(index: int, command: list[str]) -> IterationResult:
    removed = clean_previous_markdown_reports(AUDIT_DIR)
    print(f"[iteration {index}] cleaned {removed} markdown file(s) in {AUDIT_DIR.relative_to(ROOT)}")

    started_at = dt.datetime.now(dt.timezone.utc)
    started = time.perf_counter()
    completed = subprocess.run(command, cwd=ROOT, text=True)
    duration = time.perf_counter() - started

    summary: SummaryStats | None = None
    summary_parse_error: str | None = None
    if SUMMARY_PATH.exists():
        try:
            summary = parse_summary_file(SUMMARY_PATH)
        except Exception as exc:  # noqa: BLE001
            summary_parse_error = str(exc)
    else:
        summary_parse_error = f"missing summary file: {SUMMARY_PATH}"

    result = IterationResult(
        index=index,
        command=command,
        return_code=completed.returncode,
        duration_seconds=duration,
        started_at=started_at,
        summary=summary,
        summary_parse_error=summary_parse_error,
    )

    verdict = evaluate_iteration_result(result)
    print(f"[iteration {index}] status={'PASS' if verdict.passed else 'FAIL'} ({duration:.2f}s)")
    if not verdict.passed:
        for reason in verdict.reasons:
            print(f"  - {reason}")

    return result


def write_run_history(path: Path, results: list[IterationResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    generated_at = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

    lines: list[str] = [
        "# Audit Iteration Run History",
        "",
        f"Generated at: {generated_at}",
        "",
        "| Iteration | Started (UTC) | Duration (s) | Return code | Summary errors | Non-dry-run errors | Status |",
        "|---|---|---:|---:|---:|---:|---|",
    ]

    for result in results:
        evaluation = evaluate_iteration_result(result)
        summary_errors = result.summary.error_count if result.summary else 0
        non_dry_errors = result.summary.non_dry_run_error_count if result.summary else 0
        lines.append(
            "| "
            f"{result.index} | "
            f"{result.started_at.isoformat(timespec='seconds')} | "
            f"{result.duration_seconds:.2f} | "
            f"{result.return_code} | "
            f"{summary_errors} | "
            f"{non_dry_errors} | "
            f"{'PASS' if evaluation.passed else 'FAIL'} |"
        )

    lines.extend(["", "## Details", ""])

    for result in results:
        evaluation = evaluate_iteration_result(result)
        lines.append(f"### Iteration {result.index}")
        lines.append("")
        lines.append(f"- Command: `{' '.join(result.command)}`")
        lines.append(f"- Duration: {result.duration_seconds:.2f}s")
        lines.append(f"- Return code: {result.return_code}")
        lines.append(f"- Status: {'PASS' if evaluation.passed else 'FAIL'}")

        if result.summary:
            lines.append(
                "- Verdict counts: "
                f"correct={result.summary.verdict_counts['correct']}, "
                f"incorrect={result.summary.verdict_counts['incorrect']}, "
                f"missed={result.summary.verdict_counts['missed']}, "
                f"not_disclosed={result.summary.verdict_counts['not_disclosed']}"
            )
            lines.append(
                "- Summary errors: "
                f"{result.summary.error_count} total, {result.summary.non_dry_run_error_count} non-dry-run"
            )
        else:
            lines.append("- Verdict counts: unavailable")

        if result.summary_parse_error:
            lines.append(f"- Summary parse error: {result.summary_parse_error}")

        if evaluation.reasons:
            lines.append("- Failure reasons:")
            for reason in evaluation.reasons:
                lines.append(f"  - {reason}")

        lines.append("")

    overall_pass = all(evaluate_iteration_result(result).passed for result in results)
    lines.append(f"Overall status: {'PASS' if overall_pass else 'FAIL'}")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=3, help="number of audit iterations to run")
    parser.add_argument("--model", help="passthrough to audit_extractions.py --model")
    parser.add_argument("--max-chars", type=int, help="passthrough to audit_extractions.py --max-chars")
    parser.add_argument("--api-base", help="passthrough to audit_extractions.py --api-base")
    parser.add_argument("--company", help="passthrough to audit_extractions.py --company")
    parser.add_argument("--slug", help="passthrough to audit_extractions.py --slug")
    parser.add_argument("--apply", action="store_true", help="passthrough to audit_extractions.py --apply")
    parser.add_argument("--dry-run", action="store_true", help="passthrough to audit_extractions.py --dry-run")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.iterations < 1:
        parser.error("--iterations must be >= 1")

    command = build_audit_command(args)
    print(f"Running {args.iterations} iteration(s): {' '.join(command)}")

    results: list[IterationResult] = []
    for index in range(1, args.iterations + 1):
        results.append(run_single_iteration(index, command))

    write_run_history(RUN_HISTORY_PATH, results)
    print(f"run history: {RUN_HISTORY_PATH.relative_to(ROOT)}")

    any_failed = any(not evaluate_iteration_result(result).passed for result in results)
    return 1 if any_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
