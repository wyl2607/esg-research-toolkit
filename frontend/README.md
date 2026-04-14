# React + TypeScript + Vite

This frontend wraps the FastAPI backend with a React 19 + Vite application and now includes a repeatable browser validation stack for smoke, accessibility, and health checks.

## Frontend Validation

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

Notes:

- Playwright defaults to the installed Google Chrome channel via `ESG_PW_CHANNEL=chrome`.
- If you want a different browser channel, set `ESG_PW_CHANNEL` before running the tests.
- If you already have backend and frontend servers running, set `ESG_PW_SKIP_WEBSERVER=1` for Playwright and `ESG_SKIP_SERVER_BOOT=1` for `npm run health:check`.
- A reusable Codex prompt is stored in `frontend/CODEX_FRONTEND_REVIEW_PROMPT.md`.

## Frontend Localization Policy (German-first)

- Default UI language: `de` (Deutsch)
- Translation priority for new UI text: `de` → `en` → `zh`
- Do not hardcode visible UI strings in components; always use `t('...')` keys from `src/i18n/locales/*.json`
- For dashboard/homepage and any new pages, add German keys first, then provide English and Chinese equivalents in the same change

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```
