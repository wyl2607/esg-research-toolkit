import { ShieldCheck } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { EvidenceBadge } from '@/components/EvidenceBadge'
import { Panel } from '@/components/layout/Panel'
import { Badge } from '@/components/ui/badge'
import type {
  CompanyDataQualitySummary,
  CompanyProfileLatestPeriod,
  EvidenceAnchor,
} from '@/lib/types'

interface DisclosureLabel {
  metricKey: string
  label: string
}

interface DataQualityCardProps {
  dataQualitySummary: CompanyDataQualitySummary
  readinessLabel: string
  readinessToneClass: string
  presentDisclosureLabels: DisclosureLabel[]
  missingDisclosureLabels: DisclosureLabel[]
  evidenceByMetric: Map<string, EvidenceAnchor>
  latestPeriod: CompanyProfileLatestPeriod
}

export function DataQualityCard(props: DataQualityCardProps) {
  const {
    dataQualitySummary,
    readinessLabel,
    readinessToneClass,
    presentDisclosureLabels,
    missingDisclosureLabels,
    evidenceByMetric,
    latestPeriod,
  } = props
  const { t } = useTranslation()

  return (
    <Panel
      title={(
        <span className="flex items-center gap-2 text-base">
          <ShieldCheck size={16} className="text-indigo-600" />
          {t('profile.dataQualityTitle')}
        </span>
      )}
    >
      <div className="space-y-4">
        <div className="flex flex-col gap-3 rounded-lg border bg-slate-50 px-4 py-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              {t('profile.dataQualityCompletion')}
            </p>
            <p className="mt-1 text-2xl font-semibold text-slate-900">
              {dataQualitySummary.completion_percentage.toFixed(1)}%
            </p>
          </div>
          <Badge className={`border ${readinessToneClass}`}>
            {t('profile.dataQualityReadiness')}: {readinessLabel}
          </Badge>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-lg border bg-white px-4 py-3">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              {t('profile.dataQualityTotal')}
            </p>
            <p className="mt-2 text-xl font-semibold text-slate-900">
              {dataQualitySummary.total_key_metrics_count}
            </p>
          </div>
          <div className="rounded-lg border bg-white px-4 py-3">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              {t('profile.dataQualityPresent')}
            </p>
            <p className="mt-2 text-xl font-semibold text-emerald-700">
              {dataQualitySummary.present_metrics_count}
            </p>
          </div>
          <div className="rounded-lg border bg-white px-4 py-3">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              {t('profile.dataQualityMissing')}
            </p>
            <p className="mt-2 text-xl font-semibold text-amber-700">
              {dataQualitySummary.missing_metrics.length}
            </p>
          </div>
        </div>

        <div className="space-y-2">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            {t('profile.dataQualityPresentList')}
          </p>
          {presentDisclosureLabels.length === 0 ? (
            <p className="text-sm text-slate-500">{t('profile.dataQualityNoPresent')}</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {presentDisclosureLabels.map(({ metricKey, label }) => (
                <div
                  key={metricKey}
                  className="flex flex-wrap items-center gap-2 rounded-md border border-emerald-200 bg-emerald-50 px-2 py-1 text-xs text-emerald-800"
                >
                  <span>{label}</span>
                  <EvidenceBadge
                    evidence={evidenceByMetric.get(metricKey)}
                    metricLabel={label}
                    fallbackFramework={latestPeriod.source_document_type}
                    fallbackPeriodLabel={latestPeriod.reporting_period_label}
                    testId={`evidence-badge-${metricKey}-quality`}
                  />
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="space-y-2">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            {t('profile.dataQualityMissingList')}
          </p>
          {missingDisclosureLabels.length === 0 ? (
            <p className="text-sm text-emerald-700">{t('profile.dataQualityNoMissing')}</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {missingDisclosureLabels.map(({ metricKey, label }) => (
                <div
                  key={metricKey}
                  className="flex flex-wrap items-center gap-2 rounded-md border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-800"
                >
                  <span>{label}</span>
                  <EvidenceBadge
                    evidence={null}
                    metricLabel={label}
                    fallbackFramework={latestPeriod.source_document_type}
                    fallbackPeriodLabel={latestPeriod.reporting_period_label}
                    testId={`evidence-badge-${metricKey}-missing`}
                  />
                </div>
              ))}
            </div>
          )}
        </div>

        <p className="text-xs text-slate-500">{t('profile.dataQualityMissingHint')}</p>
      </div>
    </Panel>
  )
}
