import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listCompanies, getTaxonomyReport, downloadTaxonomyPdf } from '@/lib/api'
import { TaxonomyRadarChart } from '@/components/RadarChart'
import { MetricCard } from '@/components/MetricCard'
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
import { localizeErrorMessage } from '@/lib/error-utils'

export function TaxonomyPage() {
  const { t } = useTranslation()
  const [selected, setSelected] = useState<string>('')
  const [pdfLoading, setPdfLoading] = useState(false)

  const { data: companies = [], error: companiesError } = useQuery({
    queryKey: ['companies'],
    queryFn: listCompanies,
  })

  const [companyName, companyYear] = selected ? selected.split('|') : [null, null]

  const { data: report, isLoading, error: reportError } = useQuery({
    queryKey: ['taxonomy', companyName, companyYear],
    queryFn: () => getTaxonomyReport(companyName!, Number(companyYear)),
    enabled: !!companyName && !!companyYear,
  })

  return (
    <div className="space-y-8">
      <section className="editorial-panel space-y-4">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-3">
            <p className="section-kicker">{t('taxonomy.kicker')}</p>
            <div className="space-y-2">
              <h1 className="text-4xl text-slate-900">{t('taxonomy.title')}</h1>
              <p className="max-w-3xl text-sm leading-6 text-slate-600">
                {t('taxonomy.subtitle')}
              </p>
            </div>
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
            >
              <Download size={16} className="mr-2" />
              {pdfLoading ? t('taxonomy.generating') : t('taxonomy.downloadPdf')}
            </Button>
          )}
        </div>
      </section>

      {(companiesError || reportError) && (
        <p className="text-sm text-red-500">
          {localizeErrorMessage(t, reportError ?? companiesError, 'common.error')}
        </p>
      )}

      <div className="surface-card max-w-xl">
        <p className="mb-3 text-xs uppercase tracking-[0.2em] text-stone-500">
          {t('taxonomy.kicker')}
        </p>
        <Select value={selected} onValueChange={setSelected}>
          <SelectTrigger className="w-full border-stone-300 bg-white/90">
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

      {isLoading && <p className="text-slate-400">{t('taxonomy.loadingData')}</p>}

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

      {!selected && (
        <p className="py-12 text-center text-slate-400">{t('taxonomy.selectPrompt')}</p>
      )}
    </div>
  )
}
