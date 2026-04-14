# Stage 7 Frontend Design — ESG Research Toolkit

**Date**: 2026-04-12  
**Status**: Approved  
**Author**: Claude + yumei

---

## Goal

Build a React-based web dashboard that wraps the existing FastAPI backend, making ESG analysis accessible without curl commands. Reusable across future report analysis projects.

## Architecture

```
esg-research-toolkit/
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── UploadPage.tsx
│   │   │   ├── TaxonomyPage.tsx
│   │   │   ├── LcoePage.tsx
│   │   │   ├── CompaniesPage.tsx
│   │   │   └── ComparePage.tsx
│   │   ├── components/
│   │   │   ├── Layout.tsx          # Sidebar + header shell
│   │   │   ├── Sidebar.tsx         # Nav links
│   │   │   ├── RadarChart.tsx      # Taxonomy 6-objective radar
│   │   │   ├── MetricCard.tsx      # Reusable stat card
│   │   │   └── CompanyTable.tsx    # Sortable company list
│   │   ├── lib/
│   │   │   ├── api.ts              # Typed fetch wrappers for all 15 endpoints
│   │   │   └── types.ts            # TypeScript mirrors of backend schemas
│   │   ├── App.tsx                 # Router setup
│   │   └── main.tsx
│   ├── .env.local                  # VITE_API_URL=http://localhost:8000
│   ├── vite.config.ts              # proxy /api → backend
│   ├── tailwind.config.ts
│   ├── components.json             # shadcn/ui config
│   └── package.json
└── ... (backend unchanged)
```

## Tech Stack

| Layer | Choice | Reason |
|-------|--------|--------|
| Framework | React 18 + Vite 5 + TypeScript | Industry standard, portfolio-ready |
| Components | shadcn/ui | Light, composable, Tailwind-native |
| Styling | Tailwind CSS v3 | shadcn dependency, utility-first |
| Charts | Recharts | Radar + line charts, React-native |
| Routing | React Router v6 | Standard SPA routing |
| Data fetching | TanStack Query v5 | Caching, loading states, refetch |
| Icons | lucide-react | Ships with shadcn |

## Pages

### 1. Dashboard (`/`)
- Summary cards: total companies analyzed, avg taxonomy alignment %, DNSH pass rate
- Recent analyses table (last 5, with company name, year, score, DNSH status)
- Quick-upload CTA button

### 2. Upload (`/upload`)
- Drag-and-drop PDF zone (react-dropzone)
- Upload progress bar → auto-calls `POST /report/upload`
- Result preview: extracted ESG fields with confidence indicators
- "Run Taxonomy Score" button → navigates to Taxonomy page with data pre-filled

### 3. Taxonomy (`/taxonomy`)
- Company + year selector (loads from `GET /report/companies`)
- Radar chart: 6 EU Taxonomy objectives (Recharts RadarChart)
- DNSH status badge (green ✓ / red ✗)
- Gaps list with severity badges (critical / high / medium)
- Recommendations list
- Export as PDF button (window.print CSS)

### 4. LCOE (`/lcoe`)
- Technology selector (solar_pv, wind_onshore, wind_offshore, battery_storage…)
- Parameter form: capacity_mw, capacity_factor, capex_eur_per_kw, opex, lifetime, discount_rate
- Result cards: LCOE (€/MWh), NPV (€), IRR (%), Payback (years)
- Sensitivity analysis line chart (±20% CAPEX/OPEX)
- "Add benchmark" to compare multiple scenarios

### 5. Companies (`/companies`)
- Searchable, sortable table of all stored reports
- Columns: Company, Year, Scope1, Revenue, Taxonomy %, DNSH, Actions
- Row click → detail drawer (full ESG data)
- Delete button with confirmation

### 6. Compare (`/compare`)
- Multi-select dropdown (max 4 companies)
- Side-by-side radar charts
- Metric comparison table (emissions, renewable %, employees, alignment %)

## API Integration

All 15 existing endpoints are used. `src/lib/api.ts` wraps each with typed request/response:

```ts
// Example
export const uploadReport = (file: File) => ...  // POST /report/upload
export const scoreCompany = (data: CompanyESGData) => ... // POST /taxonomy/score
export const calcLcoe = (input: LCOEInput) => ... // POST /techno/lcoe
```

Vite proxy: all `/api/*` requests forwarded to `VITE_API_URL` in dev.

## CORS

Add `fastapi.middleware.cors` to `main.py` allowing `http://localhost:5173` in dev.

## Error Handling

- API errors: TanStack Query `onError` → toast notification (shadcn/ui Toaster)
- Upload failures: inline error message below drop zone
- Empty states: illustrated placeholder on all list pages

## Testing

- Component tests: Vitest + React Testing Library (Upload, MetricCard)
- API mock: MSW (Mock Service Worker) for offline dev
- No E2E tests in Stage 7 (deferred to Stage 8)

## Done Criteria

- [ ] All 6 pages render without errors
- [ ] Upload PDF → see extracted data flow works end-to-end
- [ ] Taxonomy radar chart renders with real CATL data
- [ ] LCOE form → results display
- [ ] Companies table lists stored reports
- [ ] `npm run build` succeeds with no type errors
- [ ] CORS configured, frontend talks to backend on different ports


## 相关文件

[[2026-03-30]]
[[2026-04-06-control-plane-closure-wave]]
[[2026-04-07_A组_金融一体化定义与衡量指标_文献综述报告]]
[[2026-04-07_亚洲金融一体化_中文快速核验报告]]
[[2026-04-07_亚洲金融一体化_中文快速核验报告__dup2]]
[[2026-04-13]]
[[2026-04-13_copilot-peer-review-bootstrap]]
[[2026-04-14]]
[[2026-04-14_copilot-quota-timeline-setup]]
[[DIGHUM (Digital Humanities) 150A_ Digital Humanities And Archival Design]]