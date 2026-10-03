"""CSP violation report endpoint — receives violation reports from browsers."""
from __future__ import annotations

import json
import logging
import re
import time
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from starlette.types import ASGIApp, Receive, Scope, Send

from core.limiter import limiter

router = APIRouter(tags=["csp_report"])


MAX_BODY_BYTES = 16 * 1024
MAX_LOG_LINES_PER_MINUTE = 100

_log_counts: dict[int, int] = {}
_current_minute: int = 0


def configure_csp_logging() -> None:
    """Emit reports to stderr independently of uvicorn/Alembic root logging."""
    logger = logging.getLogger("csp.report")
    logger.setLevel(logging.INFO)
    logger.disabled = False
    if not any(handler.name == "csp.report" for handler in logger.handlers):
        handler = logging.StreamHandler()
        handler.set_name("csp.report")
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.propagate = False


class LegacyCSPReport(BaseModel):
    """Legacy CSP report format: {"csp-report": {...}}"""
    csp_report: dict = Field(alias="csp-report")


class ReportEntry(BaseModel):
    """Entry in the application/reports+json format."""
    type: str
    body: dict


def _sanitize_blocked_uri(uri: str) -> str:
    """Keep only an origin or scheme, never credentials or URL payloads."""
    if not uri or uri == "self" or uri == "inline" or uri == "eval":
        return uri
    scheme = ""
    try:
        parsed = urlparse(uri)
        scheme = parsed.scheme
        if scheme and parsed.hostname:
            hostname = parsed.hostname
            port = parsed.port  # Validate before emitting any part of the origin.
            if ":" in hostname:
                hostname = f"[{hostname}]"
            return f"{scheme}://{hostname}" + (f":{port}" if port is not None else "")
    except ValueError:
        # urlparse can reject a malformed authority before returning its scheme.
        match = re.match(r"^([a-zA-Z][a-zA-Z0-9+.-]*):", uri)
        scheme = match.group(1).lower() if match else ""
    return f"{scheme}:" if scheme else ""


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


class CSPBodyLimitMiddleware:
    """Middleware to enforce body size limit on CSP report endpoint only."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["path"] == "/csp-report" and scope["method"] == "POST":
            request = Request(scope, receive)
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    if int(content_length) > MAX_BODY_BYTES:
                        await Response(status_code=413)(scope, receive, send)
                        return
                except ValueError:
                    pass
            # Read at most the limit plus the first excess ASGI chunk. Never
            # call downstream middleware on rejection: its disconnect listener
            # could otherwise keep draining the untrusted request body.
            body = bytearray()
            async for chunk in request.stream():
                if len(body) + len(chunk) > MAX_BODY_BYTES:
                    await Response(status_code=413)(scope, receive, send)
                    return
                body.extend(chunk)

            body_sent = False

            async def bounded_receive():
                nonlocal body_sent
                if not body_sent:
                    body_sent = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()

            await self.app(scope, bounded_receive, send)
            return
        await self.app(scope, receive, send)


# Allow browser bursts above the default 60/minute, but bound requests per client.
@router.post("/csp-report", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
@limiter.limit("100/minute")
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
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_BODY_BYTES:
            raise HTTPException(status_code=413, detail="Body too large")
        body.extend(chunk)

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
