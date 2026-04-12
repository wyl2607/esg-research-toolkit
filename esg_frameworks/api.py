from fastapi import APIRouter, HTTPException, Query

from core.schemas import CompanyESGData
from esg_frameworks import csrc_2023, csrd, eu_taxonomy
from esg_frameworks.schemas import FrameworkScoreResult, MultiFrameworkReport

router = APIRouter(prefix="/frameworks", tags=["esg_frameworks"])

_SCORERS = {
    "eu_taxonomy": eu_taxonomy.score,
    "csrc_2023": csrc_2023.score,
    "csrd": csrd.score,
}


def _load_company(company_name: str, report_year: int) -> CompanyESGData:
    """从数据库加载公司数据，未找到时抛 404。"""
    from core.database import get_db
    from report_parser.storage import get_report
    import json

    db = next(get_db())
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
    framework: str = Query(..., description="eu_taxonomy | csrc_2023 | csrd"),
) -> FrameworkScoreResult:
    """对指定公司按单一框架打分。"""
    if framework not in _SCORERS:
        raise HTTPException(400, f"Unknown framework '{framework}'. Choose: {list(_SCORERS)}")
    data = _load_company(company_name, report_year)
    return _SCORERS[framework](data)


@router.get("/compare", response_model=MultiFrameworkReport)
def compare_frameworks(
    company_name: str = Query(...),
    report_year: int = Query(...),
) -> MultiFrameworkReport:
    """对指定公司同时跑三个框架，返回并排对比报告。"""
    data = _load_company(company_name, report_year)
    results = [scorer(data) for scorer in _SCORERS.values()]
    return MultiFrameworkReport(
        company_name=data.company_name,
        report_year=data.report_year,
        frameworks=results,
        summary=_make_summary(results),
    )


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
