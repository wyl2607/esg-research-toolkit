import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listCompanies, getTaxonomyReport, downloadTaxonomyPdf } from '@/lib/api'
import { TaxonomyRadarChart } from '@/components/RadarChart'
import { MetricCard } from '@/components/MetricCard'
import { QueryStateCard } from '@/components/QueryStateCard'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { CheckCircle, XCircle, Download } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { localizeErrorMessage, isBackendOffline } from '@/lib/error-utils'
import { BackendOfflineBanner } from '@/components/BackendOfflineBanner'

export function TaxonomyPage() {
  const { t } = useTranslation()
  const [selected, setSelected] = useState<string>('')
  const [pdfLoading, setPdfLoading] = useState(false)

  const { data: companies = [], error: companiesError, refetch: refetchCompanies } = useQuery({
    queryKey: ['companies'],
    queryFn: listCompanies,
  })

  const [companyName, companyYear] = selected ? selected.split('|') : [null, null]

  const { data: report, isLoading, error: reportError, refetch: refetchReport } = useQuery({
    queryKey: ['taxonomy', companyName, companyYear],
    queryFn: () => getTaxonomyReport(companyName!, Number(companyYear)),
    enabled: !!companyName && !!companyYear,
  })

  const backendOffline = isBackendOffline(companiesError) || isBackendOffline(reportError)

  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <p className="section-kicker">{t('taxonomy.kicker')}</p>
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-2">
            <h1 className="text-3xl font-semibold text-slate-900">{t('taxonomy.title')}</h1>
            <p className="max-w-3xl text-sm leading-6 text-slate-600">
              {t('taxonomy.subtitle')}
            </p>
          </div>
          {report && companyName && companyYear && (
            <Button
              variant="outline"
              className="border-amber-300 bg-amber-50/80 text-amber-900 hover:bg-amber-100"
              disabled={pdfLoading}
              onClick={async () => {
                setPdfLoading(true)
                try {
                  await downloadTaxonomyPdf(companyName, Number(companyYear))
                } finally {
                  setPdfLoading(false)
                }
              }}
              aria-label={t('taxonomy.downloadPdf')}
            >
              <Download size={16} className="mr-2" />
              {pdfLoading ? t('taxonomy.generating') : t('taxonomy.downloadPdf')}
            </Button>
          )}
        </div>
      </div>

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

      <div className="surface-card max-w-xl">
        <p className="mb-3 text-xs uppercase tracking-[0.2em] text-stone-500">
          {t('common.company')} & {t('common.year')}
        </p>
        <Select value={selected} onValueChange={setSelected}>
          <SelectTrigger className="w-full border-stone-300 bg-white/90" aria-label={t('common.selectCompany')}>
            <SelectValue placeholder={t('common.selectCompany')} />
          </SelectTrigger>
          <SelectContent>
            {companies.map((c) => (
              <SelectItem
                key={`${c.company_name}|${c.report_year}`}
                value={`${c.company_name}|${c.report_year}`}
              >
                {c.company_name} ({c.report_year})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {companies.length === 0 && !companiesError && !backendOffline ? (
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
            <div className="editorial-panel">
              <p className="section-kicker">{t('taxonomy.kicker')}</p>
              <h2 className="mb-3 text-2xl text-slate-900">{t('taxonomy.objectiveScores')}</h2>
              <TaxonomyRadarChart data={report.objective_scores} />
            </div>

            <div className="editorial-panel space-y-4">
              <div>
                <h2 className="mb-3 text-2xl text-slate-900">{t('taxonomy.dnshCheck')}</h2>
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
            </div>
          </div>
        </div>
      )}

      {!selected && companies.length > 0 ? (
        <QueryStateCard
          tone="empty"
          title={t('common.selectCompany')}
          body={t('taxonomy.selectPrompt')}
          className="max-w-2xl py-8"
        />
      ) : null}
    </div>
  )
}
