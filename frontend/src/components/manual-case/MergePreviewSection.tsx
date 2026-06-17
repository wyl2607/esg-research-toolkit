import { useMemo, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { GitMerge, Plus, Trash2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { QueryStateCard } from '@/components/QueryStateCard'
import { Panel } from '@/components/layout/Panel'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { previewMerge } from '@/lib/api'
import { localizeErrorMessage } from '@/lib/error-utils'
import type {
  CompanyESGData,
  ManualReportInput,
  MergeMetricDecision,
  MergePreviewResponse,
  MergeSourceInput,
} from '@/lib/types'
import {
  buildMergeSourceId,
  formatMergeValue,
  toMergeSourceInput,
} from '@/components/manual-case/merge-utils'
import {
  asNum,
  asPct,
  metricDisclosureLabel,
  prettifyToken,
} from '@/pages/company-profile/utils'

const MERGED_METRIC_KEYS: Array<keyof CompanyESGData> = [
  'scope1_co2e_tonnes',
  'scope2_co2e_tonnes',
  'scope3_co2e_tonnes',
  'renewable_energy_pct',
  'taxonomy_aligned_revenue_pct',
  'taxonomy_aligned_capex_pct',
  'total_employees',
  'female_pct',
  'energy_consumption_mwh',
  'water_usage_m3',
  'waste_recycled_pct',
  'primary_activities',
]

interface MergePreviewSectionProps {
  currentDraft: ManualReportInput
  savedCompanies: CompanyESGData[]
  companiesLoading: boolean
  companiesError: unknown
  onRetryCompanies: () => void
}

function sourceDocumentTypeLabel(
  t: (key: string) => string,
  sourceDocumentType: string | null | undefined
) {
  if (!sourceDocumentType) return '—'
  const key = `manual.mergePreview.sourceTypes.${sourceDocumentType}`
  const translated = t(key)
  return translated === key ? prettifyToken(sourceDocumentType) : translated
}

function mergeReasonLabel(t: (key: string) => string, mergeReason: string) {
  const key = `manual.mergePreview.reasons.${mergeReason}`
  const translated = t(key)
  return translated === key ? prettifyToken(mergeReason) : translated
}

function formatSummaryMetricValue(
  metricKey: string,
  value: unknown,
  locale: string
) {
  if (value == null) return '—'
  if (metricKey.endsWith('_pct')) return asPct(value as number | null)
  if (metricKey === 'primary_activities') {
    return formatMergeValue(value as string[] | null, locale)
  }
  return asNum(value as number | null, locale)
}

function MergedMetricsSummary({
  preview,
  locale,
}: {
  preview: MergePreviewResponse
  locale: string
}) {
  const { t } = useTranslation()

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {MERGED_METRIC_KEYS.map((metricKey) => {
        const value = preview.merged_metrics[metricKey]
        if (value == null || (Array.isArray(value) && value.length === 0)) {
          return null
        }
        return (
          <div
            key={metricKey}
            className="rounded-lg border bg-slate-50 px-4 py-3"
          >
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              {metricDisclosureLabel(t, metricKey)}
            </p>
            <p className="mt-2 text-sm font-semibold text-slate-900">
              {formatSummaryMetricValue(metricKey, value, locale)}
            </p>
          </div>
        )
      })}
    </div>
  )
}

function DecisionsTable({ decisions }: { decisions: MergeMetricDecision[] }) {
  const { t, i18n } = useTranslation()

  if (decisions.length === 0) {
    return (
      <p className="text-sm text-slate-500">{t('manual.mergePreview.noDecisions')}</p>
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-4 py-3 font-medium">{t('manual.mergePreview.metric')}</th>
            <th className="px-4 py-3 font-medium">{t('manual.mergePreview.selectedValue')}</th>
            <th className="px-4 py-3 font-medium">{t('manual.mergePreview.selectedSource')}</th>
            <th className="px-4 py-3 font-medium">{t('manual.mergePreview.reason')}</th>
            <th className="px-4 py-3 font-medium">{t('manual.mergePreview.conflict')}</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {decisions.map((decision) => (
            <tr key={decision.metric} className="bg-white">
              <td className="px-4 py-3 font-medium text-slate-900">
                {metricDisclosureLabel(t, decision.metric)}
              </td>
              <td className="px-4 py-3 text-slate-700">
                {formatMergeValue(decision.selected_value, i18n.resolvedLanguage)}
              </td>
              <td className="px-4 py-3 text-slate-700">
                <div className="space-y-1">
                  <p>{sourceDocumentTypeLabel(t, decision.selected_source_document_type)}</p>
                  {decision.selected_source_id ? (
                    <p className="font-mono text-xs text-slate-500">
                      {decision.selected_source_id}
                    </p>
                  ) : null}
                </div>
              </td>
              <td className="px-4 py-3 text-slate-700">
                {mergeReasonLabel(t, decision.merge_reason)}
              </td>
              <td className="px-4 py-3">
                {decision.conflict_detected ? (
                  <Badge className="bg-amber-100 text-amber-900 hover:bg-amber-100">
                    {t('manual.mergePreview.conflictYes')}
                  </Badge>
                ) : (
                  <Badge variant="secondary" className="bg-slate-100 text-slate-700">
                    {t('manual.mergePreview.conflictNo')}
                  </Badge>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function MergePreviewSection({
  currentDraft,
  savedCompanies,
  companiesLoading,
  companiesError,
  onRetryCompanies,
}: MergePreviewSectionProps) {
  const { t, i18n } = useTranslation()
  const [sources, setSources] = useState<MergeSourceInput[]>([])

  const anchor = sources[0] ?? null

  const compatibleSavedCompanies = useMemo(() => {
    if (!anchor) return savedCompanies
    return savedCompanies.filter(
      (company) =>
        company.company_name === anchor.company_name &&
        company.report_year === anchor.report_year
    )
  }, [anchor, savedCompanies])

  const previewMutation = useMutation({
    mutationFn: (documents: MergeSourceInput[]) => previewMerge(documents),
  })

  const canAddCurrentDraft =
    currentDraft.company_name.trim().length > 0 &&
    Number.isFinite(currentDraft.report_year) &&
    (!anchor ||
      (currentDraft.company_name.trim() === anchor.company_name &&
        currentDraft.report_year === anchor.report_year))

  const currentDraftSourceId = canAddCurrentDraft
    ? buildMergeSourceId(
        currentDraft.company_name.trim(),
        currentDraft.report_year,
        currentDraft.source_document_type,
        currentDraft.source_url ?? null,
        currentDraft.reporting_period_label ?? null
      )
    : null

  const currentDraftAlreadyAdded =
    currentDraftSourceId != null &&
    sources.some((source) => source.source_id === currentDraftSourceId)

  const addSource = (source: MergeSourceInput) => {
    setSources((current) => {
      if (current.some((item) => item.source_id === source.source_id)) {
        return current
      }
      if (
        current.length > 0 &&
        (current[0].company_name !== source.company_name ||
          current[0].report_year !== source.report_year)
      ) {
        return current
      }
      return [...current, source]
    })
    previewMutation.reset()
  }

  const removeSource = (sourceId: string) => {
    setSources((current) => current.filter((source) => source.source_id !== sourceId))
    previewMutation.reset()
  }

  const handlePreview = () => {
    if (sources.length < 2) return
    previewMutation.mutate(sources)
  }

  return (
    <div className="space-y-4" data-testid="merge-preview-section">
      <Panel
        title={(
          <span className="flex items-center gap-2 text-base">
            <GitMerge size={16} className="text-amber-700" />
            {t('manual.mergePreview.title')}
          </span>
        )}
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-600">{t('manual.mergePreview.subtitle')}</p>

          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="outline"
              disabled={!canAddCurrentDraft || currentDraftAlreadyAdded}
              onClick={() => addSource(toMergeSourceInput(currentDraft))}
            >
              <Plus size={14} className="mr-1.5" />
              {t('manual.mergePreview.addCurrentDraft')}
            </Button>
          </div>

          {anchor ? (
            <p className="text-xs text-slate-500">
              {t('manual.mergePreview.lockedGroup', {
                company: anchor.company_name,
                year: anchor.report_year,
              })}
            </p>
          ) : (
            <p className="text-xs text-slate-500">{t('manual.mergePreview.pickFirstSource')}</p>
          )}

          {sources.length > 0 ? (
            <div className="space-y-2">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                {t('manual.mergePreview.selectedSources', { count: sources.length })}
              </p>
              <div className="space-y-2">
                {sources.map((source) => (
                  <div
                    key={source.source_id}
                    className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-white px-4 py-3"
                    data-testid={`merge-source-${source.source_id}`}
                  >
                    <div className="min-w-0 space-y-1">
                      <p className="text-sm font-medium text-slate-900">
                        {sourceDocumentTypeLabel(t, source.source_document_type)}
                      </p>
                      <p className="font-mono text-xs text-slate-500">{source.source_id}</p>
                      {source.source_url ? (
                        <p className="truncate text-xs text-slate-500">{source.source_url}</p>
                      ) : null}
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="text-slate-500 hover:text-red-600"
                      onClick={() => removeSource(source.source_id ?? '')}
                      aria-label={t('manual.mergePreview.removeSource')}
                    >
                      <Trash2 size={14} />
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-500">{t('manual.mergePreview.noSourcesYet')}</p>
          )}

          <div className="space-y-2 border-t pt-4">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              {t('manual.mergePreview.savedRecords')}
            </p>
            {companiesLoading ? (
              <QueryStateCard
                tone="loading"
                title={t('common.loading')}
                body={t('manual.mergePreview.savedRecords')}
              />
            ) : companiesError ? (
              <QueryStateCard
                tone="error"
                title={t('common.error')}
                body={localizeErrorMessage(t, companiesError, 'common.error')}
                actionLabel={t('errorBoundary.retry')}
                onAction={onRetryCompanies}
              />
            ) : compatibleSavedCompanies.length === 0 ? (
              <p className="text-sm text-slate-500">
                {anchor
                  ? t('manual.mergePreview.noCompatibleRecords')
                  : t('manual.mergePreview.noSavedRecords')}
              </p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {compatibleSavedCompanies.map((company) => {
                  const source = toMergeSourceInput(company)
                  const sourceId = source.source_id ?? ''
                  const alreadyAdded = sources.some((item) => item.source_id === sourceId)
                  return (
                    <button
                      key={sourceId}
                      type="button"
                      disabled={alreadyAdded}
                      onClick={() => addSource(source)}
                      className="rounded-full border bg-white px-3 py-1.5 text-left text-sm leading-5 text-slate-700 hover:border-amber-300 hover:text-amber-800 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {company.company_name} · {company.report_year} ·{' '}
                      {sourceDocumentTypeLabel(t, company.source_document_type)}
                    </button>
                  )
                })}
              </div>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-3 border-t pt-4">
            <Button
              type="button"
              onClick={handlePreview}
              disabled={sources.length < 2 || previewMutation.isPending}
              data-testid="merge-preview-run"
            >
              {previewMutation.isPending
                ? t('manual.mergePreview.running')
                : t('manual.mergePreview.run')}
            </Button>
            {sources.length < 2 ? (
              <p className="text-sm text-slate-500">{t('manual.mergePreview.needTwoSources')}</p>
            ) : null}
          </div>

          {previewMutation.isPending ? (
            <QueryStateCard
              tone="loading"
              title={t('manual.mergePreview.running')}
              body={t('manual.mergePreview.runningBody')}
            />
          ) : previewMutation.error ? (
            <QueryStateCard
              tone="error"
              title={t('manual.mergePreview.errorTitle')}
              body={localizeErrorMessage(t, previewMutation.error, 'common.error')}
              actionLabel={t('errorBoundary.retry')}
              onAction={handlePreview}
            />
          ) : null}
        </div>
      </Panel>

      {previewMutation.data ? (
        <Panel
          title={t('manual.mergePreview.resultsTitle', {
            company: previewMutation.data.company_name,
            year: previewMutation.data.report_year,
          })}
        >
          <div className="space-y-6">
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-slate-900">
                {t('manual.mergePreview.mergedSummary')}
              </h3>
              <MergedMetricsSummary
                preview={previewMutation.data}
                locale={i18n.resolvedLanguage}
              />
            </div>

            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-slate-900">
                {t('manual.mergePreview.decisionsTitle')}
              </h3>
              <DecisionsTable decisions={previewMutation.data.decisions ?? []} />
            </div>

            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-slate-900">
                {t('manual.mergePreview.priorityTitle')}
              </h3>
              <div className="flex flex-wrap gap-2">
                {(previewMutation.data.document_priority ?? []).map((docType, index) => (
                  <Badge
                    key={`${docType}-${index}`}
                    variant="secondary"
                    className="bg-slate-100 text-slate-700"
                  >
                    {index + 1}. {sourceDocumentTypeLabel(t, docType)}
                  </Badge>
                ))}
              </div>
            </div>

            {(previewMutation.data.unresolved_metrics?.length ?? 0) > 0 ? (
              <div className="space-y-3 rounded-lg border border-amber-200 bg-amber-50/70 p-4">
                <h3 className="text-sm font-semibold text-amber-950">
                  {t('manual.mergePreview.unresolvedTitle')}
                </h3>
                <div className="flex flex-wrap gap-2">
                  {previewMutation.data.unresolved_metrics?.map((metricKey) => (
                    <Badge
                      key={metricKey}
                      className="bg-amber-100 text-amber-900 hover:bg-amber-100"
                    >
                      {metricDisclosureLabel(t, metricKey)}
                    </Badge>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-sm text-slate-500">{t('manual.mergePreview.noUnresolved')}</p>
            )}
          </div>
        </Panel>
      ) : null}
    </div>
  )
}