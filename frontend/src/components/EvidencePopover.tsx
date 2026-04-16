import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { ChevronDown, ChevronUp, FileText, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'
import type { EvidenceAnchor } from '@/lib/types'

type EvidencePopoverProps = {
  anchorRect: DOMRect | null
  evidence: EvidenceAnchor
  metricLabel: string
  onClose: () => void
  testId?: string
}

function toConfidenceValue(confidence: EvidenceAnchor['confidence'], score?: number | null) {
  if (typeof score === 'number' && Number.isFinite(score)) {
    return score > 1 ? Math.max(0, Math.min(score / 100, 1)) : Math.max(0, Math.min(score, 1))
  }

  if (typeof confidence === 'number' && Number.isFinite(confidence)) {
    return confidence > 1
      ? Math.max(0, Math.min(confidence / 100, 1))
      : Math.max(0, Math.min(confidence, 1))
  }

  if (typeof confidence === 'string') {
    const normalized = confidence.trim().toLowerCase()
    if (normalized === 'high') return 0.9
    if (normalized === 'medium') return 0.65
    if (normalized === 'low') return 0.35
    const parsed = Number.parseFloat(normalized)
    if (!Number.isNaN(parsed)) {
      return parsed > 1 ? Math.max(0, Math.min(parsed / 100, 1)) : Math.max(0, Math.min(parsed, 1))
    }
  }

  return null
}

function prettifyToken(value: string | null | undefined) {
  if (!value) return null
  return value.replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim()
}

function displayPage(evidence: EvidenceAnchor) {
  return evidence.page ?? evidence.page_number ?? null
}

function displayDocumentTitle(evidence: EvidenceAnchor) {
  return (
    evidence.document_title ??
    evidence.source ??
    evidence.document_short_ref ??
    evidence.source_url ??
    evidence.file_hash ??
    null
  )
}

export function EvidencePopover({
  anchorRect,
  evidence,
  metricLabel,
  onClose,
  testId,
}: EvidencePopoverProps) {
  const { t } = useTranslation()
  const panelRef = useRef<HTMLDivElement | null>(null)
  const closeButtonRef = useRef<HTMLButtonElement | null>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)
  const [expanded, setExpanded] = useState(false)

  const confidenceValue = useMemo(
    () => toConfidenceValue(evidence.confidence, evidence.confidence_score),
    [evidence.confidence, evidence.confidence_score]
  )
  const page = displayPage(evidence)
  const documentTitle = displayDocumentTitle(evidence)
  const extractionMethod = prettifyToken(evidence.extraction_method ?? evidence.source_type)
  const confidenceLabel =
    typeof evidence.confidence === 'string'
      ? prettifyToken(evidence.confidence)
      : confidenceValue != null
        ? `${Math.round(confidenceValue * 100)}%`
        : null

  const position = useMemo(() => {
    const width = Math.min(380, Math.max(window.innerWidth - 24, 280))
    if (!anchorRect) {
      return {
        top: Math.max(24, window.innerHeight / 2 - 180),
        left: Math.max(12, window.innerWidth / 2 - width / 2),
        width,
      }
    }

    const top = Math.min(anchorRect.bottom + 10, window.innerHeight - 24 - 320)
    const left = Math.min(
      Math.max(12, anchorRect.left),
      Math.max(12, window.innerWidth - width - 12)
    )

    return { top, left, width }
  }, [anchorRect])

  useEffect(() => {
    previousFocusRef.current = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null
    const timer = window.setTimeout(() => {
      closeButtonRef.current?.focus()
    }, 0)

    const handleKeydown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        onClose()
        return
      }

      if (event.key !== 'Tab' || !panelRef.current) return

      const focusable = Array.from(
        panelRef.current.querySelectorAll<HTMLElement>(
          'button,[href],input,select,textarea,[tabindex]:not([tabindex="-1"])'
        )
      ).filter((element) => !element.hasAttribute('disabled'))

      if (focusable.length === 0) return

      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      const active = document.activeElement

      if (!event.shiftKey && active === last) {
        event.preventDefault()
        first.focus()
      } else if (event.shiftKey && active === first) {
        event.preventDefault()
        last.focus()
      }
    }

    document.addEventListener('keydown', handleKeydown)
    return () => {
      window.clearTimeout(timer)
      document.removeEventListener('keydown', handleKeydown)
      previousFocusRef.current?.focus()
    }
  }, [onClose])

  return createPortal(
    <>
      <div
        className="fixed inset-0 z-40 bg-slate-950/10"
        aria-hidden="true"
        onClick={onClose}
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={`${testId ?? 'evidence-popover'}-title`}
        data-testid={testId ? `${testId}-popover` : 'evidence-popover'}
        className="fixed z-50 rounded-2xl border border-slate-200 bg-white shadow-2xl"
        style={{
          top: `${position.top}px`,
          left: `${position.left}px`,
          width: `${position.width}px`,
          maxWidth: 'calc(100vw - 24px)',
        }}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 border-b border-slate-200 px-4 py-4">
          <div className="min-w-0">
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-500">
              {t('profile.evidenceSnippetLabel')}
            </p>
            <h3
              id={`${testId ?? 'evidence-popover'}-title`}
              className="mt-1 truncate text-sm font-semibold text-slate-900"
            >
              {t('profile.evidencePopoverTitle', { metric: metricLabel })}
            </h3>
          </div>
          <button
            ref={closeButtonRef}
            type="button"
            className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 text-slate-500 transition hover:bg-slate-100 hover:text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            aria-label={t('profile.evidenceClose')}
            onClick={onClose}
          >
            <X size={16} />
          </button>
        </div>

        <div className="space-y-4 px-4 py-4">
          <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-3">
            <p
              className={cn(
                'text-sm leading-6 text-slate-700',
                !expanded && 'overflow-hidden'
              )}
              style={
                !expanded
                  ? {
                      display: '-webkit-box',
                      WebkitLineClamp: 3,
                      WebkitBoxOrient: 'vertical',
                    }
                  : undefined
              }
            >
              {evidence.snippet ?? t('profile.noEvidence')}
            </p>
            {evidence.snippet && evidence.snippet.length > 180 ? (
              <button
                type="button"
                className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-indigo-700 hover:text-indigo-900"
                onClick={() => setExpanded((value) => !value)}
              >
                {expanded ? (
                  <>
                    <ChevronUp size={14} />
                    {t('profile.evidenceSnippetShowLess')}
                  </>
                ) : (
                  <>
                    <ChevronDown size={14} />
                    {t('profile.evidenceSnippetShowMore')}
                  </>
                )}
              </button>
            ) : null}
          </div>

          <div className="grid gap-3">
            <div className="rounded-xl border border-slate-200 px-3 py-3">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                {t('profile.evidenceDocumentLabel')}
              </p>
              <div className="mt-2 flex items-start gap-2">
                <FileText size={15} className="mt-0.5 shrink-0 text-slate-500" />
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-900">
                    {documentTitle ?? t('profile.sourceFallback')}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    {page != null
                      ? t('profile.evidencePageLabel', { page })
                      : t('profile.evidencePageUnknown')}
                  </p>
                </div>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-xl border border-slate-200 px-3 py-3">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  {t('profile.evidenceMethodLabel')}
                </p>
                <div className="mt-2 inline-flex rounded-full border border-indigo-200 bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-800">
                  {extractionMethod ?? t('profile.evidenceMethodUnknown')}
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 px-3 py-3">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  {t('profile.evidenceConfidenceLabel')}
                </p>
                <p className="mt-2 text-sm font-medium text-slate-900">
                  {confidenceLabel ?? t('profile.evidenceConfidenceUnknown')}
                </p>
                <Progress
                  className="mt-2 h-2 bg-slate-100 [&>div]:bg-emerald-500"
                  value={confidenceValue != null ? Math.round(confidenceValue * 100) : 12}
                  aria-label={t('profile.evidenceConfidenceLabel')}
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </>,
    document.body
  )
}
