import { lazy, Suspense, useEffect, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

import { NoticeBanner } from '@/components/NoticeBanner'

const CompanyProfileHeavyCharts = lazy(() =>
  import('@/components/company-profile/CompanyProfileHeavyCharts').then((module) => ({
    default: module.CompanyProfileHeavyCharts,
  }))
)

function DeferredHeavyCharts({
  ready,
  fallback,
  children,
}: {
  ready: boolean
  fallback: ReactNode
  children: ReactNode
}) {
  const [revealed, setRevealed] = useState(false)

  useEffect(() => {
    if (!ready || revealed) return

    const timer = window.setTimeout(() => setRevealed(true), 180)
    return () => window.clearTimeout(timer)
  }, [ready, revealed])

  return ready && revealed ? children : fallback
}

interface TrendDatum {
  year: number
  scope1: number | null
  renewable: number | null
  taxonomy: number | null
}

interface TrendChartsSectionProps {
  decodedName: string
  isLoading: boolean
  trendData: TrendDatum[]
  frameworkRadarData: Array<{ framework: string; score: number }>
}

export function TrendChartsSection({
  decodedName,
  isLoading,
  trendData,
  frameworkRadarData,
}: TrendChartsSectionProps) {
  const { t } = useTranslation()

  const chartFallback = (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="h-[360px] rounded-2xl border bg-stone-100/70 animate-pulse" />
      <div className="h-[360px] rounded-2xl border bg-stone-100/70 animate-pulse" />
    </div>
  )

  return (
    <DeferredHeavyCharts key={decodedName} ready={!isLoading} fallback={chartFallback}>
      {trendData.length < 2 && (
        <NoticeBanner tone="warning" title={t('profile.trendInsufficientDataTitle')}>
          <p>{t('profile.trendInsufficientDataBody')}</p>
        </NoticeBanner>
      )}
      <Suspense fallback={chartFallback}>
        <CompanyProfileHeavyCharts
          frameworkRadarData={frameworkRadarData}
          trendData={trendData}
          radarTitle={t('profile.radarTitle')}
          trendTitle={t('profile.trendTitle')}
          radarLegend={t('profile.radarLegend')}
          trendLegend={t('profile.trendLegend')}
          noFrameworkResultsLabel={t('profile.noFrameworkResults')}
          scoreLabel={t('common.score')}
          scope1Label={t('companies.scope1')}
          renewableLabel={t('companies.renewable')}
        />
      </Suspense>
    </DeferredHeavyCharts>
  )
}
