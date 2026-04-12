"""Batch analysis workflow for multiple company ESG datasets."""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path
from typing import Any

import requests

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def _load_company(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _post_json(url: str, payload: dict[str, Any]) -> requests.Response:
    try:
        return requests.post(url, json=payload, timeout=30)
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Unable to reach the ESG API at {BASE_URL}. Start the server first."
        ) from exc


def _score_company(company_data: dict[str, Any]) -> dict[str, Any]:
    response = _post_json(f"{BASE_URL}/taxonomy/score", company_data)
    if response.status_code == 422:
        raise ValueError(
            f"Invalid ESG payload for {company_data.get('company_name', '<unknown>')}: "
            f"{response.text}"
        )
    response.raise_for_status()
    return response.json()


def run_batch_analysis(
    companies_dir: str = str(Path(__file__).parent.parent / "examples" / "companies"),
) -> str:
    input_dir = Path(companies_dir)
    company_files = sorted(input_dir.glob("*.json"))
    if not company_files:
        raise FileNotFoundError(f"No company JSON files found in {input_dir}")

    output_dir = Path("reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "batch_summary.csv"

    rows: list[dict[str, Any]] = []
    for path in company_files:
        try:
            company_data = _load_company(path)
            score = _score_company(company_data)
            rows.append(
                {
                    "file": path.name,
                    "company_name": company_data.get("company_name", ""),
                    "report_year": company_data.get("report_year", ""),
                    "revenue_aligned_pct": score["revenue_aligned_pct"],
                    "capex_aligned_pct": score["capex_aligned_pct"],
                    "opex_aligned_pct": score["opex_aligned_pct"],
                    "dnsh_pass": score["dnsh_pass"],
                    "objective_scores": json.dumps(score["objective_scores"], ensure_ascii=False),
                    "status": "ok",
                    "error": "",
                }
            )
            print(f"Scored {company_data.get('company_name', path.stem)}")
        except Exception as exc:  # pragma: no cover - batch resilience path
            rows.append(
                {
                    "file": path.name,
                    "company_name": "",
                    "report_year": "",
                    "revenue_aligned_pct": "",
                    "capex_aligned_pct": "",
                    "opex_aligned_pct": "",
                    "dnsh_pass": "",
                    "objective_scores": "",
                    "status": "error",
                    "error": str(exc),
                }
            )
            print(f"Warning: {path.name} failed: {exc}")

    with summary_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "file",
                "company_name",
                "report_year",
                "revenue_aligned_pct",
                "capex_aligned_pct",
                "opex_aligned_pct",
                "dnsh_pass",
                "objective_scores",
                "status",
                "error",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Batch summary saved to: {summary_path}")
    return str(summary_path)


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    companies_dir = (
        args[0]
        if args
        else str(Path(__file__).parent.parent / "examples" / "companies")
    )
    try:
        run_batch_analysis(companies_dir)
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
