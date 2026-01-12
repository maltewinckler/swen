/**
 * Month Comparison Widget
 *
 * Compares current month vs previous month for income, spending, and net.
 * Uses shared utilities for loading/empty states.
 */

import { useQuery } from '@tanstack/react-query'
import { getMonthComparison } from '@/api'
import { formatCurrency } from '@/lib/utils'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import {
  WidgetCard,
  WidgetLoadingState,
  WidgetEmptyState,
} from './shared'
import type { WidgetProps } from './index'

function ChangeIndicator({ change, percentage }: { change: number; percentage: number }) {
  if (Math.abs(percentage) < 0.1) {
    return (
      <div className="flex items-center gap-1 text-text-muted">
        <Minus className="w-3 h-3" />
        <span className="text-xs">No change</span>
      </div>
    )
  }

  const isPositive = change > 0
  const Icon = isPositive ? TrendingUp : TrendingDown

  return (
    <div className={`flex items-center gap-1 ${isPositive ? 'text-accent-success' : 'text-accent-danger'}`}>
      <Icon className="w-3 h-3" />
      <span className="text-xs font-medium">
        {isPositive ? '+' : ''}{percentage.toFixed(1)}%
      </span>
    </div>
  )
}

export default function MonthComparisonWidget(props: WidgetProps) {
  // WidgetProps currently unused (kept for interface consistency with registry)
  void props
  const { data, isLoading } = useQuery({
    queryKey: ['analytics', 'month-comparison'],
    queryFn: () => getMonthComparison({ include_drafts: true }),
  })

  if (isLoading) {
    return <WidgetLoadingState title="Month Comparison" />
  }

  if (!data) {
    return (
      <WidgetCard title="Month Comparison">
        <WidgetEmptyState />
      </WidgetCard>
    )
  }

  const metrics = [
    {
      label: 'Income',
      current: parseFloat(data.current_income),
      previous: parseFloat(data.previous_income),
      change: parseFloat(data.income_change),
      percentage: parseFloat(data.income_change_percentage),
      colorClass: 'text-accent-success',
      invertChange: false, // Higher income is good
    },
    {
      label: 'Spending',
      current: parseFloat(data.current_spending),
      previous: parseFloat(data.previous_spending),
      change: parseFloat(data.spending_change),
      percentage: parseFloat(data.spending_change_percentage),
      colorClass: 'text-accent-danger',
      invertChange: true, // Lower spending is good
    },
    {
      label: 'Net',
      current: parseFloat(data.current_net),
      previous: parseFloat(data.previous_net),
      change: parseFloat(data.net_change),
      percentage: parseFloat(data.net_change_percentage),
      colorClass: parseFloat(data.current_net) >= 0 ? 'text-accent-success' : 'text-accent-danger',
      invertChange: false, // Higher net is good
    },
  ]

  return (
    <WidgetCard
      title="Month Comparison"
      subtitle={`${data.current_month} vs ${data.previous_month}`}
      className="flex flex-col"
    >
      <div className="space-y-4 flex-1">
        {metrics.map((metric) => (
          <div key={metric.label} className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-sm text-text-secondary">{metric.label}</span>
              <ChangeIndicator
                change={metric.invertChange ? -metric.change : metric.change}
                percentage={metric.invertChange ? -metric.percentage : metric.percentage}
              />
            </div>
            <div className="flex items-baseline justify-between">
              <span className={`text-lg font-bold font-mono ${metric.colorClass}`}>
                {formatCurrency(metric.current)}
              </span>
              <span className="text-sm text-text-muted font-mono">
                was {formatCurrency(metric.previous)}
              </span>
            </div>
          </div>
        ))}

        {/* Top category changes */}
        {data.category_comparisons.length > 0 && (
          <div className="pt-4 border-t border-border-subtle">
            <p className="text-xs text-text-muted mb-2">Top category changes</p>
            <div className="space-y-2">
              {data.category_comparisons.slice(0, 3).map((cat) => {
                const changePercent = parseFloat(cat.change_percentage)
                const isIncrease = changePercent > 0

                return (
                  <div key={cat.category} className="flex items-center justify-between text-xs">
                    <span className="text-text-secondary truncate">{cat.category}</span>
                    <span className={isIncrease ? 'text-accent-danger' : 'text-accent-success'}>
                      {isIncrease ? '+' : ''}{changePercent.toFixed(0)}%
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </WidgetCard>
  )
}
