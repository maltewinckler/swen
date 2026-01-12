/**
 * Income Breakdown Widget
 *
 * Shows income by source as a pie chart.
 * Uses the shared BreakdownPieChart component.
 */

import { getIncomeBreakdown } from '@/api'
import { BreakdownPieChart, INCOME_COLORS } from './shared'
import type { WidgetProps } from './index'

export default function IncomeBreakdownWidget({ settings }: WidgetProps) {
  const months = settings.months ?? 1

  return (
    <BreakdownPieChart
      title="Income Sources"
      months={months}
      queryKeyPrefix="income-breakdown"
      queryFn={getIncomeBreakdown}
      colors={INCOME_COLORS}
      valueColorClass="text-accent-success"
      emptyMessage="No income data for this period"
    />
  )
}
