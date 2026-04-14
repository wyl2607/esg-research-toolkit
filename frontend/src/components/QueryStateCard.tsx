import { AlertTriangle, FileSearch, LoaderCircle } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

type QueryStateTone = 'loading' | 'empty' | 'error'

interface QueryStateCardProps {
  tone: QueryStateTone
  title: string
  body: string
  actionLabel?: string
  onAction?: () => void
  className?: string
}

const toneStyles: Record<QueryStateTone, string> = {
  loading: 'border-sky-200 bg-sky-50/80 text-sky-950',
  empty: 'border-stone-200 bg-stone-50/80 text-stone-900',
  error: 'border-red-200 bg-red-50/80 text-red-950',
}

function ToneIcon({ tone }: { tone: QueryStateTone }) {
  if (tone === 'loading') {
    return <LoaderCircle className="animate-spin text-sky-700" size={18} aria-hidden="true" />
  }
  if (tone === 'error') {
    return <AlertTriangle className="text-red-700" size={18} aria-hidden="true" />
  }
  return <FileSearch className="text-stone-700" size={18} aria-hidden="true" />
}

export function QueryStateCard({
  tone,
  title,
  body,
  actionLabel,
  onAction,
  className,
}: QueryStateCardProps) {
  return (
    <div
      className={cn(
        'rounded-2xl border p-5 shadow-sm ring-1 ring-black/5',
        toneStyles[tone],
        className
      )}
      role={tone === 'error' ? 'alert' : 'status'}
      aria-live={tone === 'error' ? 'assertive' : 'polite'}
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5 rounded-full bg-white/80 p-2 shadow-sm ring-1 ring-black/5">
          <ToneIcon tone={tone} />
        </div>
        <div className="min-w-0 space-y-1">
          <p className="text-sm font-semibold tracking-tight">{title}</p>
          <p className="text-sm leading-6 text-current/80">{body}</p>
          {actionLabel && onAction ? (
            <div className="pt-2">
              <Button
                type="button"
                variant="outline"
                className="rounded-xl border-current/15 bg-white/85 hover:bg-white"
                onClick={onAction}
              >
                {actionLabel}
              </Button>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}
