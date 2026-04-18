import { useState, useCallback, useEffect } from 'react'
import { useDropzone } from 'react-dropzone'
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  approvePendingDisclosure,
  fetchDisclosure,
  getBatchStatus,
  listPendingDisclosures,
  rejectPendingDisclosure,
  uploadReport,
  uploadReportsBatch,
} from '@/lib/api'
import { ApiError } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { QueryStateCard } from '@/components/QueryStateCard'
import { PageContainer } from '@/components/layout/PageContainer'
import { PageHeader } from '@/components/layout/PageHeader'
import { Panel, FormCard, StatCard } from '@/components/layout/Panel'
import { NoticeBanner } from '@/components/NoticeBanner'
import { FilterBar } from '@/components/FilterBar'
import { Upload, FileText, CheckCircle, AlertCircle, Clock3 } from 'lucide-react'
import type { BatchStatusResponse, CompanyESGData } from '@/lib/types'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { localizeErrorMessage } from '@/lib/error-utils'
import { findNaceOption, NACE_OPTIONS } from '@/lib/nace-codes'

const BATCH_STORAGE_KEY = 'esg_last_batch_id'

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
  const [autoFetchSourceHint, setAutoFetchSourceHint] = useState<
    'company_site' | 'sec_edgar' | 'hkex' | 'csrc'
  >('company_site')
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

  const autoFetchMutation = useMutation({
    mutationFn: () => {
      if (!hasPrefilledGapTarget) throw new Error('Missing company/year prefill')
      return fetchDisclosure({
        company_name: prefilledCompany!,
        report_year: prefilledYearNumber!,
        source_url: autoFetchSourceUrl.trim() || undefined,
        source_type: autoFetchSourceType,
        source_hint: autoFetchSourceHint,
      })
    },
    onSuccess: () => {
      void pendingDisclosuresQuery.refetch()
    },
  })

  const approvePendingMutation = useMutation({
    mutationFn: (pendingId: number) => approvePendingDisclosure(pendingId),
    onSuccess: () => {
      void pendingDisclosuresQuery.refetch()
    },
  })

  const rejectPendingMutation = useMutation({
    mutationFn: (pendingId: number) =>
      rejectPendingDisclosure(pendingId, { review_note: 'Rejected from upload panel' }),
    onSuccess: () => {
      void pendingDisclosuresQuery.refetch()
    },
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

  const fields: [string, string][] = result
    ? [
        [
          t('companies.scope1'),
          result.scope1_co2e_tonnes != null
            ? `${result.scope1_co2e_tonnes.toLocaleString(i18n.resolvedLanguage)} t`
            : '—',
        ],
        [
          t('companies.scope2'),
          result.scope2_co2e_tonnes != null
            ? `${result.scope2_co2e_tonnes.toLocaleString(i18n.resolvedLanguage)} t`
            : '—',
        ],
        [
          t('upload.renewableEnergy'),
          result.renewable_energy_pct != null
            ? `${result.renewable_energy_pct.toFixed(1)}%`
            : '—',
        ],
        [
          t('companies.employees'),
          result.total_employees?.toLocaleString(i18n.resolvedLanguage) ?? '—',
        ],
        [
          t('upload.taxonomyAligned'),
          result.taxonomy_aligned_revenue_pct != null
            ? `${result.taxonomy_aligned_revenue_pct.toFixed(1)}%`
            : '—',
        ],
        [t('common.summary'), result.primary_activities.join(', ') || '—'],
      ]
    : []

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
        <Panel
          title={t('upload.autoFetchTitle')}
          description={t('upload.autoFetchDescription')}
          actions={
            <Button
              type="button"
              onClick={() => autoFetchMutation.mutate()}
              disabled={autoFetchMutation.isPending}
              data-testid="auto-fetch-trigger"
            >
              {autoFetchMutation.isPending
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
                value={autoFetchSourceHint}
                onChange={(event) =>
                  setAutoFetchSourceHint(
                    event.target.value as 'company_site' | 'sec_edgar' | 'hkex' | 'csrc'
                  )
                }
              >
                <option value="company_site">{t('upload.autoFetchSourceHintCompanySite')}</option>
                <option value="sec_edgar">{t('upload.autoFetchSourceHintSec')}</option>
                <option value="hkex">{t('upload.autoFetchSourceHintHkex')}</option>
                <option value="csrc">{t('upload.autoFetchSourceHintCsrc')}</option>
              </select>
            </label>

            <label className="flex flex-col gap-1 text-sm text-slate-600" htmlFor="auto-fetch-source-type">
              <span>{t('upload.autoFetchSourceTypeLabel')}</span>
              <select
                id="auto-fetch-source-type"
                className="h-10 rounded-lg border border-stone-300 bg-white px-3 text-sm text-stone-800 shadow-sm focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-100"
                value={autoFetchSourceType}
                onChange={(event) =>
                  setAutoFetchSourceType(event.target.value as 'pdf' | 'html' | 'filing')
                }
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
                value={autoFetchSourceUrl}
                onChange={(event) => setAutoFetchSourceUrl(event.target.value)}
                placeholder={t('upload.autoFetchSourcePlaceholder')}
              />
            </label>

            {autoFetchMutation.isError ? (
              <NoticeBanner tone="warning" title={t('common.error')}>
                {localizeErrorMessage(t, autoFetchMutation.error, 'upload.error')}
              </NoticeBanner>
            ) : null}

            {approvePendingMutation.isError || rejectPendingMutation.isError ? (
              <NoticeBanner tone="warning" title={t('common.error')}>
                {localizeErrorMessage(
                  t,
                  (approvePendingMutation.error as Error | null) ??
                    (rejectPendingMutation.error as Error | null),
                  'upload.error'
                )}
              </NoticeBanner>
            ) : null}

            {autoFetchMutation.data ? (
              <NoticeBanner tone="success" title={t('upload.autoFetchQueuedTitle')}>
                {t('upload.autoFetchQueuedBody', {
                  id: autoFetchMutation.data.pending.id,
                  source: autoFetchMutation.data.pending.source_url,
                })}
              </NoticeBanner>
            ) : null}

            {pendingDisclosuresQuery.data && pendingDisclosuresQuery.data.length > 0 ? (
              <div className="space-y-2">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  {t('upload.pendingQueueTitle')}
                </p>
                {pendingDisclosuresQuery.data.map((row) => (
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
                      {new Date(row.fetched_at).toLocaleString(i18n.resolvedLanguage)}
                    </p>
                    {row.review_note ? (
                      <p className="mt-1 text-xs text-slate-500">{row.review_note}</p>
                    ) : null}
                    {row.status === 'pending' ? (
                      <div className="mt-2 flex gap-2">
                        <Button
                          type="button"
                          size="sm"
                          data-testid={`pending-approve-${row.id}`}
                          onClick={() => approvePendingMutation.mutate(row.id)}
                          disabled={approvePendingMutation.isPending || rejectPendingMutation.isPending}
                        >
                          {t('upload.approveButton')}
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          data-testid={`pending-reject-${row.id}`}
                          onClick={() => rejectPendingMutation.mutate(row.id)}
                          disabled={approvePendingMutation.isPending || rejectPendingMutation.isPending}
                        >
                          {t('upload.rejectButton')}
                        </Button>
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        </Panel>
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

      {batchStatus && (
        <Panel
          title={t('upload.batchProgress')}
          description={t('upload.kicker')}
          actions={
            <Badge variant="secondary" className="bg-amber-100 text-amber-900">
              {batchStatus.progress_pct.toFixed(0)}%
            </Badge>
          }
        >
          <div className="space-y-4">
            <div className="grid gap-3 md:grid-cols-4">
              <StatCard label={t('upload.queued')} value={batchStatus.queued_jobs} />
              <StatCard label={t('upload.processing')} value={batchStatus.running_jobs} />
              <StatCard label={t('upload.completed')} value={batchStatus.completed_jobs} />
              <StatCard label={t('upload.failed')} value={batchStatus.failed_jobs} />
            </div>
            <div className="space-y-1" role="status" aria-live="polite">
              <div className="flex justify-between text-xs text-slate-600">
                <span>{t('upload.processing')}</span>
                <span>{batchStatus.progress_pct.toFixed(0)}%</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-stone-200" aria-hidden="true">
                <div
                  className="h-2 rounded-full bg-amber-600 transition-all"
                  style={{ width: `${Math.min(batchStatus.progress_pct, 100)}%` }}
                />
              </div>
            </div>
            <div className="max-h-64 space-y-2 overflow-auto">
              {batchStatus.jobs.map((job) => (
                <div
                  key={job.job_id}
                  className="flex items-center justify-between rounded-xl border border-stone-200 bg-white/80 px-3 py-2 text-sm"
                >
                  <div className="truncate pr-4">{job.filename}</div>
                  <div className="flex items-center gap-2">
                    {job.status === 'processing' && (
                      <Clock3 size={14} className="text-amber-600" />
                    )}
                    {job.status === 'completed' && (
                      <CheckCircle size={14} className="text-green-600" />
                    )}
                    {job.status === 'failed' && (
                      <AlertCircle size={14} className="text-red-600" />
                    )}
                    <Badge
                      variant={job.status === 'failed' ? 'destructive' : 'secondary'}
                      className="capitalize"
                    >
                      {statusText(job.status)}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
            {batchStatus.completed_jobs > 0 && (
              <Button variant="outline" onClick={() => navigate('/companies')}>
                {t('nav.companies')}
              </Button>
            )}
          </div>
        </Panel>
      )}

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

      {result && (
        <Panel>
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <CheckCircle size={18} className="text-green-500" />
              <span className="font-semibold">
                {t('upload.success')}: {result.company_name} ({result.report_year})
              </span>
            </div>
            <div className="grid gap-3 text-sm md:grid-cols-2">
              {fields.map(([k, v]) => (
                <div
                  key={k}
                  className="flex justify-between rounded-xl border border-stone-200 bg-white/80 px-3 py-3"
                >
                  <span className="text-slate-500">{k}</span>
                  <Badge variant="secondary" className="bg-stone-100 text-slate-700">
                    {v}
                  </Badge>
                </div>
              ))}
            </div>
            <div className="flex gap-3">
              <Button onClick={() => navigate('/taxonomy')}>{t('dashboard.runTaxonomy')}</Button>
              <Button variant="outline" onClick={() => navigate('/companies')}>
                {t('nav.companies')}
              </Button>
            </div>
          </div>
        </Panel>
      )}
    </PageContainer>
  )
}
