import { ShieldCheck } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Panel } from '@/components/layout/Panel'
import { Badge } from '@/components/ui/badge'
import type { FrameworkMetadata } from '@/lib/types'
import { asDate, type FrameworkDisplayResult } from '@/pages/company-profile/utils'

interface FrameworkResultsCardProps {
  frameworkScores: FrameworkDisplayResult[]
  frameworkMetaMap: Map<string, FrameworkMetadata>
  locale: string
}

export function FrameworkResultsCard({
  frameworkScores,
  frameworkMetaMap,
  locale,
}: FrameworkResultsCardProps) {
  const { t } = useTranslation()

  return (
    <Panel
      title={(
        <span className="flex items-center gap-2 text-base">
          <ShieldCheck size={16} className="text-indigo-600" />
          {t('profile.detailTitle')}
        </span>
      )}
    >
      <div className="space-y-3">
        {frameworkScores.length === 0 ? (
          <p className="text-sm text-slate-400">{t('profile.noFrameworkResults')}</p>
        ) : (
          frameworkScores.map((framework) => (
            (() => {
              const meta = frameworkMetaMap.get(framework.framework_id)
              const frameworkVersion =
                meta?.framework_version ?? framework.framework_version ?? null
              const analyzedAt =
                meta?.stored_at ??
                framework.analyzed_at ??
                framework.stored_at ??
                null

              return (
                <details
                  key={`${framework.framework_id}-${framework.framework_version ?? 'v1'}-${framework.analyzed_at ?? framework.stored_at ?? 'none'}`}
                  className="rounded-md border p-3 open:bg-slate-50"
                >
                  <summary className="cursor-pointer list-none">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="font-medium text-slate-900">{framework.framework}</p>
                        <p className="text-xs text-slate-500">
                          {t('common.score')}: {(framework.total_score * 100).toFixed(1)}% · {t('profile.detailCoverage')}:{' '}
                          {framework.coverage_pct.toFixed(1)}%
                        </p>
                      </div>
                      <Badge>{framework.grade}</Badge>
                    </div>
                  </summary>
                  <div className="mt-3 space-y-3">
                    <div className="space-y-2">
                      {framework.dimensions.map((dimension) => (
                        <div key={dimension.name}>
                          <div className="mb-1 flex items-center justify-between text-xs text-slate-600">
                            <span>{t(`frameworks.dim.${dimension.name}`, { defaultValue: dimension.name })}</span>
                            <span>
                              {dimension.disclosed}/{dimension.total}
                            </span>
                          </div>
                          <div className="h-2 rounded-full bg-slate-100">
                            <div
                              className="h-2 rounded-full bg-indigo-500"
                              style={{ width: `${Math.round(dimension.score * 100)}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                    {framework.gaps.length > 0 && (
                      <div>
                        <p className="mb-1 text-xs font-medium text-slate-700">{t('profile.detailGaps')}</p>
                        <ul className="list-disc space-y-1 pl-5 text-xs text-slate-600">
                          {framework.gaps.map((gap, index) => (
                            <li key={index}>{gap}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {framework.recommendations.length > 0 && (
                      <div>
                        <p className="mb-1 text-xs font-medium text-slate-700">
                          {t('profile.detailRecommendations')}
                        </p>
                        <ul className="list-disc space-y-1 pl-5 text-xs text-slate-600">
                          {framework.recommendations.map((recommendation, index) => (
                            <li key={index}>{recommendation}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {frameworkVersion || analyzedAt ? (
                      <p className="mt-2 text-xs text-slate-400">
                        {frameworkVersion
                          ? t('profile.frameworkVersion', {
                              version: frameworkVersion,
                            })
                          : null}
                        {analyzedAt
                          ? ` · ${t('profile.frameworkAnalyzedAt', {
                              date: asDate(analyzedAt, locale),
                            })}`
                          : null}
                      </p>
                    ) : null}
                  </div>
                </details>
              )
            })()
          ))
        )}
      </div>
    </Panel>
  )
}
