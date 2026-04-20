import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Suspense, lazy } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Layout } from '@/components/Layout'

const DashboardPage = lazy(() =>
  import('@/pages/DashboardPage').then((module) => ({ default: module.DashboardPage }))
)
const UploadPage = lazy(() =>
  import('@/pages/UploadPage').then((module) => ({ default: module.UploadPage }))
)
const PendingDisclosuresPage = lazy(() =>
  import('@/pages/PendingDisclosuresPage').then((module) => ({
    default: module.PendingDisclosuresPage,
  }))
)
const TaxonomyPage = lazy(() =>
  import('@/pages/TaxonomyPage').then((module) => ({ default: module.TaxonomyPage }))
)
const LcoePage = lazy(() =>
  import('@/pages/LcoePage').then((module) => ({ default: module.LcoePage }))
)
const CompaniesPage = lazy(() =>
  import('@/pages/CompaniesPage').then((module) => ({ default: module.CompaniesPage }))
)
const ComparePage = lazy(() =>
  import('@/pages/ComparePage').then((module) => ({ default: module.ComparePage }))
)
const BenchmarkPage = lazy(() =>
  import('@/pages/BenchmarkPage').then((module) => ({ default: module.BenchmarkPage }))
)
const FrameworksPage = lazy(() =>
  import('@/pages/FrameworksPage').then((module) => ({ default: module.FrameworksPage }))
)
const CompanyProfilePage = lazy(() =>
  import('@/pages/CompanyProfilePage').then((module) => ({ default: module.CompanyProfilePage }))
)
const RegionalPage = lazy(() =>
  import('@/pages/RegionalPage').then((module) => ({ default: module.RegionalPage }))
)
const ManualCaseBuilderPage = lazy(() =>
  import('@/pages/ManualCaseBuilderPage').then((module) => ({ default: module.ManualCaseBuilderPage }))
)

const CoverageFieldPage = lazy(() =>
  import('@/pages/CoverageFieldPage').then((module) => ({ default: module.CoverageFieldPage }))
)

const DesignPreviewPage = lazy(() =>
  import('@/pages/DesignPreviewPage').then((module) => ({ default: module.DesignPreviewPage }))
)

const SafPage = lazy(() =>
  import('@/pages/SafPage').then((module) => ({ default: module.SafPage }))
)

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Suspense fallback={<div className="p-6 text-sm text-slate-500">Loading…</div>}>
          <Routes>
            <Route element={<Layout />}>
              <Route index element={<DashboardPage />} />
              <Route path="upload" element={<UploadPage />} />
              <Route path="disclosures" element={<PendingDisclosuresPage />} />
              <Route path="taxonomy" element={<TaxonomyPage />} />
              <Route path="lcoe" element={<LcoePage />} />
              <Route path="saf" element={<SafPage />} />
              <Route path="companies" element={<CompaniesPage />} />
              <Route path="companies/:companyName" element={<CompanyProfilePage />} />
              <Route path="manual" element={<ManualCaseBuilderPage />} />
              <Route path="compare" element={<ComparePage />} />
              <Route path="benchmarks" element={<BenchmarkPage />} />
              <Route path="frameworks" element={<FrameworksPage />} />
              <Route path="regional" element={<RegionalPage />} />
              <Route path="coverage/:field" element={<CoverageFieldPage />} />
              <Route path="frameworks/regional" element={<RegionalPage />} />
              <Route path="design-preview" element={<DesignPreviewPage />} />
            </Route>
          </Routes>
        </Suspense>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
