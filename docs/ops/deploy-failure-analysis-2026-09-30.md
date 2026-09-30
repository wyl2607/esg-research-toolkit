# Deploy Failure Analysis — "Deploy to USA VPS" step (2026-04-24 through 2026-06-11)

_Written: 2026-09-30. Covers three failed workflow_dispatch runs (2026-04-24, 06-10, 06-11 ×3, last at commit `3c1c6aa`)._

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

## 2. Ranked failure causes

### Cause A — Missing `USE_ALEMBIC_INIT=true` in `.env.prod` / compose env (CRITICAL — provable from code)

**Confidence: 95 %**

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

2. `docker-compose.prod.yml` passes `APP_ENV: production` ([line 11](../../docker-compose.prod.yml#L11)) but **never** sets `USE_ALEMBIC_INIT`.

3. `scripts/setup_vps.sh` generates the `.env.prod` template without `USE_ALEMBIC_INIT` ([setup_vps.sh:36–42](../../scripts/setup_vps.sh#L36-L42)).

4. `scripts/deploy.sh` does not inject `USE_ALEMBIC_INIT` at any point.

5. The default in `core/config.py` is `use_alembic_init: bool = False` ([config.py:21](../../core/config.py#L21)).

**Crash path:** container starts → uvicorn → `lifespan` → `init_db()` → `production=True`, `use_alembic_init=False` → `RuntimeError` → uvicorn exits → container stops immediately → smoke check at port 8001 returns `Connection refused` on every attempt → `exit 1`.

**Why 2m18s?** D1–D9 (npm build + docker build + `docker compose up`) take ~2 min. The container exits almost immediately after `up -d`. The workflow-level health loop (10 × 3 s = 30 s max) then fails.

**Sub-risk:** Even if `USE_ALEMBIC_INIT=true` is added to `.env.prod`, the existing production SQLite at `/opt/esg-data/esg_toolkit.db` may lack an `alembic_version` table (pre-Alembic schema). The app would then call `alembic upgrade head` and migration `0001_baseline` tries to create tables that already exist, causing an `OperationalError: table already exists`. The correct first-deploy remedy is `alembic stamp head` to baseline the live DB before enabling `USE_ALEMBIC_INIT=true`.

---

### Cause B — `git fetch --depth=1 origin main "$GITHUB_SHA"` fails for non-tip commits (provable from code)

**Confidence: 80 %**

`git fetch --depth=1 origin main "$GITHUB_SHA"` fetches only the tip of `main` **plus** the literal refspec `"$GITHUB_SHA"`. If the workflow is dispatched on a commit that is not the current `main` tip (e.g. the 2026-06-11 reruns at `3c1c6aa` while other commits may exist on main), and the VPS repo is a shallow clone without that SHA already present, the fetch may fail with `fatal: couldn't find remote ref <sha>` because `$GITHUB_SHA` is not a valid refspec — only a branch/tag/explicit fetchspec works with shallow fetches.

> **Note:** Commit `5d5872d` (#54, 2026-06-11) specifically documents this issue: _"origin/main is stale and `git branch -r --contains HEAD` prints nothing; grep then exits 1"_ — which is `write_deploy_fingerprint.sh`, not the fetch itself. But the same shallow-clone constraint applies to the fetch step.

The correct form is:
```bash
git fetch --depth=1 origin "$GITHUB_SHA"
```
Without the `main` refspec (which conflates branch update with SHA pinning).

---

### Cause C — `--no-cache` disk exhaustion (confirmed for 2026-06-11 by commit message, needs VPS for earlier runs)

**Confidence: 75 % for 2026-06-11, 40 % for April run**

Commit `fdd7f5d` (#56, 2026-06-11) documents explicitly: _"deploy.sh tore down the running container before building, the --no-cache build failed on a full disk (18G of containerd snapshots from repeated cacheless builds)"_. The April run used the same down-then-build-with-no-cache pattern (visible in `deploy.sh` at `3c1c6aa`, D6 was `down` then `build --no-cache`). If Cause A killed the April container on startup, repeated failed deploys would still accumulate dangling image layers, eventually filling disk on a subsequent run.

---

### Cause D — `nginx -t && systemctl reload nginx` requires root (needs server)

**Confidence: 40 %**

`deploy.sh` steps D10 calls `nginx -t && systemctl reload nginx` ([lines 88, 93](../../scripts/deploy.sh#L88-L93)) without `sudo`. If `VPS_DEPLOY_USER` is non-root without passwordless sudo for `nginx`/`systemctl`, this command fails under `set -euo pipefail`. The guardrails doc requires a non-root deploy user ([DEPLOY_GUARDRAILS.md §7](../DEPLOY_GUARDRAILS.md#7-github-actions-deploy-baseline)) but does not specify sudo grants. Cannot verify without server access.

---

### Cause E — `chown -R 10001:10001` on `/opt/esg-data` requires root (needs server)

**Confidence: 35 %**

Added in `d35c22a` (#64, 2026-06-12 — after the last failure). Relevant only if Cause A and others are resolved and a future deploy runs. `chown` on a bind-mount directory owned by root fails without sudo. Non-issue for the April/June failure dates since that line did not exist yet.

---

### Summary table

| # | Cause | Provable? | Confidence |
|---|---|---|---|
| A | `USE_ALEMBIC_INIT` missing → container crashes at startup | **Code** | **95 %** |
| B | `git fetch --depth=1 origin main <sha>` bad refspec | Code | 80 % |
| C | disk full from `--no-cache` + down-before-build | Code (Jun), needs server (Apr) | 75 % / 40 % |
| D | `nginx reload` without sudo | Needs server | 40 % |
| E | `chown` without sudo | Needs server (future) | 35 % |

---

## 3. Read-only VPS diagnostic commands (no restarts, no writes, no secrets printed)

```bash
# ── Cause A: confirm container crash and reason ────────────────────────────
# 1. Is the API container running?
docker ps --filter name=esg-toolkit --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'

# 2. If stopped, show last exit reason
docker inspect esg-research-toolkit-api-1 --format '{{.State.ExitCode}} {{.State.Error}} {{json .State.StartedAt}} {{json .State.FinishedAt}}' 2>/dev/null || \
docker inspect $(docker ps -a --filter name=esg --format '{{.ID}}' | head -1) --format '{{.State.ExitCode}}: {{.State.Error}}'

# 3. Last 100 lines of container logs (proves USE_ALEMBIC_INIT crash)
docker logs --tail=100 esg-research-toolkit-api-1 2>&1 | grep -E 'RuntimeError|USE_ALEMBIC|ERROR|startup|alembic' || \
docker logs --tail=100 $(docker ps -a --filter name=esg --format '{{.ID}}' | head -1) 2>&1 | tail -50

# 4. Check what USE_ALEMBIC_INIT is set to in the running or last compose config
docker inspect esg-research-toolkit-api-1 --format '{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null | \
  grep -E 'USE_ALEMBIC|ENFORCE_MIGRATION|APP_ENV|DATABASE_URL' || echo 'container not found by that name'

# 5. Is there an alembic_version table in the production DB?
sqlite3 /opt/esg-data/esg_toolkit.db ".tables" 2>/dev/null | tr ' ' '\n' | grep alembic || echo 'no alembic_version table (migration gate will fail)'

# 6. If alembic_version exists, show the version row
sqlite3 /opt/esg-data/esg_toolkit.db "SELECT version_num FROM alembic_version;" 2>/dev/null || echo 'cannot query'

# ── Cause B: shallow clone / fetch integrity ───────────────────────────────
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

## 4. Code fix (Cause A — provable from code alone)

### Root fix: add `USE_ALEMBIC_INIT=true` to `docker-compose.prod.yml`

The safest single-file fix is injecting the required flag in the compose `environment:` block so **every** future `docker compose up` on the VPS enables Alembic init automatically, regardless of what is in `.env.prod`.

**File changed:** [`docker-compose.prod.yml`](../../docker-compose.prod.yml)

> [!IMPORTANT]
> Before running the next deploy, the owner must also **stamp the existing production DB** so Alembic does not try to re-create already-existing tables:
> ```bash
> # Run once on the VPS — no writes to app data:
> cd /opt/esg-research-toolkit
> docker compose -f docker-compose.prod.yml run --rm api \
>   alembic -c alembic.ini stamp head
> ```
> This is a prerequisite for the fix; it is a one-time operator action, not automatable from CI.

### Partial fix: also correct the `git fetch` refspec (Cause B)

**File changed:** [`.github/workflows/deploy.yml`](../../.github/workflows/deploy.yml)

Change `git fetch --depth=1 origin main "$GITHUB_SHA"` → `git fetch --depth=1 origin "$GITHUB_SHA"` to avoid conflating the branch tip update with the SHA fetch. The fingerprint script already resolves the branch correctly via `merge-base` after `#54`.

---

_Analysis by Gemini (agy). Fixes applied in worktree `esg-deploy`._
