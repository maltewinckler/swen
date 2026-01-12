/**
 * Net Income Over Time Widget
 *
 * Shows net income (income minus expenses) over time with dynamic coloring.
 * Positive values are green, negative are red.
 * Uses shared utilities for loading/empty states.
 */

import { useQuery } from '@tanstack/react-query'
import { getNetIncomeOverTime } from '@/api'
import { formatCurrency } from '@/lib/utils'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  Cell,
} from 'recharts'
import {
  WidgetCard,
  WidgetLoadingState,
  WidgetEmptyState,
  formatPeriodLabel,
} from './shared'
import type { WidgetProps } from './index'

export default function NetIncomeWidget({ settings }: WidgetProps) {
  const months = settings.months ?? 12

  const { data, isLoading } = useQuery({
    queryKey: ['analytics', 'net-income', { months }],
    queryFn: () => getNetIncomeOverTime({ months, include_drafts: true }),
  })

  const chartData = data?.data_points.map((dp) => ({
    period: dp.period_label,
    value: parseFloat(dp.value),
  })) ?? []

  if (isLoading) {
    return <WidgetLoadingState title="Net Income Over Time" height="h-80" />
  }

  return (
    <WidgetCard title="Net Income Over Time" subtitle={`Income minus expenses, last ${months} months`}>
      {chartData.length > 0 ? (
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" vertical={false} />
              <XAxis
                dataKey="period"
                tick={{ fill: 'var(--text-muted)', fontSize: 10 }}
                axisLine={{ stroke: 'var(--border-subtle)' }}
                tickLine={false}
                interval={0}
                tickFormatter={formatPeriodLabel}
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
                    const value = payload[0].value as number
                    return (
                      <div className="bg-bg-elevated border border-border-subtle rounded-lg p-3 shadow-lg">
                        <p className="text-sm text-text-muted">{label}</p>
                        <p className={`text-lg font-bold font-mono ${value >= 0 ? 'text-accent-success' : 'text-accent-danger'}`}>
                          {value >= 0 ? '+' : ''}{formatCurrency(value)}
                        </p>
                      </div>
                    )
                  }
                  return null
                }}
              />
              <ReferenceLine y={0} stroke="var(--border-default)" />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                {chartData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.value >= 0 ? '#22c55e' : '#ef4444'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <WidgetEmptyState />
      )}
    </WidgetCard>
  )
}
