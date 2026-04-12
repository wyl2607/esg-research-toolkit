import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Layout } from '@/components/Layout'
import { DashboardPage } from '@/pages/DashboardPage'
import { UploadPage } from '@/pages/UploadPage'
import { TaxonomyPage } from '@/pages/TaxonomyPage'
import { LcoePage } from '@/pages/LcoePage'
import { CompaniesPage } from '@/pages/CompaniesPage'
import { ComparePage } from '@/pages/ComparePage'
import { FrameworksPage } from '@/pages/FrameworksPage'

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
            <Route path="frameworks" element={<FrameworksPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
