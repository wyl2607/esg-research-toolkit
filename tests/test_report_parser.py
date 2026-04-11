import json
from collections.abc import Callable
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from core.database import Base
from core.schemas import CompanyESGData
from report_parser.analyzer import analyze_esg_data
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


def test_extract_text_from_pdf_success() -> None:
    first_page = MagicMock()
    first_page.extract_text.return_value = "  Executive   Summary \n\n Scope 1   emissions "
    second_page = MagicMock()
    second_page.extract_text.return_value = None
    third_page = MagicMock()
    third_page.extract_text.return_value = "Renewable\tenergy    usage"

    pdf = MagicMock()
    pdf.pages = [first_page, second_page, third_page]

    pdf_context = MagicMock()
    pdf_context.__enter__.return_value = pdf
    pdf_context.__exit__.return_value = False

    with patch("report_parser.extractor.pdfplumber.open", return_value=pdf_context) as mock_open:
        result = extract_text_from_pdf("sample.pdf")  # type: ignore[arg-type]

    assert result == "Executive Summary\nScope 1 emissions\n\nRenewable energy usage"
    mock_open.assert_called_once_with("sample.pdf")


def test_extract_text_from_pdf_invalid_file() -> None:
    with patch("report_parser.extractor.pdfplumber.open", side_effect=FileNotFoundError("missing")):
        result = extract_text_from_pdf("missing.pdf")  # type: ignore[arg-type]

    assert result == ""


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
    assert user_arg == f"Corporate Report Text:\n\n{report_text[:8000]}"
    assert mock_complete.call_args.kwargs["max_tokens"] == 1024


def test_analyze_esg_data_invalid_json() -> None:
    with patch("report_parser.analyzer.complete", return_value="not json"):
        result = analyze_esg_data("unstructured text")

    assert result == CompanyESGData(company_name="Unknown", report_year=2024)


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
