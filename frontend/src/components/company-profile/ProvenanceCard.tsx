import { FileText } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Panel } from '@/components/layout/Panel'
import type {
  CompanyProfileLatestPeriod,
  CompanySourceDocument,
} from '@/lib/types'
import {
  asDate,
  metricDisclosureLabel,
  prettifyToken,
  type FrameworkDisplayResult,
} from '@/pages/company-profile/utils'

interface LatestMergeCue {
  metricKey: string
  chosenSourceDocumentType: string
  mergeReason: string
}

interface ProvenanceCardProps {
  latestPeriod: CompanyProfileLatestPeriod
  latestSources: CompanySourceDocument[]
  mergeSourceCount: number
  latestSourceTypes: string
  latestSourceOrigin: string
  latestMergeCue: LatestMergeCue | null
  frameworkScores: FrameworkDisplayResult[]
  locale: string
}

export function ProvenanceCard({
  latestPeriod,
  latestSources,
  mergeSourceCount,
  latestSourceTypes,
  latestSourceOrigin,
  latestMergeCue,
  frameworkScores,
  locale,
}: ProvenanceCardProps) {
  const { t } = useTranslation()

  return (
    <Panel
      title={(
        <span className="flex items-center gap-2 text-base">
          <FileText size={16} className="text-indigo-600" />
          {t('profile.provenanceTitle')}
        </span>
      )}
    >
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-lg border bg-slate-50 px-4 py-3">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            {t('profile.provenancePeriodLabel')}
          </p>
          <p className="mt-2 text-sm font-semibold text-slate-900">
            {latestPeriod.period?.label ?? latestPeriod.reporting_period_label}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {t('profile.provenancePeriodSummary', {
              type: latestPeriod.period?.type ?? latestPeriod.reporting_period_type ?? '—',
              year: latestPeriod.period?.legacy_report_year ?? latestPeriod.report_year,
            })}
          </p>
        </div>

        <div className="rounded-lg border bg-slate-50 px-4 py-3">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            {t('profile.provenanceSourcesLabel')}
          </p>
          <p
            className="mt-2 text-sm font-semibold text-slate-900"
            data-testid="profile-provenance-source-summary"
          >
            {t('profile.provenanceSourceSummary', { count: latestSources.length })}
          </p>
          <p
            className="mt-1 text-xs text-slate-500"
            data-testid="profile-provenance-source-types"
          >
            {[latestSourceTypes, latestSourceOrigin].filter(Boolean).join(' · ') || '—'}
          </p>
        </div>

        <div className="rounded-lg border bg-slate-50 px-4 py-3">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            {t('profile.provenanceMergeLabel')}
          </p>
          <p
            className="mt-2 text-sm font-semibold text-slate-900"
            data-testid="profile-provenance-merge-summary"
          >
            {t('profile.provenanceMergeSummary', {
              count: mergeSourceCount,
            })}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {latestMergeCue
              ? t('profile.provenanceMergeMetricCue', {
                  metric: metricDisclosureLabel(t, latestMergeCue.metricKey),
                  sourceType: prettifyToken(latestMergeCue.chosenSourceDocumentType),
                  reason: prettifyToken(latestMergeCue.mergeReason),
                })
              : '—'}
          </p>
        </div>

        <div className="rounded-lg border bg-slate-50 px-4 py-3">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            {t('profile.provenanceFrameworkLabel')}
          </p>
          {frameworkScores.length === 0 ? (
            <p className="mt-2 text-sm text-slate-500">{t('profile.noFrameworkResults')}</p>
          ) : (
            <div className="mt-2 space-y-2">
              {frameworkScores.slice(0, 2).map((framework) => (
                <div key={`${framework.framework_id}-${framework.framework_version ?? 'unknown'}-${framework.analyzed_at ?? framework.stored_at ?? 'none'}`}>
                  <p className="text-sm font-semibold text-slate-900">
                    {t('profile.provenanceFrameworkVersion', {
                      framework: framework.framework,
                      version: framework.framework_version ?? '—',
                    })}
                  </p>
                  <p className="text-xs text-slate-500">
                    {t('profile.provenanceFrameworkTimestamp', {
                      date: asDate(framework.analyzed_at ?? framework.stored_at ?? null, locale),
                    })}
                  </p>
                </div>
              ))}
              {frameworkScores.length > 2 ? (
                <p className="text-xs text-slate-500">
                  {t('profile.provenanceFrameworkMore', {
                    count: frameworkScores.length - 2,
                  })}
                </p>
              ) : null}
            </div>
          )}
        </div>
      </div>
    </Panel>
  )
}
