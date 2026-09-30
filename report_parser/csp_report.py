"""CSP violation report endpoint — receives violation reports from browsers."""
from __future__ import annotations

import json
import logging
import re
import time
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

from core.limiter import limiter

router = APIRouter(tags=["csp_report"])


MAX_BODY_BYTES = 16 * 1024
MAX_LOG_LINES_PER_MINUTE = 100

_log_counts: dict[int, int] = {}
_current_minute: int = 0


class LegacyCSPReport(BaseModel):
    """Legacy CSP report format: {"csp-report": {...}}"""
    csp_report: dict = Field(alias="csp-report")


class ReportEntry(BaseModel):
    """Entry in the application/reports+json format."""
    type: str
    body: dict


def _sanitize_blocked_uri(uri: str) -> str:
    """Reduce blocked-uri to scheme+host, drop path and query."""
    if not uri or uri == "self" or uri == "inline" or uri == "eval":
        return uri
    try:
        parsed = urlparse(uri)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
        return uri
    except Exception:
        return uri


def _sanitize_document_uri(uri: str) -> str:
    """Extract path without query from document-uri."""
    if not uri:
        return uri
    try:
        parsed = urlparse(uri)
        return parsed.path or "/"
    except Exception:
        return uri


_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
MAX_FIELD_CHARS = 200


def _clean(value: object) -> str:
    """Strip control characters (no forged log lines) and cap length."""
    return _CONTROL_CHARS.sub(" ", str(value))[:MAX_FIELD_CHARS]


def _first(report: dict, *keys: str, default: object = "") -> object:
    for key in keys:
        value = report.get(key)
        if value not in (None, ""):
            return value
    return default


def _extract_violation_fields(report: dict) -> dict:
    """Extract and sanitize the fields we log from a CSP violation report.

    Legacy `application/csp-report` bodies use hyphenated keys (blocked-uri);
    Reporting API `application/reports+json` bodies use camelCase (blockedURL).
    """
    return {
        "directive": _clean(_first(report, "effective-directive", "violated-directive", "effectiveDirective")),
        "blocked_uri": _clean(_sanitize_blocked_uri(str(_first(report, "blocked-uri", "blockedURL")))),
        "document_uri": _clean(_sanitize_document_uri(str(_first(report, "document-uri", "documentURL")))),
        "disposition": _clean(_first(report, "disposition", default="enforce")),
        "status_code": _clean(_first(report, "status-code", "statusCode", default=0)),
    }


def _should_log() -> bool:
    """Check if we should log this violation (rate limiting)."""
    global _current_minute, _log_counts
    current = int(time.time() // 60)
    if current != _current_minute:
        _current_minute = current
        _log_counts.clear()
    count = _log_counts.get(current, 0)
    if count >= MAX_LOG_LINES_PER_MINUTE:
        return False
    _log_counts[current] = count + 1
    return True


class CSPBodyLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce body size limit on CSP report endpoint only."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/csp-report" and request.method == "POST":
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    if int(content_length) > MAX_BODY_BYTES:
                        return Response(status_code=413)
                except ValueError:
                    pass
        return await call_next(request)


# Browsers send violation reports in bursts; the global 60/min per-IP limit must not drop them.
@limiter.exempt
@router.post("/csp-report", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def receive_csp_report(request: Request) -> None:
    """
    Receive CSP violation reports.

    Accepts:
    - application/csp-report (legacy): {"csp-report": {...}}
    - application/reports+json (Reporting API v1): [{"type": "csp-violation", "body": {...}}, ...]

    Returns 204 No Content on success.
    Returns 413 if body exceeds 16 KB.
    Returns 400 if JSON is malformed.
    """
    body = await request.body()
    if len(body) > MAX_BODY_BYTES:
        raise HTTPException(status_code=413, detail="Body too large")

    content_type = request.headers.get("content-type", "").split(";")[0].strip()

    violations: list[dict] = []

    try:
        if content_type == "application/csp-report":
            data = json.loads(body)
            legacy = LegacyCSPReport(**data)
            violations.append(legacy.csp_report)
        elif content_type == "application/reports+json":
            data = json.loads(body)
            if not isinstance(data, list):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Expected array")
            for entry in data:
                report_entry = ReportEntry(**entry)
                if report_entry.type == "csp-violation":
                    violations.append(report_entry.body)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported content type")
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid report format")

    logger = logging.getLogger("csp.report")
    for violation in violations:
        if _should_log():
            fields = _extract_violation_fields(violation)
            logger.info(
                "CSP violation: directive=%s blocked_uri=%s document_uri=%s disposition=%s status_code=%s",
                fields["directive"],
                fields["blocked_uri"],
                fields["document_uri"],
                fields["disposition"],
                fields["status_code"],
            )

    return None