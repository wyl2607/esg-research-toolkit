from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from core.schemas import CompanyESGData
from main import app


def _fake_pdf_bytes() -> bytes:
    return b"%PDF-1.7\n" + b"0" * 2048


@contextmanager
def _fake_session() -> Generator[object, None, None]:
    yield object()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Generator[TestClient, None, None]:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("main.init_db", lambda: None)
    monkeypatch.setattr("report_parser.batch_jobs.extract_text_from_pdf", lambda _path: "scope 1 100")
    monkeypatch.setattr(
        "report_parser.batch_jobs.analyze_esg_data",
        lambda _text, filename="": CompanyESGData(
            company_name=Path(filename).stem,
            report_year=2024,
            scope1_co2e_tonnes=100,
            primary_activities=["battery_manufacturing"],
        ),
    )
    monkeypatch.setattr("report_parser.batch_jobs.save_report", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("report_parser.batch_jobs.SessionLocal", _fake_session)

    with TestClient(app) as test_client:
        yield test_client


def _wait_for_completion(client: TestClient, batch_id: str) -> dict:
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        response = client.get(f"/report/jobs/{batch_id}")
        assert response.status_code == 200
        status = response.json()
        if status["completed_jobs"] + status["failed_jobs"] == status["total_jobs"]:
            return status
        time.sleep(0.05)
    raise TimeoutError(f"batch {batch_id} did not complete")


def test_batch_upload_returns_batch_id_for_two_pdfs(client: TestClient) -> None:
    response = client.post(
        "/report/upload/batch",
        files=[
            ("files", ("first.pdf", _fake_pdf_bytes(), "application/pdf")),
            ("files", ("second.pdf", _fake_pdf_bytes(), "application/pdf")),
        ],
    )

    assert response.status_code == 200
    body = response.json()
    assert body["batch_id"]
    assert body["total_jobs"] == 2
    _wait_for_completion(client, body["batch_id"])


def test_batch_jobs_endpoint_reaches_completion(client: TestClient) -> None:
    upload = client.post(
        "/report/upload/batch",
        files=[
            ("files", ("first.pdf", _fake_pdf_bytes(), "application/pdf")),
            ("files", ("second.pdf", _fake_pdf_bytes(), "application/pdf")),
        ],
    )
    assert upload.status_code == 200

    status = _wait_for_completion(client, upload.json()["batch_id"])

    assert status["completed_jobs"] == 2
    assert status["failed_jobs"] == 0
    assert {job["filename"] for job in status["jobs"]} == {"first.pdf", "second.pdf"}
    assert {job["status"] for job in status["jobs"]} == {"completed"}


def test_batch_jobs_endpoint_returns_404_for_unknown_batch(client: TestClient) -> None:
    response = client.get("/report/jobs/unknown-batch")

    assert response.status_code == 404


def test_batch_upload_without_files_is_rejected(client: TestClient) -> None:
    response = client.post("/report/upload/batch")

    assert response.status_code == 422
