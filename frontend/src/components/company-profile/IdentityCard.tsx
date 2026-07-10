import { Building2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Panel } from '@/components/layout/Panel'
import type { CompanyIdentityProvenanceSummary, CompanyMergedResult } from '@/lib/types'
import { metricDisclosureLabel, prettifyToken } from '@/pages/company-profile/utils'

interface IdentityCardProps {
  companyName: string
  identitySummary: CompanyIdentityProvenanceSummary | null
  mergedResult?: CompanyMergedResult | null
}

export function IdentityCard(props: IdentityCardProps) {
  const { companyName, identitySummary, mergedResult } = props
  const { t } = useTranslation()

  return (
    <Panel
      title={(
        <span className="flex items-center gap-2 text-base">
          <Building2 size={16} className="text-indigo-600" />
          {t('profile.identityTitle')}
        </span>
      )}
    >
      <div className="grid min-w-0 gap-4 md:grid-cols-2">
        <div className="min-w-0 rounded-lg border bg-slate-50 px-4 py-3">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            {t('profile.canonicalNameLabel')}
          </p>
          <p className="mt-2 break-words text-sm font-semibold text-slate-900 [overflow-wrap:anywhere]">
            {identitySummary?.canonical_company_name ?? companyName}
          </p>
          {identitySummary?.requested_company_name &&
          identitySummary.requested_company_name !==
            (identitySummary?.canonical_company_name ?? companyName) ? (
            <p className="mt-1 break-words text-xs text-slate-500 [overflow-wrap:anywhere]">
              {identitySummary.requested_company_name} →{' '}
              {identitySummary?.canonical_company_name ?? companyName}
            </p>
          ) : null}
        </div>
        <div className="min-w-0 rounded-lg border bg-slate-50 px-4 py-3">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            {t('profile.latestSourceTypeLabel')}
          </p>
          <p className="mt-2 break-words text-sm font-semibold text-slate-900 [overflow-wrap:anywhere]">
            {identitySummary?.latest_source_document_type ?? '—'}
          </p>
        </div>
        <div className="min-w-0 rounded-lg border bg-slate-50 px-4 py-3">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            {t('profile.aliasConsolidationLabel')}
          </p>
          <p className="mt-2 text-sm font-semibold text-slate-900">
            {identitySummary?.has_alias_consolidation
              ? t('profile.aliasConsolidationYes')
              : t('profile.aliasConsolidationNo')}
          </p>
          <p className="mt-1 break-words text-xs text-slate-500 [overflow-wrap:anywhere]">
            {identitySummary?.consolidated_aliases?.length
              ? identitySummary.consolidated_aliases.join(', ')
              : t('profile.aliasListNone')}
          </p>
        </div>
        <div className="min-w-0 rounded-lg border bg-slate-50 px-4 py-3">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            {t('profile.sourceMergePriorityLabel')}
          </p>
          {identitySummary?.merge_priority_preview ? (
            <>
              <p className="mt-2 break-words text-sm text-slate-700 [overflow-wrap:anywhere]">
                {identitySummary.merge_priority_preview}
              </p>
              {identitySummary.source_priority_preview ? (
                <p className="mt-1 break-words text-xs text-amber-700 [overflow-wrap:anywhere]">{identitySummary.source_priority_preview}</p>
              ) : null}
            </>
          ) : mergedResult && Object.keys(mergedResult.metrics).length > 0 ? (
            <div className="mt-2 space-y-1.5">
              {Object.entries(mergedResult.metrics)
                .filter(([, m]) => m.chosen_source_document_type != null)
                .slice(0, 6)
                .map(([key, m]) => (
                  <div key={key} className="min-w-0 text-xs">
                    <div className="flex min-w-0 items-start justify-between gap-2">
                      <span className="break-words text-slate-600 [overflow-wrap:anywhere]">
                        {metricDisclosureLabel(t, key)}
                      </span>
                      <span className={`shrink-0 rounded px-1.5 py-0.5 font-medium ${m.conflict_detected ? 'bg-amber-50 text-amber-700' : 'bg-slate-100 text-slate-700'}`}>
                        {prettifyToken(m.chosen_source_document_type ?? '')}
                      </span>
                    </div>
                    {m.chosen_pdf_filename ? (
                      <p className="mt-0.5 break-all text-slate-500 [overflow-wrap:anywhere]">
                        {t('profile.mergeChosenFile', { filename: m.chosen_pdf_filename })}
                      </p>
                    ) : m.chosen_source_url ? (
                      <a
                        href={m.chosen_source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-0.5 block break-all text-indigo-600 underline-offset-2 hover:underline [overflow-wrap:anywhere]"
                        title={m.chosen_source_url}
                      >
                        {t('profile.mergeChosenUrl')}
                      </a>
                    ) : null}
                  </div>
                ))}
              {mergedResult.source_count > 1 && (
                <p className="text-xs text-slate-500">
                  {t('profile.provenanceMergeSummary', { count: mergedResult.source_count })}
                </p>
              )}
            </div>
          ) : (
            <p className="mt-2 break-words text-sm text-slate-500 [overflow-wrap:anywhere]">
              {t('profile.sourceMergePriorityReserved')}
            </p>
          )}
        </div>
      </div>
    </Panel>
  )
}
