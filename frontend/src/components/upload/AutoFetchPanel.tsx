import { useTranslation } from 'react-i18next'

import { NoticeBanner } from '@/components/NoticeBanner'
import { Panel } from '@/components/layout/Panel'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  type DisclosureFetchRequest,
  type DisclosureFetchResponse,
  type DisclosureMergeMetric,
  type DisclosureReviewRequest,
  type DisclosureSourceHint,
  type PendingDisclosureItem,
} from '@/lib/api'
import {
  DISCLOSURE_REVIEW_METRICS,
  areDisclosureReviewValuesEqual,
  formatDisclosureReviewMetricValue,
} from '@/lib/disclosure-review'
import { localizeErrorMessage } from '@/lib/error-utils'
import type { CompanyESGData } from '@/lib/types'

type AutoFetchSourceType = NonNullable<DisclosureFetchRequest['source_type']>

function sourceHintLabelKey(hint: DisclosureSourceHint): string {
  switch (hint) {
    case 'sec_edgar':
      return 'upload.autoFetchSourceHintSec'
    case 'hkex':
      return 'upload.autoFetchSourceHintHkex'
    case 'csrc':
      return 'upload.autoFetchSourceHintCsrc'
    case 'company_site':
    default:
      return 'upload.autoFetchSourceHintCompanySite'
  }
}

function latestAutoFetchEvidence(row: { extracted_payload: Record<string, unknown> }) {
  const evidenceSummary = row.extracted_payload?.evidence_summary
  if (!Array.isArray(evidenceSummary)) return null
  for (let index = evidenceSummary.length - 1; index >= 0; index -= 1) {
    const item = evidenceSummary[index]
    if (!item || typeof item !== 'object') continue
    if ((item as Record<string, unknown>).metric !== 'auto_disclosure_fetch') continue
    return item as Record<string, unknown>
  }
  return null
}

interface AutoFetchFormState {
  sourceHint: DisclosureSourceHint
  sourceType: AutoFetchSourceType
  sourceUrl: string
  extraHints: DisclosureSourceHint[]
  selectedSourceHints: DisclosureSourceHint[]
}

interface AutoFetchOptionsState {
  sourceHintOptions: DisclosureSourceHint[]
  sourceHintOptionsOrdered: DisclosureSourceHint[]
  lanePriorityOrder: DisclosureSourceHint[]
}

interface AutoFetchStatusState {
  hasLaneStats: boolean
  isAutoFetchPending: boolean
  isAutoFetchError: boolean
  autoFetchError: Error | null
  autoFetchQueuedData?: DisclosureFetchResponse
  isApprovePendingError: boolean
  isRejectPendingError: boolean
  approvePendingError: Error | null
  rejectPendingError: Error | null
  isApprovePending: boolean
  isRejectPending: boolean
}

interface AutoFetchReviewState {
  pendingRows: PendingDisclosureItem[]
  reviewingPending: PendingDisclosureItem | null
  selectedMergeMetrics: DisclosureMergeMetric[]
  existingReport: CompanyESGData | null
}

interface AutoFetchPanelActions {
  onAutoFetch: () => void
  onSourceHintChange: (hint: DisclosureSourceHint) => void
  onSourceTypeChange: (sourceType: AutoFetchSourceType) => void
  onSourceUrlChange: (sourceUrl: string) => void
  onApplyRecommendedLanes: () => void
  onToggleExtraHint: (hint: DisclosureSourceHint, checked: boolean) => void
  onOpenPendingReview: (pendingId: number) => void
  onApprovePending: (pendingId: number, payload?: DisclosureReviewRequest) => void
  onRejectPending: (pendingId: number) => void
  onToggleMergeMetric: (metric: DisclosureMergeMetric, checked: boolean) => void
  onCancelPendingReview: () => void
}

interface AutoFetchPanelProps {
  form: AutoFetchFormState
  options: AutoFetchOptionsState
  status: AutoFetchStatusState
  review: AutoFetchReviewState
  actions: AutoFetchPanelActions
  locale?: string
}

export function AutoFetchPanel({
  form,
  options,
  status,
  review,
  actions,
  locale,
}: AutoFetchPanelProps) {
  const { t } = useTranslation()

  return (
    <Panel
      title={t('upload.autoFetchTitle')}
      description={t('upload.autoFetchDescription')}
      actions={
        <Button
          type="button"
          onClick={actions.onAutoFetch}
          disabled={status.isAutoFetchPending}
          data-testid="auto-fetch-trigger"
        >
          {status.isAutoFetchPending
            ? t('upload.autoFetchRunning')
            : t('upload.autoFetchButton')}
        </Button>
      }
    >
      <div className="space-y-3">
        <label className="flex flex-col gap-1 text-sm text-slate-600" htmlFor="auto-fetch-source-hint">
          <span>{t('upload.autoFetchSourceHintLabel')}</span>
          <select
            id="auto-fetch-source-hint"
            className="h-10 rounded-lg border border-stone-300 bg-white px-3 text-sm text-stone-800 shadow-sm focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-100"
            value={form.sourceHint}
            onChange={(event) => actions.onSourceHintChange(event.target.value as DisclosureSourceHint)}
          >
            {options.sourceHintOptionsOrdered.map((hint) => (
              <option key={hint} value={hint}>
                {t(sourceHintLabelKey(hint))}
              </option>
            ))}
          </select>
        </label>

        <div className="space-y-1 text-sm text-slate-600">
          <span>{t('upload.autoFetchSourceHintsExtraLabel')}</span>
          {status.hasLaneStats ? (
            <div className="rounded-lg border border-amber-200 bg-amber-50/50 p-2 text-xs text-slate-600">
              <p>
                {t('upload.autoFetchRecommendedOrderLabel')}:{' '}
                {options.lanePriorityOrder.map((hint) => t(sourceHintLabelKey(hint))).join(' → ')}
              </p>
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="mt-2"
                onClick={actions.onApplyRecommendedLanes}
                data-testid="auto-fetch-apply-recommended"
              >
                {t('upload.autoFetchApplyRecommendedButton')}
              </Button>
            </div>
          ) : null}
          <div className="grid gap-2 rounded-lg border border-stone-300 bg-white p-3 md:grid-cols-2">
            {options.sourceHintOptionsOrdered.filter((hint) => hint !== form.sourceHint).map((hint) => (
              <label key={hint} className="flex items-center gap-2 text-xs text-slate-700">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-stone-300"
                  data-testid={`auto-fetch-extra-hint-${hint}`}
                  checked={form.extraHints.includes(hint)}
                  onChange={(event) => actions.onToggleExtraHint(hint, event.target.checked)}
                />
                <span>{t(sourceHintLabelKey(hint))}</span>
              </label>
            ))}
          </div>
          <p className="text-xs text-slate-500">
            {t('upload.autoFetchSourceHintsSelected', { count: form.selectedSourceHints.length })}
          </p>
        </div>

        <label className="flex flex-col gap-1 text-sm text-slate-600" htmlFor="auto-fetch-source-type">
          <span>{t('upload.autoFetchSourceTypeLabel')}</span>
          <select
            id="auto-fetch-source-type"
            className="h-10 rounded-lg border border-stone-300 bg-white px-3 text-sm text-stone-800 shadow-sm focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-100"
            value={form.sourceType}
            onChange={(event) => actions.onSourceTypeChange(event.target.value as AutoFetchSourceType)}
          >
            <option value="pdf">{t('upload.autoFetchSourceTypePdf')}</option>
            <option value="html">{t('upload.autoFetchSourceTypeHtml')}</option>
            <option value="filing">{t('upload.autoFetchSourceTypeFiling')}</option>
          </select>
        </label>

        <label className="flex flex-col gap-1 text-sm text-slate-600" htmlFor="auto-fetch-source-url">
          <span>{t('upload.autoFetchSourceLabel')}</span>
          <input
            id="auto-fetch-source-url"
            data-testid="auto-fetch-source-url"
            className="h-10 rounded-lg border border-stone-300 bg-white px-3 text-sm text-stone-800 shadow-sm focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-100"
            value={form.sourceUrl}
            onChange={(event) => actions.onSourceUrlChange(event.target.value)}
            placeholder={t('upload.autoFetchSourcePlaceholder')}
          />
        </label>

        {status.isAutoFetchError ? (
          <NoticeBanner tone="warning" title={t('common.error')}>
            {localizeErrorMessage(t, status.autoFetchError, 'upload.error')}
          </NoticeBanner>
        ) : null}

        {status.isApprovePendingError || status.isRejectPendingError ? (
          <NoticeBanner tone="warning" title={t('common.error')}>
            {localizeErrorMessage(
              t,
              status.approvePendingError ?? status.rejectPendingError,
              'upload.error'
            )}
          </NoticeBanner>
        ) : null}

        {status.autoFetchQueuedData ? (
          <NoticeBanner tone="success" title={t('upload.autoFetchQueuedTitle')}>
            {t('upload.autoFetchQueuedBody', {
              id: status.autoFetchQueuedData.pending.id,
              source: status.autoFetchQueuedData.pending.source_url,
            })}
          </NoticeBanner>
        ) : null}

        {review.pendingRows.length > 0 ? (
          <div className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              {t('upload.pendingQueueTitle')}
            </p>
            {review.pendingRows.map((row) =>
              (() => {
                const evidence = latestAutoFetchEvidence(row)
                const attemptedUrlsRaw = evidence?.attempted_urls
                const attemptedUrls = Array.isArray(attemptedUrlsRaw)
                  ? attemptedUrlsRaw.map((value) => String(value))
                  : []
                const sourceHintsRaw = evidence?.source_hints
                const sourceHints = Array.isArray(sourceHintsRaw)
                  ? sourceHintsRaw
                      .map((hint) => String(hint))
                      .filter((hint): hint is DisclosureSourceHint =>
                        options.sourceHintOptions.includes(hint as DisclosureSourceHint)
                      )
                  : []
                const laneStatsRaw = evidence?.lane_stats
                const laneStats = Array.isArray(laneStatsRaw)
                  ? laneStatsRaw
                      .map((entry) => {
                        if (!entry || typeof entry !== 'object') return null
                        const value = entry as Record<string, unknown>
                        const lane = String(value.lane ?? '')
                        if (!options.sourceHintOptions.includes(lane as DisclosureSourceHint)) return null
                        const attempted = Number(value.attempted ?? 0)
                        const succeeded = Number(value.succeeded ?? 0)
                        const failed = Number(value.failed ?? Math.max(attempted - succeeded, 0))
                        return {
                          lane: lane as DisclosureSourceHint,
                          attempted: Number.isFinite(attempted) ? attempted : 0,
                          succeeded: Number.isFinite(succeeded) ? succeeded : 0,
                          failed: Number.isFinite(failed) ? failed : 0,
                        }
                      })
                      .filter(
                        (
                          value
                        ): value is {
                          lane: DisclosureSourceHint
                          attempted: number
                          succeeded: number
                          failed: number
                        } => value != null
                      )
                  : []
                const successLaneRaw = evidence?.success_lane
                const successLane =
                  typeof successLaneRaw === 'string' &&
                  options.sourceHintOptions.includes(successLaneRaw as DisclosureSourceHint)
                    ? (successLaneRaw as DisclosureSourceHint)
                    : null

                return (
                  <div
                    key={row.id}
                    data-testid="pending-disclosure-item"
                    className="rounded-xl border border-stone-200 bg-white/80 px-3 py-2 text-sm"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium text-slate-700">
                        #{row.id} · {row.source_type.toUpperCase()}
                      </span>
                      <Badge variant="secondary">{row.status}</Badge>
                    </div>
                    <p className="mt-1 break-all text-xs text-slate-500">{row.source_url}</p>
                    <p className="mt-1 text-xs text-slate-400">
                      {new Date(row.fetched_at).toLocaleString(locale)}
                    </p>
                    {sourceHints.length > 0 ? (
                      <p className="mt-1 text-xs text-slate-500">
                        {t('upload.autoFetchLanesUsedLabel')}:{' '}
                        {sourceHints.map((hint) => t(sourceHintLabelKey(hint))).join(', ')}
                      </p>
                    ) : null}
                    {laneStats.length > 0 ? (
                      <div className="mt-1 space-y-1 text-xs text-slate-500">
                        <p>{t('upload.autoFetchLaneStatsLabel')}</p>
                        <ul className="space-y-1 pl-3">
                          {laneStats.map((stat) => (
                            <li key={`${row.id}-${stat.lane}`} data-testid={`pending-lane-stat-${stat.lane}`}>
                              {t('upload.autoFetchLaneStatsLine', {
                                lane: t(sourceHintLabelKey(stat.lane)),
                                succeeded: stat.succeeded,
                                attempted: stat.attempted,
                                failed: stat.failed,
                              })}
                            </li>
                          ))}
                        </ul>
                        {successLane ? (
                          <p className="text-emerald-700">
                            {t('upload.autoFetchSuccessLaneLabel', {
                              lane: t(sourceHintLabelKey(successLane)),
                            })}
                          </p>
                        ) : null}
                      </div>
                    ) : null}
                    {row.review_note ? (
                      <p className="mt-1 text-xs text-slate-500">{row.review_note}</p>
                    ) : null}
                    {attemptedUrls.length > 0 ? (
                      <details className="mt-1 text-xs text-slate-500">
                        <summary className="cursor-pointer select-none">
                          {t('upload.autoFetchAttemptedUrlsToggle', {
                            count: attemptedUrls.length,
                          })}
                        </summary>
                        <ul className="mt-1 space-y-1 break-all pl-4">
                          {attemptedUrls.map((url) => (
                            <li key={`${row.id}-${url}`}>{url}</li>
                          ))}
                        </ul>
                      </details>
                    ) : null}
                    {row.status === 'pending' ? (
                      <div className="mt-2 flex gap-2">
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={() => actions.onOpenPendingReview(row.id)}
                          data-testid={`pending-review-${row.id}`}
                          disabled={status.isApprovePending || status.isRejectPending}
                        >
                          {t('upload.reviewFieldsButton')}
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          data-testid={`pending-approve-${row.id}`}
                          onClick={() =>
                            actions.onApprovePending(row.id, {
                              review_note: 'approved_from_upload_panel',
                            })
                          }
                          disabled={status.isApprovePending || status.isRejectPending}
                        >
                          {t('upload.approveButton')}
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          data-testid={`pending-reject-${row.id}`}
                          onClick={() => actions.onRejectPending(row.id)}
                          disabled={status.isApprovePending || status.isRejectPending}
                        >
                          {t('upload.rejectButton')}
                        </Button>
                      </div>
                    ) : null}
                  </div>
                )
              })()
            )}
          </div>
        ) : null}

        {review.reviewingPending?.status === 'pending' ? (
          <div className="space-y-3 rounded-xl border border-amber-200 bg-amber-50/50 p-3">
            <div className="space-y-1">
              <p className="text-sm font-semibold text-slate-800">{t('upload.reviewDrawerTitle')}</p>
              <p className="text-xs text-slate-600">
                {t('upload.reviewDrawerDescription', { id: review.reviewingPending.id })}
              </p>
              {review.existingReport == null ? (
                <p className="text-xs text-slate-500">{t('upload.reviewBaselineMissing')}</p>
              ) : null}
            </div>
            <div className="space-y-2">
              {DISCLOSURE_REVIEW_METRICS.map((metric) => {
                const extracted = review.reviewingPending!.extracted_payload as Record<string, unknown>
                const nextValue = extracted[metric.key]
                const currentValue = (review.existingReport as unknown as Record<string, unknown> | null)?.[
                  metric.key
                ]
                const selectable = nextValue != null
                const changed = !areDisclosureReviewValuesEqual(
                  currentValue,
                  nextValue,
                  metric.valueKind
                )
                if (!selectable && currentValue == null) return null
                return (
                  <label
                    key={metric.key}
                    className="grid grid-cols-[auto_1fr] gap-3 rounded-lg border border-stone-200 bg-white/80 p-2 text-xs"
                  >
                    <input
                      type="checkbox"
                      className="mt-1 h-4 w-4 rounded border-stone-300"
                      checked={review.selectedMergeMetrics.includes(metric.key)}
                      disabled={!selectable}
                      onChange={(event) => actions.onToggleMergeMetric(metric.key, event.target.checked)}
                    />
                    <div className="space-y-1">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-medium text-slate-700">{t(metric.labelKey)}</span>
                        {changed ? (
                          <Badge variant="secondary" className="bg-amber-100 text-amber-900">
                            {t('upload.reviewChangedBadge')}
                          </Badge>
                        ) : (
                          <Badge variant="secondary">{t('upload.reviewUnchangedBadge')}</Badge>
                        )}
                      </div>
                      <div className="grid gap-1 md:grid-cols-2">
                        <div className="rounded border border-stone-200 bg-stone-50 p-2">
                          <p className="text-[11px] uppercase tracking-wide text-slate-500">
                            {t('upload.reviewCurrentValue')}
                          </p>
                          <p className="text-slate-700">
                            {formatDisclosureReviewMetricValue(
                              currentValue,
                              metric.valueKind,
                              locale ?? 'en-US'
                            )}
                          </p>
                        </div>
                        <div className="rounded border border-stone-200 bg-stone-50 p-2">
                          <p className="text-[11px] uppercase tracking-wide text-slate-500">
                            {t('upload.reviewPendingValue')}
                          </p>
                          <p className="text-slate-700">
                            {formatDisclosureReviewMetricValue(
                              nextValue,
                              metric.valueKind,
                              locale ?? 'en-US'
                            )}
                          </p>
                        </div>
                      </div>
                    </div>
                  </label>
                )
              })}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Button
                type="button"
                data-testid="pending-approve-selected"
                onClick={() =>
                  actions.onApprovePending(review.reviewingPending!.id, {
                    review_note: 'approved_with_selected_metrics',
                    include_metrics:
                      review.selectedMergeMetrics.length > 0 ? review.selectedMergeMetrics : undefined,
                  })
                }
                disabled={status.isApprovePending || review.selectedMergeMetrics.length === 0}
              >
                {t('upload.approveSelectedButton', { count: review.selectedMergeMetrics.length })}
              </Button>
              <Button type="button" variant="outline" onClick={actions.onCancelPendingReview}>
                {t('common.cancel')}
              </Button>
            </div>
          </div>
        ) : null}
      </div>
    </Panel>
  )
}
