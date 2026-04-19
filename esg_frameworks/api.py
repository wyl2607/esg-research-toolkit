import json
import threading
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from cachetools import TTLCache
from cachetools.keys import hashkey
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from core.database import get_db
from core.schemas import CompanyESGData, FrameworkCacheClearResponse
from esg_frameworks import csrc_2023, csrd, eu_taxonomy, gri_standards, sasb_standards, sec_climate
from esg_frameworks.comparison import build_comparison
from esg_frameworks.schemas import (
    FRAMEWORK_DISPLAY_NAMES,
    FRAMEWORK_VERSIONS,
    FrameworkScoreResult,
    FrameworkVersionInfo,
    MultiFrameworkReport,
)
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
    "sec_climate": sec_climate.score,
    "gri_universal": gri_standards.score,
    "sasb_standards": sasb_standards.score,
}

_score_cache: TTLCache = TTLCache(maxsize=200, ttl=300)
_cache_lock = threading.Lock()
MIN_REPORT_YEAR = 1900
MAX_REPORT_YEAR = 2100


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
    return f"{len(results)} 框架综合评级 {level}（均分 {avg:.0%}）。" + " | ".join(parts)


@router.get("/score", response_model=FrameworkScoreResult)
def score_single_framework(
    company_name: str = Query(..., min_length=1, max_length=200),
    report_year: int = Query(..., ge=MIN_REPORT_YEAR, le=MAX_REPORT_YEAR),
    framework: str = Query(
        ...,
        description="eu_taxonomy | csrc_2023 | csrd | sec_climate | gri_universal | sasb_standards",
    ),
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
    company_name: str = Query(..., min_length=1, max_length=200),
    report_year: int = Query(..., ge=MIN_REPORT_YEAR, le=MAX_REPORT_YEAR),
    db: Session = Depends(get_db),
) -> MultiFrameworkReport:
    """对指定公司同时跑三个框架，返回并排对比报告。"""
    cache_key = hashkey(company_name.strip().lower(), report_year)
    with _cache_lock:
        cached_report = _score_cache.get(cache_key)
    if cached_report is not None:
        return cached_report

    data = _load_company(db, company_name, report_year)
    now = datetime.now(timezone.utc).isoformat()
    results = [scorer(data).model_copy(update={"analyzed_at": now}) for scorer in _SCORERS.values()]
    for result in results:
        save_framework_result(db, result, framework_version=result.framework_version)
    report = MultiFrameworkReport(
        company_name=data.company_name,
        report_year=data.report_year,
        frameworks=results,
        summary=_make_summary(results),
    )
    with _cache_lock:
        _score_cache[cache_key] = report
    return report


@router.get("/compare/regional", response_model=dict[str, Any])
def compare_regional_frameworks(
    company_name: str = Query(..., min_length=1, max_length=200),
    report_year: int = Query(..., ge=MIN_REPORT_YEAR, le=MAX_REPORT_YEAR),
    db: Session = Depends(get_db),
) -> dict[str, object]:
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


@router.get("/results", response_model=list[dict[str, Any]])
def get_saved_results(
    company_name: str = Query(..., min_length=1, max_length=200),
    report_year: int = Query(..., ge=MIN_REPORT_YEAR, le=MAX_REPORT_YEAR),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    rows = list_framework_results(db, company_name=company_name, report_year=report_year)
    payload: list[dict[str, Any]] = []
    for row in rows:
        result = json.loads(row.result_payload)
        result["analysis_result_id"] = row.id
        result["stored_at"] = row.created_at.isoformat() if row.created_at else None
        payload.append(result)
    return payload


@router.get("/results/{result_id}", response_model=FrameworkScoreResult)
def get_saved_result_by_id(
    result_id: int = Path(..., ge=1, le=2_147_483_647),
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


@router.get("/list", response_model=list[dict[str, str]])
def list_frameworks() -> list[dict[str, str]]:
    """列出所有支持的框架及说明。"""
    return [
        {
            "id": "eu_taxonomy",
            "framework_id": "eu_taxonomy",
            "name": "EU Taxonomy 2020",
            "region": "EU",
            "mandatory_from": "2022",
            "description": "欧盟可持续金融分类法，6 大环境目标 + DNSH 检查",
        },
        {
            "id": "csrc_2023",
            "framework_id": "csrc_2023",
            "name": "中国证监会 CSRC 2023",
            "region": "China",
            "mandatory_from": "2025（沪深 300）",
            "description": "中国上市公司可持续发展报告指引，E/S/G 三维度强制披露",
        },
        {
            "id": "csrd",
            "framework_id": "csrd",
            "name": "EU CSRD / ESRS",
            "region": "EU",
            "mandatory_from": "2024（大型企业）",
            "description": "欧盟企业可持续发展报告指令，覆盖 E1-E5 + S1 + G1 共 7 个 ESRS 主题",
        },
        {
            "id": "sec_climate",
            "framework_id": "sec_climate",
            "name": "SEC Climate Disclosure",
            "region": "US",
            "mandatory_from": "2024",
            "description": "美国 SEC 气候披露规则（2024）",
        },
        {
            "id": "gri_universal",
            "framework_id": "gri_universal",
            "name": "GRI Universal Standards 2021",
            "region": "US",
            "mandatory_from": "Voluntary/Market practice",
            "description": "GRI 2/200/300/400 通用可持续披露标准",
        },
        {
            "id": "sasb_standards",
            "framework_id": "sasb_standards",
            "name": "SASB Industry Standards",
            "region": "US",
            "mandatory_from": "Industry-aligned",
            "description": "SASB 行业特定可持续会计披露标准",
        },
    ]


@router.get("/versions", response_model=list[FrameworkVersionInfo])
def list_framework_versions() -> list[FrameworkVersionInfo]:
    """列出受支持框架的标准版本元数据。"""
    framework_ids = tuple(_SCORERS.keys())
    missing_metadata = [
        framework_id
        for framework_id in framework_ids
        if framework_id not in FRAMEWORK_VERSIONS or framework_id not in FRAMEWORK_DISPLAY_NAMES
    ]
    if missing_metadata:
        raise HTTPException(
            500,
            "Framework version metadata is incomplete for: "
            + ", ".join(sorted(missing_metadata)),
        )

    return [
        FrameworkVersionInfo(
            framework_id=framework_id,
            framework_version=FRAMEWORK_VERSIONS[framework_id],
            display_name=FRAMEWORK_DISPLAY_NAMES[framework_id],
        )
        for framework_id in framework_ids
    ]


@router.post("/cache/clear", response_model=FrameworkCacheClearResponse)
def clear_framework_cache() -> FrameworkCacheClearResponse:
    """清除框架对比缓存（管理员用）。"""
    with _cache_lock:
        removed = len(_score_cache)
        _score_cache.clear()
    return {"status": "cache cleared", "entries_removed": removed}
