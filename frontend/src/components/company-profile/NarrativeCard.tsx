import { CheckCircle2, FileText, TriangleAlert } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Panel } from '@/components/layout/Panel'
import type { CompanyNarrativeSummary } from '@/lib/types'

interface NarrativeCardProps {
  narrativeSummary: CompanyNarrativeSummary
  improvedMetricLabels: string[]
  weakenedMetricLabels: string[]
  strengthMetricLabels: string[]
  gapMetricLabels: string[]
}

export function NarrativeCard({
  narrativeSummary,
  improvedMetricLabels,
  weakenedMetricLabels,
  strengthMetricLabels,
  gapMetricLabels,
}: NarrativeCardProps) {
  const { t } = useTranslation()

  return (
    <Panel
      title={(
        <span className="flex items-center gap-2 text-base">
          <FileText size={16} className="text-indigo-600" />
          {t('profile.narrativeTitle')}
        </span>
      )}
    >
      <div className="space-y-5 text-sm text-slate-700">
        <section className="space-y-2">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{t('profile.narrativeSnapshotTitle')}</p>
          <p className="rounded-lg border bg-white px-4 py-3 leading-6">
            {t('profile.narrativeSnapshotBody', {
              periods: narrativeSummary.snapshot.periods_count,
              years: narrativeSummary.snapshot.years_count,
              frameworks: narrativeSummary.snapshot.framework_count,
              latestYear: narrativeSummary.snapshot.latest_year,
              readiness: t(`profile.readinessLabel.${narrativeSummary.snapshot.readiness_label}`),
            })}
          </p>
        </section>

        <section className="space-y-2">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{t('profile.narrativeChangeTitle')}</p>
          <div className="grid gap-3 md:grid-cols-2">
            <div className="rounded-lg border bg-white px-4 py-3">
              <p className="mb-2 inline-flex items-center gap-1 text-xs font-medium text-emerald-700">
                <CheckCircle2 size={14} />
                {t('profile.narrativeImprovedLabel')}
              </p>
              {improvedMetricLabels.length === 0 ? (
                <p className="text-xs text-slate-500">{t('profile.narrativeNoImprovement')}</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {improvedMetricLabels.map((label) => (
                    <span key={label} className="rounded-md border border-emerald-200 bg-emerald-50 px-2 py-1 text-xs text-emerald-800">
                      {label}
                    </span>
                  ))}
                </div>
              )}
            </div>
            <div className="rounded-lg border bg-white px-4 py-3">
              <p className="mb-2 inline-flex items-center gap-1 text-xs font-medium text-amber-700">
                <TriangleAlert size={14} />
                {t('profile.narrativeWeakenedLabel')}
              </p>
              {weakenedMetricLabels.length === 0 ? (
                <p className="text-xs text-slate-500">{t('profile.narrativeNoWeakening')}</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {weakenedMetricLabels.map((label) => (
                    <span key={label} className="rounded-md border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-800">
                      {label}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        </section>

        <section className="space-y-2">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{t('profile.narrativeStrengthTitle')}</p>
          {strengthMetricLabels.length === 0 ? (
            <p className="rounded-lg border bg-white px-4 py-3 text-xs text-slate-500">{t('profile.narrativeNoStrengths')}</p>
          ) : (
            <div className="flex flex-wrap gap-2 rounded-lg border bg-white px-4 py-3">
              {strengthMetricLabels.map((label) => (
                <span key={label} className="rounded-md border border-emerald-200 bg-emerald-50 px-2 py-1 text-xs text-emerald-800">
                  {label}
                </span>
              ))}
            </div>
          )}
        </section>

        <section className="space-y-2">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{t('profile.narrativeGapTitle')}</p>
          {gapMetricLabels.length === 0 ? (
            <p className="rounded-lg border bg-white px-4 py-3 text-xs text-emerald-700">{t('profile.narrativeNoGaps')}</p>
          ) : (
            <div className="flex flex-wrap gap-2 rounded-lg border bg-white px-4 py-3">
              {gapMetricLabels.map((label) => (
                <span key={label} className="rounded-md border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-800">
                  {label}
                </span>
              ))}
            </div>
          )}
        </section>

        <section className="space-y-2">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{t('profile.narrativePortfolioTitle')}</p>
          <p className="rounded-lg border bg-white px-4 py-3 leading-6">
            {t('profile.narrativePortfolioBody', {
              periods: narrativeSummary.snapshot.periods_count,
              frameworks: narrativeSummary.snapshot.framework_count,
            })}
          </p>
        </section>
      </div>
    </Panel>
  )
}
