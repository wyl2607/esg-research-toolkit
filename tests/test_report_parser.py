import json
from collections.abc import Callable
from collections.abc import Generator
from unittest.mock import patch
import os

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from core.config import settings
from core.database import Base, get_db
from core.schemas import CompanyESGData, ManualReportInput, MergePreviewRequest, MergeSourceInput
from esg_frameworks.api import _SCORERS
from esg_frameworks.schemas import DimensionScore, FrameworkScoreResult
from esg_frameworks.storage import list_framework_results, save_framework_result
from report_parser.api import (
    _upload_evidence_summary,
    list_companies_with_year_coverage,
    list_company_reports,
    get_company_history,
    get_company_profile,
    get_dashboard_stats,
    preview_merge,
    router as report_router,
    save_manual_report,
)
from report_parser.disclosures_api import router as disclosures_router
from report_parser.analyzer import AIExtractionError, analyze_esg_data
from report_parser.extractor import extract_text_from_pdf
from report_parser.storage import (
    CompanyReport,
    get_report,
    list_reports,
    list_source_reports_for_company_year,
    save_report,
)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def make_company_data() -> Callable[..., CompanyESGData]:
    def _make_company_data(**overrides: object) -> CompanyESGData:
        data = {
            "company_name": "Example Corp",
            "report_year": 2024,
            "scope1_co2e_tonnes": 123.4,
            "scope2_co2e_tonnes": 56.7,
            "energy_consumption_mwh": 890.1,
            "renewable_energy_pct": 42.0,
            "total_employees": 250,
            "female_pct": 48.5,
            "primary_activities": ["solar_pv"],
        }
        data.update(overrides)
        return CompanyESGData(**data)

    return _make_company_data


def test_extract_text_from_pdf_prefers_pymupdf() -> None:
    pymupdf_text = "A" * 120
    with (
        patch("report_parser.extractor._extract_with_pymupdf", return_value=pymupdf_text) as mock_pymupdf,
        patch("report_parser.extractor._extract_with_pdfplumber") as mock_pdfplumber,
    ):
        result = extract_text_from_pdf("sample.pdf")  # type: ignore[arg-type]

    assert result == pymupdf_text
    mock_pymupdf.assert_called_once()
    mock_pdfplumber.assert_not_called()


def test_extract_text_from_pdf_fallback_to_pdfplumber() -> None:
    with (
        patch(
            "report_parser.extractor._extract_with_pymupdf",
            side_effect=FileNotFoundError("missing"),
        ),
        patch(
            "report_parser.extractor._extract_with_pdfplumber",
            return_value="Fallback extracted text",
        ),
    ):
        result = extract_text_from_pdf("missing.pdf")  # type: ignore[arg-type]

    assert result == "Fallback extracted text"


def test_analyze_esg_data_with_mock_openai() -> None:
    report_text = "A" * 9000
    response_payload = {
        "company_name": "Example Corp",
        "report_year": 2023,
        "scope1_co2e_tonnes": 12.5,
        "scope2_co2e_tonnes": 8.0,
        "scope3_co2e_tonnes": None,
        "energy_consumption_mwh": 1234.5,
        "renewable_energy_pct": 67.8,
        "water_usage_m3": 999.0,
        "waste_recycled_pct": 55.0,
        "total_revenue_eur": 1000000.0,
        "taxonomy_aligned_revenue_pct": 21.0,
        "total_capex_eur": 500000.0,
        "taxonomy_aligned_capex_pct": 34.0,
        "total_employees": 321,
        "female_pct": 49.5,
        "primary_activities": ["solar_pv", "wind_onshore"],
    }

    with patch(
        "report_parser.analyzer.complete",
        return_value=f"```json\n{json.dumps(response_payload)}\n```",
    ) as mock_complete:
        result = analyze_esg_data(report_text)

    assert isinstance(result, CompanyESGData)
    assert result.company_name == "Example Corp"
    assert result.report_year == 2023
    assert result.renewable_energy_pct == pytest.approx(67.8)
    assert result.primary_activities == ["solar_pv", "wind_onshore"]
    mock_complete.assert_called_once()

    system_arg, user_arg = mock_complete.call_args.args[:2]
    assert "Extract ESG metrics" in system_arg
    assert "Corporate Report Text:" in user_arg
    assert report_text[:100] in user_arg  # head section included
    assert mock_complete.call_args.kwargs["max_tokens"] == 2048


def test_analyze_esg_data_invalid_json() -> None:
    # AI 返回无法解析的 JSON，且文本中无可识别的 ESG 字段 → 抛出 AIExtractionError
    with patch("report_parser.analyzer.complete", return_value="not json"):
        with pytest.raises(AIExtractionError):
            analyze_esg_data("unstructured text without any ESG keywords")


def test_analyze_esg_data_invalid_json_with_regex_fallback() -> None:
    # AI 返回无效 JSON，但文本包含中文 Scope 数据 → regex fallback 成功返回部分数据
    text = "宁德时代 2024年报告\nScope 1 排放: 93,440 tCO2e\n范围二: 12,500 tCO2e"
    with patch("report_parser.analyzer.complete", return_value="not json"):
        result = analyze_esg_data(text, filename="CATL_2024.pdf")

    assert result.company_name == "CATL"
    assert result.report_year == 2024
    assert result.scope1_co2e_tonnes == pytest.approx(93440.0)
    assert result.scope2_co2e_tonnes == pytest.approx(12500.0)


def test_analyze_esg_data_ai_error_uses_regex_fallback() -> None:
    text = (
        "Example Corp 2024 Sustainability Report\n"
        "Scope 1 emissions: 10,500 tCO2e\n"
        "Renewable energy ratio: 38.5%\n"
        "Total employees: 1200"
    )
    with patch("report_parser.analyzer.complete", side_effect=Exception("401 authentication failed")):
        result = analyze_esg_data(text, filename="Example_2024.pdf")

    assert result.company_name == "Example"
    assert result.scope1_co2e_tonnes == pytest.approx(10500.0)
    assert result.renewable_energy_pct == pytest.approx(38.5)
    assert result.total_employees == 1200


def test_analyze_esg_data_regex_only_mode_extracts_extended_metrics() -> None:
    text = (
        "CATL 2024 ESG Report\n"
        "Scope 1: 93,440 tCO2e\n"
        "Scope 2: 12,500 tCO2e\n"
        "Energy consumption: 1,000,000 MWh\n"
        "Renewable energy percentage: 45.6%\n"
        "Water consumption: 12,345 m3\n"
        "Waste recycling rate: 81.2%\n"
        "Taxonomy-aligned revenue: 22.5%\n"
        "Taxonomy-aligned CapEx: 18.1%\n"
        "Total employees: 34,500\n"
        "Female employee ratio: 36.4%\n"
        "Business includes battery manufacturing and solar PV."
    )

    with patch.dict(os.environ, {"PARSER_REGEX_ONLY": "1"}), patch("report_parser.analyzer.complete") as mock_complete:
        result = analyze_esg_data(text, filename="CATL_2024.pdf")

    mock_complete.assert_not_called()
    assert result.scope1_co2e_tonnes == pytest.approx(93440.0)
    assert result.scope2_co2e_tonnes == pytest.approx(12500.0)
    assert result.energy_consumption_mwh == pytest.approx(1000000.0)
    assert result.renewable_energy_pct == pytest.approx(45.6)
    assert result.water_usage_m3 == pytest.approx(12345.0)
    assert result.waste_recycled_pct == pytest.approx(81.2)
    assert result.taxonomy_aligned_revenue_pct == pytest.approx(22.5)
    assert result.taxonomy_aligned_capex_pct == pytest.approx(18.1)
    assert result.total_employees == 34500
    assert result.female_pct == pytest.approx(36.4)
    assert "battery_manufacturing" in result.primary_activities
    assert "solar_pv" in result.primary_activities


def test_save_and_get_report(
    db_session: Session,
    make_company_data,
) -> None:
    data = make_company_data()

    saved = save_report(db_session, data, pdf_filename="example-report.pdf")
    loaded = get_report(db_session, company_name="Example Corp", report_year=2024)

    assert isinstance(saved, CompanyReport)
    assert loaded is not None
    assert loaded.id == saved.id
    assert loaded.company_name == "Example Corp"
    assert loaded.report_year == 2024
    assert loaded.pdf_filename == "example-report.pdf"
    assert loaded.scope1_co2e_tonnes == pytest.approx(123.4)
    assert loaded.primary_activities == json.dumps(["solar_pv"])


def test_upload_evidence_summary_prefers_analyzer_evidence(make_company_data: Callable[..., CompanyESGData]) -> None:
    data = make_company_data(
        evidence_summary=[
            {
                "metric": "scope1_co2e_tonnes",
                "source": "sample.pdf",
                "page": 12,
                "snippet": "Scope 1 emissions were 123.4 tonnes.",
            }
        ]
    )

    summary = _upload_evidence_summary(data, file_hash="abc123")

    assert summary == data.evidence_summary


def test_upload_evidence_summary_falls_back_to_non_null_metrics(make_company_data: Callable[..., CompanyESGData]) -> None:
    data = make_company_data(
        scope3_co2e_tonnes=None,
        water_usage_m3=None,
        evidence_summary=[],
    )

    summary = _upload_evidence_summary(data, file_hash="abc123")

    assert any(
        item["metric"] == "scope1_co2e_tonnes"
        and item["source_type"] == "pdf"
        and item["file_hash"] == "abc123"
        and item["source_doc_id"] == "abc123"
        and item["extraction_method"] == "pdf_text"
        for item in summary
    )
    assert any(
        item["metric"] == "scope2_co2e_tonnes"
        and item["source_type"] == "pdf"
        and item["file_hash"] == "abc123"
        for item in summary
    )
    assert any(
        item["metric"] == "renewable_energy_pct"
        and item["source_type"] == "pdf"
        and item["file_hash"] == "abc123"
        for item in summary
    )
    assert all(item["metric"] != "scope3_co2e_tonnes" for item in summary)
    assert all(item["metric"] != "water_usage_m3" for item in summary)


def test_save_framework_result_allows_new_row_when_framework_version_changes(db_session: Session) -> None:
    result = FrameworkScoreResult(
        framework="EU Taxonomy 2020",
        framework_id="eu_taxonomy",
        framework_version="2020/852",
        company_name="Version Corp",
        report_year=2024,
        total_score=0.66,
        grade="B",
        dimensions=[DimensionScore(name="Climate", score=0.66, weight=1.0, disclosed=1, total=1)],
        gaps=[],
        recommendations=[],
        coverage_pct=100.0,
    )

    first = save_framework_result(db_session, result, framework_version=result.framework_version)
    second = save_framework_result(
        db_session,
        result.model_copy(update={"framework_version": "2021/2139"}),
        framework_version="2021/2139",
    )
    rows = list_framework_results(db_session, company_name="Version Corp", report_year=2024)

    assert first.id != second.id
    assert len(rows) == 2
    assert {row.framework_version for row in rows} == {"2020/852", "2021/2139"}


def test_list_reports(
    db_session: Session,
    make_company_data,
) -> None:
    first = make_company_data(company_name="Alpha Energy", report_year=2023)
    second = make_company_data(company_name="Beta Renewables", report_year=2024)

    save_report(db_session, first, pdf_filename="alpha.pdf")
    save_report(db_session, second, pdf_filename="beta.pdf")

    reports = list_reports(db_session)

    assert len(reports) == 2
    assert {(report.company_name, report.report_year) for report in reports} == {
        ("Alpha Energy", 2023),
        ("Beta Renewables", 2024),
    }


def test_list_company_reports_keeps_legacy_and_metric_fields(
    db_session: Session,
    make_company_data,
) -> None:
    save_report(
        db_session,
        make_company_data(company_name="Legacy Check", report_year=2025),
        pdf_filename="legacy-check.pdf",
    )

    rows = list_company_reports(db=db_session)
    assert len(rows) == 1

    row = rows[0]
    assert row["company_name"] == "Legacy Check"
    assert row["report_year"] == 2025
    assert row["pdf_filename"] == "legacy-check.pdf"
    assert isinstance(row["created_at"], str)
    assert "T" in row["created_at"]

    # keep full metrics payload for frontend dashboards and comparisons
    assert row["scope1_co2e_tonnes"] == pytest.approx(123.4)
    assert row["taxonomy_aligned_revenue_pct"] is None
    assert row["primary_activities"] == ["solar_pv"]

    assert row["reporting_period_label"] == "2025"
    assert row["reporting_period_type"] == "annual"
    assert row["source_document_type"] == "sustainability_report"
    assert row["period"]["legacy_report_year"] == 2025
    assert row["period"]["label"] == "2025"
    assert row["period"]["type"] == "annual"
    assert row["period"]["source_document_type"] == "sustainability_report"
    assert row["evidence_summary"] == []


def test_list_companies_v2_returns_imported_and_suggested_years(
    db_session: Session,
    make_company_data,
) -> None:
    save_report(
        db_session,
        make_company_data(company_name="Multi Year Corp", report_year=2022),
        pdf_filename="multi-2022.pdf",
    )
    save_report(
        db_session,
        make_company_data(company_name="Multi Year Corp", report_year=2024),
        pdf_filename="multi-2024.pdf",
    )
    save_report(
        db_session,
        make_company_data(company_name="Single Year Co", report_year=2023),
        pdf_filename="single-2023.pdf",
    )

    rows = list_companies_with_year_coverage(db=db_session, suggested_span=5)
    by_name = {r["company_name"]: r for r in rows}

    assert by_name["Multi Year Corp"]["imported_years"] == [2024, 2022]
    assert by_name["Single Year Co"]["imported_years"] == [2023]

    # suggested_years is the union of the DB years and the rolling 5-year
    # window, sorted descending — it must be a superset of imported_years
    # so the picker always has a place to render the imported chip.
    for name in ("Multi Year Corp", "Single Year Co"):
        suggested = by_name[name]["suggested_years"]
        assert suggested == sorted(set(suggested), reverse=True)
        assert set(by_name[name]["imported_years"]).issubset(set(suggested))


def test_list_companies_v2_rejects_unbounded_suggested_span(
    make_company_data,
) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db_session = TestingSessionLocal()
    app = FastAPI()
    app.include_router(report_router)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        save_report(
            db_session,
            make_company_data(company_name="Bounded Span AG", report_year=2024),
            pdf_filename="bounded-span.pdf",
        )

        with TestClient(app) as client:
            response = client.get("/report/companies/v2?suggested_span=1000000")

        assert response.status_code == 422
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)


def test_get_company_report_rejects_out_of_range_report_year(make_company_data) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db_session = testing_session_local()
    app = FastAPI()
    app.include_router(report_router)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        save_report(
            db_session,
            make_company_data(company_name="Year Bound Corp", report_year=2024),
            pdf_filename="year-bound.pdf",
        )

        with TestClient(app) as client:
            response = client.get("/report/companies/Year%20Bound%20Corp/9223372036854775808")

        assert response.status_code == 422
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)


def test_disclosures_fetch_creates_pending_item_and_lists_it() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db_session = testing_session_local()
    app = FastAPI()
    app.include_router(disclosures_router)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        with TestClient(app) as client:
            fetch_response = client.post(
                "/disclosures/fetch",
                json={
                    "company_name": "BASF",
                    "report_year": 2022,
                },
            )
            list_response = client.get(
                "/disclosures/pending",
                params={"company_name": "BASF", "report_year": 2022},
            )

        assert fetch_response.status_code == 202
        fetch_payload = fetch_response.json()
        assert fetch_payload["status"] == "queued"
        assert fetch_payload["pending"]["company_name"] == "BASF SE"
        assert fetch_payload["pending"]["report_year"] == 2022
        assert "https://" in fetch_payload["pending"]["source_url"]

        assert list_response.status_code == 200
        listed = list_response.json()
        assert len(listed) == 1
        assert listed[0]["id"] == fetch_payload["pending"]["id"]
        assert listed[0]["status"] == "pending"
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)


def test_disclosures_fetch_upserts_same_source_without_duplication() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db_session = testing_session_local()
    app = FastAPI()
    app.include_router(disclosures_router)
    app.dependency_overrides[get_db] = lambda: db_session

    source_url = "https://example.com/basf-2022.pdf"
    try:
        with TestClient(app) as client:
            first = client.post(
                "/disclosures/fetch",
                json={
                    "company_name": "BASF",
                    "report_year": 2022,
                    "source_url": source_url,
                },
            )
            second = client.post(
                "/disclosures/fetch",
                json={
                    "company_name": "BASF",
                    "report_year": 2022,
                    "source_url": source_url,
                },
            )
            listing = client.get(
                "/disclosures/pending",
                params={"company_name": "BASF", "report_year": 2022},
            )

        assert first.status_code == 202
        assert second.status_code == 202
        assert first.json()["created"] is True
        assert second.json()["created"] is False
        assert listing.status_code == 200
        assert len(listing.json()) == 1
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.mark.parametrize(
    ("source_type", "expected_fragment"),
    [
        ("html", "/sustainability/2022"),
        ("filing", "sec.gov/cgi-bin/browse-edgar"),
    ],
)
def test_disclosures_fetch_uses_source_type_aware_default_source_url(
    source_type: str, expected_fragment: str
) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db_session = testing_session_local()
    app = FastAPI()
    app.include_router(disclosures_router)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        with TestClient(app) as client:
            response = client.post(
                "/disclosures/fetch",
                json={
                    "company_name": "BASF",
                    "report_year": 2022,
                    "source_type": source_type,
                },
            )

        assert response.status_code == 202
        payload = response.json()
        assert payload["pending"]["source_type"] == source_type
        assert expected_fragment in payload["pending"]["source_url"]
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)


def test_disclosures_fetch_supports_official_source_hints() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db_session = testing_session_local()
    app = FastAPI()
    app.include_router(disclosures_router)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        with TestClient(app) as client:
            sec_response = client.post(
                "/disclosures/fetch",
                json={
                    "company_name": "BASF",
                    "report_year": 2022,
                    "source_type": "filing",
                    "source_hint": "sec_edgar",
                },
            )
            hkex_response = client.post(
                "/disclosures/fetch",
                json={
                    "company_name": "BASF",
                    "report_year": 2022,
                    "source_type": "filing",
                    "source_hint": "hkex",
                },
            )
            csrc_response = client.post(
                "/disclosures/fetch",
                json={
                    "company_name": "BASF",
                    "report_year": 2022,
                    "source_type": "filing",
                    "source_hint": "csrc",
                },
            )

        assert sec_response.status_code == 202
        assert hkex_response.status_code == 202
        assert csrc_response.status_code == 202
        assert "sec.gov" in sec_response.json()["pending"]["source_url"]
        assert "hkexnews.hk" in hkex_response.json()["pending"]["source_url"]
        assert "cninfo.com.cn" in csrc_response.json()["pending"]["source_url"]
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)


def test_disclosures_fetch_source_url_override_wins_over_source_hint() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db_session = testing_session_local()
    app = FastAPI()
    app.include_router(disclosures_router)
    app.dependency_overrides[get_db] = lambda: db_session

    custom_url = "https://example.com/custom-source.pdf"
    try:
        with TestClient(app) as client:
            response = client.post(
                "/disclosures/fetch",
                json={
                    "company_name": "BASF",
                    "report_year": 2022,
                    "source_url": custom_url,
                    "source_hint": "sec_edgar",
                },
            )

        assert response.status_code == 202
        assert response.json()["pending"]["source_url"] == custom_url
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)


def test_disclosures_fetch_rejects_non_http_source_url() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db_session = testing_session_local()
    app = FastAPI()
    app.include_router(disclosures_router)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        with TestClient(app) as client:
            response = client.post(
                "/disclosures/fetch",
                json={
                    "company_name": "BASF",
                    "report_year": 2022,
                    "source_url": "ftp://example.com/basf.pdf",
                },
            )

        assert response.status_code == 422
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)


def test_disclosures_approve_merges_pending_report() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db_session = testing_session_local()
    app = FastAPI()
    app.include_router(disclosures_router)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        with patch.dict(os.environ, {"ESG_CONTRACT_TEST_MODE": "1"}):
            with TestClient(app) as client:
                queued = client.post(
                    "/disclosures/fetch",
                    json={
                        "company_name": "BASF",
                        "report_year": 2022,
                        "source_url": "https://example.com/basf-2022.pdf",
                    },
                )
                pending_id = queued.json()["pending"]["id"]
                approved = client.post(
                    f"/disclosures/{pending_id}/approve",
                    json={"review_note": "reviewed-by-test"},
                )

        assert queued.status_code == 202
        assert approved.status_code == 200
        body = approved.json()
        assert body["status"] == "approved"
        assert body["pending"]["status"] == "approved"
        assert body["pending"]["review_note"] == "reviewed-by-test"
        assert body["merged_report"]["company_name"] == "BASF SE"
        assert body["merged_report"]["report_year"] == 2022

        merged = get_report(db_session, company_name="BASF SE", report_year=2022)
        assert merged is not None
        assert merged.source_url == "https://example.com/basf-2022.pdf"
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)


def test_disclosures_reject_marks_pending_without_merge() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db_session = testing_session_local()
    app = FastAPI()
    app.include_router(disclosures_router)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        with patch.dict(os.environ, {"ESG_CONTRACT_TEST_MODE": "1"}):
            with TestClient(app) as client:
                queued = client.post(
                    "/disclosures/fetch",
                    json={
                        "company_name": "BASF",
                        "report_year": 2023,
                        "source_url": "https://example.com/basf-2023.pdf",
                    },
                )
                pending_id = queued.json()["pending"]["id"]
                rejected = client.post(
                    f"/disclosures/{pending_id}/reject",
                    json={"review_note": "not-relevant"},
                )

        assert queued.status_code == 202
        assert rejected.status_code == 200
        body = rejected.json()
        assert body["status"] == "rejected"
        assert body["pending"]["status"] == "rejected"
        assert body["pending"]["review_note"] == "not-relevant"
        assert body["merged_report"] is None

        merged = get_report(db_session, company_name="BASF SE", report_year=2023)
        assert merged is None
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)


def test_disclosures_review_endpoints_enforce_final_status_conflicts() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db_session = testing_session_local()
    app = FastAPI()
    app.include_router(disclosures_router)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        with patch.dict(os.environ, {"ESG_CONTRACT_TEST_MODE": "1"}):
            with TestClient(app) as client:
                approved_seed = client.post(
                    "/disclosures/fetch",
                    json={
                        "company_name": "BASF",
                        "report_year": 2024,
                        "source_url": "https://example.com/basf-2024.pdf",
                    },
                )
                approved_id = approved_seed.json()["pending"]["id"]
                approve_res = client.post(f"/disclosures/{approved_id}/approve", json={})
                reject_after_approve = client.post(f"/disclosures/{approved_id}/reject", json={})

                rejected_seed = client.post(
                    "/disclosures/fetch",
                    json={
                        "company_name": "BASF",
                        "report_year": 2025,
                        "source_url": "https://example.com/basf-2025.pdf",
                    },
                )
                rejected_id = rejected_seed.json()["pending"]["id"]
                reject_res = client.post(f"/disclosures/{rejected_id}/reject", json={})
                approve_after_reject = client.post(f"/disclosures/{rejected_id}/approve", json={})

        assert approve_res.status_code == 200
        assert reject_after_approve.status_code == 409
        assert reject_after_approve.json()["detail"] == "Approved disclosure cannot be rejected"

        assert reject_res.status_code == 200
        assert approve_after_reject.status_code == 409
        assert approve_after_reject.json()["detail"] == "Rejected disclosure cannot be approved"
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)


def test_disclosures_approve_returns_400_for_fail_closed_validation() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db_session = testing_session_local()
    app = FastAPI()
    app.include_router(disclosures_router)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        with patch.dict(os.environ, {"ESG_CONTRACT_TEST_MODE": "1"}):
            with TestClient(app) as client:
                queued = client.post(
                    "/disclosures/fetch",
                    json={
                        "company_name": "Contract Demo AG",
                        "report_year": 1900,
                        "source_url": "https://example.com/contract-demo-1900.pdf",
                    },
                )
                pending_id = queued.json()["pending"]["id"]
                approved = client.post(f"/disclosures/{pending_id}/approve", json={})

        assert queued.status_code == 202
        assert approved.status_code == 400
        assert "L0 validation failed" in approved.json()["detail"]
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)


def test_save_manual_report_persists_period_and_manual_evidence(
    db_session: Session,
) -> None:
    payload = ManualReportInput(
        company_name="Manual Demo AG",
        report_year=2025,
        reporting_period_label="FY2025 draft",
        reporting_period_type="annual",
        source_document_type="manual_case",
        source_url="https://example.com/manual-demo",
        scope1_co2e_tonnes=200.0,
        renewable_energy_pct=51.5,
        total_employees=980,
        primary_activities=["battery_manufacturing", "solar_pv"],
    )

    result = save_manual_report(payload=payload, db=db_session)

    assert result.company_name == "Manual Demo AG"
    assert result.reporting_period_label == "FY2025 draft"
    assert result.source_document_type == "manual_case"
    assert result.scope1_co2e_tonnes == pytest.approx(200.0)
    assert len(result.evidence_summary) >= 3
    assert {item["metric"] for item in result.evidence_summary} >= {
        "scope1_co2e_tonnes",
        "renewable_energy_pct",
        "total_employees",
    }

    profile = get_company_profile(company_name="Manual Demo AG", db=db_session)
    assert profile["latest_period"]["source_document_type"] == "manual_case"
    assert profile["evidence_summary"][0]["source_type"] == "manual_entry"
    assert profile["identity_provenance_summary"]["canonical_company_name"] == "Manual Demo AG"
    assert profile["identity_provenance_summary"]["has_alias_consolidation"] is False
    assert profile["identity_provenance_summary"]["latest_source_document_type"] == "manual_case"
    assert profile["identity_provenance_summary"]["source_priority_preview"] is None
    assert profile["identity_provenance_summary"]["merge_priority_preview"] is None
    assert profile["data_quality_summary"]["readiness_label"] == "draft"


def test_industry_classification_round_trip_via_profile_and_history_endpoints() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db_session = TestingSessionLocal()
    app = FastAPI()
    app.include_router(report_router)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        with TestClient(app) as client:
            manual_response = client.post(
                "/report/manual",
                json={
                    "company_name": "Industry Demo AG",
                    "report_year": 2024,
                    "industry_code": "D35.11",
                    "industry_sector": "Electricity production",
                },
            )
            profile_response = client.get("/report/companies/Industry Demo AG/profile")
            history_response = client.get("/report/companies/Industry Demo AG/history")

        assert manual_response.status_code == 200
        assert manual_response.json()["industry_code"] == "D35.11"
        assert manual_response.json()["industry_sector"] == "Electricity production"

        assert profile_response.status_code == 200
        assert history_response.status_code == 200

        profile_payload = profile_response.json()
        history_payload = history_response.json()

        assert profile_payload["industry_code"] == "D35.11"
        assert profile_payload["industry_sector"] == "Electricity production"
        assert profile_payload["latest_period"]["industry_code"] == "D35.11"
        assert profile_payload["latest_period"]["industry_sector"] == "Electricity production"

        assert history_payload["periods"][0]["industry_code"] == "D35.11"
        assert history_payload["periods"][0]["industry_sector"] == "Electricity production"
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)


def test_industry_classification_backward_compatible_for_legacy_records(
    make_company_data,
) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db_session = TestingSessionLocal()
    save_report(
        db_session,
        make_company_data(company_name="Legacy Industry Corp", report_year=2024),
        pdf_filename="legacy-industry.pdf",
    )

    app = FastAPI()
    app.include_router(report_router)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        with TestClient(app) as client:
            profile_response = client.get("/report/companies/Legacy Industry Corp/profile")
            history_response = client.get("/report/companies/Legacy Industry Corp/history")

        assert profile_response.status_code == 200
        assert history_response.status_code == 200

        profile_payload = profile_response.json()
        history_payload = history_response.json()

        assert "industry_code" in profile_payload
        assert "industry_sector" in profile_payload
        assert profile_payload["industry_code"] is None
        assert profile_payload["industry_sector"] is None
        assert "industry_code" in profile_payload["latest_period"]
        assert "industry_sector" in profile_payload["latest_period"]
        assert profile_payload["latest_period"]["industry_code"] is None
        assert profile_payload["latest_period"]["industry_sector"] is None

        assert "industry_code" in history_payload["periods"][0]
        assert "industry_sector" in history_payload["periods"][0]
        assert history_payload["periods"][0]["industry_code"] is None
        assert history_payload["periods"][0]["industry_sector"] is None
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)


def test_list_companies_by_industry_returns_matching_reports(
    make_company_data,
) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db_session = TestingSessionLocal()
    app = FastAPI()
    app.include_router(report_router)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        save_report(
            db_session,
            make_company_data(
                company_name="Util A AG",
                report_year=2024,
                industry_code="D35.11",
                industry_sector="Electricity production",
                scope1_co2e_tonnes=1000.0,
            ),
            source_document_type="sustainability_report",
        )
        save_report(
            db_session,
            make_company_data(
                company_name="Util B GmbH",
                report_year=2024,
                industry_code="D35.11",
                industry_sector="Electricity production",
                scope1_co2e_tonnes=2000.0,
            ),
            source_document_type="sustainability_report",
        )
        save_report(
            db_session,
            make_company_data(
                company_name="Steel X AG",
                report_year=2024,
                industry_code="C24.10",
                industry_sector="Basic iron and steel",
                scope1_co2e_tonnes=9999.0,
            ),
            source_document_type="annual_report",
        )

        with TestClient(app) as client:
            response = client.get("/report/companies/by-industry/D35.11")

        assert response.status_code == 200
        payload = response.json()
        assert payload["industry_code"] == "D35.11"
        assert payload["company_count"] == 2
        names = [company["company_name"] for company in payload["companies"]]
        assert "Util A AG" in names
        assert "Util B GmbH" in names
        assert "Steel X AG" not in names

        util_a = next(company for company in payload["companies"] if company["company_name"] == "Util A AG")
        assert util_a["metrics"]["scope1_co2e_tonnes"] == 1000.0
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)


def test_list_companies_by_industry_empty_returns_200_with_empty_payload(
) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db_session = TestingSessionLocal()

    app = FastAPI()
    app.include_router(report_router)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        with TestClient(app) as client:
            response = client.get("/report/companies/by-industry/Z99.99")

        assert response.status_code == 200
        payload = response.json()
        assert payload["industry_code"] == "Z99.99"
        assert payload["company_count"] == 0
        assert payload["companies"] == []
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)


def test_get_audit_trail_returns_matching_file_hash_row(make_company_data) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db_session = TestingSessionLocal()
    app = FastAPI()
    app.include_router(report_router)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        report = save_report(
            db_session,
            make_company_data(company_name="Trail Demo AG", report_year=2024),
            pdf_filename="trail-demo.pdf",
            file_hash="hash-trail-demo",
        )
        # extraction_runs is now auto-created by ensure_storage_schema; ensure
        # it exists for in-memory test DBs without colliding with the ORM table.
        db_session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS extraction_runs (
                    id INTEGER PRIMARY KEY,
                    company_report_id INTEGER,
                    file_hash TEXT,
                    run_kind TEXT,
                    model TEXT,
                    prompt_hash TEXT,
                    raw_response TEXT,
                    verdict TEXT,
                    applied BOOLEAN,
                    notes TEXT,
                    created_at TEXT
                )
                """
            )
        )
        db_session.execute(text("DELETE FROM extraction_runs"))
        db_session.execute(
            text(
                """
                INSERT INTO extraction_runs (
                    id, company_report_id, file_hash, run_kind, model, verdict, applied, notes, created_at
                ) VALUES (
                    :id, :company_report_id, :file_hash, :run_kind, :model, :verdict, :applied, :notes, :created_at
                )
                """
            ),
            {
                "id": 1,
                "company_report_id": None,
                "file_hash": "hash-trail-demo",
                "run_kind": "audit",
                "model": "gpt-4.1-mini",
                "verdict": "corrected",
                "applied": True,
                "notes": "Matched by file hash",
                "created_at": "2026-04-15T10:30:00+00:00",
            },
        )
        db_session.commit()

        with TestClient(app) as client:
            response = client.get(f"/report/{report.id}/audit-trail")

        assert response.status_code == 200
        assert response.json() == [
            {
                "id": 1,
                "run_kind": "audit",
                "model": "gpt-4.1-mini",
                "verdict": "corrected",
                "applied": True,
                "notes": "Matched by file hash",
                "created_at": "2026-04-15T10:30:00+00:00",
            }
        ]
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)


def test_alias_names_collapse_into_single_company_profile_and_listing(
    db_session: Session,
    make_company_data,
) -> None:
    save_report(
        db_session,
        make_company_data(
            company_name="catl",
            report_year=2024,
            scope1_co2e_tonnes=110.0,
            renewable_energy_pct=32.0,
        ),
        reporting_period_label="FY2024 quick extract",
        source_document_type="manual_case",
        evidence_summary=[{"metric": "scope1_co2e_tonnes", "source": "manual://catl"}],
    )
    save_report(
        db_session,
        make_company_data(
            company_name="Contemporary Amperex Technology Co., Limited",
            report_year=2024,
            scope1_co2e_tonnes=95.0,
            renewable_energy_pct=45.0,
            taxonomy_aligned_revenue_pct=24.0,
        ),
        reporting_period_label="FY2024",
        source_document_type="annual_report",
        evidence_summary=[
            {"metric": "scope1_co2e_tonnes", "source": "annual://catl-2024"},
            {"metric": "renewable_energy_pct", "source": "annual://catl-2024"},
            {"metric": "taxonomy_aligned_revenue_pct", "source": "annual://catl-2024"},
        ],
    )
    save_report(
        db_session,
        make_company_data(
            company_name="CATL",
            report_year=2025,
            scope1_co2e_tonnes=90.0,
            renewable_energy_pct=48.0,
        ),
        reporting_period_label="FY2025",
        source_document_type="sustainability_report",
    )

    history = get_company_history(company_name="catl", db=db_session)
    assert history["company_name"] == "Contemporary Amperex Technology Co., Limited"
    assert len(history["periods"]) == 2
    assert history["trend"][0]["scope1"] == pytest.approx(95.0)
    assert history["trend"][0]["taxonomy_aligned_revenue_pct"] == pytest.approx(24.0)

    profile = get_company_profile(company_name="CATL", db=db_session)
    assert profile["company_name"] == "Contemporary Amperex Technology Co., Limited"
    assert profile["years_available"] == [2024, 2025]
    assert profile["latest_year"] == 2025
    assert profile["identity_provenance_summary"]["canonical_company_name"] == "Contemporary Amperex Technology Co., Limited"
    assert profile["identity_provenance_summary"]["has_alias_consolidation"] is True
    assert "CATL" in profile["identity_provenance_summary"]["consolidated_aliases"]
    assert profile["identity_provenance_summary"]["latest_source_document_type"] == "sustainability_report"
    assert profile["narrative_summary"]["snapshot"]["periods_count"] == 2
    assert profile["narrative_summary"]["snapshot"]["framework_count"] == 0
    assert profile["narrative_summary"]["improved_metrics"] == [
        "scope1_co2e_tonnes",
        "renewable_energy_pct",
    ]
    assert profile["narrative_summary"]["weakened_metrics"] == []

    rows = list_company_reports(db=db_session)
    catl_rows = [row for row in rows if row["company_name"] == "Contemporary Amperex Technology Co., Limited"]
    assert len(catl_rows) == 2
    assert {row["report_year"] for row in catl_rows} == {2024, 2025}


def test_legacy_alias_duplicates_are_collapsed_for_listing_and_history(
    db_session: Session,
) -> None:
    db_session.add_all(
        [
            CompanyReport(
                company_name="volkswagen",
                report_year=2024,
                source_document_type="manual_case",
                scope1_co2e_tonnes=310.0,
                renewable_energy_pct=21.0,
                primary_activities=json.dumps(["automotive"]),
                evidence_summary=json.dumps([{"metric": "scope1_co2e_tonnes", "source": "manual://vw"}]),
            ),
            CompanyReport(
                company_name="Volkswagen AG",
                report_year=2024,
                source_document_type="annual_report",
                scope1_co2e_tonnes=255.0,
                renewable_energy_pct=36.0,
                primary_activities=json.dumps(["automotive"]),
                evidence_summary=json.dumps(
                    [
                        {"metric": "scope1_co2e_tonnes", "source": "annual://vw"},
                        {"metric": "renewable_energy_pct", "source": "annual://vw"},
                    ]
                ),
            ),
        ]
    )
    db_session.commit()

    rows = list_company_reports(db=db_session)
    assert len(rows) == 1
    assert rows[0]["company_name"] == "Volkswagen AG"
    assert rows[0]["scope1_co2e_tonnes"] == pytest.approx(255.0)

    history = get_company_history(company_name="volkswagen", db=db_session)
    assert history["company_name"] == "Volkswagen AG"
    assert len(history["trend"]) == 1
    assert history["trend"][0]["renewable_pct"] == pytest.approx(36.0)

    profile = get_company_profile(company_name="Volkswagen AG", db=db_session)
    assert profile["identity_provenance_summary"]["canonical_company_name"] == "Volkswagen AG"
    assert profile["identity_provenance_summary"]["has_alias_consolidation"] is True
    assert "volkswagen" in {
        alias.lower() for alias in profile["identity_provenance_summary"]["consolidated_aliases"]
    }
    assert profile["identity_provenance_summary"]["merge_priority_preview"] is not None


def test_volkswagen_profile_explains_legacy_metadata_gaps_without_fake_completeness(
    db_session: Session,
) -> None:
    db_session.add_all(
        [
            CompanyReport(
                company_name="Volkswagen AG",
                report_year=2024,
                source_document_type=None,
                reporting_period_label=None,
                reporting_period_type=None,
                pdf_filename="volkswagen_2024_esrs_sustainability_report.pdf",
                scope1_co2e_tonnes=1370000.0,
                scope2_co2e_tonnes=90000.0,
                energy_consumption_mwh=1750000.0,
                water_usage_m3=700000.0,
                total_employees=112091,
                female_pct=18.9,
                primary_activities=json.dumps(["automotive"]),
                evidence_summary=json.dumps([]),
            ),
            CompanyReport(
                company_name="volkswagen",
                report_year=2024,
                source_document_type=None,
                reporting_period_label=None,
                reporting_period_type=None,
                pdf_filename="volkswagen_2024_esrs_sustainability_report.pdf",
                scope1_co2e_tonnes=15.0,
                scope2_co2e_tonnes=290.0,
                scope3_co2e_tonnes=9653769.0,
                primary_activities=json.dumps(["automotive"]),
                evidence_summary=json.dumps([]),
            ),
        ]
    )
    db_session.commit()

    source_rows = list_source_reports_for_company_year(
        db=db_session,
        company_name="Volkswagen AG",
        report_year=2024,
    )
    assert len(source_rows) == 1
    assert source_rows[0].company_name == "Volkswagen AG"

    profile = get_company_profile(company_name="Volkswagen AG", db=db_session)
    assert profile["company_name"] == "Volkswagen AG"
    assert profile["identity_provenance_summary"]["has_alias_consolidation"] is True
    assert "volkswagen" in {
        alias.lower() for alias in profile["identity_provenance_summary"]["consolidated_aliases"]
    }
    assert profile["identity_provenance_summary"]["source_priority_preview"] is not None
    assert profile["latest_period"]["source_document_type"] == "sustainability_report"
    assert profile["data_quality_summary"]["readiness_label"] == "usable"
    assert len(profile["periods"]) == 1
    assert len(profile["trend"]) == 1


def test_identity_alias_consolidation_depends_on_observed_or_requested_aliases(
    db_session: Session,
    make_company_data,
) -> None:
    save_report(
        db_session,
        make_company_data(
            company_name="Siemens AG",
            report_year=2024,
            scope1_co2e_tonnes=200.0,
            renewable_energy_pct=46.0,
            taxonomy_aligned_revenue_pct=28.0,
            taxonomy_aligned_capex_pct=22.0,
            female_pct=34.0,
        ),
        source_document_type="annual_report",
    )

    canonical_profile = get_company_profile(company_name="Siemens AG", db=db_session)
    assert canonical_profile["company_name"] == "Siemens AG"
    assert canonical_profile["identity_provenance_summary"]["canonical_company_name"] == "Siemens AG"
    assert canonical_profile["identity_provenance_summary"]["has_alias_consolidation"] is False
    assert canonical_profile["identity_provenance_summary"]["consolidated_aliases"] == []

    alias_profile = get_company_profile(company_name="siemens", db=db_session)
    assert alias_profile["identity_provenance_summary"]["canonical_company_name"] == "Siemens AG"
    assert alias_profile["identity_provenance_summary"]["has_alias_consolidation"] is True
    assert "siemens" in {
        alias.lower() for alias in alias_profile["identity_provenance_summary"]["consolidated_aliases"]
    }


def test_third_showcase_siemens_profile_layers_are_reusable(
    db_session: Session,
    make_company_data,
) -> None:
    save_report(
        db_session,
        make_company_data(
            company_name="CATL",
            report_year=2024,
            scope1_co2e_tonnes=95.0,
            renewable_energy_pct=45.0,
        ),
        source_document_type="sustainability_report",
    )
    save_report(
        db_session,
        make_company_data(
            company_name="Volkswagen AG",
            report_year=2024,
            scope1_co2e_tonnes=255.0,
            renewable_energy_pct=36.0,
        ),
        source_document_type="annual_report",
    )
    save_report(
        db_session,
        make_company_data(
            company_name="Siemens AG",
            report_year=2023,
            scope1_co2e_tonnes=210.0,
            renewable_energy_pct=41.0,
            taxonomy_aligned_revenue_pct=24.0,
            taxonomy_aligned_capex_pct=18.0,
            female_pct=33.0,
            scope3_co2e_tonnes=900.0,
            water_usage_m3=18000.0,
        ),
        source_document_type="annual_report",
    )
    save_report(
        db_session,
        make_company_data(
            company_name="Siemens AG",
            report_year=2024,
            scope1_co2e_tonnes=198.0,
            renewable_energy_pct=46.0,
            taxonomy_aligned_revenue_pct=30.0,
            taxonomy_aligned_capex_pct=21.0,
            female_pct=34.0,
            scope3_co2e_tonnes=860.0,
            water_usage_m3=17000.0,
        ),
        source_document_type="sustainability_report",
    )

    profile = get_company_profile(company_name="siemens", db=db_session)
    assert profile["company_name"] == "Siemens AG"
    assert profile["latest_year"] == 2024
    assert len(profile["periods"]) == 2

    # profile layer
    assert profile["latest_metrics"]["scope1_co2e_tonnes"] == pytest.approx(198.0)
    assert profile["trend"][-1]["renewable_pct"] == pytest.approx(46.0)

    # identity layer
    identity = profile["identity_provenance_summary"]
    assert identity["canonical_company_name"] == "Siemens AG"
    assert identity["latest_source_document_type"] == "sustainability_report"

    # quality layer
    quality = profile["data_quality_summary"]
    assert quality["present_metrics_count"] >= 8
    assert quality["readiness_label"] in {"usable", "showcase-ready"}

    # narrative layer
    narrative = profile["narrative_summary"]
    assert narrative["snapshot"]["periods_count"] == 2
    assert narrative["has_previous_period"] is True
    assert narrative["previous_year"] == 2023
    assert "scope1_co2e_tonnes" in narrative["improved_metrics"]

    rows = list_company_reports(db=db_session)
    assert sorted({row["company_name"] for row in rows}) == [
        "Contemporary Amperex Technology Co., Limited",
        "Siemens AG",
        "Volkswagen AG",
    ]


def test_preview_merge_prefers_annual_report_and_marks_conflict() -> None:
    payload = MergePreviewRequest(
        documents=[
            MergeSourceInput(
                source_id="annual-2024",
                company_name="Merge Corp",
                report_year=2024,
                reporting_period_label="FY2024",
                reporting_period_type="annual",
                source_document_type="annual_report",
                source_url="https://example.com/annual",
                scope1_co2e_tonnes=100.0,
                renewable_energy_pct=None,
                primary_activities=["industrial_automation"],
            ),
            MergeSourceInput(
                source_id="sustainability-2024",
                company_name="Merge Corp",
                report_year=2024,
                reporting_period_label="FY2024 sustainability",
                reporting_period_type="annual",
                source_document_type="sustainability_report",
                source_url="https://example.com/sr",
                scope1_co2e_tonnes=95.0,
                renewable_energy_pct=48.0,
                primary_activities=["industrial_automation", "solar_pv"],
            ),
            MergeSourceInput(
                source_id="filing-2024",
                company_name="Merge Corp",
                report_year=2024,
                reporting_period_label="Q4 filing",
                reporting_period_type="event",
                source_document_type="filing",
                source_url="https://example.com/filing",
                renewable_energy_pct=52.0,
            ),
        ]
    )

    result = preview_merge(payload)

    assert result.company_name == "Merge Corp"
    assert result.merged_metrics.scope1_co2e_tonnes == pytest.approx(100.0)
    assert result.merged_metrics.renewable_energy_pct == pytest.approx(48.0)
    assert result.merged_metrics.primary_activities == ["industrial_automation", "solar_pv"]

    decisions = {item.metric: item for item in result.decisions}
    assert decisions["scope1_co2e_tonnes"].merge_reason == "annual_report_baseline"
    assert decisions["scope1_co2e_tonnes"].conflict_detected is True
    assert decisions["renewable_energy_pct"].merge_reason == "supplement_filled_gap"
    assert decisions["primary_activities"].merge_reason == "activity_union"
    assert "scope1_co2e_tonnes" in result.unresolved_metrics


def test_multi_source_persistence_keeps_same_year_records(
    db_session: Session,
    make_company_data,
) -> None:
    save_report(
        db_session,
        make_company_data(
            company_name="Source Stack Corp",
            report_year=2024,
            scope1_co2e_tonnes=100.0,
            renewable_energy_pct=None,
        ),
        source_document_type="annual_report",
        source_url="https://example.com/source-stack-annual",
        file_hash="hash-annual-1",
    )
    save_report(
        db_session,
        make_company_data(
            company_name="Source Stack Corp",
            report_year=2024,
            scope1_co2e_tonnes=92.0,
            renewable_energy_pct=55.0,
        ),
        source_document_type="sustainability_report",
        source_url="https://example.com/source-stack-sr",
        file_hash="hash-sr-1",
    )
    save_report(
        db_session,
        make_company_data(
            company_name="Source Stack Corp",
            report_year=2024,
            scope1_co2e_tonnes=None,
            renewable_energy_pct=57.0,
        ),
        source_document_type="announcement",
        source_url="https://example.com/source-stack-announcement",
        file_hash="hash-announcement-1",
    )

    source_rows = list_source_reports_for_company_year(
        db_session, "Source Stack Corp", 2024
    )
    assert len(source_rows) == 3
    assert {row.source_document_type for row in source_rows} == {
        "annual_report",
        "sustainability_report",
        "announcement",
    }

    history = get_company_history(company_name="Source Stack Corp", db=db_session)
    assert len(history["periods"]) == 1
    period = history["periods"][0]
    assert len(period["source_documents"]) == 3
    assert period["merged_result"]["source_count"] == 3
    assert period["merged_result"]["merged_metrics"]["scope1_co2e_tonnes"] == pytest.approx(100.0)
    assert period["merged_result"]["merged_metrics"]["renewable_energy_pct"] == pytest.approx(55.0)

    scope1_merge = period["merged_result"]["metrics"]["scope1_co2e_tonnes"]
    renewable_merge = period["merged_result"]["metrics"]["renewable_energy_pct"]
    assert scope1_merge["merge_reason"] == "annual_report_baseline"
    assert renewable_merge["merge_reason"] == "supplement_filled_gap"
    assert scope1_merge["chosen_source_document_type"] == "annual_report"
    assert renewable_merge["chosen_source_document_type"] == "sustainability_report"
    assert len(scope1_merge["candidate_values"]) == 2
    assert len(renewable_merge["candidate_values"]) == 2


def test_preview_merge_rejects_mixed_company_or_year() -> None:
    payload = MergePreviewRequest(
        documents=[
            MergeSourceInput(company_name="A Corp", report_year=2024, source_document_type="annual_report"),
            MergeSourceInput(company_name="B Corp", report_year=2024, source_document_type="sustainability_report"),
        ]
    )

    with pytest.raises(HTTPException):
        preview_merge(payload)


def test_company_history_and_profile_include_period_and_framework_results(
    db_session: Session,
    make_company_data,
) -> None:
    save_report(
        db_session,
        make_company_data(company_name="Trend Corp", report_year=2023, renewable_energy_pct=30.0),
        pdf_filename="trend-2023.pdf",
        reporting_period_label="FY2023",
        reporting_period_type="annual",
        source_document_type="annual_report",
        evidence_summary=[
            {
                "metric": "renewable_energy_pct",
                "page": 10,
                "snippet": "Renewable electricity share reached 30%.",
                "source": "Trend Corp Annual Report 2023",
            }
        ],
    )
    save_report(
        db_session,
        make_company_data(company_name="Trend Corp", report_year=2024, renewable_energy_pct=45.0),
        pdf_filename="trend-2024.pdf",
        reporting_period_label="FY2024",
        reporting_period_type="annual",
        source_document_type="sustainability_report",
        evidence_summary=[
            {
                "metric": "renewable_energy_pct",
                "page": 12,
                "snippet": "Renewable electricity share increased to 45%.",
                "source": "Trend Corp Sustainability Report 2024",
            }
        ],
    )

    result = FrameworkScoreResult(
        framework="EU Taxonomy 2020",
        framework_id="eu_taxonomy",
        framework_version="2020/852",
        company_name="Trend Corp",
        report_year=2024,
        total_score=0.66,
        grade="B",
        dimensions=[DimensionScore(name="Climate", score=0.66, weight=1.0, disclosed=1, total=1)],
        gaps=[],
        recommendations=[],
        coverage_pct=100.0,
    )
    first_save = save_framework_result(db_session, result, framework_version=result.framework_version)
    duplicate_save = save_framework_result(db_session, result, framework_version=result.framework_version)
    assert duplicate_save.id == first_save.id

    history = get_company_history(company_name="Trend Corp", db=db_session)
    assert history["company_name"] == "Trend Corp"
    assert len(history["periods"]) == 2
    assert history["periods"][0]["reporting_period_label"] == "FY2023"
    assert history["periods"][0]["period"]["legacy_report_year"] == 2023
    assert history["periods"][0]["period"]["label"] == "FY2023"
    assert history["periods"][0]["period"]["type"] == "annual"
    assert history["periods"][0]["period"]["source_document_type"] == "annual_report"
    assert history["periods"][0]["evidence_anchors"][0]["page"] == 10
    assert history["periods"][0]["evidence_anchors"][0]["source"] == "Trend Corp Annual Report 2023"
    assert history["periods"][0]["evidence_anchors"][0]["snippet"] is not None
    assert history["periods"][0]["framework_metadata"] == []
    assert len(history["periods"][1]["framework_metadata"]) == 1
    assert history["periods"][1]["framework_metadata"][0]["analysis_result_id"] == first_save.id
    assert history["periods"][1]["framework_metadata"][0]["framework_id"] == "eu_taxonomy"
    assert history["framework_metadata"][0]["framework_version"] == "2020/852"
    assert history["trend"][1]["renewable_pct"] == pytest.approx(45.0)

    profile = get_company_profile(company_name="Trend Corp", db=db_session)
    assert profile["latest_year"] == 2024
    assert profile["latest_period"]["reporting_period_label"] == "FY2024"
    assert profile["latest_period"]["period"]["legacy_report_year"] == 2024
    assert profile["latest_period"]["period"]["label"] == "FY2024"
    assert profile["latest_period"]["period"]["type"] == "annual"
    assert profile["latest_period"]["period"]["source_document_type"] == "sustainability_report"
    assert len(profile["latest_period"]["framework_metadata"]) == 1
    assert profile["latest_period"]["framework_metadata"][0]["framework_id"] == "eu_taxonomy"
    assert profile["framework_metadata"][0]["framework_version"] == "2020/852"
    assert len(profile["framework_results"]) == 1
    assert profile["framework_results"][0]["framework_version"] == "2020/852"
    assert profile["framework_results"][0]["framework_id"] == "eu_taxonomy"
    assert len(profile["framework_scores"]) == len(_SCORERS)
    assert {item["framework_id"] for item in profile["framework_scores"]} == set(_SCORERS.keys())
    renewable_summary = next(
        item for item in profile["evidence_summary"] if item["metric"] == "renewable_energy_pct"
    )
    renewable_anchor = next(
        item for item in profile["evidence_anchors"] if item["metric"] == "renewable_energy_pct"
    )
    assert renewable_summary["page"] == 12
    assert renewable_anchor["page"] == 12
    assert profile["scored_metrics"]["renewable_energy_pct"]["evidence"]["page"] == 12
    assert profile["data_quality_summary"]["total_key_metrics_count"] == 11
    assert profile["data_quality_summary"]["present_metrics_count"] == 6
    assert profile["data_quality_summary"]["completion_percentage"] == pytest.approx(54.5)
    assert profile["data_quality_summary"]["readiness_label"] == "usable"


def test_company_history_three_year_trend_ordering_and_yoy(
    db_session: Session,
    make_company_data,
) -> None:
    """Regression: ensure 3-year trend preserves chronological ordering and YoY deltas.

    This protects the multi-year demo story (BASF, RWE AG, Deutsche Telekom)
    where seeded 2022/2023/2024 data must render as an ascending 3-point line.
    """
    for year, renewable, scope1 in [
        (2022, 16.0, 16_456_000.0),
        (2023, 20.0, 15_562_000.0),
        (2024, 26.0, 15_552_000.0),
    ]:
        save_report(
            db_session,
            make_company_data(
                company_name="Trajectory AG",
                report_year=year,
                renewable_energy_pct=renewable,
                scope1_co2e_tonnes=scope1,
            ),
            pdf_filename=f"trajectory-{year}.pdf",
            reporting_period_label=f"FY{year}",
            reporting_period_type="annual",
            source_document_type="sustainability_report",
        )

    history = get_company_history(company_name="Trajectory AG", db=db_session)

    assert history["company_name"] == "Trajectory AG"
    assert len(history["periods"]) == 3
    assert len(history["trend"]) == 3

    # Trend must be chronologically ordered (critical for YoY delta cards)
    years = [point["year"] for point in history["trend"]]
    assert years == [2022, 2023, 2024], "trend must be in ascending year order"

    # Each trend point carries normalised metric keys
    for point in history["trend"]:
        assert "renewable_pct" in point
        assert "scope1" in point

    # Values preserved through storage→aggregation
    assert history["trend"][0]["renewable_pct"] == pytest.approx(16.0)
    assert history["trend"][2]["renewable_pct"] == pytest.approx(26.0)
    assert history["trend"][0]["scope1"] == pytest.approx(16_456_000.0)
    assert history["trend"][2]["scope1"] == pytest.approx(15_552_000.0)

    # Profile exposes multi-year trend so the frontend can render YoY deltas
    profile = get_company_profile(company_name="Trajectory AG", db=db_session)
    assert profile["latest_year"] == 2024
    assert profile["years_available"] == [2022, 2023, 2024]
    assert len(profile["trend"]) == 3
    assert profile["trend"][-1]["year"] == 2024
    assert profile["trend"][-2]["year"] == 2023


@pytest.mark.parametrize(
    ("company_name", "overrides", "expected_label", "expected_present", "expected_completion"),
    [
        (
            "Draft Corp",
            {
                "scope2_co2e_tonnes": None,
                "energy_consumption_mwh": None,
                "renewable_energy_pct": None,
                "water_usage_m3": None,
                "waste_recycled_pct": None,
                "taxonomy_aligned_revenue_pct": None,
                "taxonomy_aligned_capex_pct": None,
                "total_employees": None,
                "female_pct": None,
            },
            "draft",
            1,
            9.1,
        ),
        (
            "Usable Corp",
            {
                "scope3_co2e_tonnes": None,
                "water_usage_m3": None,
                "waste_recycled_pct": None,
                "taxonomy_aligned_revenue_pct": None,
                "taxonomy_aligned_capex_pct": None,
            },
            "usable",
            6,
            54.5,
        ),
        (
            "Showcase Corp",
            {
                "scope3_co2e_tonnes": 800.0,
                "water_usage_m3": 12000.0,
                "waste_recycled_pct": None,
                "taxonomy_aligned_revenue_pct": 42.0,
                "taxonomy_aligned_capex_pct": 36.0,
            },
            "showcase-ready",
            10,
            90.9,
        ),
    ],
)
def test_company_profile_data_quality_summary_readiness_bands(
    db_session: Session,
    make_company_data,
    company_name: str,
    overrides: dict[str, float | int | None],
    expected_label: str,
    expected_present: int,
    expected_completion: float,
) -> None:
    save_report(
        db_session,
        make_company_data(company_name=company_name, report_year=2024, **overrides),
        pdf_filename=f"{company_name.lower().replace(' ', '-')}.pdf",
    )

    profile = get_company_profile(company_name=company_name, db=db_session)
    summary = profile["data_quality_summary"]

    assert summary["total_key_metrics_count"] == 11
    assert summary["present_metrics_count"] == expected_present
    assert summary["completion_percentage"] == pytest.approx(expected_completion)
    assert summary["readiness_label"] == expected_label
    assert sorted(summary["present_metrics"] + summary["missing_metrics"]) == sorted(
        [
            "scope1_co2e_tonnes",
            "scope2_co2e_tonnes",
            "scope3_co2e_tonnes",
            "energy_consumption_mwh",
            "renewable_energy_pct",
            "water_usage_m3",
            "waste_recycled_pct",
            "taxonomy_aligned_revenue_pct",
            "taxonomy_aligned_capex_pct",
            "total_employees",
            "female_pct",
        ]
    )


def test_evidence_anchors_stay_stable_for_empty_and_legacy_records(
    db_session: Session,
    make_company_data,
) -> None:
    legacy = save_report(
        db_session,
        make_company_data(company_name="Legacy Corp", report_year=2022, renewable_energy_pct=20.0),
        source_url="https://example.com/legacy-2022.pdf",
        evidence_summary=[{"metric": "renewable_energy_pct", "source_type": "pdf"}],
    )
    empty = save_report(
        db_session,
        make_company_data(company_name="Legacy Corp", report_year=2023, renewable_energy_pct=25.0),
        evidence_summary=[],
    )
    # simulate malformed historical payload
    legacy.evidence_summary = "{not-json}"
    db_session.commit()
    db_session.refresh(legacy)
    db_session.refresh(empty)

    history = get_company_history(company_name="Legacy Corp", db=db_session)
    assert history["periods"][0]["evidence_anchors"] == []
    assert history["periods"][1]["evidence_anchors"] == []
    assert history["periods"][0]["framework_metadata"] == []
    assert history["framework_metadata"] == []

    profile = get_company_profile(company_name="Legacy Corp", db=db_session)
    assert profile["evidence_summary"]
    assert profile["evidence_anchors"]
    assert profile["scored_metrics"]["renewable_energy_pct"]["evidence"] is not None
    assert profile["latest_period"]["framework_metadata"] == []
    assert profile["framework_metadata"] == []
    assert len(profile["framework_scores"]) == len(_SCORERS)


def test_get_dashboard_stats_returns_empty_payload_for_no_records(db_session: Session) -> None:
    payload = get_dashboard_stats(db=db_session)
    assert payload["total_companies"] == 0
    assert payload["avg_taxonomy_aligned"] == 0
    assert payload["avg_renewable_pct"] == 0
    assert payload["yearly_trend"] == []
    assert payload["top_emitters"] == []
    assert payload["bottom_emitters"] == []
    assert payload["coverage_rates"] == {}


def test_get_dashboard_stats_returns_aggregates_rankings_and_coverage(
    db_session: Session,
    make_company_data,
) -> None:
    save_report(
        db_session,
        make_company_data(
            company_name="A Corp",
            report_year=2023,
            scope1_co2e_tonnes=100.0,
            scope3_co2e_tonnes=1100.0,
            renewable_energy_pct=20.0,
            taxonomy_aligned_revenue_pct=10.0,
            female_pct=40.0,
        ),
        pdf_filename="a-2023.pdf",
    )
    save_report(
        db_session,
        make_company_data(
            company_name="B Corp",
            report_year=2024,
            scope1_co2e_tonnes=300.0,
            scope3_co2e_tonnes=1300.0,
            renewable_energy_pct=40.0,
            taxonomy_aligned_revenue_pct=30.0,
            female_pct=50.0,
            water_usage_m3=5000.0,
        ),
        pdf_filename="b-2024.pdf",
    )
    save_report(
        db_session,
        make_company_data(
            company_name="C Corp",
            report_year=2024,
            scope1_co2e_tonnes=50.0,
            renewable_energy_pct=None,
            taxonomy_aligned_revenue_pct=None,
            female_pct=None,
            scope3_co2e_tonnes=None,
            water_usage_m3=None,
            waste_recycled_pct=None,
        ),
        pdf_filename="c-2024.pdf",
    )

    payload = get_dashboard_stats(db=db_session)
    assert payload["total_companies"] == 3
    assert payload["avg_taxonomy_aligned"] == pytest.approx(20.0)
    assert payload["avg_renewable_pct"] == pytest.approx(30.0)
    assert payload["yearly_trend"] == [
        {"year": 2023, "count": 1},
        {"year": 2024, "count": 2},
    ]

    assert payload["top_emitters"][0]["company"] == "B Corp"
    assert payload["top_emitters"][0]["scope1"] == pytest.approx(300.0)
    assert payload["bottom_emitters"][0]["company"] == "C Corp"
    assert payload["bottom_emitters"][0]["scope1"] == pytest.approx(50.0)

    assert payload["coverage_rates"]["scope1_co2e_tonnes"] == pytest.approx(100.0)
    assert payload["coverage_rates"]["scope3_co2e_tonnes"] == pytest.approx(66.7)
    assert payload["coverage_rates"]["taxonomy_aligned_revenue_pct"] == pytest.approx(66.7)
    assert payload["coverage_rates"]["female_pct"] == pytest.approx(66.7)


def test_dashboard_stats_do_not_double_count_alias_duplicates(
    db_session: Session,
    make_company_data,
) -> None:
    save_report(
        db_session,
        make_company_data(
            company_name="volkswagen",
            report_year=2024,
            scope1_co2e_tonnes=300.0,
            renewable_energy_pct=20.0,
        ),
        source_document_type="manual_case",
    )
    save_report(
        db_session,
        make_company_data(
            company_name="Volkswagen AG",
            report_year=2024,
            scope1_co2e_tonnes=250.0,
            renewable_energy_pct=35.0,
        ),
        source_document_type="annual_report",
    )

    payload = get_dashboard_stats(db=db_session)
    assert payload["total_companies"] == 1
    assert payload["yearly_trend"] == [{"year": 2024, "count": 1}]
    assert payload["top_emitters"][0]["company"] == "Volkswagen AG"
    assert payload["top_emitters"][0]["scope1"] == pytest.approx(250.0)


def test_save_report_fail_closed_blocks_invalid_values(
    db_session: Session,
    make_company_data,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "l0_fail_closed", True)
    monkeypatch.setattr(settings, "l0_fail_open_bypass", False)

    with pytest.raises(ValueError, match="L0 validation failed"):
        save_report(
            db_session,
            make_company_data(scope1_co2e_tonnes=9_999_999_999_999.0),
            pdf_filename="invalid-fail-closed.pdf",
        )


def test_save_report_fail_open_bypass_allows_invalid_values(
    db_session: Session,
    make_company_data,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "l0_fail_closed", True)
    monkeypatch.setattr(settings, "l0_fail_open_bypass", True)

    saved = save_report(
        db_session,
        make_company_data(scope1_co2e_tonnes=9_999_999_999_999.0),
        pdf_filename="invalid-fail-open.pdf",
    )
    assert saved.scope1_co2e_tonnes == pytest.approx(9_999_999_999_999.0)
