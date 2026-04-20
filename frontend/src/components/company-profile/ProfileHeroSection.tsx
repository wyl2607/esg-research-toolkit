import { ArrowLeft, Download, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

import { NoticeBanner } from '@/components/NoticeBanner'
import { PageHeader } from '@/components/layout/PageHeader'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

interface ProfileHeroSectionProps {
  companyName: string
  latestSourceDocumentType: string | null
  latestYear: number
  latestPeriodLabel: string
  periodsCount: number
  frameworksCount: number
  heroInsightTone: 'success' | 'warning' | 'info'
  heroInsightTitle: string
  heroInsightBody: string
  onExportCsv: () => void
  onExportJson: () => void
}

export function ProfileHeroSection({
  companyName,
  latestSourceDocumentType,
  latestYear,
  latestPeriodLabel,
  periodsCount,
  frameworksCount,
  heroInsightTone,
  heroInsightTitle,
  heroInsightBody,
  onExportCsv,
  onExportJson,
}: ProfileHeroSectionProps) {
  const { t } = useTranslation()

  return (
    <>
      <Link
        to="/companies"
        className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-900"
      >
        <ArrowLeft size={14} />
        {t('profile.backToCompanies')}
      </Link>

      <PageHeader
        title={companyName}
        subtitle={`${latestSourceDocumentType ?? '—'} · ${latestYear}`}
        actions={(
          <div className="flex flex-col items-start gap-3">
            <Badge variant="secondary" className="rounded-full">
              {latestPeriodLabel}
            </Badge>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={onExportCsv}
                aria-label={t('profile.exportCSV')}
              >
                <Download size={14} className="mr-1 shrink-0" aria-hidden="true" />
                {t('profile.exportCSV')}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={onExportJson}
                aria-label={t('profile.exportJSON')}
              >
                <Download size={14} className="mr-1 shrink-0" aria-hidden="true" />
                {t('profile.exportJSON')}
              </Button>
            </div>
          </div>
        )}
        kpis={[
          {
            label: t('profile.heroStatPeriods'),
            value: periodsCount,
          },
          {
            label: t('profile.heroStatFrameworks'),
            value: frameworksCount,
          },
        ]}
      />

      <NoticeBanner
        tone={heroInsightTone}
        title={(
          <span className="inline-flex items-center gap-2">
            <Sparkles size={14} />
            {t('profile.heroLabel')} · {heroInsightTitle}
          </span>
        )}
      >
        <p>{heroInsightBody}</p>
      </NoticeBanner>
    </>
  )
}
