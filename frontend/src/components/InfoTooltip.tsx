import { Info } from 'lucide-react'
import { useState } from 'react'
import { cn } from '@/lib/utils'

type Props = {
  content: string
  className?: string
}

export function InfoTooltip({ content, className }: Props) {
  const [visible, setVisible] = useState(false)

  return (
    <span
      className={cn('relative inline-flex items-center', className)}
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
      onFocus={() => setVisible(true)}
      onBlur={() => setVisible(false)}
    >
      <button
        type="button"
        tabIndex={0}
        aria-label={content}
        className="ml-1 inline-flex h-4 w-4 items-center justify-center rounded-full text-stone-400 hover:text-stone-600 dark:text-slate-500 dark:hover:text-slate-300 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-amber-600"
        style={{ minHeight: 'unset', minWidth: 'unset' }}
      >
        <Info size={12} aria-hidden="true" />
      </button>
      {visible && (
        <span
          role="tooltip"
          className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 w-56 -translate-x-1/2 rounded-xl border border-stone-200 bg-white px-3 py-2 text-xs leading-5 text-slate-700 shadow-lg dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200"
        >
          {content}
        </span>
      )}
    </span>
  )
}
