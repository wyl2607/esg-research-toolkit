#!/usr/bin/env python3
"""One-shot thyssenkrupp 2024 taxonomy_aligned_capex_pct repair.

Why this exists:
- `company_reports.id=35` stores `taxonomy_aligned_capex_pct=-9.0`
- prior L0 validation incorrectly rejected signed taxonomy percentages, so the
  disclosed `-9.0` value was rewritten to `+9.0`
- the fix must go through `POST /report/manual`, not a direct SQL update

Audit note:
- `pdfplumber` confirms the 2023 / 2024 annual report describes the KPI as a
  *negative* share of 9% because grants exceeded current-year CapEx additions
- the toolkit now allows signed taxonomy percentages in `[-100, 100]`
- this one-shot script therefore restores the disclosed signed value (`-9.0`)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pdfplumber
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.database import SessionLocal  # noqa: E402
from main import app  # noqa: E402
from report_parser.storage import CompanyReport  # noqa: E402

TARGET_COMPANY = "thyssenkrupp"
TARGET_YEAR = 2024
TARGET_PERIOD_LABEL = "2024"
TARGET_DOCUMENT_TYPE = "sustainability_report"
TARGET_PDF = ROOT / "scripts" / "seed_data" / "pdfs" / "thyssenkrupp-2024.pdf"
TARGET_PDF_FILENAME = "35166c31a14fcc37_thyssenkrupp-2024.pdf"
EXPECTED_FILE_HASH = "35166c31a14fcc37ed942b31146ec483beafa2c33ef4b78028fa3a4d344fbf79"
EXPECTED_SIGNED_PERCENT = -9.0

NARRATIVE_PAGE = 123
SUMMARY_PAGE = 111


@dataclass(frozen=True)
class PdfAuditResult:
    signed_percent: float
    narrative_page: int
    narrative_line: str
    summary_page: int
    summary_line: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Audit + print the payload/target row without posting to /report/manual.",
    )
    return parser.parse_args(argv)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _extract_page_text(path: Path, page_number: int) -> str:
    with pdfplumber.open(path) as pdf:
        return pdf.pages[page_number - 1].extract_text() or ""


def audit_pdf(path: Path) -> PdfAuditResult:
    if not path.exists():
        raise FileNotFoundError(f"source PDF not found: {path}")
    if _sha256(path) != EXPECTED_FILE_HASH:
        raise RuntimeError(
            "source PDF hash mismatch; refusing to audit/update against an unexpected file"
        )

    narrative_text = _extract_page_text(path, NARRATIVE_PAGE)
    summary_text = _extract_page_text(path, SUMMARY_PAGE)

    narrative_match = re.search(
        r"negative share of (\d+)% of total group capital expenditure",
        narrative_text,
        flags=re.IGNORECASE,
    )
    if narrative_match is None:
        raise RuntimeError("failed to locate the narrative disclosure line on page 123")

    summary_line_match = re.search(
        r"thereof Taxonomy-aligned .*? 2023 / 2024.*",
        summary_text,
        flags=re.IGNORECASE,
    )
    summary_line = ""
    if summary_line_match is not None:
        summary_line = summary_line_match.group(0)
    else:
        for line in summary_text.splitlines():
            if "thereof Taxonomy-aligned" in line and "(9)" in line:
                summary_line = line.strip()
                break
    if not summary_line:
        raise RuntimeError("failed to locate the KPI summary row with the disclosed (9) value")

    narrative_line = ""
    for line in narrative_text.splitlines():
        if "negative share of 9%" in line.lower():
            narrative_line = line.strip()
            break
    if not narrative_line:
        raise RuntimeError("failed to isolate the page 123 narrative line")

    signed_percent = -float(narrative_match.group(1))
    if signed_percent != EXPECTED_SIGNED_PERCENT:
        raise RuntimeError(
            f"unexpected signed percentage {signed_percent}; expected {EXPECTED_SIGNED_PERCENT}"
        )

    return PdfAuditResult(
        signed_percent=signed_percent,
        narrative_page=NARRATIVE_PAGE,
        narrative_line=narrative_line,
        summary_page=SUMMARY_PAGE,
        summary_line=summary_line,
    )


def load_target_row() -> CompanyReport:
    with SessionLocal() as db:
        rows = (
            db.query(CompanyReport)
            .filter(
                CompanyReport.company_name == TARGET_COMPANY,
                CompanyReport.report_year == TARGET_YEAR,
                CompanyReport.reporting_period_label == TARGET_PERIOD_LABEL,
                CompanyReport.source_document_type == TARGET_DOCUMENT_TYPE,
                CompanyReport.pdf_filename == TARGET_PDF_FILENAME,
            )
            .all()
        )

        if len(rows) != 1:
            raise RuntimeError(f"expected exactly one target row, found {len(rows)}")

        row = rows[0]
        db.expunge(row)
        return row


def snapshot_thyssenkrupp_rows() -> list[dict[str, Any]]:
    with SessionLocal() as db:
        rows = (
            db.query(CompanyReport)
            .filter(CompanyReport.company_name == TARGET_COMPANY, CompanyReport.report_year == TARGET_YEAR)
            .order_by(CompanyReport.id.asc())
            .all()
        )
        return [
            {
                "id": row.id,
                "reporting_period_label": row.reporting_period_label,
                "source_document_type": row.source_document_type,
                "pdf_filename": row.pdf_filename,
                "taxonomy_aligned_capex_pct": row.taxonomy_aligned_capex_pct,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in rows
        ]


def build_manual_payload(row: CompanyReport, corrected_pct: float) -> dict[str, Any]:
    primary_activities = json.loads(row.primary_activities) if row.primary_activities else []
    evidence_summary = json.loads(row.evidence_summary) if row.evidence_summary else []
    return {
        "company_name": row.company_name,
        "report_year": row.report_year,
        "reporting_period_label": row.reporting_period_label,
        "reporting_period_type": row.reporting_period_type,
        "source_document_type": row.source_document_type,
        "industry_code": row.industry_code,
        "industry_sector": row.industry_sector,
        "scope1_co2e_tonnes": row.scope1_co2e_tonnes,
        "scope2_co2e_tonnes": row.scope2_co2e_tonnes,
        "scope3_co2e_tonnes": row.scope3_co2e_tonnes,
        "energy_consumption_mwh": row.energy_consumption_mwh,
        "renewable_energy_pct": row.renewable_energy_pct,
        "water_usage_m3": row.water_usage_m3,
        "waste_recycled_pct": row.waste_recycled_pct,
        "total_revenue_eur": row.total_revenue_eur,
        "taxonomy_aligned_revenue_pct": row.taxonomy_aligned_revenue_pct,
        "total_capex_eur": row.total_capex_eur,
        "taxonomy_aligned_capex_pct": corrected_pct,
        "total_employees": row.total_employees,
        "female_pct": row.female_pct,
        "primary_activities": primary_activities,
        "evidence_summary": evidence_summary,
        "source_url": row.source_url,
    }


def apply_fix(payload: dict[str, Any]) -> dict[str, Any]:
    with TestClient(app) as client:
        response = client.post("/report/manual", json=payload)
    if response.status_code != 200:
        raise RuntimeError(
            f"/report/manual failed with {response.status_code}: {response.text[:400]}"
        )
    body = response.json()
    if body.get("taxonomy_aligned_capex_pct") != EXPECTED_SIGNED_PERCENT:
        raise RuntimeError(f"unexpected endpoint response: {body}")
    return body


def verify_post_state(
    before: list[dict[str, Any]],
    *,
    target_row_id: int,
    expect_metric_change: bool,
) -> list[dict[str, Any]]:
    after = snapshot_thyssenkrupp_rows()
    if len(after) != len(before):
        raise RuntimeError(
            f"row count changed unexpectedly ({len(before)} -> {len(after)})"
        )

    before_by_id = {row["id"]: row for row in before}
    after_by_id = {row["id"]: row for row in after}
    if set(before_by_id) != set(after_by_id):
        raise RuntimeError("thyssenkrupp row ids changed unexpectedly")

    changed_ids = sorted(
        [
            row_id
            for row_id in after_by_id
            if before_by_id[row_id]["taxonomy_aligned_capex_pct"]
            != after_by_id[row_id]["taxonomy_aligned_capex_pct"]
        ]
    )
    expected_changed_ids = [target_row_id] if expect_metric_change else []
    if changed_ids != expected_changed_ids:
        raise RuntimeError(f"unexpected changed row ids: {changed_ids}")

    fixed_row = after_by_id[target_row_id]
    if fixed_row["taxonomy_aligned_capex_pct"] != EXPECTED_SIGNED_PERCENT:
        raise RuntimeError(f"row {target_row_id} not fixed: {fixed_row}")

    return after


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    audit = audit_pdf(TARGET_PDF)
    target_row = load_target_row()
    before = snapshot_thyssenkrupp_rows()
    payload = build_manual_payload(target_row, audit.signed_percent)
    needs_update = target_row.taxonomy_aligned_capex_pct != audit.signed_percent

    print(
        json.dumps(
            {
                "target_row": {
                    "id": target_row.id,
                    "company_name": target_row.company_name,
                    "report_year": target_row.report_year,
                    "reporting_period_label": target_row.reporting_period_label,
                    "pdf_filename": target_row.pdf_filename,
                    "current_taxonomy_aligned_capex_pct": target_row.taxonomy_aligned_capex_pct,
                },
                "pdf_audit": {
                    "path": str(TARGET_PDF),
                    "file_hash": EXPECTED_FILE_HASH,
                    "signed_percent_disclosed": audit.signed_percent,
                    "signed_percent_to_store": audit.signed_percent,
                    "narrative_page": audit.narrative_page,
                    "narrative_line": audit.narrative_line,
                    "summary_page": audit.summary_page,
                    "summary_line": audit.summary_line,
                },
                "needs_update": needs_update,
                "dry_run": args.dry_run,
            },
            indent=2,
            ensure_ascii=False,
        )
    )

    if args.dry_run:
        return 0

    if not needs_update:
        print("already_fixed")
        return 0

    response_body = apply_fix(payload)
    after = verify_post_state(
        before,
        target_row_id=target_row.id,
        expect_metric_change=True,
    )

    print(
        json.dumps(
            {
                "status": "ok",
                "endpoint_taxonomy_aligned_capex_pct": response_body.get("taxonomy_aligned_capex_pct"),
                "before": before,
                "after": after,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
