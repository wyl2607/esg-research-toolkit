import { AlertCircle, CheckCircle, Clock3 } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Panel, StatCard } from '@/components/layout/Panel'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { BatchStatusResponse } from '@/lib/types'

interface BatchProgressPanelProps {
  batchStatus: BatchStatusResponse
  statusText: (status: BatchStatusResponse['jobs'][number]['status']) => string
  onViewCompanies: () => void
}

export function BatchProgressPanel({
  batchStatus,
  statusText,
  onViewCompanies,
}: BatchProgressPanelProps) {
  const { t } = useTranslation()

  return (
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
          <Button variant="outline" onClick={onViewCompanies}>
            {t('nav.companies')}
          </Button>
        )}
      </div>
    </Panel>
  )
}
