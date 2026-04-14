from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Float, Index, Integer, String, UniqueConstraint

from core.database import Base


class IndustryBenchmark(Base):
    __tablename__ = "industry_benchmarks"

    id = Column(Integer, primary_key=True)
    industry_code = Column(String, nullable=False, index=True)
    metric_name = Column(String, nullable=False)
    period_year = Column(Integer, nullable=False)
    p10 = Column(Float, nullable=True)
    p25 = Column(Float, nullable=True)
    p50 = Column(Float, nullable=True)
    p75 = Column(Float, nullable=True)
    p90 = Column(Float, nullable=True)
    sample_size = Column(Integer, nullable=False, default=0)
    computed_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))

    __table_args__ = (
        UniqueConstraint("industry_code", "metric_name", "period_year", name="uq_benchmark_key"),
        Index("ix_benchmark_lookup", "industry_code", "period_year"),
    )
