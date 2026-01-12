/**
 * Top Expenses Widget
 *
 * Shows a ranked list of top expense categories.
 * Uses shared utilities for loading/empty states.
 */

import { useQuery } from '@tanstack/react-query'
import { getTopExpenses } from '@/api'
import { formatCurrency } from '@/lib/utils'
import {
  WidgetCard,
  WidgetLoadingState,
  WidgetEmptyState,
  getPeriodSubtitle,
} from './shared'
import type { WidgetProps } from './index'

export default function TopExpensesWidget({ settings }: WidgetProps) {
  const months = settings.months ?? 1
  const limit = settings.limit ?? 5

  const { data, isLoading } = useQuery({
    queryKey: ['analytics', 'top-expenses', { months, limit }],
    queryFn: () => getTopExpenses({ months, top_n: limit, include_drafts: true }),
  })

  if (isLoading) {
    return <WidgetLoadingState title="Top Expenses" subtitle={getPeriodSubtitle(months)} />
  }

  const items = data?.items ?? []
  const totalSpending = data?.total_spending ? parseFloat(data.total_spending) : 0

  return (
    <WidgetCard title="Top Expenses" subtitle={getPeriodSubtitle(months)} className="flex flex-col">
      {items.length > 0 ? (
        <div className="space-y-3 flex-1 flex flex-col">
          <div className="space-y-3 flex-1">
            {items.map((item) => {
              const percentage = parseFloat(item.percentage_of_total)
              const amount = parseFloat(item.total_amount)

              return (
                <div key={item.account_id} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <span className="text-text-muted font-mono w-4">#{item.rank}</span>
                      <span className="text-text-primary truncate">{item.category}</span>
                    </div>
                    <span className="text-accent-danger font-mono font-medium">
                      {formatCurrency(amount)}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-2 bg-bg-hover rounded-full overflow-hidden">
                      <div
                        className="h-full bg-accent-danger/70 rounded-full transition-all duration-500"
                        style={{ width: `${Math.min(percentage, 100)}%` }}
                      />
                    </div>
                    <span className="text-xs text-text-muted w-10 text-right">
                      {percentage.toFixed(0)}%
                    </span>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Total */}
          <div className="border-t border-border-subtle pt-3 mt-auto">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-text-secondary">Total</span>
              <span className="text-lg font-mono font-bold text-accent-danger">
                {formatCurrency(totalSpending)}
              </span>
            </div>
          </div>
        </div>
      ) : (
        <WidgetEmptyState message="No expense data for this period" height="h-48" />
      )}
    </WidgetCard>
  )
}
