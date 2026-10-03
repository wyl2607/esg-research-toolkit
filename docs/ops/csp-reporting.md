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

    # Exact match overrides the upload-sized limit in /api/.
    location = /api/csp-report {
        client_max_body_size 16k;
        proxy_pass http://127.0.0.1:8001/csp-report;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

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

    # Locations inherit server headers only if they have no add_header of
    # their own. Repeat both reporting headers alongside Cache-Control below.

    # The shell is replaced by deployments; never cache it past a release.
    location = /index.html {
        try_files $uri =404;
        add_header Cache-Control "no-cache, must-revalidate" always;
        add_header Content-Security-Policy-Report-Only
            "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; report-uri /api/csp-report; report-to csp-endpoint"
            always;
        add_header Reporting-Endpoints 'csp-endpoint="/api/csp-report"' always;
    }

    # Vite assets are content-hashed; missing asset-like paths must be real 404s.
    location ~* \.(?:css|js|mjs|map|json|png|jpe?g|gif|svg|ico|webp|avif|woff2?|ttf|eot|wasm|txt|xml)$ {
        try_files $uri =404;
        add_header Cache-Control "public, max-age=31536000, immutable" always;
        add_header Content-Security-Policy-Report-Only
            "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; report-uri /api/csp-report; report-to csp-endpoint"
            always;
        add_header Reporting-Endpoints 'csp-endpoint="/api/csp-report"' always;
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
4. **`add_header` inheritance** — A location inherits all server-level headers only when it has no `add_header` directives of its own. Repeat both CSP and `Reporting-Endpoints` headers in every location that adds any header, including `/index.html` and the static-resource location above. SPA fallbacks internally redirect to `/index.html`, so its headers must include the reporting policy. Apply the same rule to custom locations such as `location ^~ /assets/`.
5. **Exact report location** — `location = /api/csp-report` enforces `client_max_body_size 16k` without reducing the 50M PDF upload limit for other API routes.

## Deployment Steps

1. **Update nginx config** with the headers above.
2. **Validate and reload nginx**: `nginx -t && nginx -s reload`. Verify the SPA shell headers on all three paths:

   ```bash
   for path in / /companies /index.html; do
       curl -sS -D - -o /dev/null "https://esg.meichen.beauty$path"
   done
   ```

   Each response must contain `Content-Security-Policy-Report-Only` and `Reporting-Endpoints`, plus `Cache-Control: no-cache, must-revalidate`. Verify static assets retain both reporting headers alongside their immutable cache header.
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
- `blocked_uri` — scheme + hostname + validated port only (credentials/path/query stripped); malformed or non-hierarchical URLs retain only the scheme; special values `self`, `inline`, `eval` preserved
- `document_uri` — path only (no query string)
- `disposition` — `enforce` or `report`
- `status_code` — HTTP status of the blocked resource (0 if not applicable)

No IPs, cookies, or full URLs are logged.

## Rate Limiting & Flood Protection

- Request bodies > 16 KB are rejected with **413** by nginx and the app. The app checks actual streamed bytes, including absent or incorrect Content-Length, and stops receiving at the first chunk that exceeds the limit.
- In-process flood protection: max **100 log lines/minute**; excess violations are accepted (204) but silently dropped from logs.
- The existing per-client limiter allows **100 requests/minute** for this endpoint, overriding the global 60/minute default to tolerate browser bursts. Further requests receive **429**; the log cap is independent of this request limit. Limits and log counters are per worker and use in-memory state.
- The endpoint requires **no authentication**. Client identity follows the existing limiter's remote-address key. Configure uvicorn to trust forwarded addresses only from your nginx proxy so separate clients have separate limits.

## Bounded Docker Logs

At application startup, `csp.report` is explicitly configured at INFO with its own stderr stream handler, independent of uvicorn and Alembic logging levels. Docker's logging driver captures these text lines; with `json-file`, each line is wrapped in the driver's JSON envelope.

Add this logging block to the existing `api` service in `docker-compose.prod.yml`:

```yaml
services:
  api:
    # Keep the existing service settings.
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

Recreate the API container through the normal deployment process to apply logging-driver changes (a restart alone does not apply them). This retains at most three 10 MB log files per container, bounding disk use even when many clients send reports. Verify the resulting container's logging options with `docker inspect --format '{{json .HostConfig.LogConfig}}' <api-container>` and inspect `docker logs <api-container>` for `CSP violation:` entries.

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