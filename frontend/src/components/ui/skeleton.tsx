import React from 'react'

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  count?: number
  height?: string | number
  width?: string | number
  circle?: boolean
}

export function Skeleton({
  count = 1,
  height = '1rem',
  width = '100%',
  circle = false,
  className = '',
  ...props
}: SkeletonProps) {
  const heightValue = typeof height === 'number' ? `${height}px` : height
  const widthValue = typeof width === 'number' ? `${width}px` : width

  const items = Array.from({ length: count }, (_, i) => (
    <div
      key={i}
      style={{
        height: heightValue,
        width: widthValue,
        borderRadius: circle ? '50%' : '0.375rem',
      }}
      className={`animate-pulse bg-slate-200 dark:bg-slate-700 ${className}`}
      {...props}
    />
  ))

  return <div className="space-y-2">{items}</div>
}
