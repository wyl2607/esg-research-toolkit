from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from core.schemas import CompanyESGData
from main import app


def _fake_pdf_bytes() -> bytes:
    return b"%PDF-1.7\n" + b"0" * 2048


def test_upload_rate_limit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("main.init_db", lambda: None)
    monkeypatch.setattr(
        "report_parser.api.extract_text_from_pdf",
        lambda _path: "Example Corp sustainability report",
    )
    monkeypatch.setattr(
        "report_parser.api.analyze_esg_data",
        lambda _text, filename="": CompanyESGData(
            company_name="Example Corp",
            report_year=2024,
            scope1_co2e_tonnes=123.4,
            scope2_co2e_tonnes=56.7,
            energy_consumption_mwh=890.1,
            renewable_energy_pct=42.0,
            total_employees=250,
            female_pct=48.5,
            primary_activities=["solar_pv"],
        ),
    )
    def _fake_save_report(_db, data, **kwargs):
        class _Record:
            company_name = data.company_name
            report_year = data.report_year
            reporting_period_label = "2024"
            reporting_period_type = "annual"
            source_document_type = "sustainability_report"
            industry_code = data.industry_code
            industry_sector = data.industry_sector
            scope1_co2e_tonnes = data.scope1_co2e_tonnes
            scope2_co2e_tonnes = data.scope2_co2e_tonnes
            scope3_co2e_tonnes = None
            energy_consumption_mwh = data.energy_consumption_mwh
            renewable_energy_pct = data.renewable_energy_pct
            water_usage_m3 = None
            waste_recycled_pct = None
            total_revenue_eur = None
            taxonomy_aligned_revenue_pct = None
            total_capex_eur = None
            taxonomy_aligned_capex_pct = None
            total_employees = data.total_employees
            female_pct = data.female_pct
            primary_activities = '["solar_pv"]'
            evidence_summary = "[]"
            source_url = None
            file_hash = "abc123"

        return _Record()

    monkeypatch.setattr("report_parser.api.save_report", _fake_save_report)

    statuses: list[int] = []
    with TestClient(app) as client:
        for attempt in range(6):
            response = client.post(
                "/report/upload",
                files={"file": (f"demo-{attempt}.pdf", _fake_pdf_bytes(), "application/pdf")},
            )
            statuses.append(response.status_code)

    assert statuses[:5] == [200, 200, 200, 200, 200]
    assert 429 in statuses


def test_upload_override_company_name_takes_precedence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("main.init_db", lambda: None)
    monkeypatch.setattr(
        "report_parser.api.extract_text_from_pdf",
        lambda _path: "Volkswagen sustainability report",
    )
    monkeypatch.setattr(
        "report_parser.api.analyze_esg_data",
        lambda _text, filename="": CompanyESGData(
            company_name="Volkswagen Group",
            report_year=2024,
            scope1_co2e_tonnes=123.4,
            primary_activities=["solar_pv"],
        ),
    )

    captured_company_names: list[str] = []

    def _fake_save_report(_db, data, **kwargs):
        captured_company_names.append(data.company_name)

        class _Record:
            company_name = data.company_name
            report_year = data.report_year
            reporting_period_label = "2024"
            reporting_period_type = "annual"
            source_document_type = "sustainability_report"
            industry_code = kwargs.get("industry_code")
            industry_sector = kwargs.get("industry_sector")
            scope1_co2e_tonnes = data.scope1_co2e_tonnes
            scope2_co2e_tonnes = None
            scope3_co2e_tonnes = None
            energy_consumption_mwh = None
            renewable_energy_pct = None
            water_usage_m3 = None
            waste_recycled_pct = None
            total_revenue_eur = None
            taxonomy_aligned_revenue_pct = None
            total_capex_eur = None
            taxonomy_aligned_capex_pct = None
            total_employees = None
            female_pct = None
            primary_activities = '["solar_pv"]'
            evidence_summary = "[]"
            source_url = None
            file_hash = "abc123"

        return _Record()

    monkeypatch.setattr("report_parser.api.save_report", _fake_save_report)

    with TestClient(app) as client:
        response = client.post(
            "/report/upload",
            files={"file": ("demo.pdf", _fake_pdf_bytes(), "application/pdf")},
            data={"override_company_name": "Volkswagen AG"},
        )

    assert response.status_code == 200
    assert response.json()["company_name"] == "Volkswagen AG"
    assert captured_company_names == ["Volkswagen AG"]
