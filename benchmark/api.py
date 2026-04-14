from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from benchmark.compute import recompute_industry_benchmarks
from benchmark.models import IndustryBenchmark
from core.database import get_db

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


@router.post("/recompute")
def recompute(db: Session = Depends(get_db)) -> dict[str, int]:
    return recompute_industry_benchmarks(db)


@router.get("/{industry_code}")
def get_industry_benchmarks(industry_code: str, db: Session = Depends(get_db)) -> dict:
    rows = (
        db.query(IndustryBenchmark)
        .filter(IndustryBenchmark.industry_code == industry_code)
        .order_by(IndustryBenchmark.period_year.asc(), IndustryBenchmark.metric_name.asc())
        .all()
    )
    if not rows:
        return {"industry_code": industry_code, "metrics": []}
    return {
        "industry_code": industry_code,
        "metrics": [
            {
                "metric_name": row.metric_name,
                "period_year": row.period_year,
                "p10": row.p10,
                "p25": row.p25,
                "p50": row.p50,
                "p75": row.p75,
                "p90": row.p90,
                "sample_size": row.sample_size,
                "computed_at": row.computed_at.isoformat() if row.computed_at else None,
            }
            for row in rows
        ],
    }

