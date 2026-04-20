import { Building2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Panel } from '@/components/layout/Panel'
import type { CompanyIdentityProvenanceSummary } from '@/lib/types'

interface IdentityCardProps {
  companyName: string
  identitySummary: CompanyIdentityProvenanceSummary | null
}

export function IdentityCard(props: IdentityCardProps) {
  const { companyName, identitySummary } = props
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
      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border bg-slate-50 px-4 py-3">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            {t('profile.canonicalNameLabel')}
          </p>
          <p className="mt-2 text-sm font-semibold text-slate-900">
            {identitySummary?.canonical_company_name ?? companyName}
          </p>
          {identitySummary?.requested_company_name &&
          identitySummary.requested_company_name !==
            (identitySummary?.canonical_company_name ?? companyName) ? (
            <p className="mt-1 text-xs text-slate-500">
              {identitySummary.requested_company_name} →{' '}
              {identitySummary?.canonical_company_name ?? companyName}
            </p>
          ) : null}
        </div>
        <div className="rounded-lg border bg-slate-50 px-4 py-3">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            {t('profile.latestSourceTypeLabel')}
          </p>
          <p className="mt-2 text-sm font-semibold text-slate-900">
            {identitySummary?.latest_source_document_type ?? '—'}
          </p>
        </div>
        <div className="rounded-lg border bg-slate-50 px-4 py-3">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            {t('profile.aliasConsolidationLabel')}
          </p>
          <p className="mt-2 text-sm font-semibold text-slate-900">
            {identitySummary?.has_alias_consolidation
              ? t('profile.aliasConsolidationYes')
              : t('profile.aliasConsolidationNo')}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {identitySummary?.consolidated_aliases?.length
              ? identitySummary.consolidated_aliases.join(', ')
              : t('profile.aliasListNone')}
          </p>
        </div>
        <div className="rounded-lg border bg-slate-50 px-4 py-3">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            {t('profile.sourceMergePriorityLabel')}
          </p>
          <p className="mt-2 text-sm text-slate-700">
            {identitySummary?.merge_priority_preview ?? t('profile.sourceMergePriorityReserved')}
          </p>
          {identitySummary?.source_priority_preview ? (
            <p className="mt-1 text-xs text-amber-700">{identitySummary.source_priority_preview}</p>
          ) : null}
        </div>
      </div>
    </Panel>
  )
}
