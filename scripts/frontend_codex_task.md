# Stage 7 Frontend — Codex Execution Task

Working directory: /Users/yumei/projects/esg-research-toolkit

## Context

This is the ESG Research Toolkit project. The FastAPI backend already exists with 15 endpoints.
CORS is already configured in main.py (localhost:5173 / 4173).

Your job: build the entire React frontend from scratch, following the implementation plan exactly.

## Goal

Create a production-ready React + Vite + TypeScript frontend inside `frontend/` with 6 pages:
Dashboard, Upload, Taxonomy, LCOE, Companies, Compare.

Tech stack: React 18, Vite 5, TypeScript, shadcn/ui, Tailwind CSS v3, Recharts, React Router v6,
TanStack Query v5, react-dropzone, lucide-react.

## Step-by-step Instructions

### STEP 1: Scaffold Vite project

```bash
cd /Users/yumei/projects/esg-research-toolkit
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install react-router-dom @tanstack/react-query recharts react-dropzone lucide-react
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

### STEP 2: Install shadcn/ui

```bash
cd /Users/yumei/projects/esg-research-toolkit/frontend
npx shadcn@latest init --defaults
npx shadcn@latest add button card badge table input label select separator progress
```

If shadcn init asks questions interactively, use defaults (style: default, base color: slate, CSS variables: yes).

### STEP 3: Write vite.config.ts

Replace the entire file `/Users/yumei/projects/esg-research-toolkit/frontend/vite.config.ts` with:

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

### STEP 4: Write tailwind.config.ts

Replace `/Users/yumei/projects/esg-research-toolkit/frontend/tailwind.config.ts` with:

```ts
import type { Config } from 'tailwindcss'
export default {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: { extend: {} },
  plugins: [],
} satisfies Config
```

### STEP 5: Write src/index.css

Replace entire file with:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

### STEP 6: Write .env.local

```
VITE_API_URL=http://localhost:8000
```

### STEP 7: Write frontend/src/lib/types.ts

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

### STEP 8: Write frontend/src/lib/api.ts

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

export const deleteCompany = (name: string, year: number): Promise<void> =>
  req(`/report/companies/${encodeURIComponent(name)}/${year}`, { method: 'DELETE' })

export const updateCompany = (name: string, year: number, data: Partial<CompanyESGData>): Promise<CompanyESGData> =>
  req(`/report/companies/${encodeURIComponent(name)}/${year}`, { method: 'PUT', body: JSON.stringify(data) })

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

export const listLcoeResults = (): Promise<LCOEResult[]> =>
  req('/techno/results')

export const compareLcoe = (inputs: LCOEInput[]): Promise<LCOEResult[]> =>
  req('/techno/compare', { method: 'POST', body: JSON.stringify(inputs) })
```

### STEP 9: Write frontend/src/components/Sidebar.tsx

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

### STEP 10: Write frontend/src/components/Layout.tsx

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

### STEP 11: Write frontend/src/components/MetricCard.tsx

```tsx
// frontend/src/components/MetricCard.tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface MetricCardProps {
  label: string
  value: string | number
  sub?: string
  color?: 'default' | 'green' | 'red' | 'blue'
}

export function MetricCard({ label, value, sub, color = 'default' }: MetricCardProps) {
  const valueColor = {
    default: 'text-slate-900',
    green: 'text-green-600',
    red: 'text-red-600',
    blue: 'text-indigo-600',
  }[color]

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-slate-500">{label}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className={`text-2xl font-bold ${valueColor}`}>{value}</div>
        {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
      </CardContent>
    </Card>
  )
}
```

### STEP 12: Write frontend/src/components/RadarChart.tsx

```tsx
// frontend/src/components/RadarChart.tsx
import {
  Radar, RadarChart as ReRadarChart, PolarGrid,
  PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip
} from 'recharts'

interface RadarChartProps {
  data: Record<string, number>
}

const LABEL_MAP: Record<string, string> = {
  climate_mitigation: 'Climate Mitigation',
  climate_adaptation: 'Climate Adaptation',
  water: 'Water',
  circular_economy: 'Circular Economy',
  pollution_prevention: 'Pollution Prevention',
  biodiversity: 'Biodiversity',
}

export function TaxonomyRadarChart({ data }: RadarChartProps) {
  const chartData = Object.entries(data).map(([key, value]) => ({
    subject: LABEL_MAP[key] ?? key,
    score: Math.round(value * 100),
    fullMark: 100,
  }))

  return (
    <ResponsiveContainer width="100%" height={320}>
      <ReRadarChart data={chartData}>
        <PolarGrid />
        <PolarAngleAxis dataKey="subject" tick={{ fontSize: 12 }} />
        <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 10 }} />
        <Radar name="Score" dataKey="score" stroke="#6366f1" fill="#6366f1" fillOpacity={0.3} />
        <Tooltip formatter={(v: number) => `${v}%`} />
      </ReRadarChart>
    </ResponsiveContainer>
  )
}
```

### STEP 13: Write frontend/src/App.tsx

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

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
})

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

### STEP 14: Write frontend/src/main.tsx

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><App /></React.StrictMode>
)
```

### STEP 15: Write DashboardPage.tsx

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

  const avgTaxonomy = companies.length
    ? (companies.reduce((s, c) => s + (c.taxonomy_aligned_revenue_pct ?? 0), 0) / companies.length).toFixed(1)
    : '—'

  const recent = [...companies].slice(-5).reverse()

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
        <Button onClick={() => navigate('/upload')}>Upload Report</Button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <MetricCard label="Companies Analyzed" value={isLoading ? '…' : companies.length} color="blue" />
        <MetricCard label="Avg Taxonomy Alignment" value={isLoading ? '…' : `${avgTaxonomy}%`} color="green" />
        <MetricCard
          label="DNSH Pass Rate"
          value={isLoading ? '…' : companies.length === 0 ? '—' : `${Math.round((companies.filter(c => c.taxonomy_aligned_revenue_pct !== null && (c.taxonomy_aligned_revenue_pct ?? 0) > 0).length / companies.length) * 100)}%`}
        />
      </div>

      <div>
        <h2 className="text-lg font-semibold mb-3">Recent Analyses</h2>
        {isLoading ? (
          <p className="text-slate-400">Loading…</p>
        ) : recent.length === 0 ? (
          <p className="text-slate-400">No reports yet. Upload your first ESG report.</p>
        ) : (
          <div className="rounded-lg border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 border-b">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-slate-600">Company</th>
                  <th className="px-4 py-3 text-left font-medium text-slate-600">Year</th>
                  <th className="px-4 py-3 text-left font-medium text-slate-600">Taxonomy %</th>
                  <th className="px-4 py-3 text-left font-medium text-slate-600">Employees</th>
                </tr>
              </thead>
              <tbody>
                {recent.map((c, i) => (
                  <tr key={i} className="border-b last:border-0 hover:bg-slate-50 cursor-pointer" onClick={() => navigate('/companies')}>
                    <td className="px-4 py-3 font-medium">{c.company_name}</td>
                    <td className="px-4 py-3 text-slate-600">{c.report_year}</td>
                    <td className="px-4 py-3">
                      <Badge variant={c.taxonomy_aligned_revenue_pct && c.taxonomy_aligned_revenue_pct > 50 ? 'default' : 'secondary'}>
                        {c.taxonomy_aligned_revenue_pct != null ? `${c.taxonomy_aligned_revenue_pct.toFixed(1)}%` : '—'}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{c.total_employees?.toLocaleString() ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
```

### STEP 16: Write UploadPage.tsx

```tsx
// frontend/src/pages/UploadPage.tsx
import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { useMutation } from '@tanstack/react-query'
import { uploadReport } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Upload, FileText, CheckCircle, AlertCircle } from 'lucide-react'
import type { CompanyESGData } from '@/lib/types'
import { useNavigate } from 'react-router-dom'

export function UploadPage() {
  const navigate = useNavigate()
  const [result, setResult] = useState<CompanyESGData | null>(null)

  const mutation = useMutation({
    mutationFn: uploadReport,
    onSuccess: (data) => setResult(data),
  })

  const onDrop = useCallback((files: File[]) => {
    if (files[0]) mutation.mutate(files[0])
  }, [mutation])

  const { getRootProps, getInputProps, isDragActive, acceptedFiles } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
  })

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-slate-900">Upload ESG Report</h1>

      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors ${
          isDragActive ? 'border-indigo-400 bg-indigo-50' : 'border-slate-300 hover:border-indigo-300 hover:bg-slate-50'
        }`}
      >
        <input {...getInputProps()} />
        <Upload className="mx-auto mb-4 text-slate-400" size={40} />
        {isDragActive ? (
          <p className="text-indigo-600 font-medium">Drop the PDF here…</p>
        ) : (
          <>
            <p className="text-slate-600 font-medium">Drag & drop a PDF, or click to select</p>
            <p className="text-sm text-slate-400 mt-1">Supports ESG / Sustainability / Annual Reports</p>
          </>
        )}
        {acceptedFiles[0] && (
          <div className="mt-4 flex items-center justify-center gap-2 text-sm text-slate-600">
            <FileText size={14} />
            {acceptedFiles[0].name}
          </div>
        )}
      </div>

      {mutation.isPending && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3 text-slate-600">
              <div className="animate-spin w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full" />
              Extracting ESG data from PDF…
            </div>
          </CardContent>
        </Card>
      )}

      {mutation.isError && (
        <Card className="border-red-200">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-red-600">
              <AlertCircle size={16} />
              {(mutation.error as Error).message}
            </div>
          </CardContent>
        </Card>
      )}

      {result && (
        <Card>
          <CardContent className="pt-6 space-y-4">
            <div className="flex items-center gap-2">
              <CheckCircle size={18} className="text-green-500" />
              <span className="font-semibold">Extracted: {result.company_name} ({result.report_year})</span>
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              {[
                ['Scope 1 CO₂e', result.scope1_co2e_tonnes != null ? `${result.scope1_co2e_tonnes.toLocaleString()} t` : '—'],
                ['Scope 2 CO₂e', result.scope2_co2e_tonnes != null ? `${result.scope2_co2e_tonnes.toLocaleString()} t` : '—'],
                ['Renewable Energy', result.renewable_energy_pct != null ? `${result.renewable_energy_pct.toFixed(1)}%` : '—'],
                ['Employees', result.total_employees?.toLocaleString() ?? '—'],
                ['Taxonomy Aligned', result.taxonomy_aligned_revenue_pct != null ? `${result.taxonomy_aligned_revenue_pct.toFixed(1)}%` : '—'],
                ['Activities', result.primary_activities.join(', ') || '—'],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between border rounded px-3 py-2">
                  <span className="text-slate-500">{k}</span>
                  <span className="font-medium">{v}</span>
                </div>
              ))}
            </div>
            <div className="flex gap-3">
              <Button onClick={() => navigate('/taxonomy')}>Run Taxonomy Score →</Button>
              <Button variant="outline" onClick={() => navigate('/companies')}>View All Companies</Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
```

### STEP 17: Write TaxonomyPage.tsx

```tsx
// frontend/src/pages/TaxonomyPage.tsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listCompanies, getTaxonomyReport } from '@/lib/api'
import { TaxonomyRadarChart } from '@/components/RadarChart'
import { MetricCard } from '@/components/MetricCard'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { CheckCircle, XCircle } from 'lucide-react'

export function TaxonomyPage() {
  const [selected, setSelected] = useState<string>('')

  const { data: companies = [] } = useQuery({
    queryKey: ['companies'],
    queryFn: listCompanies,
  })

  const [companyName, companyYear] = selected ? selected.split('|') : [null, null]

  const { data: report, isLoading } = useQuery({
    queryKey: ['taxonomy', companyName, companyYear],
    queryFn: () => getTaxonomyReport(companyName!, Number(companyYear)),
    enabled: !!companyName && !!companyYear,
  })

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">Taxonomy Scoring</h1>
        {report && (
          <Button variant="outline" onClick={() => window.print()}>Export PDF</Button>
        )}
      </div>

      <Select value={selected} onValueChange={setSelected}>
        <SelectTrigger className="w-72">
          <SelectValue placeholder="Select company & year…" />
        </SelectTrigger>
        <SelectContent>
          {companies.map((c) => (
            <SelectItem key={`${c.company_name}|${c.report_year}`} value={`${c.company_name}|${c.report_year}`}>
              {c.company_name} ({c.report_year})
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {isLoading && <p className="text-slate-400">Loading taxonomy data…</p>}

      {report && (
        <div className="space-y-6">
          <div className="grid grid-cols-4 gap-4">
            <MetricCard label="Revenue Aligned" value={`${report.revenue_aligned_pct.toFixed(1)}%`} color="blue" />
            <MetricCard label="CapEx Aligned" value={`${report.capex_aligned_pct.toFixed(1)}%`} color="blue" />
            <MetricCard label="OpEx Aligned" value={`${report.opex_aligned_pct.toFixed(1)}%`} color="blue" />
            <MetricCard
              label="DNSH Status"
              value={report.dnsh_pass ? '✓ Pass' : '✗ Fail'}
              color={report.dnsh_pass ? 'green' : 'red'}
            />
          </div>

          <div className="grid grid-cols-2 gap-6">
            <div>
              <h2 className="text-lg font-semibold mb-3">Objective Scores</h2>
              <TaxonomyRadarChart data={report.objective_scores} />
            </div>
            <div className="space-y-4">
              <div>
                <h2 className="text-lg font-semibold mb-3">DNSH Check</h2>
                <div className="flex items-center gap-2">
                  {report.dnsh_pass
                    ? <><CheckCircle className="text-green-500" size={20} /><span className="text-green-700 font-medium">All DNSH criteria met</span></>
                    : <><XCircle className="text-red-500" size={20} /><span className="text-red-700 font-medium">DNSH criteria not fully met</span></>
                  }
                </div>
              </div>
              {report.gaps.length > 0 && (
                <div>
                  <h3 className="font-medium mb-2">Gaps</h3>
                  <ul className="space-y-1">
                    {report.gaps.map((g, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <Badge variant="destructive" className="shrink-0 mt-0.5">Gap</Badge>
                        <span className="text-sm text-slate-600">{g}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {report.recommendations.length > 0 && (
                <div>
                  <h3 className="font-medium mb-2">Recommendations</h3>
                  <ul className="space-y-1">
                    {report.recommendations.map((r, i) => (
                      <li key={i} className="text-sm text-slate-600">• {r}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {!selected && (
        <p className="text-slate-400 text-center py-12">Select a company above to view taxonomy analysis.</p>
      )}
    </div>
  )
}
```

### STEP 18: Write LcoePage.tsx

```tsx
// frontend/src/pages/LcoePage.tsx
import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { calcLcoe, calcSensitivity, getBenchmarks } from '@/lib/api'
import { MetricCard } from '@/components/MetricCard'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import type { LCOEInput } from '@/lib/types'

const TECHNOLOGIES = ['solar_pv', 'wind_onshore', 'wind_offshore', 'battery_storage']

const DEFAULTS: LCOEInput = {
  technology: 'solar_pv',
  capacity_mw: 100,
  capacity_factor: 0.22,
  capex_eur_per_kw: 800,
  opex_eur_per_kw_year: 16,
  lifetime_years: 25,
  discount_rate: 0.05,
}

export function LcoePage() {
  const [form, setForm] = useState<LCOEInput>(DEFAULTS)

  const lcoeMutation = useMutation({ mutationFn: calcLcoe })
  const sensitivityMutation = useMutation({ mutationFn: calcSensitivity })

  const { data: benchmarks } = useQuery({ queryKey: ['benchmarks'], queryFn: getBenchmarks })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    lcoeMutation.mutate(form)
    sensitivityMutation.mutate(form)
  }

  const loadBenchmark = (tech: string) => {
    if (benchmarks?.[tech]) setForm(benchmarks[tech])
  }

  const sensitivityChartData = sensitivityMutation.data?.flatMap(s =>
    s.values.map((v, i) => ({
      value: v,
      [s.parameter]: s.lcoe_results[i],
    }))
  )

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-slate-900">LCOE Analysis</h1>

      <div className="grid grid-cols-2 gap-8">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Technology</Label>
              <Select value={form.technology} onValueChange={v => setForm(f => ({ ...f, technology: v }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {TECHNOLOGIES.map(t => (
                    <SelectItem key={t} value={t}>{t.replace(/_/g, ' ')}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-end gap-2">
              <Button type="button" variant="outline" size="sm" onClick={() => loadBenchmark(form.technology)}>
                Load Benchmark
              </Button>
            </div>
          </div>

          {[
            ['capacity_mw', 'Capacity (MW)', '0.1'],
            ['capacity_factor', 'Capacity Factor (0-1)', '0.01'],
            ['capex_eur_per_kw', 'CAPEX (€/kW)', '1'],
            ['opex_eur_per_kw_year', 'OPEX (€/kW/yr)', '0.1'],
            ['lifetime_years', 'Lifetime (years)', '1'],
            ['discount_rate', 'Discount Rate (0-1)', '0.001'],
          ].map(([key, label, step]) => (
            <div key={key}>
              <Label>{label}</Label>
              <Input
                type="number"
                step={step}
                value={form[key as keyof LCOEInput] as number}
                onChange={e => setForm(f => ({ ...f, [key]: parseFloat(e.target.value) || 0 }))}
              />
            </div>
          ))}

          <Button type="submit" disabled={lcoeMutation.isPending} className="w-full">
            {lcoeMutation.isPending ? 'Calculating…' : 'Calculate LCOE'}
          </Button>
        </form>

        <div className="space-y-4">
          {lcoeMutation.data && (
            <div className="grid grid-cols-2 gap-3">
              <MetricCard label="LCOE" value={`€${lcoeMutation.data.lcoe_eur_per_mwh.toFixed(1)}/MWh`} color="blue" />
              <MetricCard label="NPV" value={`€${(lcoeMutation.data.npv_eur / 1e6).toFixed(1)}M`} color={lcoeMutation.data.npv_eur > 0 ? 'green' : 'red'} />
              <MetricCard label="IRR" value={`${(lcoeMutation.data.irr * 100).toFixed(1)}%`} color="blue" />
              <MetricCard label="Payback" value={`${lcoeMutation.data.payback_years.toFixed(1)} yr`} />
            </div>
          )}
          {!lcoeMutation.data && (
            <p className="text-slate-400 text-center py-8">Fill in the form and click Calculate.</p>
          )}
        </div>
      </div>

      {sensitivityMutation.data && sensitivityChartData && (
        <div>
          <h2 className="text-lg font-semibold mb-3">Sensitivity Analysis (±20%)</h2>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={sensitivityChartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="value" />
              <YAxis label={{ value: '€/MWh', angle: -90, position: 'insideLeft' }} />
              <Tooltip />
              <Legend />
              {sensitivityMutation.data.map((s, i) => (
                <Line key={s.parameter} type="monotone" dataKey={s.parameter}
                  stroke={['#6366f1','#22c55e','#f59e0b','#ef4444'][i % 4]} dot={false} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
```

### STEP 19: Write CompaniesPage.tsx

```tsx
// frontend/src/pages/CompaniesPage.tsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listCompanies, deleteCompany } from '@/lib/api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Trash2, Search } from 'lucide-react'

export function CompaniesPage() {
  const [search, setSearch] = useState('')
  const [sortKey, setSortKey] = useState<'company_name' | 'report_year' | 'taxonomy_aligned_revenue_pct'>('report_year')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const queryClient = useQueryClient()

  const { data: companies = [], isLoading } = useQuery({
    queryKey: ['companies'],
    queryFn: listCompanies,
  })

  const deleteMutation = useMutation({
    mutationFn: ({ name, year }: { name: string; year: number }) => deleteCompany(name, year),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['companies'] }),
  })

  const filtered = companies
    .filter(c => c.company_name.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => {
      const va = a[sortKey] ?? 0
      const vb = b[sortKey] ?? 0
      return sortDir === 'asc' ? (va > vb ? 1 : -1) : (va < vb ? 1 : -1)
    })

  const toggleSort = (key: typeof sortKey) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key); setSortDir('desc') }
  }

  const thClass = (key: typeof sortKey) =>
    `px-4 py-3 text-left font-medium text-slate-600 cursor-pointer hover:text-indigo-600 ${sortKey === key ? 'text-indigo-600' : ''}`

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">Companies</h1>

      <div className="relative w-72">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        <Input
          className="pl-8"
          placeholder="Search companies…"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      {isLoading ? (
        <p className="text-slate-400">Loading…</p>
      ) : filtered.length === 0 ? (
        <p className="text-slate-400">No companies found.</p>
      ) : (
        <div className="rounded-lg border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b">
              <tr>
                <th className={thClass('company_name')} onClick={() => toggleSort('company_name')}>Company</th>
                <th className={thClass('report_year')} onClick={() => toggleSort('report_year')}>Year</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Scope 1</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Employees</th>
                <th className={thClass('taxonomy_aligned_revenue_pct')} onClick={() => toggleSort('taxonomy_aligned_revenue_pct')}>Taxonomy %</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c, i) => (
                <tr key={i} className="border-b last:border-0 hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium">{c.company_name}</td>
                  <td className="px-4 py-3 text-slate-600">{c.report_year}</td>
                  <td className="px-4 py-3 text-slate-600">{c.scope1_co2e_tonnes?.toLocaleString() ?? '—'}</td>
                  <td className="px-4 py-3 text-slate-600">{c.total_employees?.toLocaleString() ?? '—'}</td>
                  <td className="px-4 py-3">
                    {c.taxonomy_aligned_revenue_pct != null
                      ? <Badge variant={c.taxonomy_aligned_revenue_pct > 50 ? 'default' : 'secondary'}>{c.taxonomy_aligned_revenue_pct.toFixed(1)}%</Badge>
                      : <span className="text-slate-400">—</span>
                    }
                  </td>
                  <td className="px-4 py-3">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-red-500 hover:text-red-700"
                      onClick={() => {
                        if (confirm(`Delete ${c.company_name} (${c.report_year})?`)) {
                          deleteMutation.mutate({ name: c.company_name, year: c.report_year })
                        }
                      }}
                    >
                      <Trash2 size={14} />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
```

### STEP 20: Write ComparePage.tsx

```tsx
// frontend/src/pages/ComparePage.tsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listCompanies } from '@/lib/api'
import { TaxonomyRadarChart } from '@/components/RadarChart'
import { MetricCard } from '@/components/MetricCard'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { CompanyESGData } from '@/lib/types'

export function ComparePage() {
  const [selected, setSelected] = useState<string[]>([])

  const { data: companies = [] } = useQuery({
    queryKey: ['companies'],
    queryFn: listCompanies,
  })

  const toggleCompany = (key: string) => {
    setSelected(prev =>
      prev.includes(key) ? prev.filter(k => k !== key) : prev.length < 4 ? [...prev, key] : prev
    )
  }

  const selectedCompanies: CompanyESGData[] = selected
    .map(k => {
      const [name, year] = k.split('|')
      return companies.find(c => c.company_name === name && c.report_year === Number(year))
    })
    .filter(Boolean) as CompanyESGData[]

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-slate-900">Compare Companies</h1>

      <div>
        <p className="text-sm text-slate-500 mb-3">Select up to 4 companies to compare</p>
        <div className="flex flex-wrap gap-2">
          {companies.map(c => {
            const key = `${c.company_name}|${c.report_year}`
            const isSelected = selected.includes(key)
            return (
              <Button
                key={key}
                variant={isSelected ? 'default' : 'outline'}
                size="sm"
                onClick={() => toggleCompany(key)}
              >
                {c.company_name} ({c.report_year})
              </Button>
            )
          })}
        </div>
      </div>

      {selectedCompanies.length >= 2 && (
        <div className="space-y-8">
          <div>
            <h2 className="text-lg font-semibold mb-4">Key Metrics</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm border rounded-lg overflow-hidden">
                <thead className="bg-slate-50 border-b">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium text-slate-600">Metric</th>
                    {selectedCompanies.map(c => (
                      <th key={`${c.company_name}${c.report_year}`} className="px-4 py-3 text-left font-medium text-slate-600">
                        {c.company_name} ({c.report_year})
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[
                    ['Taxonomy %', (c: CompanyESGData) => c.taxonomy_aligned_revenue_pct != null ? `${c.taxonomy_aligned_revenue_pct.toFixed(1)}%` : '—'],
                    ['Scope 1 (t)', (c: CompanyESGData) => c.scope1_co2e_tonnes?.toLocaleString() ?? '—'],
                    ['Renewable %', (c: CompanyESGData) => c.renewable_energy_pct != null ? `${c.renewable_energy_pct.toFixed(1)}%` : '—'],
                    ['Employees', (c: CompanyESGData) => c.total_employees?.toLocaleString() ?? '—'],
                    ['Female %', (c: CompanyESGData) => c.female_pct != null ? `${c.female_pct.toFixed(1)}%` : '—'],
                  ].map(([label, fmt]) => (
                    <tr key={label as string} className="border-b last:border-0">
                      <td className="px-4 py-2 text-slate-600 font-medium">{label as string}</td>
                      {selectedCompanies.map(c => (
                        <td key={`${c.company_name}${c.report_year}`} className="px-4 py-2">
                          {(fmt as (c: CompanyESGData) => string)(c)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {selectedCompanies.length < 2 && (
        <p className="text-slate-400 text-center py-12">Select at least 2 companies to compare.</p>
      )}
    </div>
  )
}
```

### STEP 21: Run build and fix errors

```bash
cd /Users/yumei/projects/esg-research-toolkit/frontend
npm run build
```

If there are TypeScript errors:
- Fix import paths (make sure @/ alias works, check tsconfig.json has `"baseUrl": "."` and paths configured)
- Fix any missing type imports
- Fix any component prop mismatches

### STEP 22: Fix tsconfig.json if needed

If the @/ alias doesn't work, update `tsconfig.json` to add:
```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

### STEP 23: Commit everything

```bash
cd /Users/yumei/projects/esg-research-toolkit
git add frontend/ main.py
git commit -m "feat: Stage 7 React+Vite frontend with 6 pages (dashboard, upload, taxonomy, LCOE, companies, compare)"
```

## Self-Healing Instructions

If `npm run build` fails:
1. Read the error messages carefully
2. Fix TypeScript type errors (most common: missing imports, wrong prop types)
3. If shadcn components are missing, run: `npx shadcn@latest add <component>`
4. If @/ paths fail, verify tsconfig.json has the paths config AND vite.config.ts has the alias
5. Re-run `npm run build` after each fix
6. Keep fixing until build succeeds

Do NOT stop on first error. Keep iterating until all steps are done and build passes.
