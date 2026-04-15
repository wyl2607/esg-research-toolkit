from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from core.schemas import CompanyESGData
from main import app


def _fake_pdf_bytes() -> bytes:
    return b"%PDF-1.7\n" + b"0" * 2048


def test_upload_rate_limit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
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
    monkeypatch.setattr("report_parser.api.save_report", lambda *args, **kwargs: None)

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
