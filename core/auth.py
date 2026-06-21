"""Shared authentication dependencies.

`require_api_token` gates mutating / abuse-prone endpoints (e.g. disclosure
fetch and review) WITHOUT breaking local/dev usage:

- When no token is configured (``API_ACCESS_TOKEN`` / ``settings.api_access_token``
  is empty), the dependency is a no-op so the bundled frontend keeps working
  out of the box.
- When a token IS configured (recommended for any public deployment), every
  guarded request must present a matching ``X-API-Token`` header. The frontend
  must then be configured to send it.

Comparison is constant-time to avoid leaking the token through timing.
"""
from __future__ import annotations

import os
import secrets

from fastapi import Header, HTTPException

from core.config import settings


def require_api_token(x_api_token: str | None = Header(default=None)) -> None:
    configured_token = os.getenv("API_ACCESS_TOKEN", settings.api_access_token).strip()
    if not configured_token:
        # Unconfigured: open by default (local/dev). Operators opt in for public use.
        return
    if not secrets.compare_digest(x_api_token or "", configured_token):
        raise HTTPException(401, "API token required")
