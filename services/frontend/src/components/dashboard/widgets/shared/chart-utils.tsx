/**
 * Shared Chart Utilities
 *
 * Common components and utilities for dashboard chart widgets.
 * Reduces duplication across pie charts, bar charts, and other visualizations.
 */

import { Card, CardHeader, CardTitle, CardContent, Spinner } from '@/components/ui'
import { formatCurrency } from '@/lib/utils'
import type { ReactNode } from 'react'

// =============================================================================
// Period Formatting
// =============================================================================

/**
 * Format a period label for chart X-axis.
 * Converts "February 2025" to "Feb '25"
 */
export function formatPeriodLabel(value: string): string {
  const parts = value.split(' ')
  const month = parts[0]?.substring(0, 3) ?? ''
  const year = parts[1]?.slice(-2) ?? ''
  return year ? `${month} '${year}` : month
}

// =============================================================================
// Chart Tooltip
// =============================================================================

interface TooltipContentProps {
  label: string
  value: number
  /** Optional: show percentage (for pie charts) */
  percentage?: number
  /** Value color class (e.g., 'text-accent-success') */
  valueColorClass?: string
  /** Format value as currency (default: true) */
  formatAsCurrency?: boolean
  /** Show sign prefix for currency */
  showSign?: boolean
}

/**
 * Reusable tooltip content for charts.
 */
export function ChartTooltipContent({
  label,
  value,
  percentage,
  valueColorClass = 'text-text-primary',
  formatAsCurrency = true,
  showSign = false,
}: TooltipContentProps) {
  const formattedValue = formatAsCurrency
    ? (showSign && value >= 0 ? '+' : '') + formatCurrency(value)
    : value.toFixed(1)

  return (
    <div className="bg-bg-elevated border border-border-subtle rounded-lg p-3 shadow-lg">
      <p className="text-sm text-text-muted">{label}</p>
      <p className={`text-lg font-bold font-mono ${valueColorClass}`}>
        {formattedValue}
        {!formatAsCurrency && '%'}
      </p>
      {percentage !== undefined && (
        <p className="text-xs text-text-muted">{percentage.toFixed(1)}% of total</p>
      )}
    </div>
  )
}

// =============================================================================
// Widget States
// =============================================================================

interface WidgetLoadingStateProps {
  title: string
  subtitle?: string
  height?: string
}

/**
 * Loading state for widget cards.
 */
export function WidgetLoadingState({
  title,
  subtitle,
  height = 'h-64',
}: WidgetLoadingStateProps) {
  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {subtitle && <p className="text-sm text-text-muted">{subtitle}</p>}
      </CardHeader>
      <CardContent className={`${height} flex items-center justify-center`}>
        <Spinner size="lg" />
      </CardContent>
    </Card>
  )
}

interface WidgetEmptyStateProps {
  message?: string
  height?: string
}

/**
 * Empty state for widget content.
 */
export function WidgetEmptyState({
  message = 'No data available',
  height = 'h-64',
}: WidgetEmptyStateProps) {
  return (
    <div className={`${height} flex items-center justify-center text-text-muted`}>
      {message}
    </div>
  )
}

// =============================================================================
// Widget Card Wrapper
// =============================================================================

interface WidgetCardProps {
  title: string
  subtitle?: string
  children: ReactNode
  className?: string
  headerRight?: ReactNode
}

/**
 * Standard widget card wrapper with header.
 */
export function WidgetCard({
  title,
  subtitle,
  children,
  className = '',
  headerRight,
}: WidgetCardProps) {
  return (
    <Card className={`h-full ${className}`}>
      <CardHeader className={headerRight ? 'flex flex-row items-center justify-between' : ''}>
        <div>
          <CardTitle>{title}</CardTitle>
          {subtitle && <p className="text-sm text-text-muted">{subtitle}</p>}
        </div>
        {headerRight}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  )
}

// =============================================================================
// Rotated XAxis Tick (for time series)
// =============================================================================

interface RotatedTickProps {
  x: number
  y: number
  payload: { value: string }
}

/**
 * Rotated tick component for XAxis in time series charts.
 * Abbreviates month names and rotates -45 degrees.
 */
export function RotatedAxisTick({ x, y, payload }: RotatedTickProps) {
  const label = formatPeriodLabel(payload.value)
  return (
    <text
      x={x}
      y={y}
      dy={10}
      fill="var(--text-muted)"
      fontSize={10}
      textAnchor="end"
      transform={`rotate(-45, ${x}, ${y})`}
    >
      {label}
    </text>
  )
}

// =============================================================================
// Color Palettes
// =============================================================================

/** Colors for spending/expense charts */
export const SPENDING_COLORS = [
  '#f97316', // orange
  '#ef4444', // red
  '#f59e0b', // amber
  '#ec4899', // pink
  '#8b5cf6', // violet
  '#6366f1', // indigo
  '#14b8a6', // teal
]

/** Colors for income charts */
export const INCOME_COLORS = [
  '#22c55e', // green
  '#10b981', // emerald
  '#14b8a6', // teal
  '#06b6d4', // cyan
  '#3b82f6', // blue
  '#8b5cf6', // violet
  '#a855f7', // purple
]

// =============================================================================
// Period Subtitle Helper
// =============================================================================

/**
 * Generate a human-readable period subtitle.
 */
export function getPeriodSubtitle(months: number): string {
  if (months === 1) return 'This month'
  return `Last ${months} months`
}
