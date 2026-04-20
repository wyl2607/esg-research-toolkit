import { Leaf } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { EvidenceBadge } from '@/components/EvidenceBadge'
import { Panel } from '@/components/layout/Panel'
import type { EvidenceAnchor } from '@/lib/types'
import { metricDisclosureLabel } from '@/pages/company-profile/utils'

interface EvidenceCardProps {
  latestEvidenceSummary: EvidenceAnchor[]
  fallbackFramework: string | null
  fallbackPeriodLabel: string | null
}

export function EvidenceCard({
  latestEvidenceSummary,
  fallbackFramework,
  fallbackPeriodLabel,
}: EvidenceCardProps) {
  const { t } = useTranslation()

  return (
    <Panel
      title={(
        <span className="flex items-center gap-2 text-base">
          <Leaf size={16} className="text-indigo-600" />
          {t('profile.evidenceTitle')}
        </span>
      )}
    >
      <div className="space-y-2">
        {latestEvidenceSummary.length === 0 ? (
          <p className="text-sm text-slate-400">{t('profile.noEvidence')}</p>
        ) : (
          latestEvidenceSummary.map((e, i) => (
            <div
              key={`${e.metric ?? 'metric'}-${i}`}
              className="flex flex-wrap items-center justify-between gap-3 rounded-md border px-3 py-3 text-sm text-slate-700"
            >
              <div className="min-w-0">
                <p className="font-medium text-slate-900">
                  {e.metric ? metricDisclosureLabel(t, e.metric) : t('profile.metricFallback')}
                </p>
                <p className="mt-1 truncate text-xs text-slate-500">
                  {[
                    e.document_title ?? e.source ?? e.source_type ?? t('profile.sourceFallback'),
                    e.page != null ? t('profile.evidencePageLabel', { page: e.page }) : null,
                  ]
                    .filter(Boolean)
                    .join(' · ')}
                </p>
              </div>
              <EvidenceBadge
                evidence={e}
                metricLabel={e.metric ? metricDisclosureLabel(t, e.metric) : t('profile.metricFallback')}
                fallbackFramework={fallbackFramework}
                fallbackPeriodLabel={fallbackPeriodLabel}
                testId={`evidence-summary-${e.metric ?? i}`}
              />
            </div>
          ))
        )}
      </div>
    </Panel>
  )
}
