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

export function TaxonomyPage() {
  const { t } = useTranslation()
  const [selected, setSelected] = useState<string>('')
  const [pdfLoading, setPdfLoading] = useState(false)

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
        <h1 className="text-2xl font-bold text-slate-900">{t('taxonomy.title')}</h1>
        {report && companyName && companyYear && (
          <Button
            variant="outline"
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

      <Select value={selected} onValueChange={setSelected}>
        <SelectTrigger className="w-72">
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

      {isLoading && (
        <p className="text-slate-400">{t('taxonomy.loadingData')}</p>
      )}

      {report && (
        <div className="space-y-6">
          <div className="grid grid-cols-4 gap-4">
            <MetricCard
              label={t('taxonomy.revenueAligned')}
              value={`${report.revenue_aligned_pct.toFixed(1)}%`}
              color="blue"
            />
            <MetricCard
              label={t('taxonomy.capexAligned')}
              value={`${report.capex_aligned_pct.toFixed(1)}%`}
              color="blue"
            />
            <MetricCard
              label={t('taxonomy.opexAligned')}
              value={`${report.opex_aligned_pct.toFixed(1)}%`}
              color="blue"
            />
            <MetricCard
              label={t('taxonomy.dnshStatus')}
              value={report.dnsh_pass ? t('taxonomy.dnshPass') : t('taxonomy.dnshFail')}
              color={report.dnsh_pass ? 'green' : 'red'}
            />
          </div>

          <div className="grid grid-cols-2 gap-6">
            <div>
              <h2 className="text-lg font-semibold mb-3">{t('taxonomy.objectiveScores')}</h2>
              <TaxonomyRadarChart data={report.objective_scores} />
            </div>
            <div className="space-y-4">
              <div>
                <h2 className="text-lg font-semibold mb-3">{t('taxonomy.dnshCheck')}</h2>
                <div className="flex items-center gap-2">
                  {report.dnsh_pass ? (
                    <>
                      <CheckCircle className="text-green-500" size={20} />
                      <span className="text-green-700 font-medium">
                        {t('taxonomy.dnshAllMet')}
                      </span>
                    </>
                  ) : (
                    <>
                      <XCircle className="text-red-500" size={20} />
                      <span className="text-red-700 font-medium">
                        {t('taxonomy.dnshNotMet')}
                      </span>
                    </>
                  )}
                </div>
              </div>
              {report.gaps.length > 0 && (
                <div>
                  <h3 className="font-medium mb-2">{t('common.gaps')}</h3>
                  <ul className="space-y-1">
                    {report.gaps.map((g, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <Badge variant="destructive" className="shrink-0 mt-0.5">
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
                  <h3 className="font-medium mb-2">{t('common.recommendations')}</h3>
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
        <p className="text-slate-400 text-center py-12">
          {t('taxonomy.selectPrompt')}
        </p>
      )}
    </div>
  )
}
