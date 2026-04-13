import json
from dataclasses import asdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.database import get_db
from core.schemas import CompanyESGData
from esg_frameworks import csrc_2023, csrd, eu_taxonomy
from esg_frameworks.comparison import build_comparison
from esg_frameworks.schemas import FrameworkScoreResult, MultiFrameworkReport
from esg_frameworks.storage import (
    get_framework_result,
    list_framework_results,
    save_framework_result,
)

router = APIRouter(prefix="/frameworks", tags=["esg_frameworks"])

_SCORERS = {
    "eu_taxonomy": eu_taxonomy.score,
    "csrc_2023": csrc_2023.score,
    "csrd": csrd.score,
}


def _load_company(db: Session, company_name: str, report_year: int) -> CompanyESGData:
    """从数据库加载公司数据，未找到时抛 404。"""
    from report_parser.storage import get_report

    record = get_report(db, company_name, report_year)
    if not record:
        raise HTTPException(404, f"No report found for {company_name} ({report_year})")

    raw = record.__dict__.copy()
    if isinstance(raw.get("primary_activities"), str):
        raw["primary_activities"] = json.loads(raw["primary_activities"])
    if isinstance(raw.get("evidence_summary"), str):
        raw["evidence_summary"] = json.loads(raw["evidence_summary"])

    return CompanyESGData.model_validate(raw)


def _make_summary(results: list[FrameworkScoreResult]) -> str:
    parts = []
    for r in results:
        parts.append(f"{r.framework}: {r.grade}（{r.total_score:.0%}，覆盖率 {r.coverage_pct:.0f}%）")
    avg = sum(r.total_score for r in results) / len(results)
    level = "良好" if avg >= 0.6 else "中等" if avg >= 0.4 else "待改进"
    return f"三框架综合评级 {level}（均分 {avg:.0%}）。" + " | ".join(parts)


@router.get("/score", response_model=FrameworkScoreResult)
def score_single_framework(
    company_name: str = Query(...),
    report_year: int = Query(...),
    framework: str = Query(..., description="eu_taxonomy | csrc_2023 | csrd"),
    db: Session = Depends(get_db),
) -> FrameworkScoreResult:
    """对指定公司按单一框架打分。"""
    if framework not in _SCORERS:
        raise HTTPException(400, f"Unknown framework '{framework}'. Choose: {list(_SCORERS)}")
    data = _load_company(db, company_name, report_year)
    result = _SCORERS[framework](data)
    save_framework_result(db, result, framework_version=result.framework_version)
    return result.model_copy(update={"analyzed_at": datetime.now(timezone.utc).isoformat()})


@router.get("/compare", response_model=MultiFrameworkReport)
def compare_frameworks(
    company_name: str = Query(...),
    report_year: int = Query(...),
    db: Session = Depends(get_db),
) -> MultiFrameworkReport:
    """对指定公司同时跑三个框架，返回并排对比报告。"""
    data = _load_company(db, company_name, report_year)
    now = datetime.now(timezone.utc).isoformat()
    results = [scorer(data).model_copy(update={"analyzed_at": now}) for scorer in _SCORERS.values()]
    for result in results:
        save_framework_result(db, result, framework_version=result.framework_version)
    return MultiFrameworkReport(
        company_name=data.company_name,
        report_year=data.report_year,
        frameworks=results,
        summary=_make_summary(results),
    )


@router.get("/compare/regional")
def compare_regional_frameworks(
    company_name: str = Query(...),
    report_year: int = Query(...),
    db: Session = Depends(get_db),
):
    """三地对比分析：返回 RegionalComparisonReport。"""
    data = _load_company(db, company_name, report_year)
    now = datetime.now(timezone.utc).isoformat()
    results = [scorer(data).model_copy(update={"analyzed_at": now}) for scorer in _SCORERS.values()]
    for result in results:
        save_framework_result(db, result, framework_version=result.framework_version)
    report = build_comparison(data, results)
    return asdict(report)


@router.post("/score/upload", response_model=MultiFrameworkReport)
def score_from_data(data: CompanyESGData) -> MultiFrameworkReport:
    """直接传入 CompanyESGData，跑三框架（无需数据库记录）。"""
    now = datetime.now(timezone.utc).isoformat()
    results = [scorer(data).model_copy(update={"analyzed_at": now}) for scorer in _SCORERS.values()]
    return MultiFrameworkReport(
        company_name=data.company_name,
        report_year=data.report_year,
        frameworks=results,
        summary=_make_summary(results),
    )


@router.get("/results")
def get_saved_results(
    company_name: str = Query(...),
    report_year: int = Query(...),
    db: Session = Depends(get_db),
):
    rows = list_framework_results(db, company_name=company_name, report_year=report_year)
    payload: list[dict] = []
    for row in rows:
        result = json.loads(row.result_payload)
        result["analysis_result_id"] = row.id
        result["stored_at"] = row.created_at.isoformat() if row.created_at else None
        payload.append(result)
    return payload


@router.get("/results/{result_id}", response_model=FrameworkScoreResult)
def get_saved_result_by_id(
    result_id: int,
    db: Session = Depends(get_db),
) -> FrameworkScoreResult:
    row = get_framework_result(db, result_id)
    if not row:
        raise HTTPException(404, "Framework analysis result not found")
    result = FrameworkScoreResult.model_validate(json.loads(row.result_payload))
    return result.model_copy(
        update={
            "framework_version": row.framework_version,
            "analyzed_at": row.created_at.isoformat() if row.created_at else None,
        }
    )


@router.get("/list")
def list_frameworks() -> list[dict]:
    """列出所有支持的框架及说明。"""
    return [
        {
            "id": "eu_taxonomy",
            "name": "EU Taxonomy 2020",
            "region": "EU",
            "mandatory_from": "2022",
            "description": "欧盟可持续金融分类法，6 大环境目标 + DNSH 检查",
        },
        {
            "id": "csrc_2023",
            "name": "中国证监会 CSRC 2023",
            "region": "China",
            "mandatory_from": "2025（沪深 300）",
            "description": "中国上市公司可持续发展报告指引，E/S/G 三维度强制披露",
        },
        {
            "id": "csrd",
            "name": "EU CSRD / ESRS",
            "region": "EU",
            "mandatory_from": "2024（大型企业）",
            "description": "欧盟企业可持续发展报告指令，覆盖 E1-E5 + S1 + G1 共 7 个 ESRS 主题",
        },
    ]
