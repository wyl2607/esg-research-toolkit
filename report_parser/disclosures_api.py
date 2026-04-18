from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.schemas import (
    CompanyESGData,
    DisclosureFetchRequest,
    DisclosureFetchResponse,
    PendingDisclosureItem,
    PendingDisclosureStatus,
)
from report_parser.company_identity import canonical_company_name
from report_parser.storage import (
    PendingDisclosure,
    list_pending_disclosures,
    upsert_pending_disclosure,
)

router = APIRouter(prefix="/disclosures", tags=["disclosures"])
MIN_REPORT_YEAR = 1900
MAX_REPORT_YEAR = 2100


def _slugify_company(name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", canonical_company_name(name).lower()).strip("-")
    return normalized or "company"


def _default_source_url(company_name: str, report_year: int) -> str:
    slug = _slugify_company(company_name)
    return f"https://www.{slug}.com/sustainability/{report_year}/report.pdf"


def _pending_to_item(row: PendingDisclosure) -> PendingDisclosureItem:
    try:
        payload: dict[str, Any] = json.loads(row.extracted_payload)
    except json.JSONDecodeError:
        payload = {}

    fetched_at = row.fetched_at or row.created_at or datetime.now(timezone.utc)
    return PendingDisclosureItem(
        id=row.id,
        company_name=row.company_name,
        report_year=row.report_year,
        source_url=row.source_url,
        source_type=row.source_type,
        fetched_at=fetched_at.isoformat() if hasattr(fetched_at, "isoformat") else str(fetched_at),
        extracted_payload=payload,
        status=row.status,  # type: ignore[arg-type]
        review_note=row.review_note,
    )


@router.post("/fetch", response_model=DisclosureFetchResponse, status_code=status.HTTP_202_ACCEPTED)
def fetch_disclosure(
    payload: DisclosureFetchRequest,
    db: Session = Depends(get_db),
) -> DisclosureFetchResponse:
    source_url = payload.source_url.strip() if payload.source_url else _default_source_url(
        payload.company_name,
        payload.report_year,
    )

    canonical_name = canonical_company_name(payload.company_name)
    draft = CompanyESGData(
        company_name=canonical_name,
        report_year=payload.report_year,
        source_document_type="sustainability_report",
        evidence_summary=[
            {
                "metric": "auto_disclosure_fetch",
                "source": source_url,
                "source_url": source_url,
                "source_type": payload.source_type,
                "snippet": "Auto-fetch queued. Awaiting review before merge.",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
        ],
    )

    row, created = upsert_pending_disclosure(
        db,
        company_name=canonical_name,
        report_year=payload.report_year,
        source_url=source_url,
        source_type=payload.source_type,
        extracted_payload=draft.model_dump(mode="json"),
        status="pending",
    )

    return DisclosureFetchResponse(
        status="queued",
        created=created,
        pending=_pending_to_item(row),
    )


@router.get("/pending", response_model=list[PendingDisclosureItem])
def get_pending_disclosures(
    company_name: str | None = Query(default=None, min_length=1, max_length=200),
    report_year: int | None = Query(default=None, ge=MIN_REPORT_YEAR, le=MAX_REPORT_YEAR),
    status: PendingDisclosureStatus | None = Query(default="pending"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[PendingDisclosureItem]:
    rows = list_pending_disclosures(
        db,
        company_name=company_name,
        report_year=report_year,
        status=status,
        limit=limit,
    )
    return [_pending_to_item(row) for row in rows]
