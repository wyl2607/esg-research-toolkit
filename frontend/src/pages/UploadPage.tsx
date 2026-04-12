import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { useMutation, useQuery } from '@tanstack/react-query'
import { getBatchStatus, uploadReport, uploadReportsBatch } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Upload, FileText, CheckCircle, AlertCircle, Clock3 } from 'lucide-react'
import type { BatchStatusResponse, CompanyESGData } from '@/lib/types'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

export function UploadPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [result, setResult] = useState<CompanyESGData | null>(null)
  const [batchId, setBatchId] = useState<string | null>(null)

  const singleMutation = useMutation({
    mutationFn: uploadReport,
    onSuccess: (data) => {
      setBatchId(null)
      setResult(data)
    },
  })

  const batchMutation = useMutation({
    mutationFn: uploadReportsBatch,
    onSuccess: (data) => {
      setResult(null)
      setBatchId(data.batch_id)
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
            ? `${result.scope1_co2e_tonnes.toLocaleString()} t`
            : '—',
        ],
        [
          t('companies.scope2'),
          result.scope2_co2e_tonnes != null
            ? `${result.scope2_co2e_tonnes.toLocaleString()} t`
            : '—',
        ],
        [
          t('upload.renewableEnergy'),
          result.renewable_energy_pct != null
            ? `${result.renewable_energy_pct.toFixed(1)}%`
            : '—',
        ],
        [t('companies.employees'), result.total_employees?.toLocaleString() ?? '—'],
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
  const uploadError = (singleMutation.error as Error | null) ?? (batchMutation.error as Error | null)
  const errMsg = uploadError?.message?.includes('401')
    ? t('errors.unauthorized')
    : uploadError?.message?.includes('422')
      ? t('upload.aiError')
      : t('upload.error')

  const statusText = (status: string) => {
    if (status === 'completed') return t('upload.completed')
    if (status === 'failed') return t('upload.failed')
    if (status === 'queued') return t('upload.queued')
    return t('upload.processing')
  }

  const batchStatus = batchStatusQuery.data

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-slate-900">{t('upload.title')}</h1>

      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors ${
          isDragActive
            ? 'border-indigo-400 bg-indigo-50'
            : 'border-slate-300 hover:border-indigo-300 hover:bg-slate-50'
        }`}
      >
        <input {...getInputProps()} />
        <Upload className="mx-auto mb-4 text-slate-400" size={40} />
        {isDragActive ? (
          <p className="text-indigo-600 font-medium">{t('upload.dropzone')}</p>
        ) : (
          <>
            <p className="text-slate-600 font-medium">{t('upload.dropzoneHint')}</p>
            <p className="text-sm text-slate-400 mt-1">
              {t('upload.singleUpload')} · {t('upload.batchUpload')}
            </p>
          </>
        )}
        {acceptedFiles.length > 0 && (
          <div className="mt-4 space-y-1 text-sm text-slate-600">
            {acceptedFiles.slice(0, 5).map((file) => (
              <div key={file.name} className="flex items-center justify-center gap-2">
                <FileText size={14} />
                {file.name}
              </div>
            ))}
            {acceptedFiles.length > 5 && (
              <div className="text-slate-400">+{acceptedFiles.length - 5} more files</div>
            )}
          </div>
        )}
      </div>

      {isUploading && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3 text-slate-600">
              <div className="animate-spin w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full" />
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
        <Card>
          <CardContent className="pt-6 space-y-4">
            <div className="flex items-center justify-between">
              <div className="font-semibold">{t('upload.batchProgress')}</div>
              <Badge variant="secondary">{batchStatus.progress_pct.toFixed(0)}%</Badge>
            </div>
            <div className="grid grid-cols-4 gap-3 text-sm">
              <div className="border rounded px-3 py-2">{t('upload.queued')}: {batchStatus.queued_jobs}</div>
              <div className="border rounded px-3 py-2">{t('upload.processing')}: {batchStatus.running_jobs}</div>
              <div className="border rounded px-3 py-2 text-green-700">
                {t('upload.completed')}: {batchStatus.completed_jobs}
              </div>
              <div className="border rounded px-3 py-2 text-red-700">{t('upload.failed')}: {batchStatus.failed_jobs}</div>
            </div>
            <div className="space-y-2 max-h-64 overflow-auto">
              {batchStatus.jobs.map((job) => (
                <div key={job.job_id} className="flex items-center justify-between border rounded px-3 py-2 text-sm">
                  <div className="truncate pr-4">{job.filename}</div>
                  <div className="flex items-center gap-2">
                    {job.status === 'processing' && <Clock3 size={14} className="text-amber-600" />}
                    {job.status === 'completed' && <CheckCircle size={14} className="text-green-600" />}
                    {job.status === 'failed' && <AlertCircle size={14} className="text-red-600" />}
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
        <Card>
          <CardContent className="pt-6 space-y-4">
            <div className="flex items-center gap-2">
              <CheckCircle size={18} className="text-green-500" />
              <span className="font-semibold">
                {t('upload.success')}: {result.company_name} ({result.report_year})
              </span>
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              {fields.map(([k, v]) => (
                <div key={k} className="flex justify-between border rounded px-3 py-2">
                  <span className="text-slate-500">{k}</span>
                  <Badge variant="secondary">{v}</Badge>
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
