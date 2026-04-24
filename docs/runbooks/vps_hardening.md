# VPS Hardening Runbook (P0/P1 fixes)

> Action list to make the demo VPS production-acceptable. Items mirror the
>压力测试 findings from 2026-04-15.

---

## P0 — Required before any public link is shared

### P0.0 Production environment gates

Set these before exposing the service publicly:

```bash
APP_ENV=production
CORS_ALLOWED_ORIGINS=https://demo.example.com
ADMIN_API_TOKEN=<long-random-token>
USE_ALEMBIC_INIT=true
ENFORCE_MIGRATION_GATE=true
```

`CORS_ALLOWED_ORIGINS` must list deployed frontend origins explicitly. Destructive report management routes require `X-Admin-Token`; in production they return 503 when `ADMIN_API_TOKEN` is not configured.

`USE_ALEMBIC_INIT=true` makes startup run `alembic upgrade head`; the migration gate then verifies `alembic_version` before the service finishes booting. Production startup intentionally refuses the legacy runtime `create_all` path.

### P0.1 Run uvicorn with multiple workers

**Symptom**: single-worker p50 went from 48ms → 299ms under burst-200 concurrency.

**Fix on VPS** (`/etc/systemd/system/esg-toolkit.service` or your launcher):

```ini
ExecStart=/opt/esg-toolkit/.venv/bin/uvicorn main:app \
    --host 127.0.0.1 --port 8000 \
    --workers 4 \
    --proxy-headers \
    --forwarded-allow-ips '127.0.0.1'
```

Behind nginx reverse proxy. **Never** expose 8000 directly.

### P0.2 PDF upload validation (DONE in code)

Already enforced in `report_parser/api.py::_validate_pdf_bytes`:

- extension `.pdf`
- size 1 KB ≤ x ≤ 50 MB
- magic bytes `%PDF-` at offset 0

No additional VPS work needed. Verify via:

```bash
curl -i -F file=@/etc/passwd http://127.0.0.1:8000/report/upload
# expect: 400 "Only PDF files are supported"

dd if=/dev/urandom bs=1M count=60 of=/tmp/big.pdf
curl -i -F file=@/tmp/big.pdf http://127.0.0.1:8000/report/upload
# expect: 413 "PDF too large"
```

---

## P1 — Add within first week of public exposure

### P1.1 Rate limiting via slowapi

Install:

```bash
.venv/bin/pip install 'slowapi>=0.1.9'
```

Patch `main.py` (apply on VPS deploy branch — keep the in-repo version
clean because local dev doesn't need this):

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Tighter limit on upload routes:
# (in report_parser/api.py)
# @router.post("/upload")
# @limiter.limit("5/minute")
```

### P1.2 Connection pool (DONE in code)

`core/database.py` already opens Postgres engines with
`pool_size=10, max_overflow=20, pool_recycle=1800, pool_pre_ping=True`.

### P1.3 Bounded `_jobs` dict (DONE in code)

`report_parser/batch_jobs.py` now evicts terminal jobs older than 24h
on every `submit()`, hard-cap 5000 jobs in memory.

### P1.4 nginx hardening

```nginx
client_max_body_size 60M;          # match MAX_PDF_BYTES + headroom
client_body_timeout 60s;
limit_req_zone $binary_remote_addr zone=esg_api:10m rate=2r/s;
limit_req zone=esg_api burst=10 nodelay;

# headers
add_header X-Frame-Options DENY;
add_header X-Content-Type-Options nosniff;
add_header Referrer-Policy strict-origin-when-cross-origin;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

---

## P2 — Nice to have

| Item | Why | Effort |
|---|---|---|
| `/techno/lcoe` payload schema fix | one of the stress tests hit a 422 | 30 min |
| Recharts width(-1) warnings | console noise in prod console | 1 hour |
| Sentry / OpenTelemetry | catch errors you don't see | half day |
| Daily DB backup (`pg_dump` cron) | recover from accidental deletion | 30 min |

---

## Verification checklist after every deploy

```bash
# health
curl -fsS https://demo.example.com/health

# upload validation
curl -i -F file=@/etc/hostname https://demo.example.com/report/upload   # 400
echo "%PDF-1.4 fake" > /tmp/fake.pdf && \
  curl -i -F file=@/tmp/fake.pdf https://demo.example.com/report/upload  # 422

# rate limit
for i in $(seq 1 70); do curl -s -o /dev/null -w "%{http_code} " https://demo.example.com/health; done
# expect: bunch of 200, then some 429

# benchmark
curl -s https://demo.example.com/benchmarks/D35.11 | jq '.metrics | length'
# expect: > 0
```
