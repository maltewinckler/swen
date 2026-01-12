/**
 * Spending Breakdown Pie Chart Widget
 *
 * Shows spending by category as a pie chart.
 * Uses the shared BreakdownPieChart component.
 */

import { getSpendingBreakdown } from '@/api'
import { BreakdownPieChart, SPENDING_COLORS } from './shared'
import type { WidgetProps } from './index'

export default function SpendingPieWidget({ settings }: WidgetProps) {
  const months = settings.months ?? 1

  return (
    <BreakdownPieChart
      title="Spending by Category"
      months={months}
      queryKeyPrefix="spending-breakdown"
      queryFn={getSpendingBreakdown}
      colors={SPENDING_COLORS}
      valueColorClass="text-text-secondary"
      emptyMessage="No spending data for this period"
      chartHeight="h-80"
      innerRadius={60}
      outerRadius={100}
    />
  )
}
