import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Suspense, lazy } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Layout } from '@/components/Layout'

const DashboardPage = lazy(() =>
  import('@/pages/DashboardPage').then((module) => ({ default: module.DashboardPage }))
)
const UploadPage = lazy(() =>
  import('@/pages/UploadPage').then((module) => ({ default: module.UploadPage }))
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
const DesignLabPage = lazy(() =>
  import('@/pages/DesignLabPage').then((module) => ({ default: module.DesignLabPage }))
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
              <Route path="taxonomy" element={<TaxonomyPage />} />
              <Route path="lcoe" element={<LcoePage />} />
              <Route path="companies" element={<CompaniesPage />} />
              <Route path="companies/:companyName" element={<CompanyProfilePage />} />
              <Route path="manual" element={<ManualCaseBuilderPage />} />
              <Route path="design-lab" element={<DesignLabPage />} />
              <Route path="compare" element={<ComparePage />} />
              <Route path="frameworks" element={<FrameworksPage />} />
              <Route path="regional" element={<RegionalPage />} />
              <Route path="frameworks/regional" element={<RegionalPage />} />
            </Route>
          </Routes>
        </Suspense>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
