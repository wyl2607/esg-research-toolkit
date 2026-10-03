# Nginx SPA Routing Contract

The production Nginx server is the boundary for the built React application:

- `/index.html` and SPA shells use UTF-8 and `Cache-Control: no-cache`.
- Existing files under `/assets/` retain immutable caching for one year. Missing assets, including extensionless files and unknown suffixes, return 404 without the SPA shell or immutable caching.
- Dotfiles/directories in any path segment and source/backup extensions return 404 before disk lookup, even under a known route or `/assets/`. These responses never contain `index.html`.
- Only production routes in `frontend/src/App.tsx` fall back to the shell. Dynamic routes accept one nonempty segment, and trailing slashes are supported. `design-preview` is development-only.
- Unknown application paths still render the React NotFound page with a real 404 status.
- The six security headers observed in production on 2026-10-03 apply to successful responses and errors, with the exact values listed below. Every location with a Cache-Control `add_header` repeats all six with `always` because nginx otherwise drops inherited headers.

## Local config check

Run the parser-based contract check, also included in the normal backend test gate:

```bash
OPENAI_API_KEY=test_key_placeholder DATABASE_URL=sqlite:// \
  ADMIN_API_TOKEN=test_admin_token \
  .venv/bin/pytest tests/test_nginx_spa_contract.py -q
```

It verifies regex order, rejection before disk lookup, asset handling, security
header inheritance, and fallback for every production route read from the frontend
router. The repository's Docker setup runs the backend, not nginx; this check
needs no nginx installation or Docker daemon. It does not replace `nginx -t` on
the deployment host against its complete configuration (including TLS and other
includes).

## Post-deploy checks (operator only)

**Operator warning:** the live `/etc/nginx/sites-available/esg.conf` already
differs from the repository. As observed on 2026-10-03, live index HTML sends
`Cache-Control: no-cache, no-store, must-revalidate`, and live already returns
404 for `/.env`. Diff the live config against `nginx/esg.conf` before installing
and reconcile existing deployment-specific behavior, including HTML caching.
After installing, run `sudo nginx -t` against the complete config before
reloading. The deployment script installs the config only on first deploy:
an existing installation needs an explicit config update. This task does not
deploy or reload nginx.

Run the read-only smoke check against the deployed build:

```bash
ESG_FRONTEND_URL=https://esg.meichen.beauty node scripts/qa/nginx-spa-smoke.mjs
```

It checks every route below, denial responses without the shell, UTF-8/no-cache
HTML, all six security headers (including 404s), and a real built asset's
immutable caching. DNS/TLS and any site-specific additional headers still need
operator verification.

Each URL below must return **200**, including refreshed dynamic/deep routes:

```bash
base=https://esg.meichen.beauty
for path in / /upload /disclosures /taxonomy /lcoe /saf /companies \
  /companies/SAP%20SE /manual /compare /benchmarks /frameworks /regional \
  /coverage/scope1 /frameworks/regional; do
  curl --path-as-is -sS -o /dev/null -w "$path %{http_code}\n" "$base$path"
done
```

Each URL below must return **404**:

```bash
for path in /nonexistent-page-xyz /upload-typo /upload/unknown \
  /companies/SAP/unknown /frameworks/unknown /coverage/scope1/unknown \
  /.env /.git/config /companies/.env /assets/.hidden/file.js \
  /index.php /dump.sql /backup.bak /source.env /source.git /settings.ini \
  /debug.log /index.old /file.swp /assets/__missing__.js \
  /assets/__missing__ /assets/__missing__.unknown; do
  curl --path-as-is -sS -o /dev/null -w "$path %{http_code}\n" "$base$path"
done
```

Only unknown application routes may include the SPA NotFound shell; dotfiles,
source/backups, and missing assets must contain nginx's 404 body instead.
Check response headers and bodies with `curl --path-as-is -sS -i "$base/.env"`
and `curl -sS -i "$base/assets/__missing__.unknown"`: expect 404, the six
security headers, no immutable cache header, and no SPA shell.

Choose an actual hashed `/assets/...` URL from the current index HTML and run:

```bash
curl -sS "$base/"
# Replace the placeholder with a real src/href from the HTML above.
curl -sS -D - -o /dev/null "$base/assets/<actual-hashed-file>.js"
```

Expect **200**, `Cache-Control: public, max-age=31536000, immutable`, and
all six security headers below. Check `/` and `/companies/SAP%20SE` for 200,
`text/html; charset=utf-8`, `Cache-Control: no-cache, must-revalidate` per the
repo config (live currently also includes `no-store`), and the same headers.

Preserve this exact production security-header set on successful responses and
404s; this change does not tighten any values:

```text
Strict-Transport-Security: max-age=31536000
X-Content-Type-Options: nosniff
X-Frame-Options: SAMEORIGIN
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
Content-Security-Policy-Report-Only: default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'self'; img-src 'self' data: blob: https:; font-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self' https:; worker-src 'self' blob:;
```
