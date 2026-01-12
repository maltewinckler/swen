/**
 * Generic Time Series Bar Chart Component
 *
 * Reusable bar chart for time series data (spending over time, income over time, etc.)
 * Eliminates duplication between SpendingOverTimeWidget and IncomeOverTimeWidget.
 */

import { useQuery } from '@tanstack/react-query'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts'
import { formatCurrency } from '@/lib/utils'
import {
  WidgetCard,
  WidgetLoadingState,
  WidgetEmptyState,
  RotatedAxisTick,
} from './chart-utils'

// =============================================================================
// Types
// =============================================================================

interface DataPoint {
  period_label: string
  value?: string
  total?: string
}

interface TimeSeriesResponse {
  data_points: DataPoint[]
}

interface TimeSeriesBarChartProps {
  /** Widget title */
  title: string
  /** Number of months to show */
  months: number
  /** React Query key prefix */
  queryKeyPrefix: string
  /** API function to fetch data */
  queryFn: (params: { months: number; include_drafts: boolean }) => Promise<TimeSeriesResponse>
  /** Bar color (hex code) */
  barColor: string
  /** Color class for values in tooltip (e.g., 'text-accent-success') */
  valueColorClass?: string
  /** Field to use for value (some APIs use 'total', others use 'value') */
  valueField?: 'value' | 'total'
  /** Empty state message */
  emptyMessage?: string
  /** Chart height class */
  chartHeight?: string
}

// =============================================================================
// Component
// =============================================================================

export function TimeSeriesBarChart({
  title,
  months,
  queryKeyPrefix,
  queryFn,
  barColor,
  valueColorClass = 'text-text-primary',
  valueField = 'value',
  emptyMessage = 'No data available',
  chartHeight = 'h-64',
}: TimeSeriesBarChartProps) {
  const { data, isLoading } = useQuery({
    queryKey: ['analytics', queryKeyPrefix, { months }],
    queryFn: () => queryFn({ months, include_drafts: true }),
  })

  // Transform data for chart - handle both 'value' and 'total' fields
  const chartData = data?.data_points.map((dp) => ({
    period: dp.period_label,
    value: parseFloat(valueField === 'total' ? (dp.total ?? '0') : (dp.value ?? '0')),
  })) ?? []

  if (isLoading) {
    return <WidgetLoadingState title={title} subtitle={`Last ${months} months`} />
  }

  return (
    <WidgetCard title={title} subtitle={`Last ${months} months`}>
      {chartData.length > 0 ? (
        <div className={chartHeight}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="var(--border-subtle)"
                vertical={false}
              />
              <XAxis
                dataKey="period"
                tick={RotatedAxisTick}
                axisLine={{ stroke: 'var(--border-subtle)' }}
                tickLine={false}
                interval={0}
                height={50}
              />
              <YAxis
                tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                tickFormatter={(v) => formatCurrency(v)}
                axisLine={false}
                tickLine={false}
                width={70}
              />
              <Tooltip
                isAnimationActive={false}
                content={({ active, payload, label }) => {
                  if (active && payload && payload.length) {
                    return (
                      <div className="bg-bg-elevated border border-border-subtle rounded-lg p-3 shadow-lg">
                        <p className="text-sm text-text-muted">{label}</p>
                        <p className={`text-lg font-bold font-mono ${valueColorClass}`}>
                          {formatCurrency(payload[0].value as number)}
                        </p>
                      </div>
                    )
                  }
                  return null
                }}
              />
              <Bar dataKey="value" fill={barColor} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <WidgetEmptyState message={emptyMessage} height={chartHeight} />
      )}
    </WidgetCard>
  )
}

