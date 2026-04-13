import json
from collections.abc import Callable
from collections.abc import Generator
from unittest.mock import patch
import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from core.database import Base
from core.schemas import CompanyESGData
from esg_frameworks.api import _SCORERS
from esg_frameworks.schemas import DimensionScore, FrameworkScoreResult
from esg_frameworks.storage import save_framework_result
from report_parser.api import list_company_reports
from report_parser.api import get_company_history, get_company_profile, get_dashboard_stats
from report_parser.analyzer import AIExtractionError, analyze_esg_data
from report_parser.extractor import extract_text_from_pdf
from report_parser.storage import CompanyReport, get_report, list_reports, save_report


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
    save_framework_result(db_session, result, framework_version=result.framework_version)

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
    assert profile["latest_period"]["framework_metadata"][0]["framework_id"] == "eu_taxonomy"
    assert profile["framework_metadata"][0]["framework_version"] == "2020/852"
    assert len(profile["framework_results"]) == 1
    assert profile["framework_results"][0]["framework_version"] == "2020/852"
    assert profile["framework_results"][0]["framework_id"] == "eu_taxonomy"
    assert len(profile["framework_scores"]) == len(_SCORERS)
    assert {item["framework_id"] for item in profile["framework_scores"]} == set(_SCORERS.keys())
    assert profile["evidence_summary"][0]["metric"] == "renewable_energy_pct"
    assert profile["evidence_summary"][0]["page"] == 12
    assert profile["evidence_anchors"][0]["page"] == 12


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
    assert profile["evidence_summary"] == []
    assert profile["evidence_anchors"] == []
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
