from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from benchmark.models import IndustryBenchmark
from benchmark.percentiles import five_point_summary
from report_parser.storage import CompanyReport

# The list of CompanyESGData numeric fields we benchmark.
# Confirmed against core.schemas.CompanyESGData and report_parser.storage.CompanyReport.
BENCHMARK_METRICS: list[str] = [
    "scope1_co2e_tonnes",
    "scope2_co2e_tonnes",
    "scope3_co2e_tonnes",
    "energy_consumption_mwh",
    "renewable_energy_pct",
    "water_usage_m3",
    "waste_recycled_pct",
    "taxonomy_aligned_revenue_pct",
    "female_pct",
]


def recompute_industry_benchmarks(db: Session) -> dict[str, int]:
    """
    Reads all CompanyReport rows with a non-null industry_code,
    groups by (industry_code, report_year, metric), computes the
    five-point summary, and upserts into industry_benchmarks.

    Returns a summary dict: {"industries": N, "metric_rows": M}
    """
    rows = db.query(CompanyReport).filter(CompanyReport.industry_code.isnot(None)).all()

    # Shape: {(industry_code, report_year, metric): [values...]}
    buckets: dict[tuple[str, int, str], list[float]] = defaultdict(list)

    for row in rows:
        if not row.industry_code:
            continue
        for metric in BENCHMARK_METRICS:
            val = getattr(row, metric, None)
            if val is None:
                continue
            try:
                numeric_val = float(val)
            except (TypeError, ValueError):
                continue
            if numeric_val != numeric_val:  # NaN guard
                continue
            buckets[(row.industry_code, row.report_year, metric)].append(numeric_val)

    # Wipe old benchmarks for the affected industry codes, then insert fresh ones.
    affected_codes = {key[0] for key in buckets}
    if affected_codes:
        db.query(IndustryBenchmark).filter(
            IndustryBenchmark.industry_code.in_(affected_codes)
        ).delete(synchronize_session=False)

    now = datetime.now(UTC)
    new_rows: list[IndustryBenchmark] = []
    for (code, year, metric), values in buckets.items():
        summary = five_point_summary(values)
        new_rows.append(
            IndustryBenchmark(
                industry_code=code,
                metric_name=metric,
                period_year=year,
                p10=summary["p10"],
                p25=summary["p25"],
                p50=summary["p50"],
                p75=summary["p75"],
                p90=summary["p90"],
                sample_size=len(values),
                computed_at=now,
            )
        )

    db.add_all(new_rows)
    db.commit()

    return {"industries": len(affected_codes), "metric_rows": len(new_rows)}
