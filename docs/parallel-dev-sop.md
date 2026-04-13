# Parallel Development SOP (Sanitized)

This SOP defines a safe workflow for parallel development with local Codex, GitHub Copilot (web), coco build host, and VPS deployment.

## 1. Scope and Principles

- `GitHub` is the single source of truth for code.
- `coco` is for build/test verification, not long-term source of truth.
- `VPS` is deploy-only (no feature development on server).
- All examples below are sanitized and use placeholders only.

## 2. Sensitive Data Policy

- Never commit real hosts, usernames, API keys, tokens, or private paths.
- Use placeholders:
  - `<COCO_USER>@<COCO_HOST>`
  - `<VPS_USER>@<VPS_HOST>`
  - `<COCO_BUILD_DIR>`
  - `<VPS_DEPLOY_DIR>`
  - `<DEPLOY_DOMAIN>`
- Keep real values in local config only (for example `~/.esg-deploy-config`).
- Team template file: `.esg-deploy-config.example` (sanitized placeholders only).

## 3. Branching Strategy

- Protected branch: `main`
- Feature branch: `feat/<owner>-<topic>`
- Fix branch: `fix/<owner>-<topic>`
- Hotfix branch: `hotfix/<topic>`

Rules:

- Do not push directly to `main`.
- Prefer one task per branch.
- Avoid two developers changing the same file block at the same time.

## 4. Parallel Work Model (Codex + Copilot + Local)

For each developer/agent:

1. Sync from main:
   - `git checkout main`
   - `git pull origin main`
2. Create branch:
   - `git checkout -b feat/<owner>-<topic>`
3. Commit in small units:
   - `git add ...`
   - `git commit -m "feat: ..."`
4. Rebase before pushing:
   - `git pull --rebase origin feat/<owner>-<topic>`
5. Push branch:
   - `git push -u origin feat/<owner>-<topic>`

Conflict handling:

- Resolve conflicts branch-side, then re-run tests/build.
- Do not force-push over teammate work unless explicitly coordinated.

## 5. Merge Gate

Before merge to `main`, all of the following must pass:

1. Local checks:
   - `bash scripts/security_check.sh`
   - `bash scripts/review_push_guard.sh origin/main`
2. Branch pushed to GitHub.
3. coco verification passes (`release_pipeline.sh` coco stage).
4. Reviewer confirms no sensitive data introduced.

## 6. Deployment Gate (coco -> VPS)

Always run preflight before remote execution:

- `bash scripts/preflight_safe_exec.sh --target <user@host> --remote-dir <path> --preflight-only`

Recommended deploy flow:

1. Verify + push + coco build:
   - `bash scripts/release_pipeline.sh --branch <branch>`
2. Deploy VPS after verification:
   - `bash scripts/release_pipeline.sh --branch <branch> --skip-coco --no-push --deploy-vps`

Guardrails:

- VPS deploy must pass git SHA alignment gate (remote `HEAD` equals local `HEAD`).
- Use `{{COMPOSE}}` via preflight scripts (do not hardcode compose command).
- Use explicit `user@ip` or `user@fqdn`, not local SSH aliases.

## 7. Emergency Hotfix Flow

1. Branch from `main`: `hotfix/<topic>`
2. Minimal fix + tests
3. Open PR and fast review
4. Deploy using the same gated pipeline
5. Back-merge hotfix into ongoing feature branches if needed

## 8. Operational Checklist

Daily:

- Rebase active branches from `main`
- Keep commits small and descriptive

Per deployment:

- Preflight passed
- coco stage passed
- SHA aligned on VPS
- Health check passed
- Deployment fingerprint written
