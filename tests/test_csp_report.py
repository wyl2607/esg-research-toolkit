"""Tests for CSP violation report endpoint."""
from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import sys
from io import StringIO

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client(monkeypatch, log_capture):
    monkeypatch.setattr("main.init_db", lambda: None)
    with TestClient(app) as client:
        yield client


@pytest.fixture
def log_capture(monkeypatch):
    """Capture stderr from the application's startup-installed stream handler."""
    import report_parser.csp_report as csp_module

    logger = logging.getLogger("csp.report")
    old_handlers = logger.handlers[:]
    old_level, old_propagate, old_disabled = logger.level, logger.propagate, logger.disabled
    logger.handlers = []
    logger.setLevel(logging.NOTSET)
    monkeypatch.setattr(logging.getLogger(), "level", logging.WARNING)
    monkeypatch.setattr(csp_module, "_log_counts", {})
    stream = StringIO()
    monkeypatch.setattr("sys.stderr", stream)
    yield stream
    for handler in logger.handlers:
        handler.close()
    logger.handlers = old_handlers
    logger.setLevel(old_level)
    logger.propagate = old_propagate
    logger.disabled = old_disabled


def test_csp_report_legacy_format(client, log_capture):
    """Legacy application/csp-report format returns 204 and logs sanitized fields."""
    payload = {
        "csp-report": {
            "document-uri": "https://example.com/page?query=1",
            "referrer": "https://example.com/",
            "violated-directive": "script-src",
            "effective-directive": "script-src",
            "original-policy": "script-src 'self'",
            "blocked-uri": "https://evil.com/script.js?param=value",
            "disposition": "enforce",
            "status-code": 200,
        }
    }

    response = client.post(
        "/csp-report",
        json=payload,
        headers={"content-type": "application/csp-report"},
    )

    assert response.status_code == 204
    log_output = log_capture.getvalue()
    assert "CSP violation:" in log_output
    assert "directive=script-src" in log_output
    assert "blocked_uri=https://evil.com" in log_output  # sanitized to scheme+host
    assert "document_uri=/page" in log_output  # path without query
    assert "disposition=enforce" in log_output
    assert "status_code=200" in log_output
    # Ensure full URLs are NOT logged
    assert "evil.com/script.js" not in log_output
    assert "?query=1" not in log_output


def test_csp_report_reports_json_format(client, log_capture):
    """application/reports+json format with multiple violations returns 204."""
    payload = [
        {
            "type": "csp-violation",
            "body": {
                "document-uri": "https://example.com/page1",
                "violated-directive": "img-src",
                "blocked-uri": "https://tracker.com/pixel.gif",
                "disposition": "report",
                "status-code": 200,
            },
        },
        {
            "type": "csp-violation",
            "body": {
                "document-uri": "https://example.com/page2",
                "violated-directive": "connect-src",
                "blocked-uri": "https://analytics.com/collect",
                "disposition": "enforce",
                "status-code": 200,
            },
        },
    ]

    response = client.post(
        "/csp-report",
        json=payload,
        headers={"content-type": "application/reports+json"},
    )

    assert response.status_code == 204
    log_output = log_capture.getvalue()
    assert log_output.count("CSP violation:") == 2
    assert "directive=img-src" in log_output
    assert "directive=connect-src" in log_output
    assert "blocked_uri=https://tracker.com" in log_output
    assert "blocked_uri=https://analytics.com" in log_output


def test_csp_report_oversized_body(client):
    """Body larger than 16KB returns 413."""
    payload = {
        "csp-report": {
            "document-uri": "https://example.com/",
            "violated-directive": "default-src",
            "blocked-uri": "https://evil.com/" + "x" * 20000,  # > 16KB
        }
    }
    body = json.dumps(payload).encode()

    response = client.post(
        "/csp-report",
        content=body,
        headers={"content-type": "application/csp-report"},
    )

    assert response.status_code == 413


def test_csp_report_no_auth_required(client):
    """Endpoint works without any authentication headers."""
    payload = {
        "csp-report": {
            "document-uri": "https://example.com/",
            "violated-directive": "script-src",
            "blocked-uri": "https://evil.com/x.js",
        }
    }

    response = client.post(
        "/csp-report",
        json=payload,
        headers={"content-type": "application/csp-report"},
    )

    assert response.status_code == 204


def test_csp_report_flood_protection(client, log_capture, monkeypatch):
    """Flood protection drops extra log lines after limit."""
    import report_parser.csp_report as csp_module

    original_limit = csp_module.MAX_LOG_LINES_PER_MINUTE
    monkeypatch.setattr(csp_module, "MAX_LOG_LINES_PER_MINUTE", 3)
    # Also reset the internal counters
    monkeypatch.setattr(csp_module, "_log_counts", {})
    monkeypatch.setattr(csp_module, "_current_minute", int(__import__("time").time() // 60))

    try:
        payload = {
            "csp-report": {
                "document-uri": "https://example.com/",
                "violated-directive": "script-src",
                "blocked-uri": "https://evil.com/x.js",
            }
        }

        for i in range(5):
            response = client.post(
                "/csp-report",
                json=payload,
                headers={"content-type": "application/csp-report"},
            )
            assert response.status_code == 204

        log_output = log_capture.getvalue()
        assert log_output.count("CSP violation:") == 3
    finally:
        monkeypatch.setattr(csp_module, "MAX_LOG_LINES_PER_MINUTE", original_limit)


def test_csp_report_malformed_json(client):
    """Malformed JSON returns 400."""
    response = client.post(
        "/csp-report",
        content=b"not valid json",
        headers={"content-type": "application/csp-report"},
    )

    assert response.status_code == 400


def test_csp_report_unsupported_content_type(client):
    """Unsupported content type returns 400."""
    payload = {"csp-report": {"document-uri": "https://example.com/"}}
    response = client.post(
        "/csp-report",
        json=payload,
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 400


def test_csp_report_reports_json_non_csp_type_ignored(client, log_capture):
    """Non-csp-violation types in reports+json are ignored."""
    payload = [
        {"type": "other-type", "body": {}},
        {"type": "csp-violation", "body": {"document-uri": "https://example.com/", "violated-directive": "script-src"}},
    ]

    response = client.post(
        "/csp-report",
        json=payload,
        headers={"content-type": "application/reports+json"},
    )

    assert response.status_code == 204
    log_output = log_capture.getvalue()
    assert log_output.count("CSP violation:") == 1


def test_csp_report_special_blocked_uris(client, log_capture):
    """Special blocked-uri values (self, inline, eval) are preserved."""
    for special_uri in ["self", "inline", "eval"]:
        log_capture.seek(0)
        log_capture.truncate(0)

        payload = {
            "csp-report": {
                "document-uri": "https://example.com/",
                "violated-directive": "script-src",
                "blocked-uri": special_uri,
            }
        }

        response = client.post(
            "/csp-report",
            json=payload,
            headers={"content-type": "application/csp-report"},
        )

        assert response.status_code == 204
        log_output = log_capture.getvalue()
        assert f"blocked_uri={special_uri}" in log_output


def test_csp_report_empty_blocked_uri(client, log_capture):
    """Empty blocked-uri is handled gracefully."""
    payload = {
        "csp-report": {
            "document-uri": "https://example.com/",
            "violated-directive": "script-src",
            "blocked-uri": "",
        }
    }

    response = client.post(
        "/csp-report",
        json=payload,
        headers={"content-type": "application/csp-report"},
    )

    assert response.status_code == 204
    log_output = log_capture.getvalue()
    assert "blocked_uri=" in log_output

def test_reporting_api_camelcase_fields_are_logged(client, log_capture):
    """Real Reporting API payloads (Chrome/Edge) use camelCase keys in body."""
    payload = [{
        "type": "csp-violation",
        "age": 10,
        "url": "https://esg.example/report?id=1",
        "user_agent": "Mozilla/5.0",
        "body": {
            "documentURL": "https://esg.example/report?id=1",
            "blockedURL": "https://cdn.evil.example/x.js?token=abc",
            "effectiveDirective": "script-src-elem",
            "disposition": "report",
            "statusCode": 200,
        },
    }]
    response = client.post("/csp-report", content=json.dumps(payload),
                               headers={"Content-Type": "application/reports+json"})
    assert response.status_code == 204
    text = log_capture.getvalue()
    assert "directive=script-src-elem" in text
    assert "blocked_uri=https://cdn.evil.example " in text
    assert "document_uri=/report " in text
    assert "token=abc" not in text and "id=1" not in text


def test_control_characters_cannot_forge_log_lines(client, log_capture):
    payload = {"csp-report": {"document-uri": "https://esg.example/",
                              "violated-directive": "img-src\nCSP violation: directive=FORGED"}}
    response = client.post("/csp-report", content=json.dumps(payload),
                               headers={"Content-Type": "application/csp-report"})
    assert response.status_code == 204
    lines = log_capture.getvalue().splitlines()
    assert len(lines) == 1
    assert "img-src CSP violation: directive=FORGED" in lines[0]


def test_csp_request_limit_allows_bursts_then_rejects(client, monkeypatch):
    from core.limiter import limiter
    monkeypatch.setattr(limiter, "enabled", True)
    payload = {"csp-report": {"document-uri": "https://esg.example/", "violated-directive": "img-src"}}
    codes = [client.post("/csp-report", content=json.dumps(payload),
                         headers={"Content-Type": "application/csp-report"}).status_code
             for _ in range(120)]
    assert codes[:100] == [204] * 100
    assert codes[100:] == [429] * 20
    import httpx

    async def send_from_other_client():
        transport = httpx.ASGITransport(app=app, client=("192.0.2.2", 12345))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as other_client:
            return await other_client.post("/csp-report", json=payload,
                                           headers={"Content-Type": "application/csp-report"})

    assert asyncio.run(send_from_other_client()).status_code == 204


@pytest.mark.parametrize("uri, expected", [
    ("https://user:pass@example.org/x", "https://example.org"),
    ("https://user:pass@example.org:8443/x?token=secret", "https://example.org:8443"),
    ("https://user:pass@[2001:db8::1]:8443/x", "https://[2001:db8::1]:8443"),
    ("https://example.org:bad/x", "https:"),
    ("https://example.org:65536/x", "https:"),
    ("https://[invalid/x", "https:"),
    ("https:/secret/path", "https:"),
    ("data:text/plain,secret", "data:"),
    ("blob:https://example.org/secret", "blob:"),
    ("mailto:user:pass@example.org", "mailto:"),
    ("/secret/path", ""),
])
def test_blocked_uri_origin_only(uri, expected):
    from report_parser.csp_report import _sanitize_blocked_uri

    assert _sanitize_blocked_uri(uri) == expected


def test_credentials_are_not_logged(client, log_capture):
    response = client.post("/csp-report", json={"csp-report": {
        "blocked-uri": "https://user:pass@example.org/x",
    }}, headers={"Content-Type": "application/csp-report"})
    assert response.status_code == 204
    assert "blocked_uri=https://example.org " in log_capture.getvalue()
    assert "user" not in log_capture.getvalue()
    assert "pass" not in log_capture.getvalue()


@pytest.mark.parametrize("content_length", [None, b"1", b"invalid"])
def test_streaming_body_limit_stops_receiving(client, content_length):
    """Reject a chunked 1 MiB upload immediately on the first excess chunk."""
    from report_parser.csp_report import MAX_BODY_BYTES

    chunk = b"x" * 4096
    received = 0
    messages = []
    headers = [(b"content-type", b"application/csp-report")]
    if content_length is not None:
        headers.append((b"content-length", content_length))

    async def receive():
        nonlocal received
        received += len(chunk)
        assert received <= MAX_BODY_BYTES + len(chunk), "Read past the first oversized chunk"
        return {"type": "http.request", "body": chunk, "more_body": received < 1024 * 1024}

    async def send(message):
        messages.append(message)

    asyncio.run(app({
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": "POST", "scheme": "http", "path": "/csp-report",
        "raw_path": b"/csp-report", "query_string": b"", "headers": headers,
        "client": ("192.0.2.1", 12345), "server": ("test", 80),
    }, receive, send))
    assert messages[0]["status"] == 413
    assert received == MAX_BODY_BYTES + len(chunk)


def test_body_exactly_at_limit_is_accepted(client):
    from report_parser.csp_report import MAX_BODY_BYTES

    body = b'{"csp-report": {}}'
    body += b" " * (MAX_BODY_BYTES - len(body))
    assert client.post("/csp-report", content=body,
                       headers={"Content-Type": "application/csp-report"}).status_code == 204


def test_startup_logging_survives_uvicorn_and_alembic_config():
    # Run real startup logging configuration in isolation from pytest handlers.
    result = subprocess.run([sys.executable, "-c", """
import logging
from logging.config import dictConfig, fileConfig
from fastapi.testclient import TestClient
from uvicorn.config import LOGGING_CONFIG
import main
from report_parser.csp_report import configure_csp_logging

dictConfig(LOGGING_CONFIG)
def init_db():
    fileConfig('alembic.ini', disable_existing_loggers=False)
main.init_db = init_db
main.validate_models_startup = lambda: None
with TestClient(main.app) as client:
    assert logging.getLogger().getEffectiveLevel() == logging.WARNING
    logger = logging.getLogger('csp.report')
    assert logger.getEffectiveLevel() == logging.INFO
    configure_csp_logging()
    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], logging.StreamHandler)
    response = client.post('/csp-report', json={'csp-report': {
        'effective-directive': 'script-src',
    }}, headers={'Content-Type': 'application/csp-report'})
    assert response.status_code == 204
"""], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert result.stderr.count("CSP violation:") == 1
