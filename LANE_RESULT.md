# LANE_RESULT — pydantic ~=2.13.5 contracts type drift

## Outcome

`frontend/src/lib/types.ts` was regenerated from a live OpenAPI schema produced by pydantic 2.13.5. That is the only product change. Frontend lint, unit tests, and build passed with no TypeScript edits. Backend pytest passed (411 passed, 4 skipped). No commit, no push, git config untouched. `.venv-lane` was deleted. `frontend/node_modules` was left in place.

## Files changed

- `frontend/src/lib/types.ts` — regenerated. `git diff --stat`: 105 insertions, 37 deletions.
  - 35 `dict[str, Any]` fields / dict response bodies changed from `Record<string, never>` to `{ [key: string]: unknown }`.
  - Two generated doc comments lost `@enum {string}` on const literals: `CompanyProfileV1Response.api_version: "v1"` and `DisclosureFetchResponse.status: "queued"`. Those comments come from the generator; restoring them by hand would fail the next `contracts` diff.
- `scripts/gen-types.sh` — `chmod +x` during the contracts steps flipped the mode `100644 → 100755`. Restored with `git checkout -- scripts/gen-types.sh`. Not part of the fix.
- `LANE_RESULT.md` — this report.

No other frontend or backend source files needed edits. The hand-written compatibility layer at the bottom of `types.ts` is unchanged (appended by `scripts/gen-types.sh`).

## Environment note

`python3` on this machine is 3.14.7. `numpy~=1.26` has no cp314 wheel, and CI uses Python 3.12, so the venv was created with `/Users/yumei/.local/bin/python3.12` (`3.12.14`) instead of `python3 -m venv`. Installed pydantic is `2.13.5` (`pydantic-core 2.46.5`). Local Node is `v24.14.1` (CI is Node 22); `npm ci`, `openapi-typescript` 7.13.0, lint, unit, and build all succeeded on that Node.

## Commands

| Command | Result |
| --- | --- |
| `python3.12 -m venv .venv-lane && .venv-lane/bin/pip install -r requirements.txt` | PASS |
| contracts-equivalent API boot + `npm run gen:types` | PASS |
| `frontend`: `npm ci` | PASS |
| `frontend`: `npx tsc -b --pretty false` | PASS (exit 0) |
| `frontend`: `npm run lint` | PASS |
| `frontend`: `npm run test:unit` | PASS — 7 files, 57 tests |
| `frontend`: `npm run build` (`tsc -b && vite build`) | PASS — built in 1.21s |
| `.venv-lane/bin/pip install -r requirements-ci.txt` then pytest | PASS — 411 passed, 4 skipped, 8 warnings in 20.31s |
| `scripts/check_version_consistency.py` | PASS — `version consistent: 0.3.1` |
| `python -c "from main import app"` | PASS — `App imports OK` |

### Type generation (same env as `.github/workflows/contracts.yml`)

```
OPENAI_API_KEY=test_key_placeholder
DATABASE_URL=sqlite:////tmp/esg-openapi-types.db
ESG_OPENAPI_SERVER_URL=http://127.0.0.1:8000
ADMIN_API_TOKEN=test_admin_token
.venv-lane/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Health check succeeded after 8s. Then, from `frontend/`:

```
OPENAPI_URL=http://127.0.0.1:8000/openapi.json npm run gen:types
```

Tail:

```
✨ openapi-typescript 7.13.0
Generated .../frontend/src/lib/types.ts from http://127.0.0.1:8000/openapi.json
```

The uvicorn process was stopped afterwards. Port 8000 was free before the write-up.

### Frontend tails

`npm ci`: `added 89 packages, and audited 91 packages in 10s` (exit 0). npm audit reports existing vulnerabilities; not addressed.

`npm run lint`: `eslint .` exit 0.

`npm run test:unit`:

```
Test Files  7 passed (7)
     Tests  57 passed (57)
  Duration  642ms
```

`npm run build`: `tsc -b` then vite, `✓ built in 1.21s` (exit 0).

### Pytest tail

Env matched `.github/workflows/test.yml`: `OPENAI_API_KEY=test_key_placeholder`, `DATABASE_URL=sqlite://`, `ADMIN_API_TOKEN=test_admin_token`.

```
================= 411 passed, 4 skipped, 8 warnings in 20.31s ==================
```

The 4 skips are pre-existing missing gitignored PDFs in `tests/test_table_extraction_regression.py` (`PDF not present (gitignored)`), not caused by the pydantic bump. Warnings are Starlette/reportlab/SWIG deprecations, not failures.

## Unresolved

- Schemathesis step in `contracts.yml` (`schemathesis run ... --max-examples 100` against port 8001) was not executed. The known CI failure was the `types.ts` git diff; pytest is the backend check that was requested.
- This worktree is not committed. `contracts` on a PR still runs `git diff --exit-code -- frontend/src/lib/types.ts` against the committed file, so the regenerated `types.ts` has to be committed before that gate can go green.
- `git status --short` after deleting `.venv-lane` and before this file: `M frontend/src/lib/types.ts`.
