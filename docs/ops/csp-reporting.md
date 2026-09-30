# CSP Violation Reporting — Operations Guide

## Overview

This document describes the nginx configuration required to send Content-Security-Policy violation reports to the FastAPI endpoint `/api/csp-report`.

The FastAPI application exposes `POST /csp-report` (mounted at `/api/csp-report` through nginx proxy). It accepts both legacy `application/csp-report` and modern `application/reports+json` (Reporting API v1) formats.

## Nginx Configuration

Add the following to your server block in `nginx/esg.conf` (or equivalent production config):

```nginx
server {
    listen 80;
    server_name esg.meichen.beauty;

    # Content-Security-Policy-Report-Only with reporting endpoint
    add_header Content-Security-Policy-Report-Only
        "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self';
         report-uri /api/csp-report;
         report-to csp-endpoint"
        always;

    # Reporting API v1 endpoint declaration
    add_header Reporting-Endpoints 'csp-endpoint="/api/csp-report"' always;

    # Frontend static files
    root /opt/esg-research-toolkit/frontend/dist;
    index index.html;
    charset utf-8;

    # API proxy → FastAPI on port 8001
    location /api/ {
        proxy_pass http://127.0.0.1:8001/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        # Allow large PDF uploads
        client_max_body_size 50M;
    }

    # IMPORTANT: add_header is NOT inherited into nested location blocks.
    # The location ^~ /assets/ block (and any other location blocks that serve
    # responses) must also include the CSP headers if you want violations
    # from those responses to be reported.
    #
    # Example for assets block:
    # location ^~ /assets/ {
    #     add_header Content-Security-Policy-Report-Only
    #         "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self';
    #          report-uri /api/csp-report;
    #          report-to csp-endpoint"
    #         always;
    #     add_header Reporting-Endpoints 'csp-endpoint="/api/csp-report"' always;
    #     ...
    # }

    # The shell is replaced by deployments; never cache it past a release.
    location = /index.html {
        try_files $uri =404;
        add_header Cache-Control "no-cache, must-revalidate" always;
    }

    # Vite assets are content-hashed; missing asset-like paths must be real 404s.
    location ~* \.(?:css|js|mjs|map|json|png|jpe?g|gif|svg|ico|webp|avif|woff2?|ttf|eot|wasm|txt|xml)$ {
        try_files $uri =404;
        add_header Cache-Control "public, max-age=31536000, immutable" always;
    }

    # Keep this list synchronized with the route prefixes in frontend/src/App.tsx.
    # Only known React Router routes may fall back to the SPA shell.
    location ~ ^/(?:upload|disclosures|taxonomy|lcoe|saf|companies(?:/|$)|manual|compare|benchmarks|frameworks(?:/|$)|regional|coverage(?:/|$))(?:.*)?$ {
        try_files $uri $uri/ /index.html;
    }

    # Unknown application paths render the React NotFound route, while retaining
    # the original 404 status. Static-resource locations above keep their own 404s.
    location / {
        error_page 404 =404 /index.html;
        try_files $uri $uri/ =404;
    }
}
```

## Key Points

1. **`report-uri`** — Legacy directive, still widely supported. Points to `/api/csp-report`.
2. **`report-to`** — Modern Reporting API v1 directive, references a named endpoint group.
3. **`Reporting-Endpoints` header** — Declares the named endpoint group (`csp-endpoint`) and its URL.
4. **`add_header` is not inherited** — Every `location` block that serves HTML/JS/CSS responses must include these headers. At minimum:
   - The main `server` block (covers `/` and SPA routes)
   - The `location ^~ /assets/` block (covers Vite assets)
   - Any other custom location blocks serving content

## Deployment Steps

1. **Update nginx config** with the headers above.
2. **Reload nginx**: `nginx -s reload`
3. **Observe for 7 days** in `Report-Only` mode:
   - Check logs for `CSP violation:` entries (structured JSON via logging driver)
   - Verify no legitimate resources are being blocked
   - Adjust policy directives as needed
4. **Promote to enforcing** by changing `Content-Security-Policy-Report-Only` to `Content-Security-Policy` (same value, no `-Report-Only` suffix).
5. **Reload nginx** again.

## Log Format

Each violation produces one structured log line:

```
CSP violation: directive=script-src blocked_uri=https://evil.com document_uri=/page disposition=enforce status_code=200
```

Fields:
- `directive` — effective/violated directive (e.g., `script-src`)
- `blocked_uri` — scheme+host only (path/query stripped); special values `self`, `inline`, `eval` preserved
- `document_uri` — path only (no query string)
- `disposition` — `enforce` or `report`
- `status_code` — HTTP status of the blocked resource (0 if not applicable)

No IPs, cookies, or full URLs are logged.

## Rate Limiting & Flood Protection

- Request bodies > 16 KB are rejected with **413**.
- In-process flood protection: max **100 log lines/minute**; excess violations are accepted (204) but silently dropped from logs.
- Endpoint is **exempt from global API rate limiting** and requires **no authentication**.

## Testing the Endpoint

```bash
# Legacy format
curl -X POST https://esg.meichen.beauty/api/csp-report \
  -H "Content-Type: application/csp-report" \
  -d '{"csp-report":{"document-uri":"https://example.com/","violated-directive":"script-src","blocked-uri":"https://evil.com/x.js"}}'

# Reporting API v1 format
curl -X POST https://esg.meichen.beauty/api/csp-report \
  -H "Content-Type: application/reports+json" \
  -d '[{"type":"csp-violation","body":{"document-uri":"https://example.com/","violated-directive":"script-src","blocked-uri":"https://evil.com/x.js"}}]'

# Both should return 204 No Content
```