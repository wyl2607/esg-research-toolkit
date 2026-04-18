import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listCompaniesWithYearCoverage, getTaxonomyReport, downloadTaxonomyPdf } from '@/lib/api'
import { CompanyYearPicker, type CompanyYearSelection } from '@/components/CompanyYearPicker'
import { TaxonomyRadarChart } from '@/components/RadarChart'
import { MetricCard } from '@/components/MetricCard'
import { QueryStateCard } from '@/components/QueryStateCard'
import { PageContainer } from '@/components/layout/PageContainer'
import { PageHeader } from '@/components/layout/PageHeader'
import { Panel } from '@/components/layout/Panel'
import { NoticeBanner } from '@/components/NoticeBanner'
import { FilterBar } from '@/components/FilterBar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { CheckCircle, XCircle, Download } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { localizeErrorMessage, isBackendOffline } from '@/lib/error-utils'
import { BackendOfflineBanner } from '@/components/BackendOfflineBanner'

export function TaxonomyPage() {
  const { t } = useTranslation()
  const [selection, setSelection] = useState<CompanyYearSelection>({ company: null, year: null })
  const [pdfLoading, setPdfLoading] = useState(false)

  const {
    data: companies = [],
    isLoading: companiesLoading,
    error: companiesError,
    refetch: refetchCompanies,
  } = useQuery({
    queryKey: ['companies-v2'],
    queryFn: listCompaniesWithYearCoverage,
  })

  const companyName = selection.company
  const companyYear = selection.year

  const { data: report, isLoading, error: reportError, refetch: refetchReport } = useQuery({
    queryKey: ['taxonomy', companyName, companyYear],
    queryFn: () => getTaxonomyReport(companyName!, companyYear!),
    enabled: !!companyName && !!companyYear,
  })

  const backendOffline = isBackendOffline(companiesError) || isBackendOffline(reportError)

  return (
    <PageContainer>
      <PageHeader
        title={t('taxonomy.title')}
        subtitle={t('taxonomy.subtitle')}
        actions={
          report && companyName && companyYear ? (
            <Button
              variant="outline"
              className="border-amber-300 bg-amber-50/80 text-amber-900 hover:bg-amber-100"
              disabled={pdfLoading}
              onClick={async () => {
                setPdfLoading(true)
                try {
                  await downloadTaxonomyPdf(companyName, companyYear)
                } finally {
                  setPdfLoading(false)
                }
              }}
              aria-label={t('taxonomy.downloadPdf')}
            >
              <Download size={16} className="mr-2" />
              {pdfLoading ? t('taxonomy.generating') : t('taxonomy.downloadPdf')}
            </Button>
          ) : null
        }
      />

      <NoticeBanner tone="info">{t('taxonomy.disclaimer')}</NoticeBanner>

      {backendOffline ? (
        <BackendOfflineBanner />
      ) : (companiesError || reportError) ? (
        <QueryStateCard
          tone="error"
          title={t('common.error')}
          body={localizeErrorMessage(t, reportError ?? companiesError, 'common.error')}
          actionLabel={t('errorBoundary.retry')}
          onAction={() => {
            if (reportError) void refetchReport()
            else void refetchCompanies()
          }}
          className="max-w-2xl"
        />
      ) : null}

      {companiesLoading ? (
        <QueryStateCard
          tone="loading"
          title={t('common.loading')}
          body={t('taxonomy.subtitle')}
          className="max-w-2xl"
        />
      ) : null}

      <FilterBar>
        <FilterBar.Field
          label={`${t('common.company')} & ${t('common.year')}`}
          htmlFor="taxonomy-company-year-picker-company"
        >
          <CompanyYearPicker
            idPrefix="taxonomy-company-year-picker"
            companies={companies}
            value={selection}
            onChange={setSelection}
          />
        </FilterBar.Field>
      </FilterBar>

      {companies.length === 0 && !companiesLoading && !companiesError && !backendOffline ? (
        <QueryStateCard
          tone="empty"
          title={t('common.noData')}
          body={t('dashboard.noCompanies')}
          className="max-w-2xl"
        />
      ) : null}

      {isLoading ? (
        <QueryStateCard
          tone="loading"
          title={t('common.loading')}
          body={t('taxonomy.loadingData')}
          className="max-w-2xl"
        />
      ) : null}

      {report && (
        <div className="space-y-6">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              label={t('taxonomy.revenueAligned')}
              value={report.revenue_aligned_pct.toFixed(1)}
              unit="%"
              color="blue"
            />
            <MetricCard
              label={t('taxonomy.capexAligned')}
              value={report.capex_aligned_pct.toFixed(1)}
              unit="%"
              color="blue"
            />
            <MetricCard
              label={t('taxonomy.opexAligned')}
              value={report.opex_aligned_pct.toFixed(1)}
              unit="%"
              color="blue"
            />
            <MetricCard
              label={t('taxonomy.dnshStatus')}
              value={report.dnsh_pass ? t('taxonomy.dnshPass') : t('taxonomy.dnshFail')}
              color={report.dnsh_pass ? 'green' : 'red'}
            />
          </div>

          <div className="grid gap-6 xl:grid-cols-2">
            <Panel title={t('taxonomy.objectiveScores')}>
              <TaxonomyRadarChart data={report.objective_scores} />
            </Panel>

            <Panel title={t('taxonomy.dnshCheck')} className="space-y-4">
              <div>
                <div className="flex items-center gap-2">
                  {report.dnsh_pass ? (
                    <>
                      <CheckCircle className="text-green-500" size={20} />
                      <span className="font-medium text-green-700">
                        {t('taxonomy.dnshAllMet')}
                      </span>
                    </>
                  ) : (
                    <>
                      <XCircle className="text-red-500" size={20} />
                      <span className="font-medium text-red-700">
                        {t('taxonomy.dnshNotMet')}
                      </span>
                    </>
                  )}
                </div>
              </div>

              {report.gaps.length > 0 && (
                <div>
                  <h3 className="mb-2 font-medium">{t('common.gaps')}</h3>
                  <ul className="space-y-1">
                    {report.gaps.map((g, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <Badge variant="destructive" className="mt-0.5 shrink-0">
                          {t('common.missing')}
                        </Badge>
                        <span className="text-sm text-slate-600">{g}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {report.recommendations.length > 0 && (
                <div>
                  <h3 className="mb-2 font-medium">{t('common.recommendations')}</h3>
                  <ul className="space-y-1">
                    {report.recommendations.map((r, i) => (
                      <li key={i} className="text-sm text-slate-600">
                        • {r}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </Panel>
          </div>
        </div>
      )}

      {!companyYear && companies.length > 0 ? (
        <QueryStateCard
          tone="empty"
          title={t('common.selectCompany')}
          body={t('taxonomy.selectPrompt')}
          className="max-w-2xl py-8"
        />
      ) : null}
    </PageContainer>
  )
}
