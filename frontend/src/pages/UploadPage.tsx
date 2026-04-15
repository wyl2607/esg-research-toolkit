import { useState, useCallback, useEffect } from 'react'
import { useDropzone } from 'react-dropzone'
import { useMutation, useQuery } from '@tanstack/react-query'
import { getBatchStatus, uploadReport, uploadReportsBatch } from '@/lib/api'
import { ApiError } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Upload, FileText, CheckCircle, AlertCircle, Clock3 } from 'lucide-react'
import type { BatchStatusResponse, CompanyESGData } from '@/lib/types'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { localizeErrorMessage } from '@/lib/error-utils'
import { findNaceOption, NACE_OPTIONS } from '@/lib/nace-codes'

const BATCH_STORAGE_KEY = 'esg_last_batch_id'

export function UploadPage() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const [result, setResult] = useState<CompanyESGData | null>(null)
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
    <div className="space-y-8">
      <div className="space-y-2">
        <p className="section-kicker">{t('upload.kicker')}</p>
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-2">
            <h1 className="text-3xl font-semibold text-slate-900">{t('upload.title')}</h1>
            <p className="max-w-3xl text-sm leading-6 text-slate-600">
              {t('upload.subtitle')}
            </p>
          </div>
          <div className="max-w-sm rounded-2xl border border-amber-200 bg-amber-50/90 px-4 py-4 text-sm leading-6 text-amber-900">
            {t('upload.supportedHint')}
          </div>
        </div>
      </div>

      <div className="surface-card space-y-2">
        <label htmlFor="upload-industry-code" className="text-sm font-medium text-stone-700">
          {t('upload.industryLabel')}
        </label>
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
      </div>

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
        <Card className="surface-card border-amber-200/70">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3 text-slate-600">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-amber-600 border-t-transparent" />
              {singleMutation.isPending ? t('upload.uploading') : t('upload.processing')}
            </div>
          </CardContent>
        </Card>
      )}

      {uploadError && (
        <Card className="border-red-200">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-red-600">
              <AlertCircle size={16} />
              {errMsg}
            </div>
          </CardContent>
        </Card>
      )}

      {batchStatus && (
        <Card className="surface-card">
          <CardContent className="space-y-4 pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="section-kicker">{t('upload.kicker')}</p>
                <div className="font-semibold text-slate-900">{t('upload.batchProgress')}</div>
              </div>
              <Badge variant="secondary" className="bg-amber-100 text-amber-900">
                {batchStatus.progress_pct.toFixed(0)}%
              </Badge>
            </div>
            <div className="grid gap-3 text-sm md:grid-cols-4">
              <div className="rounded-xl border border-stone-200 bg-white/70 px-3 py-3">
                {t('upload.queued')}: {batchStatus.queued_jobs}
              </div>
              <div className="rounded-xl border border-stone-200 bg-white/70 px-3 py-3">
                {t('upload.processing')}: {batchStatus.running_jobs}
              </div>
              <div className="rounded-xl border border-green-200 bg-green-50/70 px-3 py-3 text-green-700">
                {t('upload.completed')}: {batchStatus.completed_jobs}
              </div>
              <div className="rounded-xl border border-red-200 bg-red-50/70 px-3 py-3 text-red-700">
                {t('upload.failed')}: {batchStatus.failed_jobs}
              </div>
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
          </CardContent>
        </Card>
      )}

      {result && (
        <Card className="surface-card">
          <CardContent className="space-y-4 pt-6">
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
          </CardContent>
        </Card>
      )}
    </div>
  )
}
