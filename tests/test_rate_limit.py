"""
Rate limit regression test.
Sends 6 rapid POST requests to /report/upload and asserts at least one 429.
Uses TestClient with X-Forwarded-For header to simulate same IP.
"""
import io

import pytest
from fastapi.testclient import TestClient


def _fresh_limiter_storage() -> None:
    """Replace the limiter's storage with a fresh MemoryStorage instance."""
    from limits.storage import MemoryStorage

    from core.limiter import limiter

    limiter._storage = MemoryStorage()


def test_upload_rate_limit() -> None:
    """6 rapid uploads from same IP should trigger 429 on at least the 6th request."""
    _fresh_limiter_storage()

    from main import app

    client = TestClient(app, raise_server_exceptions=False)

    responses = []
    for _ in range(6):
        fake_pdf = io.BytesIO(b"%PDF-1.4 fake content" + b"x" * 2048)
        resp = client.post(
            "/report/upload",
            files={"file": ("test.pdf", fake_pdf, "application/pdf")},
            headers={"X-Forwarded-For": "10.0.0.1"},
        )
        responses.append(resp.status_code)

    assert 429 in responses, f"Expected 429 in responses, got: {responses}"
