from dataclasses import asdict
import json
import threading

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from cachetools import TTLCache
from cachetools.keys import hashkey

from core.schemas import CompanyESGData
from core.database import get_db
from esg_frameworks import csrc_2023, csrd, eu_taxonomy
from esg_frameworks.comparison import build_comparison
from esg_frameworks.gri_standards import score_gri
from esg_frameworks.sasb_standards import score_sasb
from esg_frameworks.sec_climate import score_sec_climate
from esg_frameworks.schemas import FrameworkScoreResult, MultiFrameworkReport

router = APIRouter(prefix="/frameworks", tags=["esg_frameworks"])

_score_cache: TTLCache = TTLCache(maxsize=200, ttl=300)
_cache_lock = threading.Lock()

_SCORERS = {
    "eu_taxonomy": eu_taxonomy.score,
    "csrc_2023": csrc_2023.score,
    "csrd": csrd.score,
    "sec_climate": score_sec_climate,
    "gri_universal": score_gri,
    "sasb_standards": score_sasb,
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
    return _SCORERS[framework](data)


@router.get("/compare", response_model=MultiFrameworkReport)
def compare_frameworks(
    company_name: str = Query(...),
    report_year: int = Query(...),
    db: Session = Depends(get_db),
) -> MultiFrameworkReport:
    """对指定公司同时跑三个框架，返回并排对比报告。"""
    cache_key = hashkey(company_name, report_year)
    with _cache_lock:
        cached_report = _score_cache.get(cache_key)
    if cached_report is not None:
        return cached_report

    data = _load_company(db, company_name, report_year)
    results = [scorer(data) for scorer in _SCORERS.values()]
    report = MultiFrameworkReport(
        company_name=data.company_name,
        report_year=data.report_year,
        frameworks=results,
        summary=_make_summary(results),
    )
    with _cache_lock:
        _score_cache[cache_key] = report
    return report


@router.post("/cache/clear")
def clear_framework_cache() -> dict[str, int | str]:
    """清除框架评分缓存（管理员用）"""
    with _cache_lock:
        removed = len(_score_cache)
        _score_cache.clear()
    return {"status": "cache cleared", "entries_removed": removed}


@router.post("/score/upload", response_model=MultiFrameworkReport)
def score_from_data(data: CompanyESGData) -> MultiFrameworkReport:
    """直接传入 CompanyESGData，跑三框架（无需数据库记录）。"""
    results = [scorer(data) for scorer in _SCORERS.values()]
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
    """
    三地对比分析：返回 RegionalComparisonReport
    包含：区域分组得分、维度交叉矩阵、合规优先级排序、核心洞察
    """
    data = _load_company(db, company_name, report_year)
    results = [scorer(data) for scorer in _SCORERS.values()]
    report = build_comparison(data, results)
    return asdict(report)


@router.get("/list")
def list_frameworks() -> list[dict]:
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
            "description": "美国 SEC 气候披露规则，覆盖气候风险、GHG 披露和财务影响",
        },
        {
            "id": "gri_universal",
            "framework_id": "gri_universal",
            "name": "GRI Universal Standards 2021",
            "region": "US",
            "mandatory_from": "Voluntary / market practice",
            "description": "GRI 2/200/300/400 通用标准体系，覆盖环境、社会、治理和经济披露",
        },
        {
            "id": "sasb_standards",
            "framework_id": "sasb_standards",
            "name": "SASB Industry Standards",
            "region": "US",
            "mandatory_from": "Investor-driven",
            "description": "SASB 行业标准，强调财务重要性的行业 ESG 指标",
        },
    ]
