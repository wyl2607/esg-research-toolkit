/**
 * Chart colours as CSS custom properties.
 *
 * Charts render to SVG, so Tailwind's `dark:` variants never reach them —
 * every colour in the dashboard charts used to be a hardcoded hex, which meant
 * the grid, the axis labels and the tooltip stayed in their light-mode colours
 * on a dark page (the category labels landed at roughly 2:1 contrast).
 * Referencing the tokens through `var()` lets the same chart follow the theme.
 */
export const CHART = {
  grid: 'hsl(var(--chart-grid))',
  axis: 'hsl(var(--chart-axis))',
  axisStrong: 'hsl(var(--chart-axis-strong))',
  /** Primary series — the brand accent. */
  series1: 'hsl(var(--chart-series-1))',
  /** Secondary series — used where a second series must stay distinguishable. */
  series2: 'hsl(var(--chart-series-2))',
  surface: 'hsl(var(--chart-surface))',
  surfaceBorder: 'hsl(var(--chart-surface-border))',
} as const

/** Shared Recharts tooltip styling so every tooltip matches the card surface. */
export const CHART_TOOLTIP_STYLE = {
  borderRadius: 16,
  backgroundColor: CHART.surface,
  borderColor: CHART.surfaceBorder,
  color: CHART.axisStrong,
} as const

/** Shared axis tick styling. */
export const CHART_TICK = { fill: CHART.axis, fontSize: 12 } as const
export const CHART_TICK_STRONG = { fill: CHART.axisStrong, fontSize: 12 } as const
