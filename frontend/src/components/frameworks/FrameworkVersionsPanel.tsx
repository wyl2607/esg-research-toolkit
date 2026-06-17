import { useTranslation } from 'react-i18next'

import { QueryStateCard } from '@/components/QueryStateCard'
import { Panel } from '@/components/layout/Panel'
import { Badge } from '@/components/ui/badge'
import type { FrameworkVersionInfo } from '@/lib/api'
import { localizeErrorMessage } from '@/lib/error-utils'

const FRAMEWORK_COLORS: Record<string, string> = {
  eu_taxonomy: '#b45309',
  csrc_2023: '#9a3412',
  csrd: '#3f6212',
  sec_climate: '#1d4ed8',
  gri_universal: '#7c3aed',
  sasb_standards: '#0f766e',
}

interface FrameworkVersionsPanelProps {
  versions: FrameworkVersionInfo[] | undefined
  isLoading: boolean
  error: Error | null
  onRetry?: () => void
}

export function FrameworkVersionsPanel({
  versions,
  isLoading,
  error,
  onRetry,
}: FrameworkVersionsPanelProps) {
  const { t } = useTranslation()

  if (isLoading) {
    return (
      <QueryStateCard
        tone="loading"
        title={t('common.loading')}
        body={t('frameworks.versions.loading')}
        className="max-w-2xl"
      />
    )
  }

  if (error) {
    return (
      <QueryStateCard
        tone="error"
        title={t('common.error')}
        body={localizeErrorMessage(t, error, 'common.error')}
        actionLabel={onRetry ? t('errorBoundary.retry') : undefined}
        onAction={onRetry}
        className="max-w-2xl"
      />
    )
  }

  if (!versions || versions.length === 0) {
    return (
      <QueryStateCard
        tone="empty"
        title={t('common.noData')}
        body={t('frameworks.versions.empty')}
        className="max-w-2xl"
      />
    )
  }

  return (
    <Panel
      title={t('frameworks.versions.title')}
      description={t('frameworks.versions.subtitle')}
    >
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-stone-200 text-slate-500">
              <th className="py-1.5 pr-3 text-left font-medium">
                {t('frameworks.versions.frameworkId')}
              </th>
              <th className="py-1.5 pr-3 text-left font-medium">
                {t('frameworks.versions.displayName')}
              </th>
              <th className="py-1.5 text-left font-medium">
                {t('frameworks.versions.frameworkVersion')}
              </th>
            </tr>
          </thead>
          <tbody>
            {versions.map((version) => {
              const color = FRAMEWORK_COLORS[version.framework_id] ?? '#b45309'

              return (
                <tr
                  key={`${version.framework_id}-${version.framework_version}`}
                  className="border-b border-stone-100 last:border-0"
                >
                  <td className="py-2 pr-3">
                    <span className="inline-flex items-center gap-1.5 font-medium text-slate-700">
                      <span
                        className="inline-block h-2.5 w-2.5 shrink-0 rounded-full"
                        style={{ background: color }}
                        aria-hidden="true"
                      />
                      <code className="rounded bg-stone-100 px-1.5 py-0.5 font-mono text-[11px] text-slate-600">
                        {version.framework_id}
                      </code>
                    </span>
                  </td>
                  <td className="py-2 pr-3 text-slate-600">{version.display_name}</td>
                  <td className="py-2">
                    <Badge variant="outline" className="font-mono text-[10px]">
                      {version.framework_version}
                    </Badge>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </Panel>
  )
}