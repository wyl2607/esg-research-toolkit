import { useState, useCallback, useEffect } from 'react'
import { useDropzone } from 'react-dropzone'
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  approvePendingDisclosure,
  fetchDisclosure,
  getDisclosureLaneStats,
  getBatchStatus,
  getCompany,
  listCompaniesWithYearCoverage,
  listPendingDisclosures,
  rejectPendingDisclosure,
  uploadReport,
  uploadReportsBatch,
} from '@/lib/api'
import {
  ApiError,
  type DisclosureMergeMetric,
  type DisclosureReviewRequest,
  type DisclosureSourceHint,
} from '@/lib/api'
import { QueryStateCard } from '@/components/QueryStateCard'
import { PageContainer } from '@/components/layout/PageContainer'
import { PageHeader } from '@/components/layout/PageHeader'
import { FormCard } from '@/components/layout/Panel'
import { AutoFetchPanel } from '@/components/upload/AutoFetchPanel'
import { BatchProgressPanel } from '@/components/upload/BatchProgressPanel'
import { NoticeBanner } from '@/components/NoticeBanner'
import { FilterBar } from '@/components/FilterBar'
import { UploadSuccessPanel } from '@/components/upload/UploadSuccessPanel'
import { Upload, FileText } from 'lucide-react'
import type { BatchStatusResponse, CompanyESGData } from '@/lib/types'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { localizeErrorMessage } from '@/lib/error-utils'
import { findNaceOption, NACE_OPTIONS } from '@/lib/nace-codes'
import { DISCLOSURE_REVIEW_METRICS, areDisclosureReviewValuesEqual } from '@/lib/disclosure-review'

const BATCH_STORAGE_KEY = 'esg_last_batch_id'
const SOURCE_HINT_OPTIONS: DisclosureSourceHint[] = ['company_site', 'sec_edgar', 'hkex', 'csrc']

export function UploadPage() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  // Deep-link contract from CompanyYearPicker when a user picks a year that
  // hasn't been imported yet — we show a hint banner so the user knows the
  // upload is expected to close a specific gap.
  const prefilledCompany = searchParams.get('company')
  const prefilledYear = searchParams.get('year')
  const prefilledYearNumber = prefilledYear ? Number(prefilledYear) : null
  const hasPrefilledGapTarget =
    Boolean(prefilledCompany) && prefilledYearNumber != null && Number.isFinite(prefilledYearNumber)
  const [result, setResult] = useState<CompanyESGData | null>(null)
  const [autoFetchSourceUrl, setAutoFetchSourceUrl] = useState('')
  const [autoFetchSourceType, setAutoFetchSourceType] = useState<'pdf' | 'html' | 'filing'>('pdf')
  const [autoFetchSourceHint, setAutoFetchSourceHint] = useState<DisclosureSourceHint>('company_site')
  const [autoFetchExtraHints, setAutoFetchExtraHints] = useState<DisclosureSourceHint[]>([])
  const [reviewingPendingId, setReviewingPendingId] = useState<number | null>(null)
  const [selectedMergeMetrics, setSelectedMergeMetrics] = useState<DisclosureMergeMetric[]>([])
  // Init batch_id from localStorage so progress survives page refresh
  const [batchId, setBatchId] = useState<string | null>(
    () => localStorage.getItem(BATCH_STORAGE_KEY)
  )
  const [industryCode, setIndustryCode] = useState<string>('')

  const selectedIndustry = findNaceOption(industryCode)
  const industryPayload = selectedIndustry
    ? { industryCode: selectedIndustry.code, industrySector: selectedIndustry.sectorEn }
    : undefined

  const singleMutation = useMutation({
    mutationFn: (file: File) => uploadReport(file, industryPayload),
    onSuccess: (data) => {
      setBatchId(null)
      localStorage.removeItem(BATCH_STORAGE_KEY)
      setResult(data)
    },
  })

  const batchMutation = useMutation({
    mutationFn: (files: File[]) => uploadReportsBatch(files, industryPayload),
    onSuccess: (data) => {
      setResult(null)
      setBatchId(data.batch_id)
      localStorage.setItem(BATCH_STORAGE_KEY, data.batch_id)
    },
  })

  const batchStatusQuery = useQuery({
    queryKey: ['batch-status', batchId],
    queryFn: () => getBatchStatus(batchId!),
    enabled: !!batchId,
    refetchInterval: (query) => {
      const data = query.state.data as BatchStatusResponse | undefined
      if (!data) return 1500
      const done = data.completed_jobs + data.failed_jobs
      return done >= data.total_jobs ? false : 1500
    },
  })

  const pendingDisclosuresQuery = useQuery({
    queryKey: ['pending-disclosures', prefilledCompany, prefilledYearNumber],
    queryFn: () =>
      listPendingDisclosures({
        companyName: prefilledCompany ?? undefined,
        reportYear: prefilledYearNumber ?? undefined,
        status: 'pending',
        limit: 20,
      }),
    enabled: hasPrefilledGapTarget,
    refetchInterval: 5000,
  })

  const laneStatsQuery = useQuery({
    queryKey: ['disclosure-lane-stats', prefilledCompany, prefilledYearNumber],
    queryFn: () =>
      getDisclosureLaneStats({
        companyName: prefilledCompany ?? undefined,
        reportYear: prefilledYearNumber ?? undefined,
        windowDays: 30,
      }),
    enabled: hasPrefilledGapTarget,
    staleTime: 60_000,
    refetchInterval: 30_000,
  })

  const companyCoverageQuery = useQuery({
    queryKey: ['company-year-coverage'],
    queryFn: listCompaniesWithYearCoverage,
    enabled: hasPrefilledGapTarget,
    staleTime: 60_000,
  })

  const hasImportedPrefilledYear =
    hasPrefilledGapTarget &&
    (companyCoverageQuery.data ?? []).some(
      (item) =>
        item.company_name.toLowerCase() === prefilledCompany!.toLowerCase() &&
        item.imported_years.includes(prefilledYearNumber!)
    )

  const existingReportQuery = useQuery({
    queryKey: ['company-report', prefilledCompany, prefilledYearNumber],
    enabled: hasImportedPrefilledYear,
    retry: false,
    queryFn: async () => {
      try {
        return await getCompany(prefilledCompany!, prefilledYearNumber!)
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) {
          return null
        }
        throw error
      }
    },
  })

  const autoFetchMutation = useMutation({
    mutationFn: () => {
      if (!hasPrefilledGapTarget) throw new Error('Missing company/year prefill')
      return fetchDisclosure({
        company_name: prefilledCompany!,
        report_year: prefilledYearNumber!,
        source_url: autoFetchSourceUrl.trim() || undefined,
        source_type: autoFetchSourceType,
        source_hint: autoFetchSourceHint,
        source_hints: selectedSourceHints,
      })
    },
    onSuccess: () => {
      void pendingDisclosuresQuery.refetch()
    },
  })

  const approvePendingMutation = useMutation({
    mutationFn: ({
      pendingId,
      payload,
    }: {
      pendingId: number
      payload?: { review_note?: string; include_metrics?: DisclosureMergeMetric[] }
    }) => approvePendingDisclosure(pendingId, payload ?? {}),
    onSuccess: () => {
      setReviewingPendingId(null)
      setSelectedMergeMetrics([])
      void pendingDisclosuresQuery.refetch()
    },
  })

  const rejectPendingMutation = useMutation({
    mutationFn: (pendingId: number) =>
      rejectPendingDisclosure(pendingId, { review_note: 'Rejected from upload panel' }),
    onSuccess: () => {
      setReviewingPendingId(null)
      setSelectedMergeMetrics([])
      void pendingDisclosuresQuery.refetch()
    },
  })

  const pendingRows = pendingDisclosuresQuery.data ?? []
  const reviewingPending = pendingRows.find((row) => row.id === reviewingPendingId) ?? null

  const lanePriorityOrder = laneStatsQuery.data?.recommended_lane_order ?? []
  const sourceHintOptionsOrdered = [...SOURCE_HINT_OPTIONS].sort((a, b) => {
    const rankA = lanePriorityOrder.indexOf(a)
    const rankB = lanePriorityOrder.indexOf(b)
    const normalizedA = rankA === -1 ? Number.POSITIVE_INFINITY : rankA
    const normalizedB = rankB === -1 ? Number.POSITIVE_INFINITY : rankB
    if (normalizedA !== normalizedB) return normalizedA - normalizedB
    return a.localeCompare(b)
  })

  // Clear stored batch_id once batch fully completes
  useEffect(() => {
    if (!batchId) return
    const data = batchStatusQuery.data
    if (!data) return
    const done = data.completed_jobs + data.failed_jobs
    if (done >= data.total_jobs && data.total_jobs > 0) {
      localStorage.removeItem(BATCH_STORAGE_KEY)
    }
  }, [batchId, batchStatusQuery.data])

  const openPendingReview = (pendingId: number) => {
    const row = pendingRows.find((item) => item.id === pendingId)
    if (!row) return

    const extracted = row.extracted_payload as Record<string, unknown>
    const current = existingReportQuery.data as Record<string, unknown> | null
    let defaults = DISCLOSURE_REVIEW_METRICS.filter((metric) => {
      const nextValue = extracted[metric.key]
      if (nextValue == null) return false
      return !areDisclosureReviewValuesEqual(current?.[metric.key], nextValue, metric.valueKind)
    }).map((metric) => metric.key)

    if (defaults.length === 0) {
      defaults = DISCLOSURE_REVIEW_METRICS.filter((metric) => extracted[metric.key] != null).map(
        (metric) => metric.key
      )
    }

    setReviewingPendingId(pendingId)
    setSelectedMergeMetrics(defaults)
  }

  const toggleMergeMetric = (metric: DisclosureMergeMetric, checked: boolean) => {
    setSelectedMergeMetrics((prev) => {
      if (checked) {
        if (prev.includes(metric)) return prev
        return [...prev, metric]
      }
      return prev.filter((item) => item !== metric)
    })
  }

  const selectedSourceHints = [autoFetchSourceHint, ...autoFetchExtraHints].filter(
    (hint, index, hints) => hints.indexOf(hint) === index
  )

  const toggleExtraHint = (hint: DisclosureSourceHint, checked: boolean) => {
    setAutoFetchExtraHints((prev) => {
      if (checked) {
        if (prev.includes(hint) || hint === autoFetchSourceHint) return prev
        return [...prev, hint]
      }
      return prev.filter((item) => item !== hint)
    })
  }

  const applyRecommendedLanes = () => {
    if (!lanePriorityOrder.length) return
    const nextPrimary = lanePriorityOrder[0]
    const nextExtras = lanePriorityOrder.slice(1).filter((hint) => SOURCE_HINT_OPTIONS.includes(hint))
    setAutoFetchSourceHint(nextPrimary)
    setAutoFetchExtraHints(nextExtras)
  }

  const handleAutoFetch = () => autoFetchMutation.mutate()

  const handleAutoFetchSourceHintChange = (nextHint: DisclosureSourceHint) => {
    setAutoFetchSourceHint(nextHint)
    setAutoFetchExtraHints((prev) => prev.filter((hint) => hint !== nextHint))
  }

  const handleApprovePending = (pendingId: number, payload?: DisclosureReviewRequest) => {
    approvePendingMutation.mutate({ pendingId, payload })
  }

  const handleRejectPending = (pendingId: number) => {
    rejectPendingMutation.mutate(pendingId)
  }

  const handleCancelPendingReview = () => {
    setReviewingPendingId(null)
    setSelectedMergeMetrics([])
  }

  const onDrop = useCallback(
    (files: File[]) => {
      if (!files.length) return
      if (files.length === 1) {
        singleMutation.mutate(files[0])
      } else {
        batchMutation.mutate(files)
      }
    },
    [singleMutation, batchMutation]
  )

  const { getRootProps, getInputProps, isDragActive, acceptedFiles } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 20,
    multiple: true,
  })

  const isUploading = singleMutation.isPending || batchMutation.isPending
  const uploadError =
    (singleMutation.error as Error | null) ?? (batchMutation.error as Error | null)
  const errMsg =
    uploadError instanceof ApiError && uploadError.status === 422
      ? t('upload.aiError')
      : localizeErrorMessage(t, uploadError, 'upload.error')

  const statusText = (status: string) => {
    if (status === 'completed') return t('upload.completed')
    if (status === 'failed') return t('upload.failed')
    if (status === 'queued') return t('upload.queued')
    return t('upload.processing')
  }

  const batchStatus = batchStatusQuery.data

  return (
    <PageContainer>
      <PageHeader title={t('upload.title')} subtitle={t('upload.subtitle')} />

      {prefilledCompany && prefilledYear ? (
        <NoticeBanner tone="info" title={t('upload.gapBannerTitle')}>
          {t('upload.gapBannerBody', { company: prefilledCompany, year: prefilledYear })}
        </NoticeBanner>
      ) : null}

      {hasPrefilledGapTarget ? (
        <AutoFetchPanel
          form={{
            sourceHint: autoFetchSourceHint,
            sourceType: autoFetchSourceType,
            sourceUrl: autoFetchSourceUrl,
            extraHints: autoFetchExtraHints,
            selectedSourceHints,
          }}
          options={{
            sourceHintOptions: SOURCE_HINT_OPTIONS,
            sourceHintOptionsOrdered,
            lanePriorityOrder,
          }}
          status={{
            hasLaneStats: Boolean(laneStatsQuery.data?.lanes?.length),
            isAutoFetchPending: autoFetchMutation.isPending,
            isAutoFetchError: autoFetchMutation.isError,
            autoFetchError: autoFetchMutation.error as Error | null,
            autoFetchQueuedData: autoFetchMutation.data,
            isApprovePendingError: approvePendingMutation.isError,
            isRejectPendingError: rejectPendingMutation.isError,
            approvePendingError: approvePendingMutation.error as Error | null,
            rejectPendingError: rejectPendingMutation.error as Error | null,
            isApprovePending: approvePendingMutation.isPending,
            isRejectPending: rejectPendingMutation.isPending,
          }}
          review={{
            pendingRows,
            reviewingPending,
            selectedMergeMetrics,
            existingReport: existingReportQuery.data ?? null,
          }}
          actions={{
            onAutoFetch: handleAutoFetch,
            onSourceHintChange: handleAutoFetchSourceHintChange,
            onSourceTypeChange: setAutoFetchSourceType,
            onSourceUrlChange: setAutoFetchSourceUrl,
            onApplyRecommendedLanes: applyRecommendedLanes,
            onToggleExtraHint: toggleExtraHint,
            onOpenPendingReview: openPendingReview,
            onApprovePending: handleApprovePending,
            onRejectPending: handleRejectPending,
            onToggleMergeMetric: toggleMergeMetric,
            onCancelPendingReview: handleCancelPendingReview,
          }}
          locale={i18n.resolvedLanguage}
        />
      ) : null}

      <NoticeBanner tone="warning">{t('upload.supportedHint')}</NoticeBanner>

      <FilterBar>
        <FilterBar.Field label={t('upload.industryLabel')} htmlFor="upload-industry-code">
          <select
            id="upload-industry-code"
            className="h-10 w-full rounded-xl border border-stone-200 bg-white px-3 text-sm"
            value={industryCode}
            onChange={(e) => setIndustryCode(e.target.value)}
          >
            <option value="">{t('upload.industryNone')}</option>
            {NACE_OPTIONS.map((option) => (
              <option key={option.code} value={option.code}>
                {option.code} —{' '}
                {i18n.resolvedLanguage?.startsWith('de') ? option.sectorDe : option.sectorEn}
              </option>
            ))}
          </select>
          <p className="text-xs text-stone-500">{t('upload.industryHint')}</p>
        </FilterBar.Field>
      </FilterBar>

      <div
        {...getRootProps()}
        className={`editorial-panel cursor-pointer border-2 border-dashed p-12 text-center transition-colors ${
          isDragActive
            ? 'border-amber-500 bg-amber-50/80'
            : 'border-stone-300 hover:border-amber-400 hover:bg-amber-50/60'
        }`}
      >
        <input {...getInputProps({ 'aria-label': t('upload.dropzoneHint') })} />
        <Upload className="mx-auto mb-4 text-amber-700" size={40} />
        {isDragActive ? (
          <p className="font-medium text-amber-800">{t('upload.dropzone')}</p>
        ) : (
          <>
            <p className="font-medium text-slate-700">{t('upload.dropzoneHint')}</p>
            <p className="mt-1 text-sm text-slate-500">
              {t('upload.singleUpload')} · {t('upload.batchUpload')}
            </p>
          </>
        )}
        {acceptedFiles.length > 0 && (
          <div className="mt-4 space-y-1 text-sm text-slate-700">
            {acceptedFiles.slice(0, 5).map((file) => (
              <div key={file.name} className="flex items-center justify-center gap-2">
                <FileText size={14} />
                {file.name}
              </div>
            ))}
            {acceptedFiles.length > 5 && (
              <div className="text-slate-400">
                {t('upload.moreFiles', { count: acceptedFiles.length - 5 })}
              </div>
            )}
          </div>
        )}
      </div>

      {isUploading && (
        <FormCard className="border-amber-200/70">
          <div className="flex items-center gap-3 text-slate-600">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-amber-600 border-t-transparent" />
            {singleMutation.isPending ? t('upload.uploading') : t('upload.processing')}
          </div>
        </FormCard>
      )}

      {uploadError && (
        <NoticeBanner tone="warning" title={t('common.error')}>
          {errMsg}
        </NoticeBanner>
      )}

      {batchStatus ? (
        <BatchProgressPanel
          batchStatus={batchStatus}
          statusText={statusText}
          onViewCompanies={() => navigate('/companies')}
        />
      ) : null}

      {batchStatusQuery.isLoading && batchId && !batchStatus ? (
        <QueryStateCard
          tone="loading"
          title={t('common.loading')}
          body={t('upload.batchProgress')}
          className="max-w-2xl"
        />
      ) : null}

      {batchStatusQuery.isError ? (
        <QueryStateCard
          tone="error"
          title={t('common.error')}
          body={localizeErrorMessage(t, batchStatusQuery.error, 'common.error')}
          actionLabel={t('errorBoundary.retry')}
          onAction={() => void batchStatusQuery.refetch()}
          className="max-w-2xl"
        />
      ) : null}

      {result ? <UploadSuccessPanel result={result} /> : null}
    </PageContainer>
  )
}
