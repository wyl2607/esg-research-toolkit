import json

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from core.schemas import CompanyESGData, TaxonomyScoreResult
from taxonomy_scorer.gap_analyzer import analyze_gaps
from taxonomy_scorer.reporter import generate_json_report, generate_text_summary
from taxonomy_scorer.scorer import score_company

router = APIRouter(prefix="/taxonomy", tags=["taxonomy_scorer"])


def _record_to_company_esg(record) -> CompanyESGData:
    """Normalize DB record fields to CompanyESGData input shape."""
    payload = record.__dict__.copy()
    raw_activities = payload.get("primary_activities")
    if isinstance(raw_activities, str):
        try:
            payload["primary_activities"] = json.loads(raw_activities) if raw_activities else []
        except json.JSONDecodeError:
            payload["primary_activities"] = []
    return CompanyESGData.model_validate(payload)


@router.post("/score", response_model=TaxonomyScoreResult)
def score(data: CompanyESGData) -> TaxonomyScoreResult:
    """Accept CompanyESGData and return an EU Taxonomy score."""
    return score_company(data)


@router.post("/report")
def full_report(data: CompanyESGData) -> dict:
    """Return score, gap analysis, and recommendations."""
    result = score_company(data)
    gaps = analyze_gaps(data, result)
    return generate_json_report(data, result, gaps)


@router.post("/report/text")
def text_report(data: CompanyESGData) -> dict[str, str]:
    """Return a plain-text summary report."""
    result = score_company(data)
    gaps = analyze_gaps(data, result)
    return {"report": generate_text_summary(result, gaps)}


@router.get("/report")
def get_report_by_name(
    company_name: str = Query(...),
    report_year: int = Query(...),
) -> dict:
    """Fetch stored company data and return taxonomy report (GET convenience endpoint)."""
    from core.database import get_db
    from report_parser.storage import get_report

    db = next(get_db())
    record = get_report(db, company_name, report_year)
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"No report found for {company_name} ({report_year})",
        )
    data = _record_to_company_esg(record)
    result = score_company(data)
    gaps = analyze_gaps(data, result)
    return generate_json_report(data, result, gaps)


@router.get("/report/pdf")
def download_pdf_report(
    company_name: str = Query(...),
    report_year: int = Query(...),
) -> Response:
    """Generate and return a PDF EU Taxonomy report for a stored company."""
    from core.database import get_db
    from report_parser.storage import get_report
    from taxonomy_scorer.pdf_report import generate_pdf

    db = next(get_db())
    record = get_report(db, company_name, report_year)
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"No report found for {company_name} ({report_year})",
        )
    data = _record_to_company_esg(record)
    result = score_company(data)
    gaps = analyze_gaps(data, result)
    pdf_bytes = generate_pdf(data, result, gaps)
    safe_name = company_name.replace(" ", "_")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}_{report_year}_taxonomy.pdf"'
        },
    )


@router.get("/activities")
def list_taxonomy_activities() -> list[dict[str, str | float | None]]:
    """List all supported EU Taxonomy activities."""
    from taxonomy_scorer.framework import list_activities

    return [
        {
            "activity_id": activity.activity_id,
            "name": activity.name,
            "sector": activity.sector,
            "ghg_threshold_gco2e_per_kwh": activity.ghg_threshold_gco2e_per_kwh,
        }
        for activity in list_activities()
    ]
