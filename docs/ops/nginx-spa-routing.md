# Nginx SPA Routing Contract

The production Nginx server is the boundary for the built React application:

- `/index.html` is served with `charset=utf-8` and `Cache-Control: no-cache`.
- Hashed files under `/assets/` are served only when present and are immutable for one year.
- Known React Router prefixes fall back to `/index.html`.
- Unknown paths and missing asset-like paths return a real 404.

Run the live smoke check after installing/reloading Nginx:

```bash
ESG_FRONTEND_URL=https://esg.meichen.beauty   node scripts/qa/nginx-spa-smoke.mjs
```

The check verifies the root shell, `/companies`, a missing JavaScript asset, UTF-8 HTML, no-cache HTML, and immutable hashed assets. It requires a deployed build and does not replace a VPS-level DNS or TLS check.
