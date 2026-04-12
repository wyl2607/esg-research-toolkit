from fastapi import APIRouter, HTTPException, Query

from core.schemas import CompanyESGData, TaxonomyScoreResult
from taxonomy_scorer.gap_analyzer import analyze_gaps
from taxonomy_scorer.reporter import generate_json_report, generate_text_summary
from taxonomy_scorer.scorer import score_company

router = APIRouter(prefix="/taxonomy", tags=["taxonomy_scorer"])


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
    data = CompanyESGData.model_validate(record.__dict__)
    result = score_company(data)
    gaps = analyze_gaps(data, result)
    return generate_json_report(data, result, gaps)


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
