# Stage 7 Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a React + Vite dashboard with 6 pages that wraps all 15 existing FastAPI endpoints, using shadcn/ui + Tailwind + Recharts.

**Architecture:** Independent `frontend/` directory inside the repo; Vite dev proxy forwards `/api/*` to FastAPI on port 8000; TanStack Query manages all server state; React Router v6 handles navigation.

**Tech Stack:** React 18, Vite 5, TypeScript, shadcn/ui, Tailwind CSS v3, Recharts, React Router v6, TanStack Query v5, react-dropzone, lucide-react

---

## File Map

```
frontend/
├── src/
│   ├── lib/
│   │   ├── api.ts            # typed fetch wrappers for all 15 endpoints
│   │   └── types.ts          # TypeScript mirrors of backend Pydantic schemas
│   ├── components/
│   │   ├── Layout.tsx        # sidebar shell, header, outlet
│   │   ├── Sidebar.tsx       # nav links with active state
│   │   ├── MetricCard.tsx    # reusable stat card (label + value + optional trend)
│   │   ├── RadarChart.tsx    # Recharts radar for 6 Taxonomy objectives
│   │   └── CompanyTable.tsx  # sortable/searchable company list
│   ├── pages/
│   │   ├── DashboardPage.tsx
│   │   ├── UploadPage.tsx
│   │   ├── TaxonomyPage.tsx
│   │   ├── LcoePage.tsx
│   │   ├── CompaniesPage.tsx
│   │   └── ComparePage.tsx
│   ├── App.tsx               # BrowserRouter + routes
│   └── main.tsx              # ReactDOM.createRoot
├── .env.local                # VITE_API_URL=http://localhost:8000
├── vite.config.ts            # proxy config
├── tailwind.config.ts
├── components.json           # shadcn config
├── tsconfig.json
└── package.json
```

**Backend change (1 file):**
- Modify: `main.py` — add CORSMiddleware

---

## Task 1: Scaffold + CORS

**Files:**
- Create: `frontend/` (entire directory via npm/vite)
- Modify: `main.py`

- [ ] **Step 1: Add CORS to FastAPI**

  Edit `main.py`, add after `app = FastAPI(...)`:

  ```python
  from fastapi.middleware.cors import CORSMiddleware

  app.add_middleware(
      CORSMiddleware,
      allow_origins=["http://localhost:5173", "http://localhost:4173"],
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```

- [ ] **Step 2: Scaffold Vite project**

  ```bash
  cd /Users/yumei/projects/esg-research-toolkit
  npm create vite@latest frontend -- --template react-ts
  cd frontend
  npm install
  ```

- [ ] **Step 3: Install all dependencies**

  ```bash
  npm install react-router-dom @tanstack/react-query recharts react-dropzone lucide-react
  npm install -D tailwindcss postcss autoprefixer
  npx tailwindcss init -p
  ```

- [ ] **Step 4: Install shadcn/ui**

  ```bash
  npx shadcn@latest init -d
  npx shadcn@latest add button card badge table input label select toast progress separator
  ```

- [ ] **Step 5: Write `vite.config.ts`**

  ```ts
  import { defineConfig } from 'vite'
  import react from '@vitejs/plugin-react'
  import path from 'path'

  export default defineConfig({
    plugins: [react()],
    resolve: { alias: { '@': path.resolve(__dirname, './src') } },
    server: {
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          rewrite: (p) => p.replace(/^\/api/, ''),
        },
      },
    },
  })
  ```

- [ ] **Step 6: Write `tailwind.config.ts`**

  ```ts
  export default {
    darkMode: ['class'],
    content: ['./index.html', './src/**/*.{ts,tsx}'],
    theme: { extend: {} },
    plugins: [],
  }
  ```

- [ ] **Step 7: Update `src/index.css`**

  Replace entire file with:
  ```css
  @tailwind base;
  @tailwind components;
  @tailwind utilities;
  ```

- [ ] **Step 8: Write `.env.local`**

  ```
  VITE_API_URL=http://localhost:8000
  ```

- [ ] **Step 9: Verify build succeeds**

  ```bash
  npm run build
  ```
  Expected: `dist/` created, no TypeScript errors.

- [ ] **Step 10: Commit**

  ```bash
  cd ..
  git add frontend/ main.py
  git commit -m "feat: scaffold React+Vite frontend, add CORS to FastAPI"
  ```

---

## Task 2: Types + API Client

**Files:**
- Create: `frontend/src/lib/types.ts`
- Create: `frontend/src/lib/api.ts`

- [ ] **Step 1: Write `types.ts`**

  ```ts
  // frontend/src/lib/types.ts
  export interface CompanyESGData {
    company_name: string
    report_year: number
    scope1_co2e_tonnes: number | null
    scope2_co2e_tonnes: number | null
    scope3_co2e_tonnes: number | null
    energy_consumption_mwh: number | null
    renewable_energy_pct: number | null
    water_usage_m3: number | null
    waste_recycled_pct: number | null
    total_revenue_eur: number | null
    taxonomy_aligned_revenue_pct: number | null
    total_capex_eur: number | null
    taxonomy_aligned_capex_pct: number | null
    total_employees: number | null
    female_pct: number | null
    primary_activities: string[]
  }

  export interface TaxonomyScoreResult {
    company_name: string
    report_year: number
    revenue_aligned_pct: number
    capex_aligned_pct: number
    opex_aligned_pct: number
    objective_scores: Record<string, number>
    dnsh_pass: boolean
    gaps: string[]
    recommendations: string[]
  }

  export interface LCOEInput {
    technology: string
    capacity_mw: number
    capacity_factor: number
    capex_eur_per_kw: number
    opex_eur_per_kw_year: number
    lifetime_years: number
    discount_rate: number
  }

  export interface LCOEResult {
    technology: string
    lcoe_eur_per_mwh: number
    npv_eur: number
    irr: number
    payback_years: number
    lifetime_years: number
  }

  export interface SensitivityResult {
    parameter: string
    values: number[]
    lcoe_results: number[]
  }

  export interface TaxonomyActivity {
    activity_id: string
    name: string
    sector: string
    ghg_threshold_gco2e_per_kwh: number | null
  }
  ```

- [ ] **Step 2: Write `api.ts`**

  ```ts
  // frontend/src/lib/api.ts
  import type {
    CompanyESGData, TaxonomyScoreResult,
    LCOEInput, LCOEResult, SensitivityResult, TaxonomyActivity
  } from './types'

  const BASE = '/api'

  async function req<T>(path: string, init?: RequestInit): Promise<T> {
    const res = await fetch(BASE + path, {
      headers: { 'Content-Type': 'application/json' },
      ...init,
    })
    if (!res.ok) throw new Error(`${res.status} ${await res.text()}`)
    return res.json()
  }

  // Report Parser
  export const uploadReport = (file: File): Promise<CompanyESGData> => {
    const form = new FormData()
    form.append('file', file)
    return fetch(BASE + '/report/upload', { method: 'POST', body: form })
      .then(r => { if (!r.ok) throw new Error(r.statusText); return r.json() })
  }

  export const listCompanies = (): Promise<CompanyESGData[]> =>
    req('/report/companies')

  export const getCompany = (name: string, year: number): Promise<CompanyESGData> =>
    req(`/report/companies/${encodeURIComponent(name)}/${year}`)

  // Taxonomy
  export const scoreCompany = (data: CompanyESGData): Promise<TaxonomyScoreResult> =>
    req('/taxonomy/score', { method: 'POST', body: JSON.stringify(data) })

  export const getTaxonomyReport = (name: string, year: number): Promise<TaxonomyScoreResult> =>
    req(`/taxonomy/report?company_name=${encodeURIComponent(name)}&report_year=${year}`)

  export const listActivities = (): Promise<TaxonomyActivity[]> =>
    req('/taxonomy/activities')

  // Techno-Economics
  export const calcLcoe = (input: LCOEInput): Promise<LCOEResult> =>
    req('/techno/lcoe', { method: 'POST', body: JSON.stringify(input) })

  export const calcSensitivity = (input: LCOEInput): Promise<SensitivityResult[]> =>
    req('/techno/sensitivity', { method: 'POST', body: JSON.stringify(input) })

  export const getBenchmarks = (): Promise<Record<string, LCOEInput>> =>
    req('/techno/benchmarks')
  ```

- [ ] **Step 3: Verify TypeScript compiles**

  ```bash
  npx tsc --noEmit
  ```
  Expected: no errors.

- [ ] **Step 4: Commit**

  ```bash
  git add frontend/src/lib/
  git commit -m "feat: typed API client and TypeScript schema mirrors"
  ```

---

## Task 3: Layout + Routing Shell

**Files:**
- Create: `frontend/src/components/Layout.tsx`
- Create: `frontend/src/components/Sidebar.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/main.tsx`

- [ ] **Step 1: Write `Sidebar.tsx`**

  ```tsx
  // frontend/src/components/Sidebar.tsx
  import { NavLink } from 'react-router-dom'
  import { LayoutDashboard, Upload, Tag, Zap, Building2, GitCompare } from 'lucide-react'
  import { cn } from '@/lib/utils'

  const links = [
    { to: '/',          label: 'Dashboard',  icon: LayoutDashboard },
    { to: '/upload',    label: 'Upload',     icon: Upload },
    { to: '/taxonomy',  label: 'Taxonomy',   icon: Tag },
    { to: '/lcoe',      label: 'LCOE',       icon: Zap },
    { to: '/companies', label: 'Companies',  icon: Building2 },
    { to: '/compare',   label: 'Compare',    icon: GitCompare },
  ]

  export function Sidebar() {
    return (
      <aside className="w-56 shrink-0 border-r bg-white flex flex-col">
        <div className="px-6 py-5 border-b">
          <span className="font-bold text-indigo-600 text-lg">ESG Toolkit</span>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                cn('flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-indigo-50 text-indigo-700'
                    : 'text-slate-600 hover:bg-slate-100'
                )
              }
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>
    )
  }
  ```

- [ ] **Step 2: Write `Layout.tsx`**

  ```tsx
  // frontend/src/components/Layout.tsx
  import { Outlet } from 'react-router-dom'
  import { Sidebar } from './Sidebar'

  export function Layout() {
    return (
      <div className="flex h-screen bg-slate-50 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-6xl mx-auto p-8">
            <Outlet />
          </div>
        </main>
      </div>
    )
  }
  ```

- [ ] **Step 3: Write `App.tsx`**

  ```tsx
  // frontend/src/App.tsx
  import { BrowserRouter, Routes, Route } from 'react-router-dom'
  import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
  import { Layout } from '@/components/Layout'
  import { DashboardPage } from '@/pages/DashboardPage'
  import { UploadPage } from '@/pages/UploadPage'
  import { TaxonomyPage } from '@/pages/TaxonomyPage'
  import { LcoePage } from '@/pages/LcoePage'
  import { CompaniesPage } from '@/pages/CompaniesPage'
  import { ComparePage } from '@/pages/ComparePage'

  const queryClient = new QueryClient()

  export default function App() {
    return (
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route index element={<DashboardPage />} />
              <Route path="upload" element={<UploadPage />} />
              <Route path="taxonomy" element={<TaxonomyPage />} />
              <Route path="lcoe" element={<LcoePage />} />
              <Route path="companies" element={<CompaniesPage />} />
              <Route path="compare" element={<ComparePage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </QueryClientProvider>
    )
  }
  ```

- [ ] **Step 4: Write stub page files** (all 6, each identical structure):

  For each of `DashboardPage`, `UploadPage`, `TaxonomyPage`, `LcoePage`, `CompaniesPage`, `ComparePage`, create `frontend/src/pages/<Name>Page.tsx`:

  ```tsx
  // Example: frontend/src/pages/DashboardPage.tsx
  export function DashboardPage() {
    return <div><h1 className="text-2xl font-bold">Dashboard</h1></div>
  }
  ```
  (Repeat for all 6, changing the name.)

- [ ] **Step 5: Update `main.tsx`**

  ```tsx
  import React from 'react'
  import ReactDOM from 'react-dom/client'
  import App from './App.tsx'
  import './index.css'

  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode><App /></React.StrictMode>
  )
  ```

- [ ] **Step 6: Run dev server and verify routing works**

  ```bash
  npm run dev
  ```
  Open http://localhost:5173 — sidebar should show, all 6 nav links should navigate.

- [ ] **Step 7: Commit**

  ```bash
  git add frontend/src/
  git commit -m "feat: layout shell, sidebar nav, React Router routing"
  ```

---

## Task 4: Dashboard Page

**Files:**
- Create: `frontend/src/components/MetricCard.tsx`
- Modify: `frontend/src/pages/DashboardPage.tsx`

- [ ] **Step 1: Write `MetricCard.tsx`**

  ```tsx
  // frontend/src/components/MetricCard.tsx
  import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

  interface Props {
    title: string
    value: string | number
    subtitle?: string
    accent?: 'default' | 'green' | 'red'
  }

  export function MetricCard({ title, value, subtitle, accent = 'default' }: Props) {
    const color = accent === 'green' ? 'text-green-600' : accent === 'red' ? 'text-red-500' : 'text-indigo-600'
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-slate-500">{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className={`text-3xl font-bold ${color}`}>{value}</p>
          {subtitle && <p className="text-xs text-slate-400 mt-1">{subtitle}</p>}
        </CardContent>
      </Card>
    )
  }
  ```

- [ ] **Step 2: Write `DashboardPage.tsx`**

  ```tsx
  // frontend/src/pages/DashboardPage.tsx
  import { useQuery } from '@tanstack/react-query'
  import { listCompanies } from '@/lib/api'
  import { MetricCard } from '@/components/MetricCard'
  import { Badge } from '@/components/ui/badge'
  import { useNavigate } from 'react-router-dom'
  import { Button } from '@/components/ui/button'

  export function DashboardPage() {
    const navigate = useNavigate()
    const { data: companies = [], isLoading } = useQuery({
      queryKey: ['companies'],
      queryFn: listCompanies,
    })

    const recent = companies.slice(-5).reverse()

    return (
      <div className="space-y-8">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold text-slate-800">Dashboard</h1>
          <Button onClick={() => navigate('/upload')}>+ Upload PDF</Button>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <MetricCard title="Companies Analyzed" value={companies.length} />
          <MetricCard
            title="Reports Total"
            value={companies.length}
            subtitle="across all years"
          />
          <MetricCard
            title="Data Status"
            value={isLoading ? '...' : 'Live'}
            accent="green"
          />
        </div>

        <div>
          <h2 className="text-lg font-semibold text-slate-700 mb-3">Recent Analyses</h2>
          {isLoading ? (
            <p className="text-slate-400 text-sm">Loading...</p>
          ) : recent.length === 0 ? (
            <p className="text-slate-400 text-sm">No reports yet. <button className="text-indigo-600 underline" onClick={() => navigate('/upload')}>Upload one</button></p>
          ) : (
            <div className="space-y-2">
              {recent.map(c => (
                <div key={`${c.company_name}-${c.report_year}`}
                  className="flex items-center justify-between bg-white border rounded-lg px-4 py-3 cursor-pointer hover:border-indigo-300 transition"
                  onClick={() => navigate('/taxonomy')}
                >
                  <div>
                    <p className="font-medium text-slate-800">{c.company_name}</p>
                    <p className="text-xs text-slate-400">{c.report_year}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    {c.renewable_energy_pct != null && (
                      <span className="text-sm text-slate-500">{c.renewable_energy_pct}% renewable</span>
                    )}
                    <Badge variant="outline">{c.primary_activities[0] ?? 'n/a'}</Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    )
  }
  ```

- [ ] **Step 3: Verify no TypeScript errors**

  ```bash
  npx tsc --noEmit
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add frontend/src/
  git commit -m "feat: Dashboard page with company summary cards"
  ```

---

## Task 5: Upload Page

**Files:**
- Modify: `frontend/src/pages/UploadPage.tsx`

- [ ] **Step 1: Write `UploadPage.tsx`**

  ```tsx
  // frontend/src/pages/UploadPage.tsx
  import { useState, useCallback } from 'react'
  import { useDropzone } from 'react-dropzone'
  import { uploadReport } from '@/lib/api'
  import type { CompanyESGData } from '@/lib/types'
  import { Button } from '@/components/ui/button'
  import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
  import { Badge } from '@/components/ui/badge'
  import { useQueryClient } from '@tanstack/react-query'
  import { useNavigate } from 'react-router-dom'

  function Field({ label, value }: { label: string; value: unknown }) {
    return (
      <div className="flex justify-between py-1 border-b last:border-0">
        <span className="text-sm text-slate-500">{label}</span>
        <span className="text-sm font-medium text-slate-800">
          {value == null ? <span className="text-slate-300">—</span> : String(value)}
        </span>
      </div>
    )
  }

  export function UploadPage() {
    const [status, setStatus] = useState<'idle' | 'uploading' | 'done' | 'error'>('idle')
    const [result, setResult] = useState<CompanyESGData | null>(null)
    const [error, setError] = useState('')
    const qc = useQueryClient()
    const navigate = useNavigate()

    const onDrop = useCallback(async (files: File[]) => {
      const file = files[0]
      if (!file) return
      setStatus('uploading')
      setError('')
      try {
        const data = await uploadReport(file)
        setResult(data)
        setStatus('done')
        qc.invalidateQueries({ queryKey: ['companies'] })
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Upload failed')
        setStatus('error')
      }
    }, [qc])

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
      onDrop, accept: { 'application/pdf': ['.pdf'] }, maxFiles: 1,
    })

    return (
      <div className="space-y-6 max-w-2xl">
        <h1 className="text-2xl font-bold text-slate-800">Upload ESG Report</h1>

        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition ${
            isDragActive ? 'border-indigo-500 bg-indigo-50' : 'border-slate-300 hover:border-indigo-400'
          }`}
        >
          <input {...getInputProps()} />
          <p className="text-4xl mb-3">📄</p>
          {status === 'uploading' ? (
            <p className="text-indigo-600 font-medium">Extracting ESG data…</p>
          ) : (
            <>
              <p className="text-slate-600 font-medium">Drop a PDF here, or click to browse</p>
              <p className="text-slate-400 text-sm mt-1">Supports annual ESG / sustainability reports</p>
            </>
          )}
        </div>

        {error && <p className="text-red-500 text-sm">{error}</p>}

        {result && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                {result.company_name}
                <Badge variant="secondary">{result.report_year}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-1">
              <Field label="Scope 1 (tCO₂e)" value={result.scope1_co2e_tonnes?.toLocaleString()} />
              <Field label="Scope 2 (tCO₂e)" value={result.scope2_co2e_tonnes?.toLocaleString()} />
              <Field label="Scope 3 (tCO₂e)" value={result.scope3_co2e_tonnes?.toLocaleString()} />
              <Field label="Energy (MWh)" value={result.energy_consumption_mwh?.toLocaleString()} />
              <Field label="Renewable Energy" value={result.renewable_energy_pct != null ? `${result.renewable_energy_pct}%` : null} />
              <Field label="Employees" value={result.total_employees?.toLocaleString()} />
              <Field label="Female %" value={result.female_pct != null ? `${result.female_pct}%` : null} />
              <Field label="Revenue (EUR)" value={result.total_revenue_eur != null ? `€${(result.total_revenue_eur / 1e9).toFixed(1)}B` : null} />
              <Field label="Activities" value={result.primary_activities.join(', ')} />
            </CardContent>
          </Card>
        )}

        {result && (
          <Button className="w-full" onClick={() => navigate('/taxonomy')}>
            Run Taxonomy Score →
          </Button>
        )}
      </div>
    )
  }
  ```

- [ ] **Step 2: Verify**

  ```bash
  npx tsc --noEmit
  ```

- [ ] **Step 3: Commit**

  ```bash
  git add frontend/src/pages/UploadPage.tsx
  git commit -m "feat: Upload page with drag-and-drop PDF and result preview"
  ```

---

## Task 6: Taxonomy Page + Radar Chart

**Files:**
- Create: `frontend/src/components/RadarChart.tsx`
- Modify: `frontend/src/pages/TaxonomyPage.tsx`

- [ ] **Step 1: Write `RadarChart.tsx`**

  ```tsx
  // frontend/src/components/RadarChart.tsx
  import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer, Tooltip } from 'recharts'

  interface Props {
    scores: Record<string, number>
  }

  const LABELS: Record<string, string> = {
    climate_mitigation: 'Climate\nMitigation',
    climate_adaptation: 'Climate\nAdaptation',
    water: 'Water',
    circular_economy: 'Circular\nEconomy',
    pollution: 'Pollution',
    biodiversity: 'Biodiversity',
  }

  export function TaxonomyRadar({ scores }: Props) {
    const data = Object.entries(scores).map(([key, value]) => ({
      subject: LABELS[key] ?? key,
      score: Math.round(value * 100),
      fullMark: 100,
    }))

    return (
      <ResponsiveContainer width="100%" height={300}>
        <RadarChart data={data}>
          <PolarGrid />
          <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11 }} />
          <Tooltip formatter={(v: number) => `${v}%`} />
          <Radar dataKey="score" stroke="#6366f1" fill="#6366f1" fillOpacity={0.3} />
        </RadarChart>
      </ResponsiveContainer>
    )
  }
  ```

- [ ] **Step 2: Write `TaxonomyPage.tsx`**

  ```tsx
  // frontend/src/pages/TaxonomyPage.tsx
  import { useState } from 'react'
  import { useQuery, useMutation } from '@tanstack/react-query'
  import { listCompanies, scoreCompany } from '@/lib/api'
  import { TaxonomyRadar } from '@/components/RadarChart'
  import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
  import { Badge } from '@/components/ui/badge'
  import { Button } from '@/components/ui/button'
  import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
  import type { TaxonomyScoreResult } from '@/lib/types'

  export function TaxonomyPage() {
    const [selected, setSelected] = useState('')
    const [result, setResult] = useState<TaxonomyScoreResult | null>(null)

    const { data: companies = [] } = useQuery({ queryKey: ['companies'], queryFn: listCompanies })
    const mutation = useMutation({
      mutationFn: scoreCompany,
      onSuccess: setResult,
    })

    const run = () => {
      const company = companies.find(c => `${c.company_name}__${c.report_year}` === selected)
      if (company) mutation.mutate(company)
    }

    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-slate-800">EU Taxonomy Score</h1>

        <div className="flex gap-3 items-end">
          <div className="flex-1">
            <Select value={selected} onValueChange={setSelected}>
              <SelectTrigger><SelectValue placeholder="Select company…" /></SelectTrigger>
              <SelectContent>
                {companies.map(c => (
                  <SelectItem key={`${c.company_name}__${c.report_year}`} value={`${c.company_name}__${c.report_year}`}>
                    {c.company_name} ({c.report_year})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button onClick={run} disabled={!selected || mutation.isPending}>
            {mutation.isPending ? 'Scoring…' : 'Score'}
          </Button>
        </div>

        {result && (
          <div className="grid grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  EU Taxonomy Alignment
                  <Badge variant={result.dnsh_pass ? 'default' : 'destructive'}>
                    DNSH {result.dnsh_pass ? '✓' : '✗'}
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <TaxonomyRadar scores={result.objective_scores} />
                <div className="grid grid-cols-3 gap-2 mt-4 text-center">
                  <div><p className="text-xs text-slate-400">Revenue</p><p className="font-bold text-indigo-600">{result.revenue_aligned_pct}%</p></div>
                  <div><p className="text-xs text-slate-400">CapEx</p><p className="font-bold text-indigo-600">{result.capex_aligned_pct}%</p></div>
                  <div><p className="text-xs text-slate-400">OpEx</p><p className="font-bold text-indigo-600">{result.opex_aligned_pct}%</p></div>
                </div>
              </CardContent>
            </Card>

            <div className="space-y-4">
              {result.gaps.length > 0 && (
                <Card>
                  <CardHeader><CardTitle className="text-base text-red-600">Gaps</CardTitle></CardHeader>
                  <CardContent>
                    <ul className="space-y-1">
                      {result.gaps.map((g, i) => <li key={i} className="text-sm text-slate-600 flex gap-2"><span className="text-red-400">•</span>{g}</li>)}
                    </ul>
                  </CardContent>
                </Card>
              )}
              {result.recommendations.length > 0 && (
                <Card>
                  <CardHeader><CardTitle className="text-base text-indigo-600">Recommendations</CardTitle></CardHeader>
                  <CardContent>
                    <ul className="space-y-1">
                      {result.recommendations.map((r, i) => <li key={i} className="text-sm text-slate-600 flex gap-2"><span className="text-indigo-400">→</span>{r}</li>)}
                    </ul>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
        )}
      </div>
    )
  }
  ```

- [ ] **Step 3: Verify**

  ```bash
  npx tsc --noEmit
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add frontend/src/
  git commit -m "feat: Taxonomy page with EU radar chart, DNSH badge, gaps & recommendations"
  ```

---

## Task 7: LCOE Page

**Files:**
- Modify: `frontend/src/pages/LcoePage.tsx`

- [ ] **Step 1: Write `LcoePage.tsx`**

  ```tsx
  // frontend/src/pages/LcoePage.tsx
  import { useState } from 'react'
  import { useMutation, useQuery } from '@tanstack/react-query'
  import { calcLcoe, calcSensitivity, getBenchmarks } from '@/lib/api'
  import type { LCOEInput, LCOEResult, SensitivityResult } from '@/lib/types'
  import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
  import { Button } from '@/components/ui/button'
  import { Input } from '@/components/ui/input'
  import { Label } from '@/components/ui/label'
  import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
  import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts'
  import { MetricCard } from '@/components/MetricCard'

  const TECHNOLOGIES = ['solar_pv', 'wind_onshore', 'wind_offshore', 'battery_storage', 'battery_manufacturing']

  export function LcoePage() {
    const [form, setForm] = useState<LCOEInput>({
      technology: 'solar_pv', capacity_mw: 100, capacity_factor: 0.22,
      capex_eur_per_kw: 850, opex_eur_per_kw_year: 15, lifetime_years: 25, discount_rate: 0.07,
    })
    const [lcoe, setLcoe] = useState<LCOEResult | null>(null)
    const [sensitivity, setSensitivity] = useState<SensitivityResult[]>([])

    const { data: benchmarks = {} } = useQuery({ queryKey: ['benchmarks'], queryFn: getBenchmarks })

    const lcoeMutation = useMutation({ mutationFn: calcLcoe, onSuccess: setLcoe })
    const sensMutation = useMutation({ mutationFn: calcSensitivity, onSuccess: setSensitivity })

    const run = () => {
      lcoeMutation.mutate(form)
      sensMutation.mutate(form)
    }

    const loadBenchmark = (tech: string) => {
      if (benchmarks[tech]) setForm({ ...benchmarks[tech], technology: tech })
    }

    const set = (k: keyof LCOEInput, v: string | number) => setForm(f => ({ ...f, [k]: v }))

    const sensChartData = sensitivity[0]?.values.map((v, i) => ({
      capex_delta: `${v > 0 ? '+' : ''}${Math.round(v * 100)}%`,
      ...Object.fromEntries(sensitivity.map(s => [s.parameter, s.lcoe_results[i]?.toFixed(2)])),
    }))

    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-slate-800">LCOE Calculator</h1>

        <div className="grid grid-cols-2 gap-6">
          <Card>
            <CardHeader><CardTitle className="text-base">Parameters</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <Label>Technology</Label>
                  <Select value={form.technology} onValueChange={v => { set('technology', v); loadBenchmark(v) }}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>{TECHNOLOGIES.map(t => <SelectItem key={t} value={t}>{t.replace(/_/g,' ')}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div><Label>Capacity (MW)</Label><Input type="number" value={form.capacity_mw} onChange={e => set('capacity_mw', +e.target.value)} /></div>
                <div><Label>Capacity Factor</Label><Input type="number" step="0.01" value={form.capacity_factor} onChange={e => set('capacity_factor', +e.target.value)} /></div>
                <div><Label>CAPEX (€/kW)</Label><Input type="number" value={form.capex_eur_per_kw} onChange={e => set('capex_eur_per_kw', +e.target.value)} /></div>
                <div><Label>OPEX (€/kW/yr)</Label><Input type="number" value={form.opex_eur_per_kw_year} onChange={e => set('opex_eur_per_kw_year', +e.target.value)} /></div>
                <div><Label>Lifetime (years)</Label><Input type="number" value={form.lifetime_years} onChange={e => set('lifetime_years', +e.target.value)} /></div>
                <div><Label>Discount Rate</Label><Input type="number" step="0.01" value={form.discount_rate} onChange={e => set('discount_rate', +e.target.value)} /></div>
              </div>
              <Button className="w-full" onClick={run} disabled={lcoeMutation.isPending}>
                {lcoeMutation.isPending ? 'Calculating…' : 'Calculate'}
              </Button>
            </CardContent>
          </Card>

          {lcoe && (
            <div className="grid grid-cols-2 gap-3 content-start">
              <MetricCard title="LCOE" value={`€${lcoe.lcoe_eur_per_mwh.toFixed(2)}/MWh`} />
              <MetricCard title="IRR" value={`${(lcoe.irr * 100).toFixed(1)}%`} accent="green" />
              <MetricCard title="NPV" value={`€${(lcoe.npv_eur / 1e6).toFixed(1)}M`} />
              <MetricCard title="Payback" value={`${lcoe.payback_years.toFixed(1)} yr`} />
            </div>
          )}
        </div>

        {sensChartData && sensChartData.length > 0 && (
          <Card>
            <CardHeader><CardTitle className="text-base">Sensitivity Analysis (LCOE €/MWh)</CardTitle></CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={240}>
                <LineChart data={sensChartData}>
                  <XAxis dataKey="capex_delta" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  {sensitivity.map((s, i) => (
                    <Line key={s.parameter} dataKey={s.parameter} stroke={i === 0 ? '#6366f1' : '#22c55e'} dot={false} />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}
      </div>
    )
  }
  ```

- [ ] **Step 2: Verify**

  ```bash
  npx tsc --noEmit
  ```

- [ ] **Step 3: Commit**

  ```bash
  git add frontend/src/pages/LcoePage.tsx
  git commit -m "feat: LCOE calculator page with sensitivity analysis chart"
  ```

---

## Task 8: Companies + Compare Pages

**Files:**
- Modify: `frontend/src/pages/CompaniesPage.tsx`
- Modify: `frontend/src/pages/ComparePage.tsx`

- [ ] **Step 1: Write `CompaniesPage.tsx`**

  ```tsx
  // frontend/src/pages/CompaniesPage.tsx
  import { useState } from 'react'
  import { useQuery } from '@tanstack/react-query'
  import { listCompanies } from '@/lib/api'
  import { Input } from '@/components/ui/input'
  import { Badge } from '@/components/ui/badge'
  import { Card, CardContent } from '@/components/ui/card'

  export function CompaniesPage() {
    const [search, setSearch] = useState('')
    const { data: companies = [], isLoading } = useQuery({ queryKey: ['companies'], queryFn: listCompanies })

    const filtered = companies.filter(c =>
      c.company_name.toLowerCase().includes(search.toLowerCase())
    )

    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold text-slate-800">Companies</h1>
          <Input placeholder="Search…" value={search} onChange={e => setSearch(e.target.value)} className="w-64" />
        </div>

        {isLoading ? <p className="text-slate-400">Loading…</p> : (
          <div className="space-y-2">
            {filtered.map(c => (
              <Card key={`${c.company_name}-${c.report_year}`}>
                <CardContent className="py-4 flex items-center justify-between">
                  <div>
                    <p className="font-semibold text-slate-800">{c.company_name}</p>
                    <p className="text-sm text-slate-400">{c.report_year} · {c.total_employees?.toLocaleString() ?? '—'} employees</p>
                  </div>
                  <div className="flex items-center gap-4 text-sm text-slate-500">
                    {c.renewable_energy_pct != null && <span>{c.renewable_energy_pct}% renewable</span>}
                    {c.scope1_co2e_tonnes != null && <span>Scope1: {(c.scope1_co2e_tonnes/1e6).toFixed(2)}Mt</span>}
                    <div className="flex gap-1">{c.primary_activities.map(a => <Badge key={a} variant="outline" className="text-xs">{a}</Badge>)}</div>
                  </div>
                </CardContent>
              </Card>
            ))}
            {filtered.length === 0 && <p className="text-slate-400 text-sm">No results.</p>}
          </div>
        )}
      </div>
    )
  }
  ```

- [ ] **Step 2: Write `ComparePage.tsx`**

  ```tsx
  // frontend/src/pages/ComparePage.tsx
  import { useState } from 'react'
  import { useQuery, useMutation } from '@tanstack/react-query'
  import { listCompanies, scoreCompany } from '@/lib/api'
  import { TaxonomyRadar } from '@/components/RadarChart'
  import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
  import { Badge } from '@/components/ui/badge'
  import { Button } from '@/components/ui/button'
  import type { TaxonomyScoreResult } from '@/lib/types'

  export function ComparePage() {
    const [selected, setSelected] = useState<string[]>([])
    const [results, setResults] = useState<TaxonomyScoreResult[]>([])

    const { data: companies = [] } = useQuery({ queryKey: ['companies'], queryFn: listCompanies })

    const toggle = (key: string) =>
      setSelected(s => s.includes(key) ? s.filter(x => x !== key) : s.length < 4 ? [...s, key] : s)

    const runCompare = async () => {
      const chosen = companies.filter(c => selected.includes(`${c.company_name}__${c.report_year}`))
      const scores = await Promise.all(chosen.map(scoreCompany))
      setResults(scores)
    }

    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-slate-800">Compare Companies</h1>
        <p className="text-slate-500 text-sm">Select up to 4 companies</p>

        <div className="flex flex-wrap gap-2">
          {companies.map(c => {
            const key = `${c.company_name}__${c.report_year}`
            return (
              <Badge
                key={key}
                variant={selected.includes(key) ? 'default' : 'outline'}
                className="cursor-pointer"
                onClick={() => toggle(key)}
              >
                {c.company_name} ({c.report_year})
              </Badge>
            )
          })}
        </div>

        <Button onClick={runCompare} disabled={selected.length < 2}>
          Compare {selected.length} companies
        </Button>

        {results.length > 0 && (
          <div className="grid grid-cols-2 gap-6">
            {results.map(r => (
              <Card key={`${r.company_name}-${r.report_year}`}>
                <CardHeader>
                  <CardTitle className="text-sm flex gap-2 items-center">
                    {r.company_name} ({r.report_year})
                    <Badge variant={r.dnsh_pass ? 'default' : 'destructive'}>DNSH {r.dnsh_pass ? '✓' : '✗'}</Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <TaxonomyRadar scores={r.objective_scores} />
                  <p className="text-center text-sm mt-2 text-indigo-600 font-semibold">{r.revenue_aligned_pct}% aligned</p>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    )
  }
  ```

- [ ] **Step 3: Verify**

  ```bash
  npx tsc --noEmit && npm run build
  ```
  Expected: build succeeds, no errors.

- [ ] **Step 4: Commit**

  ```bash
  git add frontend/src/
  git commit -m "feat: Companies list and Compare pages — Stage 7 complete"
  git push
  ```

---

## Self-Healing Loop Script

Save as `scripts/frontend_loop.sh` and run it to let Codex iterate autonomously:

```bash
#!/bin/bash
# Self-healing frontend build loop
# Usage: bash scripts/frontend_loop.sh

cd /Users/yumei/projects/esg-research-toolkit/frontend

MAX=5; attempt=0
while [ $attempt -lt $MAX ]; do
  echo "=== Build attempt $((attempt+1)) ==="
  if npm run build 2>&1 | tee /tmp/fe_build.log; then
    echo "✅ Build succeeded"
    break
  fi
  attempt=$((attempt+1))
  echo "❌ Build failed — asking Codex to fix..."
  ERROR=$(tail -30 /tmp/fe_build.log)
  codex exec --full-auto "Fix the TypeScript/build error in the frontend/ React+Vite project.
Error output:
$ERROR

Rules: only edit files in frontend/src/, do not change backend, run 'npx tsc --noEmit' after fixing."
done
```
