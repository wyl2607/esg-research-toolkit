import { useMemo, useRef, useState } from 'react'
import { ChevronRight } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { EvidencePopover } from '@/components/EvidencePopover'
import { cn } from '@/lib/utils'
import type { EvidenceAnchor } from '@/lib/types'

type EvidenceBadgeProps = {
  evidence: EvidenceAnchor | null | undefined
  metricLabel: string
  fallbackFramework?: string | null
  fallbackPeriodLabel?: string | null
  testId?: string
  className?: string
}

function prettifyToken(value: string | null | undefined) {
  if (!value) return null
  return value.replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim()
}

function truncateDocumentRef(value: string | null | undefined) {
  if (!value) return null
  const normalized = value
    .replace(/^https?:\/\//, '')
    .replace(/\/$/, '')
    .replace(/[_-]+/g, ' ')
    .replace(/\.[a-z0-9]{2,4}$/i, '')
    .trim()

  if (normalized.length <= 22) return normalized
  return `${normalized.slice(0, 19).trimEnd()}…`
}

function documentReference(evidence: EvidenceAnchor | null | undefined) {
  if (!evidence) return null
  return (
    evidence.document_short_ref ??
    truncateDocumentRef(evidence.document_title) ??
    truncateDocumentRef(evidence.source) ??
    truncateDocumentRef(evidence.source_url) ??
    truncateDocumentRef(evidence.file_hash) ??
    null
  )
}

export function EvidenceBadge({
  evidence,
  metricLabel,
  fallbackFramework,
  fallbackPeriodLabel,
  testId,
  className,
}: EvidenceBadgeProps) {
  const { t } = useTranslation()
  const triggerRef = useRef<HTMLButtonElement | null>(null)
  const [open, setOpen] = useState(false)
  const [anchorRect, setAnchorRect] = useState<DOMRect | null>(null)

  const badgeLabel = useMemo(() => {
    if (!evidence) return null

    const frameworkLabel = prettifyToken(
      evidence.framework ?? evidence.source_type ?? fallbackFramework
    )
    const periodLabel =
      evidence.reporting_period_label ?? evidence.period_label ?? fallbackPeriodLabel ?? null
    const docRef = documentReference(evidence)

    return [frameworkLabel, periodLabel, docRef]
      .filter((value): value is string => Boolean(value))
      .join(' · ')
  }, [evidence, fallbackFramework, fallbackPeriodLabel])

  if (!evidence || !badgeLabel) {
    return (
      <span
        data-testid={testId}
        className={cn(
          'inline-flex rounded-full border border-slate-300 bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700',
          className
        )}
      >
        {t('profile.evidenceNotDisclosed')}
      </span>
    )
  }

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        data-testid={testId}
        className={cn(
          'inline-flex items-center gap-1 rounded-full border border-indigo-200 bg-indigo-50 px-2.5 py-1 text-left text-xs font-medium text-indigo-800 transition hover:border-indigo-300 hover:bg-indigo-100 focus:outline-none focus:ring-2 focus:ring-indigo-500',
          className
        )}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-label={t('profile.evidenceOpenLabel', { metric: metricLabel })}
        onClick={() => {
          setAnchorRect(triggerRef.current?.getBoundingClientRect() ?? null)
          setOpen(true)
        }}
      >
        <span className="truncate">{badgeLabel}</span>
        <ChevronRight size={13} className="shrink-0" />
      </button>

      {open ? (
        <EvidencePopover
          anchorRect={anchorRect}
          evidence={evidence}
          metricLabel={metricLabel}
          onClose={() => setOpen(false)}
          testId={testId}
        />
      ) : null}
    </>
  )
}
