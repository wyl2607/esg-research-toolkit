# ESG Research Toolkit Frontend

React 19 + Vite application for the FastAPI ESG Research Toolkit backend. The frontend covers report upload, company history, framework comparison, taxonomy scoring, benchmarking, and techno-economic analysis workflows.

## Requirements

- Node.js 20+
- npm 10+
- Backend available at `http://127.0.0.1:8000` for live API calls and type generation

## Local Development

```bash
npm ci
npm run dev
```

The Vite dev server runs on `http://127.0.0.1:5173` by default.

## Validation

Run the core checks from `frontend/`:

```bash
npm run lint
npm run build
npm run test:smoke
npm run test:a11y
npm run health:check
```

Artifacts are written to:

```text
frontend/playwright-report/
frontend/test-results/
frontend/health-reports/latest/
```

## API Types

Generated API types live at `src/lib/types.ts` and are produced from the backend OpenAPI schema:

```bash
npm run gen:types
```

Start the backend first, or set `OPENAPI_URL` to a running schema endpoint. CI fails pull requests when generated types drift.

## Localization Policy

- Default UI language: `de` (Deutsch)
- Translation priority for new UI text: `de` -> `en` -> `zh`
- Do not hardcode visible UI strings in components; use `t('...')` keys from `src/i18n/locales/*.json`
- Add German keys first for new pages or dashboard copy, then provide English and Chinese equivalents in the same change

## Browser Tests

- Playwright defaults to the installed Google Chrome channel via `ESG_PW_CHANNEL=chrome`.
- Set `ESG_PW_CHANNEL` to use another browser channel.
- If backend and frontend servers are already running, set `ESG_PW_SKIP_WEBSERVER=1` for Playwright and `ESG_SKIP_SERVER_BOOT=1` for `npm run health:check`.
