import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

type Width = 'default' | 'narrow' | 'wide'

const WIDTH: Record<Width, string> = {
  default: '',
  narrow: 'max-w-3xl mx-auto',
  wide: 'max-w-none',
}

export function PageContainer({
  children,
  width = 'default',
  className,
}: {
  children: ReactNode
  width?: Width
  className?: string
}) {
  return <div className={cn('space-y-8', WIDTH[width], className)}>{children}</div>
}
