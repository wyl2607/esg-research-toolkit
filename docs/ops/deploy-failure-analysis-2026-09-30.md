# Deploy Failure Analysis — "Deploy to USA VPS" step (2026-04-24 through 2026-06-11)

_Written: 2026-09-30. Reviews failed workflow_dispatch runs on 2026-04-24, 06-10, and 06-11 (three reruns on 06-11, last at commit `3c1c6aa`)._

The missing Alembic flag is a reproduced production startup failure, covered by
`tests/test_migrations.py::test_production_init_requires_alembic_init`. It is not
a proven explanation for every historical failed deploy. History also records a
fingerprint-script failure (#54) and disk exhaustion (#56); attributing an
individual run requires its failing command and logs.

---

## 1. What "Deploy to USA VPS" runs on the server, step by step

The step uses `appleboy/ssh-action@v1.0.3` (at failure time) to SSH in and execute the following inline script with `set -e`:

| # | Command (deploy.yml line) | Script line |
|---|---|---|
| 1 | `cd /opt/esg-research-toolkit` | [deploy.yml:48](../../.github/workflows/deploy.yml#L48) |
| 2 | `git fetch --depth=1 origin main "$GITHUB_SHA"` | [deploy.yml:51](../../.github/workflows/deploy.yml#L51) |
| 3 | `git checkout --detach "$GITHUB_SHA"` | [deploy.yml:52](../../.github/workflows/deploy.yml#L52) |
| 4 | `bash scripts/deploy.sh` | [deploy.yml:55](../../.github/workflows/deploy.yml#L55) |
| 5 | Health-check loop: `curl -sf http://127.0.0.1:8001/health` × 10, 3 s sleep | [deploy.yml:58–63](../../.github/workflows/deploy.yml#L58-L63) |

**Inside `scripts/deploy.sh`** (after checkout, with `set -euo pipefail`):

| # | What it does | File:line |
|---|---|---|
| D1 | Detect `docker compose` vs `docker-compose` | [deploy.sh:17–25](../../scripts/deploy.sh#L17-L25) |
| D2 | `git rev-parse HEAD` (sanity check) | [deploy.sh:38](../../scripts/deploy.sh#L38) |
| D3 | `npm install && npm run build` in `frontend/` | [deploy.sh:43–44](../../scripts/deploy.sh#L43-L44) |
| D4 | `mkdir -p /opt/esg-data /opt/esg-reports` + `chown` (added 2026-06-12) | [deploy.sh:47–48](../../scripts/deploy.sh#L47-L48) |
| D5 | Assert `.env.prod` exists | [deploy.sh:51–55](../../scripts/deploy.sh#L51-L55) |
| D6 | `write_deploy_fingerprint.sh` → writes `.deploy-fingerprint.json` | [deploy.sh:59–64](../../scripts/deploy.sh#L59-L64) |
| D7 | `docker compose -f docker-compose.prod.yml build` (build-before-swap, added 2026-06-11 #56) | [deploy.sh:77](../../scripts/deploy.sh#L77) |
| D8 | `docker compose ... down --remove-orphans \|\| true` | [deploy.sh:80](../../scripts/deploy.sh#L80) |
| D9 | `docker compose ... up -d` | [deploy.sh:81](../../scripts/deploy.sh#L81) |
| D10 | `nginx -t && systemctl reload nginx` | [deploy.sh:88/93](../../scripts/deploy.sh#L88) |
| D11 | Smoke check: `/health`, `/health/deploy`, `/report/companies`, `/report/dashboard/stats` | [deploy.sh:123–144](../../scripts/deploy.sh#L123-L144) |
| D12 | `docker image prune -f` | [deploy.sh:148](../../scripts/deploy.sh#L148) |

The container itself (`CMD uvicorn main:app …`) calls `init_db()` synchronously in the FastAPI `lifespan` hook ([main.py:217](../../main.py#L217)) before accepting any request.

---

## 2. Reproduced defect and historical failure evidence

### A — Missing `USE_ALEMBIC_INIT=true` (reproduced startup failure)

**Evidence chain:**

1. Commit `e650838` (2026-04-24 21:19 — the **same day** as the first failure) added to `core/database.py` ([lines 144–148](../../core/database.py#L144-L148)):

   ```python
   else:        # use_alembic_init is False
       if production:
           raise RuntimeError(
               "Production startup requires USE_ALEMBIC_INIT=true so schema changes are "
               "managed by Alembic instead of runtime create_all helpers."
           )
   ```

2. `docker-compose.prod.yml` passes `APP_ENV: production` ([line 11](../../docker-compose.prod.yml#L11)) but did not set `USE_ALEMBIC_INIT` before this PR. The compose fix now sets it explicitly.

3. `scripts/setup_vps.sh` generates the `.env.prod` template without `USE_ALEMBIC_INIT` ([setup_vps.sh:36–42](../../scripts/setup_vps.sh#L36-L42)).

4. `scripts/deploy.sh` does not inject `USE_ALEMBIC_INIT` at any point.

5. The default in `core/config.py` is `use_alembic_init: bool = False` ([config.py:21](../../core/config.py#L21)).

**Crash path:** container starts → uvicorn → `lifespan` → `init_db()` → `production=True`, `use_alembic_init=False` → `RuntimeError` → uvicorn exits → container stops immediately → smoke check at port 8001 returns `Connection refused` on every attempt → `exit 1`.

A short deploy duration alone cannot identify the failing command. This crash
path applies when the effective production configuration leaves the flag false;
it does not establish which historical runs reached container startup.

**Migration risk:** An existing SQLite DB at `/opt/esg-data/esg_toolkit.db` may lack
an `alembic_version` table. Running `alembic upgrade head` on existing unversioned
tables can fail with `OperationalError: table already exists`. Stamping `head`
would only record migrations as applied, without executing them: a pre-0003
schema would still lack `company_reports.scope2_basis` and its data backfill.
Inspect the schema and revision, back up, and validate the cutover on a DB copy
first. Stamp only a verified matching revision when necessary, then run
`alembic upgrade head`; see section 4.

---

### B — Fingerprint-script failure (#54), not a fetch failure

Commit `5d5872d` (#54, 2026-06-11) documents stale `origin/main` and
`git branch -r --contains HEAD` returning no branch, causing the fingerprint
script's `grep` to exit 1. That is evidence of failure in
`write_deploy_fingerprint.sh`, not evidence that fetching a non-tip SHA failed.

Review reproduction fetched a non-tip SHA successfully with both
`git fetch --depth=1 origin main "$GITHUB_SHA"` and
`git fetch --depth=1 origin "$GITHUB_SHA"`. The earlier bad-refspec theory and its
confidence claim are withdrawn. Keep the existing fetch of `main` plus the SHA;
no fetch change is required for this startup fix.

---

### Cause C — `--no-cache` disk exhaustion (confirmed for 2026-06-11 by commit message, needs VPS for earlier runs)

Commit `fdd7f5d` (#56, 2026-06-11) documents explicitly: _"deploy.sh tore down the running container before building, the --no-cache build failed on a full disk (18G of containerd snapshots from repeated cacheless builds)"_. The April run used the same down-then-build-with-no-cache pattern (visible in `deploy.sh` at `3c1c6aa`, D6 was `down` then `build --no-cache`). The June disk failure does not establish the cause of the April run; earlier runs require their own logs.

---

### Cause D — `nginx -t && systemctl reload nginx` requires root (needs server)

`deploy.sh` steps D10 calls `nginx -t && systemctl reload nginx` ([lines 88, 93](../../scripts/deploy.sh#L88-L93)) without `sudo`. If `VPS_DEPLOY_USER` is non-root without passwordless sudo for `nginx`/`systemctl`, this command fails under `set -euo pipefail`. The guardrails doc requires a non-root deploy user ([DEPLOY_GUARDRAILS.md §7](../DEPLOY_GUARDRAILS.md#7-github-actions-deploy-baseline)) but does not specify sudo grants. Cannot verify without server access.

---

### Cause E — `chown -R 10001:10001` on `/opt/esg-data` requires root (needs server)

Added in `d35c22a` (#64, 2026-06-12 — after the last failure). Relevant only if Cause A and others are resolved and a future deploy runs. `chown` on a bind-mount directory owned by root fails without sudo. Non-issue for the April/June failure dates since that line did not exist yet.

---

### Summary table

| # | Finding | Evidence and limits |
|---|---|---|
| A | Missing `USE_ALEMBIC_INIT` causes production startup failure | Reproduced in migration test; historical effective env/logs still needed |
| B | Fingerprint script exits on missing branch match | Recorded by #54; non-tip SHA fetch succeeds in review reproduction |
| C | Disk full from `--no-cache` + down-before-build | Recorded by #56 for June; earlier runs unconfirmed |
| D | `nginx reload` permissions | Requires server verification |
| E | `chown` permissions | Requires server verification; added after the failed runs |

---

## 3. Read-only VPS diagnostic commands (no restarts, no writes, no secrets printed)

```bash
# ── Cause A: confirm container crash and reason ────────────────────────────
# 1. Is the API container running?
docker ps --filter name=esg-toolkit --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'

# 2. If stopped, show last exit reason
docker inspect esg-research-toolkit-api-1 --format '{{.State.ExitCode}} {{.State.Error}} {{json .State.StartedAt}} {{json .State.FinishedAt}}' 2>/dev/null || \
docker inspect $(docker ps -a --filter name=esg --format '{{.ID}}' | head -1) --format '{{.State.ExitCode}}: {{.State.Error}}'

# 3. Last 100 lines of container logs (look for the reproduced startup error)
docker logs --tail=100 esg-research-toolkit-api-1 2>&1 | grep -E 'RuntimeError|USE_ALEMBIC|ERROR|startup|alembic' || \
docker logs --tail=100 $(docker ps -a --filter name=esg --format '{{.ID}}' | head -1) 2>&1 | tail -50

# 4. Check what USE_ALEMBIC_INIT is set to in the running or last compose config
docker inspect esg-research-toolkit-api-1 --format '{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null | \
  grep -E '^(USE_ALEMBIC_INIT|ENFORCE_MIGRATION_GATE|APP_ENV)=' || echo 'container not found by that name'

# 5. Is there an alembic_version table in the production DB?
sqlite3 /opt/esg-data/esg_toolkit.db ".tables" 2>/dev/null | tr ' ' '\n' | grep alembic || echo 'no alembic_version table (migration gate will fail)'

# 6. If alembic_version exists, show the version row
sqlite3 /opt/esg-data/esg_toolkit.db "SELECT version_num FROM alembic_version;" 2>/dev/null || echo 'cannot query'

# ── B: repository state for fingerprint diagnosis ───────────────────────────────
# 7. Is the VPS repo a shallow clone?
git -C /opt/esg-research-toolkit rev-parse --is-shallow-repository

# 8. What SHA is HEAD?
git -C /opt/esg-research-toolkit log -1 --oneline

# ── Cause C: disk usage ────────────────────────────────────────────────────
# 9. How much disk is left?
df -h /var/lib/docker /opt

# 10. Docker image disk usage (dangling images = failed no-cache builds)
docker system df

# ── Cause D: nginx/sudo ────────────────────────────────────────────────────
# 11. Passwordless sudo grants for deploy user
sudo -l -U "$(cat /opt/esg-research-toolkit/.env.prod 2>/dev/null | grep -oP '(?<=VPS_DEPLOY_USER=)\S+' || echo $USER)" 2>/dev/null | grep -E 'nginx|systemctl|NOPASSWD' || echo 'check sudo config manually'

# 12. Nginx config test (read-only)
sudo nginx -t 2>&1
```

---

## 4. Startup fix and safe database cutover

### Startup fix: add `USE_ALEMBIC_INIT=true` to `docker-compose.prod.yml`

The safest single-file fix is injecting the required flag in the compose `environment:` block so **every** future `docker compose up` on the VPS enables Alembic init automatically, regardless of what is in `.env.prod`.

**File changed:** [`docker-compose.prod.yml`](../../docker-compose.prod.yml)

> [!IMPORTANT]
> Validate the migration on a database copy before deploying with this flag.
> `stamp` writes revision metadata only; it does not apply schema changes or data
> backfills. Never stamp `head` merely because tables already exist.

Operator procedure (not run by CI):

1. Inspect the database's actual schema and revision using `alembic current`,
   `alembic history`, SQLite `.schema`, and `PRAGMA table_info(company_reports)`.
   Compare all managed tables, columns, types, constraints and indexes against
   the migration files in `alembic/versions/`, including their data preconditions.
   An existing version row alone does not prove that the schema matches it.
2. Pause all writers during cutover and take a restorable SQLite backup using the
   SQLite backup API or `.backup` (rather than copying a live DB file that may
   have WAL changes). Retain the untouched backup and make a separate working
   copy for rehearsal. Point `DATABASE_URL` explicitly at that copy; do not use
   the production compose bind mount for rehearsal.
3. If the DB is unversioned, stamp only the revision whose schema **and data
   effects** have been verified as already present. For example, an inspected
   DB matching `0002_retire_runtime_helpers` should be stamped at that revision,
   leaving `0003_add_scope2_basis` to run. If no revision matches, stop and
   reconcile the schema rather than guessing. If already versioned and verified,
   skip stamping. An empty DB needs only `upgrade head`.
4. Run `alembic upgrade head` on the working copy. Check `alembic current` against
   `alembic heads`, run `PRAGMA integrity_check`, compare row counts and critical
   records with the backup, and verify that `scope2_basis` exists with the
   expected backfill. Review 0003's #61 precision-correction prerequisite and
   RWE 2023 exact-name guard before upgrading. Validate application startup and
   representative reads against the upgraded copy.
5. Only after rehearsal succeeds, repeat the verified procedure on the backed-up
   target DB while writers remain paused, run the same checks, then deploy.
   Preserve the backup for restoration if validation fails.

Example commands **for the rehearsal copy only**, after its schema and data have
been verified to match 0002 (use an absolute path to the working copy):

```bash
DATABASE_URL=sqlite:////path/to/rehearsal.db alembic current
# Skip this stamp if the copy already has the verified revision recorded.
DATABASE_URL=sqlite:////path/to/rehearsal.db alembic stamp 0002_retire_runtime_helpers
DATABASE_URL=sqlite:////path/to/rehearsal.db alembic upgrade head
DATABASE_URL=sqlite:////path/to/rehearsal.db alembic current
sqlite3 /path/to/rehearsal.db 'PRAGMA integrity_check; PRAGMA table_info(company_reports);'
```

### Fetch remains unchanged

[`.github/workflows/deploy.yml`](../../.github/workflows/deploy.yml) retains
`git fetch --depth=1 origin main "$GITHUB_SHA"`. #54 addressed the fingerprint
script; the reproduced startup defect does not require a different fetch.

---

_Analysis by Gemini (agy). Fixes applied in worktree `esg-deploy`._
