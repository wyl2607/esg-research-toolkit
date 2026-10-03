from __future__ import annotations

import re
from pathlib import Path

import pytest


CONFIG = Path("nginx/esg.conf").read_text(encoding="utf-8")
SERVER_CONFIG = re.split(r"(?m)^\s*location\s", CONFIG, maxsplit=1)[0]
# This config uses flat location blocks. Preserve their order: nginx selects the
# first matching regex after checking exact locations and the longest prefix.
LOCATIONS = re.findall(r"location\s+([^\n{]+)\s*\{([^{}]*)\}", CONFIG)
HEADERS = (
    "X-Frame-Options SAMEORIGIN",
    "X-Content-Type-Options nosniff",
    "Referrer-Policy strict-origin-when-cross-origin",
    'Strict-Transport-Security "max-age=31536000"',
    'Permissions-Policy "camera=(), microphone=(), geolocation=()"',
    "Content-Security-Policy-Report-Only \"default-src 'self'; base-uri 'self'; "
    "object-src 'none'; frame-ancestors 'self'; img-src 'self' data: blob: https:; "
    "font-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; "
    "connect-src 'self' https:; worker-src 'self' blob:;\"",
)


def location_for(path: str) -> str:
    for selector, body in LOCATIONS:
        if selector.strip() == f"= {path}":
            return body
    # ^~ would bypass the denial regexes. Do not allow it in this config.
    assert not any(selector.strip().startswith("^~") for selector, _ in LOCATIONS)
    for selector, body in LOCATIONS:
        parts = selector.strip().split(maxsplit=1)
        if parts[0] in ("~", "~*"):
            flags = re.IGNORECASE if parts[0] == "~*" else 0
            if re.search(parts[1], path, flags):
                return body
    prefixes = [(s.strip(), b) for s, b in LOCATIONS if not s.strip().startswith(("=", "~"))]
    return max((pair for pair in prefixes if path.startswith(pair[0])), key=lambda pair: len(pair[0]))[1]


def test_nginx_spa_contract_separates_routes_assets_and_404s() -> None:
    assert "charset utf-8;" in CONFIG
    assert LOCATIONS, "must parse location blocks"
    shell = location_for("/index.html")
    assert 'add_header Cache-Control "no-cache, must-revalidate" always;' in shell
    assert "try_files $uri =404;" in shell
    default = location_for("/nonexistent-page-xyz")
    assert "error_page 404 =404 /index.html;" in default
    assert "try_files $uri $uri/ =404;" in default
    assert "error_page" not in SERVER_CONFIG, "denials must not inherit the SPA error page"
    assert "try_files $uri $uri/ =404;" in location_for("/")
    assert "proxy_pass http://127.0.0.1:8001/;" in location_for("/api/health")


def test_production_router_routes_have_spa_fallback() -> None:
    app = Path("frontend/src/App.tsx").read_text(encoding="utf-8")
    routes = re.findall(r'<Route path="([^"]+)"', app)
    for route in routes:
        if route in ("*", "design-preview"):
            continue
        path = "/" + route.replace(":companyName", "SAP%20SE").replace(":field", "scope1")
        for candidate in (path, path + "/"):
            assert "try_files $uri /index.html;" in location_for(candidate), candidate
    # React Router's default matching is case-insensitive.
    assert "try_files $uri /index.html;" in location_for("/UPLOAD")


@pytest.mark.parametrize("path", [
    "/.env", "/.git/config", "/.hidden/", "/companies/.env",
    "/frameworks/.git/config", "/assets/.hidden/file.js", "/api/.env",
    "/index.php", "/companies/SAP.PHP", "/upload.sql", "/dump.sql/extra",
    "/companies/report.bak", "/assets/source.env", "/source.git/config",
    "/settings.ini", "/debug.log", "/index.old", "/file.swp", "/file.swo",
    "/file.backup", "/file.orig", "/file.save", "/file.tmp", "/file.phtml",
    "/file.phar", "/file.php8", "/file.conf", "/file.config", "/file.yaml",
    "/file.yml", "/file.toml", "/file.py", "/file.sh",
])
def test_sensitive_paths_return_404_without_shell_or_disk_lookup(path: str) -> None:
    body = location_for(path)
    assert "return 404;" in body
    assert "try_files" not in body
    assert "index.html" not in body
    assert "error_page" not in body


@pytest.mark.parametrize("path", [
    "/assets/missing.js", "/assets/missing.css", "/assets/missing",
    "/assets/missing.unknown", "/assets/nested/missing.bin", "/assets/", "/assets",
    "/missing.js", "/missing.svg",
])
def test_assets_never_fall_back_to_shell(path: str) -> None:
    body = location_for(path)
    assert "try_files $uri =404;" in body
    assert "index.html" not in body
    assert 'add_header Cache-Control "public, max-age=31536000, immutable";' in body
    assert 'immutable" always' not in body, "do not cache missing assets for a year"


@pytest.mark.parametrize("path", [
    "/upload-typo", "/upload/unknown", "/frameworks/unknown",
    "/companies/SAP/unknown", "/coverage", "/coverage/scope1/unknown",
    "/taxonomy-typo", "/nonexistent-page-xyz",
])
def test_unknown_routes_keep_real_404(path: str) -> None:
    body = location_for(path)
    assert "try_files $uri $uri/ =404;" in body
    assert "error_page 404 =404 /index.html;" in body


def test_security_headers_survive_cache_header_overrides() -> None:
    server_headers = SERVER_CONFIG
    for header in HEADERS:
        assert f"add_header {header} always;" in server_headers
    for selector, body in LOCATIONS:
        if "add_header" in body:
            for header in HEADERS:
                assert f"add_header {header} always;" in body, selector
