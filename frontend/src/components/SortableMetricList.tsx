import { useRef, useState } from 'react'
import { GripVertical } from 'lucide-react'
import { MetricCard } from '@/components/MetricCard'

export interface MetricItem {
  id: string
  label: string
  value: string | number
  color?: 'default' | 'green' | 'red' | 'blue'
}

interface Props {
  items: MetricItem[]
  loading?: boolean
  storageKey?: string
  direction?: 'vertical' | 'horizontal'
}

const DRAG_OVER_CLASS = 'ring-2 ring-amber-400 ring-offset-2 rounded-xl'

export function SortableMetricList({ items, loading, storageKey = 'metric-card-order', direction = 'vertical' }: Props) {
  const getInitialOrder = (): string[] => {
    try {
      const saved = localStorage.getItem(storageKey)
      if (saved) {
        const parsed: string[] = JSON.parse(saved)
        // only keep ids that still exist in current items
        const ids = new Set(items.map((i) => i.id))
        const filtered = parsed.filter((id) => ids.has(id))
        // append any new ids not yet in saved order
        items.forEach((i) => { if (!filtered.includes(i.id)) filtered.push(i.id) })
        return filtered
      }
    } catch {
      // ignore
    }
    return items.map((i) => i.id)
  }

  const [order, setOrder] = useState<string[]>(getInitialOrder)
  const dragId = useRef<string | null>(null)
  const dragOverId = useRef<string | null>(null)

  const sorted = order
    .map((id) => items.find((i) => i.id === id))
    .filter((i): i is MetricItem => i !== undefined)

  const persist = (next: string[]) => {
    setOrder(next)
    try { localStorage.setItem(storageKey, JSON.stringify(next)) } catch { /* quota */ }
  }

  const handleDragStart = (id: string) => (e: React.DragEvent) => {
    dragId.current = id
    e.dataTransfer.effectAllowed = 'move'
  }

  const handleDragOver = (id: string) => (e: React.DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    dragOverId.current = id
  }

  const handleDrop = (targetId: string) => (e: React.DragEvent) => {
    e.preventDefault()
    const src = dragId.current
    if (!src || src === targetId) return
    const next = [...order]
    const srcIdx = next.indexOf(src)
    const tgtIdx = next.indexOf(targetId)
    next.splice(srcIdx, 1)
    next.splice(tgtIdx, 0, src)
    persist(next)
    dragId.current = null
    dragOverId.current = null
  }

  const handleDragEnd = () => {
    dragId.current = null
    dragOverId.current = null
  }

  // keyboard reorder: move focused item up/down with Alt+Arrow
  const handleKeyDown = (id: string) => (e: React.KeyboardEvent) => {
    if (!e.altKey) return
    const idx = order.indexOf(id)
    if (e.key === 'ArrowUp' && idx > 0) {
      e.preventDefault()
      const next = [...order]
      ;[next[idx - 1], next[idx]] = [next[idx], next[idx - 1]]
      persist(next)
    } else if (e.key === 'ArrowDown' && idx < order.length - 1) {
      e.preventDefault()
      const next = [...order]
      ;[next[idx], next[idx + 1]] = [next[idx + 1], next[idx]]
      persist(next)
    }
  }

  return (
    <div
      className={
        direction === 'horizontal'
          ? 'grid grid-cols-1 gap-4 md:grid-cols-3'
          : 'flex flex-col gap-3'
      }
      role="list"
      aria-label="Metric cards — drag to reorder"
    >
      {sorted.map((item) => (
        <div
          key={item.id}
          role="listitem"
          draggable
          onDragStart={handleDragStart(item.id)}
          onDragOver={handleDragOver(item.id)}
          onDrop={handleDrop(item.id)}
          onDragEnd={handleDragEnd}
          onKeyDown={handleKeyDown(item.id)}
          tabIndex={0}
          aria-label={`${item.label} — drag or use Alt+Arrow to reorder`}
          className={[
            'group relative cursor-grab rounded-xl active:cursor-grabbing',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-600',
            direction === 'vertical' ? 'flex items-stretch gap-2' : 'flex flex-col',
          ].join(' ')}
        >
          {direction === 'vertical' ? (
            /* vertical: grip on left side */
            <>
              <div
                className="flex shrink-0 items-center justify-center rounded-l-xl border border-r-0 border-stone-200 bg-stone-50 px-1.5 opacity-40 transition-opacity group-hover:opacity-90 group-focus-visible:opacity-90"
                aria-hidden="true"
              >
                <GripVertical size={16} className="text-slate-500" />
              </div>
              <div className="min-w-0 flex-1">
                <MetricCard label={item.label} value={loading ? '…' : item.value} color={item.color} />
              </div>
            </>
          ) : (
            /* horizontal: grip icon floats top-right corner */
            <>
              <div
                className="absolute right-2 top-2 z-10 opacity-0 transition-opacity group-hover:opacity-60 group-focus-visible:opacity-60"
                aria-hidden="true"
              >
                <GripVertical size={14} className="text-slate-400" />
              </div>
              <MetricCard label={item.label} value={loading ? '…' : item.value} color={item.color} />
            </>
          )}
        </div>
      ))}
    </div>
  )
}
