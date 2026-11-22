# AGENTS.md

Single entry point for AI and human executors working in this repository.

## Directory map

- `main.py` — FastAPI application entrypoint.
- `core/` — shared backend modules.
- `report_parser/`, `taxonomy_scorer/`, `esg_frameworks/`, `techno_economics/` — domain packages.
- `frontend/` — React frontend; generated API types live in `frontend/src/lib/types.ts`.
- `tests/` — backend pytest suite; frontend unit tests live in `frontend/`.
- `scripts/` — local gates and automation.
- `docs/` — SOP, contracts, policies, and runbooks.
- `.guard/` — zone policy and public/local file lists.

## Gate commands

Run the smallest relevant gate before claiming completion.

| Gate | Command | Defined in |
| --- | --- | --- |
| Pre-commit security/zone | `bash scripts/security_check.sh` | `.guard/ZONE_POLICY.md`, `docs/parallel-dev-sop.md` |
| Pre-push review | `bash scripts/review_push_guard.sh origin/main` | `.github/workflows/repo-guard.yml`, `docs/parallel-dev-sop.md` |
| Backend tests | `pytest tests/ -v --tb=short` | `.github/workflows/test.yml` |
| Version consistency | `python scripts/check_version_consistency.py` | `.github/workflows/test.yml`, `.github/workflows/deploy.yml` |
| Backend lint | `ruff check core report_parser taxonomy_scorer esg_frameworks techno_economics benchmark tests main.py --ignore E501` | `.github/workflows/lint.yml` |
| Frontend checks (in `frontend/`) | `npm run lint`, `npm run test:unit`, `npm run build` | `.github/workflows/lint.yml` |
| API contract/types (in `frontend/`) | `npm run gen:types`, then `git diff --exit-code -- frontend/src/lib/types.ts` | `.github/workflows/contracts.yml` |

## Forbidden and generated paths

- `frontend/src/lib/types.ts` is generated from the backend OpenAPI schema; regenerate it, never hand-edit it.
- Do not edit `.guard/local-prefixes.txt` or `.guard/local-only-files.txt` outside an explicit policy change.
- Do not commit secrets, `.env` files, credentials, local absolute paths, usernames, or hostnames.
- Do not push directly to `main`; do not push, open PRs, merge, deploy, sync, or run remote/destructive Git operations without explicit approval.

## Zone rules (`.guard/ZONE_POLICY.md`)

- Every changed file must be classified `public` or `local`; `unclassified` blocks commit and push.
- Public prefixes: `.guard/public-prefixes.txt`; local prefixes: `.guard/local-prefixes.txt`; local-only files: `.guard/local-only-files.txt`.
- Classify a new path in the policy files before committing it.
- Local artifacts belong under local prefixes such as `dev-local/`, `logs/`, `data/`, `reports/`, `runtime/`, `.tmp/`.
