/**
 * Spending Over Time Widget
 *
 * Shows monthly spending trend as a bar chart.
 * Uses the shared TimeSeriesBarChart component.
 */

import { getSpendingOverTime } from '@/api'
import { TimeSeriesBarChart } from './shared'
import type { WidgetProps } from './index'

export default function SpendingOverTimeWidget({ settings }: WidgetProps) {
  const months = settings.months ?? 12

  return (
    <TimeSeriesBarChart
      title="Spending Over Time"
      months={months}
      queryKeyPrefix="spending-over-time"
      queryFn={getSpendingOverTime}
      barColor="#ef4444"
      valueColorClass="text-accent-danger"
      valueField="total"
      emptyMessage="No spending data available"
    />
  )
}
