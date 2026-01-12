/**
 * Income Over Time Widget
 *
 * Shows monthly income trend as a bar chart.
 * Uses the shared TimeSeriesBarChart component.
 */

import { getIncomeOverTime } from '@/api'
import { TimeSeriesBarChart } from './shared'
import type { WidgetProps } from './index'

export default function IncomeOverTimeWidget({ settings }: WidgetProps) {
  const months = settings.months ?? 12

  return (
    <TimeSeriesBarChart
      title="Income Over Time"
      months={months}
      queryKeyPrefix="income-over-time"
      queryFn={getIncomeOverTime}
      barColor="#22c55e"
      valueColorClass="text-accent-success"
      valueField="value"
      emptyMessage="No income data available"
    />
  )
}
