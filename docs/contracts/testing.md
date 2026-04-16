# Contract testing

This repo now treats FastAPI OpenAPI output as the frontend type source of truth and runs schema-driven contract fuzzing on every PR.

## Local type generation

1. Start the backend:

```bash
OPENAI_API_KEY=dummy DATABASE_URL=sqlite:///./data/openapi-dev.db python -m uvicorn main:app --reload --port 8000
```

2. Regenerate frontend types:

```bash
cd frontend
npm run gen:types
```

`frontend/src/lib/types.ts` is generated from `http://127.0.0.1:8000/openapi.json` by default. Override with `OPENAPI_URL=...` if your backend runs elsewhere.

## CI contract gate

`.github/workflows/contracts.yml` does two things on every PR / `main` push:

1. Boots a normal backend instance and runs `npm run gen:types`.
   - CI fails if the regenerated `frontend/src/lib/types.ts` differs from the committed file.
2. Boots a contract-test backend instance and runs:

```bash
schemathesis run \
  --experimental openapi-3.1 \
  --checks all \
  --contrib-openapi-fill-missing-examples \
  --generation-codec ascii \
  --hypothesis-derandomize \
  --hypothesis-max-examples 100 \
  --base-url http://127.0.0.1:8001 \
  http://127.0.0.1:8001/openapi.json
```

## Contract-test mode

`ESG_CONTRACT_TEST_MODE=1` enables a deterministic OpenAPI/testing surface:

- seeds `Contract Demo AG` data for profile/history/framework/benchmark reads
- adds explicit OpenAPI examples for the seeded company and core POST payloads
- documents expected 4xx responses for resource lookups and guarded upload paths
- removes unstable binary / destructive operations from the Schemathesis-only schema subset

The production schema used for frontend type generation remains the full app schema.

## Drift validation workflow

To prove the gate works:

1. Break a live response shape without updating its schema, for example rename a field returned by `/techno/sensitivity`.
2. Push the branch and confirm the `API Contracts` workflow fails.
3. Revert the contract break and confirm CI is green again.

This is the expected release gate for future API edits.
