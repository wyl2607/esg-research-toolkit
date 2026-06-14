import { lazy, Suspense } from 'react'
import { useTranslation } from 'react-i18next'

import { EvidenceBadge } from '@/components/EvidenceBadge'
import { MetricCard } from '@/components/MetricCard'
import type {
  CompanyESGData,
  CompanyProfileLatestPeriod,
  EvidenceAnchor,
} from '@/lib/types'
import { asNum, asPct, metricDisclosureLabel } from '@/pages/company-profile/utils'

const PeerComparisonCard = lazy(() =>
  import('@/components/company-profile/PeerComparisonCard').then((module) => ({
    default: module.PeerComparisonCard,
  }))
)

interface CoreMetricsSectionProps {
  latestMetrics: CompanyESGData
  locale: string
  evidenceByMetric: Map<string, EvidenceAnchor>
  latestPeriod: CompanyProfileLatestPeriod
  latestCompanyReportId: number | null
  latestYear: number
}

export function CoreMetricsSection({
  latestMetrics,
  locale,
  evidenceByMetric,
  latestPeriod,
  latestCompanyReportId,
  latestYear,
}: CoreMetricsSectionProps) {
  const { t } = useTranslation()

  return (
    <>
      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard
          label={t('companies.scope1')}
          value={asNum(latestMetrics.scope1_co2e_tonnes, locale)}
          unit="tCO2e"
          footer={
            <EvidenceBadge
              evidence={evidenceByMetric.get('scope1_co2e_tonnes')}
              metricLabel={metricDisclosureLabel(t, 'scope1_co2e_tonnes')}
              fallbackFramework={latestPeriod.source_document_type}
              fallbackPeriodLabel={latestPeriod.reporting_period_label}
              testId="evidence-badge-scope1_co2e_tonnes"
            />
          }
        />
        <MetricCard
          label={t('companies.scope2')}
          value={asNum(latestMetrics.scope2_co2e_tonnes, locale)}
          unit="tCO2e"
          footer={
            <div className="space-y-1.5">
              {latestMetrics.scope2_basis === 'market' && (
                <span className="inline-block rounded border border-sky-200 bg-sky-50 px-1.5 py-0.5 text-[10px] font-medium text-sky-700">
                  {t('profile.scope2BasisMarket')}
                </span>
              )}
              {latestMetrics.scope2_basis === 'location' && (
                <span className="inline-block rounded border border-violet-200 bg-violet-50 px-1.5 py-0.5 text-[10px] font-medium text-violet-700">
                  {t('profile.scope2BasisLocation')}
                </span>
              )}
              <EvidenceBadge
                evidence={evidenceByMetric.get('scope2_co2e_tonnes')}
                metricLabel={metricDisclosureLabel(t, 'scope2_co2e_tonnes')}
                fallbackFramework={latestPeriod.source_document_type}
                fallbackPeriodLabel={latestPeriod.reporting_period_label}
                testId="evidence-badge-scope2_co2e_tonnes"
              />
            </div>
          }
        />
        <MetricCard
          label={t('companies.employees')}
          value={asNum(latestMetrics.total_employees, locale)}
          unit={t('companies.unitPeople')}
          footer={
            <EvidenceBadge
              evidence={evidenceByMetric.get('total_employees')}
              metricLabel={metricDisclosureLabel(t, 'total_employees')}
              fallbackFramework={latestPeriod.source_document_type}
              fallbackPeriodLabel={latestPeriod.reporting_period_label}
              testId="evidence-badge-total_employees"
            />
          }
        />
        <MetricCard
          label={t('companies.renewable')}
          value={asPct(latestMetrics.renewable_energy_pct)}
          unit={t('companies.unitPercent')}
          color="green"
          footer={
            <EvidenceBadge
              evidence={evidenceByMetric.get('renewable_energy_pct')}
              metricLabel={metricDisclosureLabel(t, 'renewable_energy_pct')}
              fallbackFramework={latestPeriod.source_document_type}
              fallbackPeriodLabel={latestPeriod.reporting_period_label}
              testId="evidence-badge-renewable_energy_pct"
            />
          }
        />
      </div>

      <Suspense
        fallback={(
          <div className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-500 shadow-sm dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
            {t('common.loading')}
          </div>
        )}
      >
        <PeerComparisonCard
          companyReportId={latestCompanyReportId}
          industryCode={latestPeriod?.industry_code ?? null}
          reportYear={latestYear}
          metrics={latestMetrics}
        />
      </Suspense>
    </>
  )
}
