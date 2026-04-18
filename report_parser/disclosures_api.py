from __future__ import annotations

import ipaddress
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urljoin, urlparse

import httpx
from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Path as FastAPIPath, Query, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from core.database import SessionLocal, get_db
from core.schemas import (
    CompanyESGData,
    DisclosureMergeMetric,
    DisclosureSourceHint,
    DisclosureFetchRequest,
    DisclosureFetchResponse,
    DisclosureReviewRequest,
    DisclosureReviewResponse,
    PendingDisclosureItem,
    PendingDisclosureStatus,
)
from report_parser.analyzer import analyze_esg_data
from report_parser.company_identity import canonical_company_name
from report_parser.extractor import extract_text_from_pdf
from report_parser.storage import (
    PendingDisclosure,
    get_report,
    get_pending_disclosure,
    list_pending_disclosures,
    review_pending_disclosure,
    save_report,
    update_pending_disclosure_payload,
    upsert_pending_disclosure,
)

router = APIRouter(prefix="/disclosures", tags=["disclosures"])
MIN_REPORT_YEAR = 1900
MAX_REPORT_YEAR = 2100
MAX_PENDING_DISCLOSURE_ID = 9_223_372_036_854_775_807
MIN_PDF_BYTES = 1024
HTTP_TIMEOUT_SECONDS = 4.0
HTTP_HEADERS = {
    "User-Agent": "esg-research-toolkit/0.2 (+contact: docs/esg-research-toolkit)",
    "Accept": "application/pdf,text/html;q=0.9,*/*;q=0.8",
}
SOURCE_HINTS = {"company_site", "sec_edgar", "hkex", "csrc"}
MAX_SOURCE_CANDIDATES = 12
MERGEABLE_DISCLOSURE_METRICS: tuple[DisclosureMergeMetric, ...] = (
    "scope1_co2e_tonnes",
    "scope2_co2e_tonnes",
    "scope3_co2e_tonnes",
    "energy_consumption_mwh",
    "renewable_energy_pct",
    "water_usage_m3",
    "waste_recycled_pct",
    "total_revenue_eur",
    "taxonomy_aligned_revenue_pct",
    "total_capex_eur",
    "taxonomy_aligned_capex_pct",
    "total_employees",
    "female_pct",
    "primary_activities",
)


def _slugify_company(name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", canonical_company_name(name).lower()).strip("-")
    return normalized or "company"


def _default_source_url(
    company_name: str,
    report_year: int,
    source_type: str,
    source_hint: str = "company_site",
) -> str:
    slug = _slugify_company(company_name)
    query_company = quote_plus(canonical_company_name(company_name))
    if source_hint == "sec_edgar":
        return (
            "https://www.sec.gov/edgar/search/#/"
            f"q={query_company}%20{report_year}%20sustainability%20report"
            f"&dateRange=custom&startdt={report_year}-01-01&enddt={report_year}-12-31"
        )
    if source_hint == "hkex":
        return (
            "https://www1.hkexnews.hk/search/titlesearch.xhtml"
            f"?lang=en&query={query_company}%20{report_year}%20sustainability"
        )
    if source_hint == "csrc":
        return (
            "https://www.cninfo.com.cn/new/fulltextSearch"
            f"?notautosubmit=&keyWord={query_company}%20{report_year}%20可持续发展报告"
        )
    if source_type == "html":
        return f"https://www.{slug}.com/sustainability/{report_year}"
    if source_type == "filing":
        return f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company={slug}"
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


def _is_contract_test_mode() -> bool:
    return os.getenv("ESG_CONTRACT_TEST_MODE") == "1"


def _is_pytest_mode() -> bool:
    return bool(os.getenv("PYTEST_CURRENT_TEST"))


def _is_private_or_local_hostname(hostname: str | None) -> bool:
    if not hostname:
        return True
    lowered = hostname.lower()
    if lowered in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        ip = ipaddress.ip_address(lowered)
    except ValueError:
        return lowered.endswith(".local")
    return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved


def _candidate_source_urls(
    company_name: str,
    report_year: int,
    explicit_source_url: str | None,
    source_type: str,
    source_hint: str = "company_site",
) -> list[str]:
    if explicit_source_url:
        return [explicit_source_url]

    slug = _slugify_company(company_name)
    query_company = quote_plus(canonical_company_name(company_name))

    def _dedupe_candidates(candidates: list[str]) -> list[str]:
        deduped: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            normalized = candidate.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(normalized)
            if len(deduped) >= MAX_SOURCE_CANDIDATES:
                break
        return deduped

    if source_hint == "sec_edgar":
        return _dedupe_candidates([
            _default_source_url(company_name, report_year, source_type=source_type, source_hint="sec_edgar"),
            f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company={query_company}&owner=exclude&count=40",
            f"https://www.{slug}.com/investor-relations/{report_year}/annual-report.pdf",
        ])
    if source_hint == "hkex":
        return _dedupe_candidates([
            _default_source_url(company_name, report_year, source_type=source_type, source_hint="hkex"),
            f"https://www1.hkexnews.hk/search/prefixsearch.xhtml?lang=en&query={query_company}",
            f"https://www.{slug}.com/investor-relations/{report_year}/annual-report.pdf",
        ])
    if source_hint == "csrc":
        return _dedupe_candidates([
            _default_source_url(company_name, report_year, source_type=source_type, source_hint="csrc"),
            f"https://www.cninfo.com.cn/new/fulltextSearch?notautosubmit=&keyWord={query_company}%20{report_year}",
            f"https://www.{slug}.com/sustainability/{report_year}/report.pdf",
        ])
    if source_type == "html":
        return _dedupe_candidates([
            f"https://www.{slug}.com/sustainability/{report_year}",
            f"https://www.{slug}.com/sustainability",
            f"https://www.{slug}.com/esg",
            f"https://www.{slug}.com/investor-relations/{report_year}",
        ])
    if source_type == "filing":
        return _dedupe_candidates([
            f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company={slug}",
            f"https://www.{slug}.com/investor-relations/{report_year}/annual-report.pdf",
            f"https://www.{slug}.com/investor-relations/{report_year}",
            f"https://www.{slug}.com/sustainability/{report_year}/report.pdf",
        ])
    return _dedupe_candidates([
        f"https://www.{slug}.com/sustainability/{report_year}/report.pdf",
        f"https://www.{slug}.com/investor-relations/{report_year}/annual-report.pdf",
        f"https://www.{slug}.com/sustainability/{report_year}",
    ])


def _normalize_source_hints(
    source_hint: DisclosureSourceHint,
    source_hints: list[DisclosureSourceHint] | None,
) -> list[DisclosureSourceHint]:
    normalized: list[DisclosureSourceHint] = []
    candidates = source_hints or [source_hint]
    for hint in candidates:
        if hint not in SOURCE_HINTS:
            continue
        if hint not in normalized:
            normalized.append(hint)
    if source_hint in SOURCE_HINTS and source_hint not in normalized:
        normalized.insert(0, source_hint)
    if not normalized:
        normalized = ["company_site"]
    return normalized


def _candidate_source_urls_for_hints(
    *,
    company_name: str,
    report_year: int,
    explicit_source_url: str | None,
    source_type: str,
    source_hints: list[DisclosureSourceHint],
) -> list[str]:
    if explicit_source_url:
        return [explicit_source_url]
    combined: list[str] = []
    seen: set[str] = set()
    for source_hint in source_hints:
        for candidate in _candidate_source_urls(
            company_name=company_name,
            report_year=report_year,
            explicit_source_url=None,
            source_type=source_type,
            source_hint=source_hint,
        ):
            if candidate in seen:
                continue
            seen.add(candidate)
            combined.append(candidate)
            if len(combined) >= MAX_SOURCE_CANDIDATES:
                return combined
    return combined


def _download_pdf_bytes(client: httpx.Client, source_url: str) -> tuple[bytes, str] | None:
    try:
        response = client.get(source_url, timeout=HTTP_TIMEOUT_SECONDS, headers=HTTP_HEADERS)
    except httpx.HTTPError:
        return None

    if response.status_code != 200:
        return None

    body = response.content
    if len(body) < MIN_PDF_BYTES:
        return None

    content_type = response.headers.get("content-type", "").lower()
    if "pdf" not in content_type and not body.startswith(b"%PDF-"):
        return None

    return body, str(response.url)


def _discover_pdf_url_from_html(client: httpx.Client, page_url: str) -> str | None:
    try:
        response = client.get(page_url, timeout=HTTP_TIMEOUT_SECONDS, headers=HTTP_HEADERS)
    except httpx.HTTPError:
        return None

    if response.status_code != 200:
        return None

    content_type = response.headers.get("content-type", "").lower()
    if "html" not in content_type and "text" not in content_type:
        return None

    html = response.text[:500_000]
    matches = re.findall(r'href=["\']([^"\']+\.pdf(?:\?[^"\']*)?)["\']', html, flags=re.IGNORECASE)
    for href in matches:
        resolved = urljoin(str(response.url), href)
        if not _is_private_or_local_hostname(urlparse(resolved).hostname):
            return resolved
    return None


def _build_pending_payload(
    *,
    company_name: str,
    report_year: int,
    source_url: str,
    source_type: str,
    source_hint: str,
    source_hints: list[DisclosureSourceHint],
    snippet: str,
    attempted_urls: list[str] | None = None,
) -> CompanyESGData:
    evidence_item: dict[str, Any] = {
        "metric": "auto_disclosure_fetch",
        "source": source_url,
        "source_url": source_url,
        "source_type": source_type,
        "source_hint": source_hint,
        "source_hints": source_hints,
        "snippet": snippet,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    if attempted_urls:
        evidence_item["attempted_urls"] = attempted_urls[:MAX_SOURCE_CANDIDATES]

    return CompanyESGData(
        company_name=company_name,
        report_year=report_year,
        source_document_type="sustainability_report",
        evidence_summary=[evidence_item],
    )


def _run_fetch_pipeline(
    *,
    pending_id: int,
    company_name: str,
    report_year: int,
    source_type: str,
    source_hint: str,
    source_hints: list[DisclosureSourceHint],
    source_url: str,
) -> None:
    if _is_contract_test_mode():
        db = SessionLocal()
        try:
            fallback = _build_pending_payload(
                company_name=company_name,
                report_year=report_year,
                source_url=source_url,
                source_type=source_type,
                source_hint=source_hint,
                source_hints=source_hints,
                snippet="Contract test mode: fetch skipped.",
            )
            update_pending_disclosure_payload(
                db,
                pending_id=pending_id,
                extracted_payload=fallback.model_dump(mode="json"),
                review_note="fetch_skipped_contract_mode",
            )
        finally:
            db.close()
        return

    candidates = _candidate_source_urls_for_hints(
        company_name=company_name,
        report_year=report_year,
        explicit_source_url=source_url,
        source_type=source_type,
        source_hints=source_hints,
    )
    client = httpx.Client(follow_redirects=True)
    downloaded: tuple[bytes, str] | None = None
    attempted_urls: list[str] = []

    try:
        for candidate in candidates:
            if _is_private_or_local_hostname(urlparse(candidate).hostname):
                continue
            attempted_urls.append(candidate)

            if candidate.lower().endswith(".pdf"):
                downloaded = _download_pdf_bytes(client, candidate)
            else:
                discovered_pdf_url = _discover_pdf_url_from_html(client, candidate)
                if discovered_pdf_url:
                    downloaded = _download_pdf_bytes(client, discovered_pdf_url)

            if downloaded is not None:
                break
    finally:
        client.close()

    db = SessionLocal()
    try:
        if downloaded is None:
            fallback = _build_pending_payload(
                company_name=company_name,
                report_year=report_year,
                source_url=source_url,
                source_type=source_type,
                source_hint=source_hint,
                source_hints=source_hints,
                snippet=(
                    f"No reachable public PDF was found after {len(attempted_urls)} attempts. "
                    "Upload manually or provide a direct PDF URL."
                ),
                attempted_urls=attempted_urls,
            )
            update_pending_disclosure_payload(
                db,
                pending_id=pending_id,
                extracted_payload=fallback.model_dump(mode="json"),
                review_note=f"fetch_no_public_pdf_found:{len(attempted_urls)}",
            )
            return

        pdf_bytes, resolved_source_url = downloaded
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as handle:
            handle.write(pdf_bytes)
            temp_pdf_path = Path(handle.name)

        try:
            extracted_text = extract_text_from_pdf(temp_pdf_path)
            parsed = analyze_esg_data(extracted_text, filename=f"{_slugify_company(company_name)}-{report_year}.pdf")
        finally:
            temp_pdf_path.unlink(missing_ok=True)

        payload = parsed.model_dump(mode="json")
        payload["company_name"] = company_name
        payload["report_year"] = report_year
        payload.setdefault("source_document_type", "sustainability_report")

        evidence_summary = payload.get("evidence_summary")
        if not isinstance(evidence_summary, list):
            evidence_summary = []
        evidence_summary.append(
            {
                "metric": "auto_disclosure_fetch",
                "source": resolved_source_url,
                "source_url": resolved_source_url,
                "source_type": source_type,
                "source_hint": source_hint,
                "source_hints": source_hints,
                "snippet": "Auto fetch succeeded and extracted draft metrics.",
                "attempted_urls": attempted_urls[:MAX_SOURCE_CANDIDATES],
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        payload["evidence_summary"] = evidence_summary

        update_pending_disclosure_payload(
            db,
            pending_id=pending_id,
            extracted_payload=payload,
            review_note="fetch_succeeded",
        )
    except Exception as exc:  # noqa: BLE001
        fallback = _build_pending_payload(
            company_name=company_name,
            report_year=report_year,
            source_url=source_url,
            source_type=source_type,
            source_hint=source_hint,
            source_hints=source_hints,
            snippet="Fetch attempted but extraction failed. Review source and upload manually if needed.",
            attempted_urls=attempted_urls,
        )
        update_pending_disclosure_payload(
            db,
            pending_id=pending_id,
            extracted_payload=fallback.model_dump(mode="json"),
            review_note=f"fetch_failed:{type(exc).__name__}",
        )
    finally:
        db.close()


def _record_to_company_data(record: Any) -> CompanyESGData:
    payload = {
        "company_name": record.company_name,
        "report_year": record.report_year,
        "reporting_period_label": record.reporting_period_label,
        "reporting_period_type": record.reporting_period_type,
        "source_document_type": record.source_document_type,
        "industry_code": record.industry_code,
        "industry_sector": record.industry_sector,
        "scope1_co2e_tonnes": record.scope1_co2e_tonnes,
        "scope2_co2e_tonnes": record.scope2_co2e_tonnes,
        "scope3_co2e_tonnes": record.scope3_co2e_tonnes,
        "energy_consumption_mwh": record.energy_consumption_mwh,
        "renewable_energy_pct": record.renewable_energy_pct,
        "water_usage_m3": record.water_usage_m3,
        "waste_recycled_pct": record.waste_recycled_pct,
        "total_revenue_eur": record.total_revenue_eur,
        "taxonomy_aligned_revenue_pct": record.taxonomy_aligned_revenue_pct,
        "total_capex_eur": record.total_capex_eur,
        "taxonomy_aligned_capex_pct": record.taxonomy_aligned_capex_pct,
        "total_employees": record.total_employees,
        "female_pct": record.female_pct,
        "primary_activities": [],
        "evidence_summary": [],
    }
    if isinstance(record.primary_activities, str) and record.primary_activities:
        try:
            payload["primary_activities"] = json.loads(record.primary_activities)
        except json.JSONDecodeError:
            payload["primary_activities"] = []
    if isinstance(record.evidence_summary, str) and record.evidence_summary:
        try:
            payload["evidence_summary"] = json.loads(record.evidence_summary)
        except json.JSONDecodeError:
            payload["evidence_summary"] = []
    return CompanyESGData.model_validate(payload)


def _merge_payload_with_selected_metrics(
    *,
    row: PendingDisclosure,
    extracted_payload: dict[str, Any],
    include_metrics: list[DisclosureMergeMetric],
    db: Session,
) -> dict[str, Any]:
    existing_record = get_report(db, company_name=row.company_name, report_year=row.report_year)
    if existing_record is None:
        base_payload: dict[str, Any] = {
            "company_name": row.company_name,
            "report_year": row.report_year,
            "primary_activities": [],
            "evidence_summary": [],
        }
    else:
        base_payload = _record_to_company_data(existing_record).model_dump(mode="json")

    for metric in include_metrics:
        if metric in extracted_payload:
            base_payload[metric] = extracted_payload[metric]

    base_payload["company_name"] = row.company_name
    base_payload["report_year"] = row.report_year
    base_payload["source_document_type"] = extracted_payload.get(
        "source_document_type",
        base_payload.get("source_document_type", "sustainability_report"),
    )
    if not isinstance(base_payload.get("primary_activities"), list):
        base_payload["primary_activities"] = []
    if not isinstance(base_payload.get("evidence_summary"), list):
        base_payload["evidence_summary"] = []
    return base_payload


@router.post("/fetch", response_model=DisclosureFetchResponse, status_code=status.HTTP_202_ACCEPTED)
def fetch_disclosure(
    payload: DisclosureFetchRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> DisclosureFetchResponse:
    source_hint = payload.source_hint if payload.source_hint in SOURCE_HINTS else "company_site"
    source_hints = _normalize_source_hints(source_hint, payload.source_hints)
    source_url = (
        payload.source_url.strip()
        if payload.source_url
        else _default_source_url(payload.company_name, payload.report_year, payload.source_type, source_hint)
    )

    canonical_name = canonical_company_name(payload.company_name)
    queued_payload = _build_pending_payload(
        company_name=canonical_name,
        report_year=payload.report_year,
        source_url=source_url,
        source_type=payload.source_type,
        source_hint=source_hint,
        source_hints=source_hints,
        snippet="Auto-fetch queued. Awaiting extraction + review before merge.",
    )

    row, created = upsert_pending_disclosure(
        db,
        company_name=canonical_name,
        report_year=payload.report_year,
        source_url=source_url,
        source_type=payload.source_type,
        extracted_payload=queued_payload.model_dump(mode="json"),
        status="pending",
        review_note="fetch_queued",
    )

    if not _is_pytest_mode():
        background_tasks.add_task(
            _run_fetch_pipeline,
            pending_id=row.id,
            company_name=canonical_name,
            report_year=payload.report_year,
            source_type=payload.source_type,
            source_hint=source_hint,
            source_hints=source_hints,
            source_url=source_url,
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


@router.post(
    "/{pending_id}/approve",
    response_model=DisclosureReviewResponse,
    responses={
        400: {"description": "Pending disclosure payload is invalid for approval"},
        404: {"description": "Pending disclosure not found"},
        409: {"description": "Pending disclosure is in a conflicting final status"},
    },
)
def approve_pending_disclosure(
    pending_id: int = FastAPIPath(..., ge=1, le=MAX_PENDING_DISCLOSURE_ID),
    payload: DisclosureReviewRequest = Body(...),
    db: Session = Depends(get_db),
) -> DisclosureReviewResponse:
    row = get_pending_disclosure(db, pending_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Pending disclosure not found")
    if row.status == "approved":
        raise HTTPException(status_code=409, detail="Disclosure is already approved")
    if row.status == "rejected":
        raise HTTPException(status_code=409, detail="Rejected disclosure cannot be approved")

    try:
        extracted_payload = json.loads(row.extracted_payload)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Pending disclosure payload is invalid JSON") from exc

    extracted_payload["company_name"] = row.company_name
    extracted_payload["report_year"] = row.report_year

    include_metrics = payload.include_metrics or []
    if include_metrics:
        include_metrics = [metric for metric in include_metrics if metric in MERGEABLE_DISCLOSURE_METRICS]
        extracted_payload = _merge_payload_with_selected_metrics(
            row=row,
            extracted_payload=extracted_payload,
            include_metrics=include_metrics,
            db=db,
        )

    extracted_payload.setdefault("source_document_type", "sustainability_report")
    extracted_payload.setdefault("evidence_summary", [])

    if isinstance(extracted_payload["evidence_summary"], list):
        extracted_payload["evidence_summary"].append(
            {
                "metric": "auto_disclosure_review",
                "source": row.source_url,
                "source_url": row.source_url,
                "source_type": row.source_type,
                "snippet": "Pending disclosure approved and merged into company_reports.",
                "selected_metrics": include_metrics if include_metrics else "all",
                "approved_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    try:
        merged_input = CompanyESGData.model_validate(extracted_payload)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail="Pending disclosure payload validation failed") from exc

    try:
        merged_record = save_report(
            db,
            merged_input,
            source_url=row.source_url,
            source_document_type=merged_input.source_document_type,
            evidence_summary=merged_input.evidence_summary,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    reviewed = review_pending_disclosure(
        db,
        pending_id=pending_id,
        status="approved",
        review_note=payload.review_note or "approved",
    )
    assert reviewed is not None

    return DisclosureReviewResponse(
        status="approved",
        pending=_pending_to_item(reviewed),
        merged_report=_record_to_company_data(merged_record),
    )


@router.post(
    "/{pending_id}/reject",
    response_model=DisclosureReviewResponse,
    responses={
        400: {"description": "Pending disclosure request is invalid"},
        404: {"description": "Pending disclosure not found"},
        409: {"description": "Pending disclosure is in a conflicting final status"},
    },
)
def reject_pending_disclosure(
    pending_id: int = FastAPIPath(..., ge=1, le=MAX_PENDING_DISCLOSURE_ID),
    payload: DisclosureReviewRequest = Body(...),
    db: Session = Depends(get_db),
) -> DisclosureReviewResponse:
    row = get_pending_disclosure(db, pending_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Pending disclosure not found")
    if row.status == "approved":
        raise HTTPException(status_code=409, detail="Approved disclosure cannot be rejected")

    reviewed = review_pending_disclosure(
        db,
        pending_id=pending_id,
        status="rejected",
        review_note=payload.review_note or "rejected",
    )
    assert reviewed is not None

    return DisclosureReviewResponse(
        status="rejected",
        pending=_pending_to_item(reviewed),
        merged_report=None,
    )
