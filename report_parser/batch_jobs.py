from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from core.config import settings
from core.database import SessionLocal
from core.schemas import BatchJobItem, BatchStatusResponse
from report_parser.analyzer import analyze_esg_data
from report_parser.extractor import extract_text_from_pdf
from report_parser.storage import save_report

# Evict completed/failed jobs older than this many seconds to keep the dict bounded.
JOB_RETENTION_SECONDS = 24 * 3600
MAX_JOBS_IN_MEMORY = 5_000


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class BatchAnalysisManager:
    """In-process queue for PDF batch analysis with bounded memory footprint."""

    def __init__(self, max_workers: int = 2) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="esg-batch")
        self._lock = threading.Lock()
        self._jobs: dict[str, dict] = {}
        self._batches: dict[str, list[str]] = {}

    def _evict_stale_locked(self) -> None:
        """Drop terminal jobs older than JOB_RETENTION_SECONDS.

        Caller must hold ``self._lock``. Also enforces a hard cap so a runaway
        producer cannot exhaust memory between evictions.
        """
        if not self._jobs:
            return
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=JOB_RETENTION_SECONDS)
        cutoff_iso = cutoff.isoformat()

        stale_job_ids: list[str] = []
        for job_id, job in self._jobs.items():
            if job["status"] not in ("completed", "failed"):
                continue
            finished = job.get("finished_at")
            if finished and finished < cutoff_iso:
                stale_job_ids.append(job_id)

        for job_id in stale_job_ids:
            self._jobs.pop(job_id, None)

        # Hard cap: if still oversized, drop oldest terminal jobs first
        if len(self._jobs) > MAX_JOBS_IN_MEMORY:
            terminal = sorted(
                (
                    (job["finished_at"] or job["created_at"], job_id)
                    for job_id, job in self._jobs.items()
                    if job["status"] in ("completed", "failed")
                ),
            )
            overflow = len(self._jobs) - MAX_JOBS_IN_MEMORY
            for _ts, job_id in terminal[:overflow]:
                self._jobs.pop(job_id, None)

        # Drop empty batches
        empty_batches = [
            batch_id
            for batch_id, job_ids in self._batches.items()
            if not any(jid in self._jobs for jid in job_ids)
        ]
        for batch_id in empty_batches:
            self._batches.pop(batch_id, None)

    def submit(self, files: list[tuple[Path, str]]) -> BatchStatusResponse:
        if not files:
            raise ValueError("No files submitted")

        batch_id = uuid4().hex
        now = _utc_now_iso()

        with self._lock:
            self._evict_stale_locked()
            self._batches[batch_id] = []
            for file_path, filename in files:
                job_id = uuid4().hex
                job = {
                    "job_id": job_id,
                    "batch_id": batch_id,
                    "filename": filename,
                    "file_path": str(file_path),
                    "status": "queued",
                    "error": None,
                    "result": None,
                    "created_at": now,
                    "started_at": None,
                    "finished_at": None,
                    "duration_seconds": None,
                }
                self._jobs[job_id] = job
                self._batches[batch_id].append(job_id)
                self._executor.submit(self._run_job, job_id)

        return self.get_batch_status(batch_id)

    def get_batch_status(self, batch_id: str) -> BatchStatusResponse:
        with self._lock:
            job_ids = self._batches.get(batch_id)
            if not job_ids:
                raise KeyError(batch_id)

            jobs = [self._to_job_item(self._jobs[job_id]) for job_id in job_ids]

        total_jobs = len(jobs)
        queued_jobs = sum(job.status == "queued" for job in jobs)
        running_jobs = sum(job.status == "processing" for job in jobs)
        completed_jobs = sum(job.status == "completed" for job in jobs)
        failed_jobs = sum(job.status == "failed" for job in jobs)
        done_jobs = completed_jobs + failed_jobs
        progress_pct = round((done_jobs / total_jobs) * 100, 2) if total_jobs else 0.0

        return BatchStatusResponse(
            batch_id=batch_id,
            total_jobs=total_jobs,
            queued_jobs=queued_jobs,
            running_jobs=running_jobs,
            completed_jobs=completed_jobs,
            failed_jobs=failed_jobs,
            progress_pct=progress_pct,
            jobs=jobs,
        )

    def _to_job_item(self, job: dict) -> BatchJobItem:
        return BatchJobItem(
            job_id=job["job_id"],
            filename=job["filename"],
            status=job["status"],
            error=job["error"],
            result=job["result"],
            created_at=job["created_at"],
            started_at=job["started_at"],
            finished_at=job["finished_at"],
            duration_seconds=job["duration_seconds"],
        )

    def _run_job(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job["status"] = "processing"
            job["started_at"] = _utc_now_iso()

        started = time.perf_counter()
        try:
            pdf_path = Path(job["file_path"])
            text = extract_text_from_pdf(pdf_path)
            if not text:
                raise ValueError(
                    "无法从该 PDF 提取文本。请确认文件不是纯图片扫描件，或尝试上传文字版 PDF。"
                )

            esg_data = analyze_esg_data(text, filename=job["filename"])
            with SessionLocal() as db:
                save_report(db, esg_data, pdf_filename=job["filename"])

            status = "completed"
            error = None
            result = esg_data
        except Exception as exc:  # pragma: no cover - background execution path
            status = "failed"
            error = str(exc)
            result = None

        finished = _utc_now_iso()
        duration = round(time.perf_counter() - started, 3)

        with self._lock:
            job = self._jobs[job_id]
            job["status"] = status
            job["error"] = error
            job["result"] = result
            job["finished_at"] = finished
            job["duration_seconds"] = duration


batch_manager = BatchAnalysisManager(max_workers=max(1, settings.batch_max_workers))
