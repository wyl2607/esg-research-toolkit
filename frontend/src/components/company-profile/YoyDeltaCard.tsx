import { TrendingUp } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Panel } from '@/components/layout/Panel'
import { deltaPercentLabel, deltaToneClass } from '@/pages/company-profile/utils'

interface YoyDelta {
  previousYear: number | null
  co2eDeltaPct: number | null
  revenueDeltaPct: number | null
  alignmentDeltaPct: number | null
}

interface YoySummary {
  previousYear: number | null
  renewableDelta: number | null
  taxonomyDelta: number | null
  hasAnyDelta: boolean
}

interface YoyDeltaCardProps {
  yoyDeltaCard: YoyDelta | null
  yoySummary: YoySummary | null
}

export function YoyDeltaCard({ yoyDeltaCard, yoySummary }: YoyDeltaCardProps) {
  const { t } = useTranslation()

  if (!yoyDeltaCard) return null

  return (
    <div data-testid="yoy-delta-card">
      <Panel
        title={(
          <span className="flex items-center gap-2 text-base">
            <TrendingUp size={16} className="text-indigo-600" />
            {t('profile.yoyTitle')}
          </span>
        )}
      >
        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-lg border bg-slate-50 px-4 py-4">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              YoY CO2e
            </p>
            <p className={`mt-2 text-2xl font-semibold ${deltaToneClass(yoyDeltaCard.co2eDeltaPct)}`}>
              {deltaPercentLabel(yoyDeltaCard.co2eDeltaPct)}
            </p>
            <p className="mt-1 text-xs text-slate-500">
              {t('profile.yoyComparedTo', { year: yoyDeltaCard.previousYear ?? '—' })}
            </p>
          </div>
          <div className="rounded-lg border bg-slate-50 px-4 py-4">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              YoY Revenue
            </p>
            <p className={`mt-2 text-2xl font-semibold ${deltaToneClass(yoyDeltaCard.revenueDeltaPct)}`}>
              {deltaPercentLabel(yoyDeltaCard.revenueDeltaPct)}
            </p>
            <p className="mt-1 text-xs text-slate-500">
              {t('profile.yoyComparedTo', { year: yoyDeltaCard.previousYear ?? '—' })}
            </p>
          </div>
          <div className="rounded-lg border bg-slate-50 px-4 py-4">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              YoY Alignment
            </p>
            <p className={`mt-2 text-2xl font-semibold ${deltaToneClass(yoyDeltaCard.alignmentDeltaPct)}`}>
              {deltaPercentLabel(yoyDeltaCard.alignmentDeltaPct)}
            </p>
            <p className="mt-1 text-xs text-slate-500">
              {t('profile.yoyComparedTo', { year: yoyDeltaCard.previousYear ?? '—' })}
            </p>
          </div>
          <div className="rounded-lg border bg-white px-4 py-4 md:col-span-3">
            <p className="text-sm leading-6 text-slate-700">
              {yoySummary?.hasAnyDelta
                ? t('profile.yoyNarrativeReady', {
                    year: yoySummary.previousYear ?? '—',
                    renewableDelta: yoySummary.renewableDelta != null ? `${yoySummary.renewableDelta >= 0 ? '+' : ''}${yoySummary.renewableDelta.toFixed(1)}%` : '—',
                    taxonomyDelta: yoySummary.taxonomyDelta != null ? `${yoySummary.taxonomyDelta >= 0 ? '+' : ''}${yoySummary.taxonomyDelta.toFixed(1)}%` : '—',
                  })
                : t('profile.yoyNarrativeMissing')}
            </p>
          </div>
        </div>
      </Panel>
    </div>
  )
}
