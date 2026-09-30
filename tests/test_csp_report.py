"""Tests for CSP violation report endpoint."""
from __future__ import annotations

import json
import logging
from io import StringIO

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("main.init_db", lambda: None)
    return TestClient(app)


@pytest.fixture
def log_capture():
    """Capture log output from csp.report logger."""
    logger = logging.getLogger("csp.report")
    logger.setLevel(logging.INFO)
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    yield stream
    logger.removeHandler(handler)


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

def test_reporting_api_camelcase_fields_are_logged(client, caplog):
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
    with caplog.at_level("INFO", logger="csp.report"):
        response = client.post("/csp-report", content=json.dumps(payload),
                               headers={"Content-Type": "application/reports+json"})
    assert response.status_code == 204
    text = caplog.text
    assert "directive=script-src-elem" in text
    assert "blocked_uri=https://cdn.evil.example " in text
    assert "document_uri=/report " in text
    assert "token=abc" not in text and "id=1" not in text


def test_control_characters_cannot_forge_log_lines(client, caplog):
    payload = {"csp-report": {"document-uri": "https://esg.example/",
                              "violated-directive": "img-src\nCSP violation: directive=FORGED"}}
    with caplog.at_level("INFO", logger="csp.report"):
        response = client.post("/csp-report", content=json.dumps(payload),
                               headers={"Content-Type": "application/csp-report"})
    assert response.status_code == 204
    records = [r for r in caplog.records if r.name == "csp.report"]
    assert len(records) == 1
    assert "\n" not in records[0].getMessage()


def test_not_subject_to_global_rate_limit(client, monkeypatch):
    from core.limiter import limiter
    monkeypatch.setattr(limiter, "enabled", True)
    payload = {"csp-report": {"document-uri": "https://esg.example/", "violated-directive": "img-src"}}
    codes = {client.post("/csp-report", content=json.dumps(payload),
                         headers={"Content-Type": "application/csp-report"}).status_code
             for _ in range(70)}
    assert codes == {204}
