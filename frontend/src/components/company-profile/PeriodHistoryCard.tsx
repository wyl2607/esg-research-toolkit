import { Clock3 } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { EvidenceCard } from '@/components/company-profile/EvidenceCard'
import { Panel } from '@/components/layout/Panel'
import { Badge } from '@/components/ui/badge'
import type { CompanyHistoryPeriod, EvidenceAnchor } from '@/lib/types'
import { prettifyToken } from '@/pages/company-profile/utils'

interface PeriodHistoryCardProps {
  periods: CompanyHistoryPeriod[]
  latestEvidenceSummary: EvidenceAnchor[]
  fallbackFramework: string | null
  fallbackPeriodLabel: string | null
}

export function PeriodHistoryCard({
  periods,
  latestEvidenceSummary,
  fallbackFramework,
  fallbackPeriodLabel,
}: PeriodHistoryCardProps) {
  const { t } = useTranslation()

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Panel
        title={(
          <span className="flex items-center gap-2 text-base">
            <Clock3 size={16} className="text-indigo-600" />
            {t('profile.periodTitle')}
          </span>
        )}
      >
        <div className="space-y-2">
          {periods.map((p) => (
            <div
              key={`${p.report_year}-${p.reporting_period_label}`}
              className="flex items-center justify-between gap-3 rounded-md border px-3 py-2"
            >
              <div>
                <p className="text-sm font-medium text-slate-900">{p.reporting_period_label}</p>
                <p className="text-xs text-slate-500">
                  {[
                    prettifyToken(p.reporting_period_type),
                    p.source_document_type ? prettifyToken(p.source_document_type) : null,
                    t('profile.periodSourcesCount', {
                      count: p.source_documents?.length ?? 0,
                    }),
                  ]
                    .filter(Boolean)
                    .join(' · ')}
                </p>
              </div>
              <div className="text-right">
                <Badge variant="secondary">{p.report_year}</Badge>
                <p className="mt-1 text-xs text-slate-500">
                  {t('profile.provenanceMergeSummary', {
                    count: p.merged_result?.source_count ?? p.source_documents?.length ?? 0,
                  })}
                </p>
              </div>
            </div>
          ))}
        </div>
      </Panel>

      <EvidenceCard
        latestEvidenceSummary={latestEvidenceSummary}
        fallbackFramework={fallbackFramework}
        fallbackPeriodLabel={fallbackPeriodLabel}
      />
    </div>
  )
}
