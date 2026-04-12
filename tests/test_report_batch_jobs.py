import time
from contextlib import contextmanager
from pathlib import Path

from core.schemas import CompanyESGData
from report_parser.batch_jobs import BatchAnalysisManager


@contextmanager
def _fake_session():
    yield object()


def _wait_until_done(manager: BatchAnalysisManager, batch_id: str, timeout: float = 3.0):
    start = time.time()
    while time.time() - start < timeout:
        status = manager.get_batch_status(batch_id)
        if status.completed_jobs + status.failed_jobs == status.total_jobs:
            return status
        time.sleep(0.05)
    raise TimeoutError("batch job did not finish in time")


def test_batch_job_success(monkeypatch):
    manager = BatchAnalysisManager(max_workers=1)

    monkeypatch.setattr("report_parser.batch_jobs.extract_text_from_pdf", lambda _p: "scope 1 100")
    monkeypatch.setattr(
        "report_parser.batch_jobs.analyze_esg_data",
        lambda _text, filename="": CompanyESGData(
            company_name=filename.replace(".pdf", ""),
            report_year=2024,
            scope1_co2e_tonnes=100,
            primary_activities=["battery_manufacturing"],
        ),
    )
    monkeypatch.setattr("report_parser.batch_jobs.save_report", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("report_parser.batch_jobs.SessionLocal", _fake_session)

    submitted = manager.submit([(Path("/tmp/a.pdf"), "a.pdf")])
    status = _wait_until_done(manager, submitted.batch_id)

    assert status.total_jobs == 1
    assert status.completed_jobs == 1
    assert status.failed_jobs == 0
    assert status.jobs[0].status == "completed"
    assert status.jobs[0].result is not None
    assert status.jobs[0].result.company_name == "a"


def test_batch_job_failure(monkeypatch):
    manager = BatchAnalysisManager(max_workers=1)

    monkeypatch.setattr("report_parser.batch_jobs.extract_text_from_pdf", lambda _p: "")

    submitted = manager.submit([(Path("/tmp/b.pdf"), "b.pdf")])
    status = _wait_until_done(manager, submitted.batch_id)

    assert status.total_jobs == 1
    assert status.completed_jobs == 0
    assert status.failed_jobs == 1
    assert status.jobs[0].status == "failed"
    assert status.jobs[0].error is not None
