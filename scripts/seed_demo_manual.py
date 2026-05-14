"""Deterministic manual demo seed for the analyst workflow.

This seed path intentionally uses the public ``POST /report/manual`` API
instead of writing SQL directly. It creates a small, repeatable company-year
dataset that exercises company profiles, evidence anchors, period metadata,
and framework comparison without requiring network PDF downloads.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.schemas import ManualReportInput

DEFAULT_API_BASE = os.environ.get("API_BASE", "http://localhost:8000")
DEFAULT_TIMEOUT = float(os.environ.get("SEED_TIMEOUT", "60"))


@dataclass(frozen=True)
class DemoManualRecord:
    slug: str
    payload: ManualReportInput


def _source_url(company_slug: str, year: int, document_slug: str) -> str:
    return f"https://demo.local/disclosures/{company_slug}/{year}-{document_slug}"


def _evidence(
    *,
    company_slug: str,
    year: int,
    document_type: str,
    metric: str,
    page: int,
    snippet: str,
) -> dict[str, Any]:
    return {
        "metric": metric,
        "source": _source_url(company_slug, year, document_type.replace("_", "-")),
        "page": page,
        "snippet": snippet,
        "source_type": document_type,
        "extraction_method": "demo_manual_seed",
        "confidence": 0.99,
    }


def _record(
    *,
    company_slug: str,
    company_name: str,
    year: int,
    source_document_type: str,
    industry_code: str,
    industry_sector: str,
    scope1: float,
    scope2: float,
    scope3: float,
    energy: float,
    renewable_pct: float,
    water: float,
    waste_recycled_pct: float,
    revenue: float,
    taxonomy_revenue_pct: float,
    capex: float,
    taxonomy_capex_pct: float,
    employees: int,
    female_pct: float,
    primary_activities: list[str],
) -> DemoManualRecord:
    source_url = _source_url(company_slug, year, source_document_type.replace("_", "-"))
    label = f"FY {year}"
    evidence_summary = [
        _evidence(
            company_slug=company_slug,
            year=year,
            document_type=source_document_type,
            metric="scope1_co2e_tonnes",
            page=18,
            snippet=f"{label} Scope 1 emissions were disclosed as {scope1:,.0f} tCO2e.",
        ),
        _evidence(
            company_slug=company_slug,
            year=year,
            document_type=source_document_type,
            metric="renewable_energy_pct",
            page=24,
            snippet=f"Renewable electricity reached {renewable_pct:.1f}% for {label}.",
        ),
        _evidence(
            company_slug=company_slug,
            year=year,
            document_type=source_document_type,
            metric="taxonomy_aligned_revenue_pct",
            page=31,
            snippet=(
                f"Taxonomy-aligned revenue was reported at "
                f"{taxonomy_revenue_pct:.1f}% for {label}."
            ),
        ),
        _evidence(
            company_slug=company_slug,
            year=year,
            document_type=source_document_type,
            metric="total_employees",
            page=42,
            snippet=f"Average employees for {label} were disclosed as {employees:,}.",
        ),
    ]
    return DemoManualRecord(
        slug=f"{company_slug}-{year}",
        payload=ManualReportInput(
            company_name=company_name,
            report_year=year,
            reporting_period_label=label,
            reporting_period_type="annual",
            source_document_type=source_document_type,
            industry_code=industry_code,
            industry_sector=industry_sector,
            source_url=source_url,
            scope1_co2e_tonnes=scope1,
            scope2_co2e_tonnes=scope2,
            scope3_co2e_tonnes=scope3,
            energy_consumption_mwh=energy,
            renewable_energy_pct=renewable_pct,
            water_usage_m3=water,
            waste_recycled_pct=waste_recycled_pct,
            total_revenue_eur=revenue,
            taxonomy_aligned_revenue_pct=taxonomy_revenue_pct,
            total_capex_eur=capex,
            taxonomy_aligned_capex_pct=taxonomy_capex_pct,
            total_employees=employees,
            female_pct=female_pct,
            primary_activities=primary_activities,
            evidence_summary=evidence_summary,
        ),
    )


DEMO_RECORDS: tuple[DemoManualRecord, ...] = (
    _record(
        company_slug="demo-utility-grid-ag",
        company_name="Demo Utility Grid AG",
        year=2022,
        source_document_type="sustainability_report",
        industry_code="D35.11",
        industry_sector="Electricity production",
        scope1=1240000.0,
        scope2=188000.0,
        scope3=2950000.0,
        energy=7800000.0,
        renewable_pct=46.2,
        water=1900000.0,
        waste_recycled_pct=62.0,
        revenue=5200000000.0,
        taxonomy_revenue_pct=28.0,
        capex=1100000000.0,
        taxonomy_capex_pct=36.0,
        employees=6200,
        female_pct=31.0,
        primary_activities=["wind_onshore", "solar_pv", "hydroelectricity"],
    ),
    _record(
        company_slug="demo-utility-grid-ag",
        company_name="Demo Utility Grid AG",
        year=2023,
        source_document_type="sustainability_report",
        industry_code="D35.11",
        industry_sector="Electricity production",
        scope1=1110000.0,
        scope2=161000.0,
        scope3=2820000.0,
        energy=7950000.0,
        renewable_pct=54.8,
        water=1820000.0,
        waste_recycled_pct=66.5,
        revenue=5580000000.0,
        taxonomy_revenue_pct=34.0,
        capex=1260000000.0,
        taxonomy_capex_pct=42.5,
        employees=6380,
        female_pct=32.6,
        primary_activities=["wind_onshore", "solar_pv", "hydroelectricity"],
    ),
    _record(
        company_slug="demo-utility-grid-ag",
        company_name="Demo Utility Grid AG",
        year=2024,
        source_document_type="sustainability_report",
        industry_code="D35.11",
        industry_sector="Electricity production",
        scope1=970000.0,
        scope2=129000.0,
        scope3=2690000.0,
        energy=8120000.0,
        renewable_pct=63.4,
        water=1710000.0,
        waste_recycled_pct=70.0,
        revenue=5900000000.0,
        taxonomy_revenue_pct=41.0,
        capex=1390000000.0,
        taxonomy_capex_pct=49.0,
        employees=6510,
        female_pct=34.1,
        primary_activities=["wind_onshore", "solar_pv", "hydroelectricity"],
    ),
    _record(
        company_slug="demo-battery-materials-se",
        company_name="Demo Battery Materials SE",
        year=2023,
        source_document_type="annual_sustainability_report",
        industry_code="C27.20",
        industry_sector="Battery manufacturing",
        scope1=84000.0,
        scope2=126000.0,
        scope3=980000.0,
        energy=890000.0,
        renewable_pct=38.0,
        water=510000.0,
        waste_recycled_pct=71.0,
        revenue=2300000000.0,
        taxonomy_revenue_pct=19.5,
        capex=700000000.0,
        taxonomy_capex_pct=28.0,
        employees=3800,
        female_pct=42.5,
        primary_activities=["battery_manufacturing", "energy_storage"],
    ),
    _record(
        company_slug="demo-battery-materials-se",
        company_name="Demo Battery Materials SE",
        year=2024,
        source_document_type="annual_sustainability_report",
        industry_code="C27.20",
        industry_sector="Battery manufacturing",
        scope1=79000.0,
        scope2=104000.0,
        scope3=940000.0,
        energy=925000.0,
        renewable_pct=47.5,
        water=485000.0,
        waste_recycled_pct=76.0,
        revenue=2620000000.0,
        taxonomy_revenue_pct=25.0,
        capex=760000000.0,
        taxonomy_capex_pct=34.0,
        employees=4050,
        female_pct=43.8,
        primary_activities=["battery_manufacturing", "energy_storage"],
    ),
)


def demo_records() -> list[DemoManualRecord]:
    return list(DEMO_RECORDS)


def _normalize_filter_values(values: list[str] | None) -> set[str]:
    normalized: set[str] = set()
    for value in values or []:
        for token in value.split(","):
            cleaned = token.strip().lower()
            if cleaned:
                normalized.add(cleaned)
    return normalized


def filter_demo_records(
    records: list[DemoManualRecord],
    *,
    slugs: list[str] | None = None,
    company_names: list[str] | None = None,
    only_filters: list[str] | None = None,
) -> list[DemoManualRecord]:
    selected = records
    normalized_only = _normalize_filter_values(only_filters)
    if normalized_only:
        return [
            record
            for record in selected
            if record.slug.lower() in normalized_only
            or record.payload.company_name.lower() in normalized_only
        ]

    normalized_slugs = _normalize_filter_values(slugs)
    if normalized_slugs:
        selected = [record for record in selected if record.slug.lower() in normalized_slugs]

    normalized_names = _normalize_filter_values(company_names)
    if normalized_names:
        selected = [
            record
            for record in selected
            if record.payload.company_name.lower() in normalized_names
        ]

    return selected


def _manual_url(api_base: str) -> str:
    return f"{api_base.rstrip('/')}/report/manual"


def _compare_url(api_base: str, company_name: str, year: int) -> str:
    encoded = quote(company_name, safe="")
    return f"{api_base.rstrip('/')}/frameworks/compare?company_name={encoded}&report_year={year}"


def _raise_for_status(response: httpx.Response, *, action: str) -> None:
    status_code = getattr(response, "status_code", 0)
    if status_code < 400:
        return
    body = getattr(response, "text", "")
    raise RuntimeError(f"{action} failed with HTTP {status_code}: {body}")


def _post_manual_record(client: httpx.Client, api_base: str, record: DemoManualRecord) -> dict[str, Any]:
    payload = record.payload.model_dump(mode="json")
    response = client.post(_manual_url(api_base), json=payload)
    _raise_for_status(response, action=f"seed {record.slug}")
    return response.json()


def _run_framework_compare(
    client: httpx.Client,
    api_base: str,
    *,
    company_name: str,
    year: int,
) -> dict[str, Any]:
    response = client.get(_compare_url(api_base, company_name, year))
    _raise_for_status(response, action=f"framework compare {company_name} {year}")
    return response.json()


def _latest_records_by_company(records: list[DemoManualRecord]) -> list[DemoManualRecord]:
    latest: dict[str, DemoManualRecord] = {}
    for record in records:
        company_name = record.payload.company_name
        current = latest.get(company_name)
        if current is None or record.payload.report_year > current.payload.report_year:
            latest[company_name] = record
    return list(latest.values())


def seed_demo_manual(
    *,
    api_base: str = DEFAULT_API_BASE,
    dry_run: bool = False,
    score_frameworks: bool = True,
    slugs: list[str] | None = None,
    company_names: list[str] | None = None,
    only_filters: list[str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    selected = filter_demo_records(
        demo_records(),
        slugs=slugs,
        company_names=company_names,
        only_filters=only_filters,
    )
    if not selected:
        raise ValueError("no demo records matched the selected filters")

    summary: dict[str, Any] = {
        "selected": len(selected),
        "posted": 0,
        "framework_compares": 0,
        "records": [record.slug for record in selected],
    }

    if dry_run:
        for record in selected:
            payload = record.payload.model_dump(mode="json")
            print(json.dumps({"slug": record.slug, "payload": payload}, ensure_ascii=False))
        return summary

    with httpx.Client(timeout=timeout) as client:
        for record in selected:
            result = _post_manual_record(client, api_base, record)
            summary["posted"] += 1
            print(f"seeded {result['company_name']} {result['report_year']} from {record.slug}")

        if score_frameworks:
            for record in _latest_records_by_company(selected):
                _run_framework_compare(
                    client,
                    api_base,
                    company_name=record.payload.company_name,
                    year=record.payload.report_year,
                )
                summary["framework_compares"] += 1
                print(f"compared frameworks for {record.payload.company_name} {record.payload.report_year}")

    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed deterministic manual ESG demo records.")
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-framework-compare", action="store_true")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--slug", action="append", help="Seed only matching record slug(s).")
    parser.add_argument("--company", action="append", help="Seed only matching company name(s).")
    parser.add_argument("--only", action="append", help="Seed matching slug or company; comma-separated allowed.")
    args = parser.parse_args(argv)

    try:
        summary = seed_demo_manual(
            api_base=args.api_base,
            dry_run=args.dry_run,
            score_frameworks=not args.skip_framework_compare,
            slugs=args.slug,
            company_names=args.company,
            only_filters=args.only,
            timeout=args.timeout,
        )
    except ValueError as exc:
        print(str(exc))
        return 2
    except RuntimeError as exc:
        print(str(exc))
        return 1

    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
