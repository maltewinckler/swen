/**
 * Net Worth Over Time Widget
 *
 * Shows net worth (assets - liabilities) over time as an area chart.
 * Uses shared utilities for loading/empty states and axis formatting.
 */

import { useQuery } from '@tanstack/react-query'
import { getNetWorth } from '@/api'
import { formatCurrency } from '@/lib/utils'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts'
import {
  WidgetCard,
  WidgetLoadingState,
  WidgetEmptyState,
  RotatedAxisTick,
} from './shared'
import type { WidgetProps } from './index'

export default function NetWorthWidget({ settings }: WidgetProps) {
  const months = settings.months ?? 12

  const { data, isLoading } = useQuery({
    queryKey: ['analytics', 'net-worth', { months }],
    queryFn: () => getNetWorth({ months, include_drafts: true }),
  })

  const chartData = data?.data_points.map((dp) => ({
    period: dp.period_label,
    value: parseFloat(dp.value),
  })) ?? []

  if (isLoading) {
    return <WidgetLoadingState title="Net Worth Over Time" subtitle={`Last ${months} months`} />
  }

  const latestValue = chartData.length > 0 ? chartData[chartData.length - 1].value : 0

  const headerRight = (
    <div className="text-right">
      <p className="text-2xl font-bold font-mono text-accent-primary">
        {formatCurrency(latestValue)}
      </p>
      <p className="text-xs text-text-muted">Current</p>
    </div>
  )

  return (
    <WidgetCard title="Net Worth Over Time" subtitle={`Last ${months} months`} headerRight={headerRight}>
      {chartData.length > 0 ? (
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="netWorthGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" vertical={false} />
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
                width={80}
              />
              <Tooltip
                isAnimationActive={false}
                content={({ active, payload, label }) => {
                  if (active && payload && payload.length) {
                    return (
                      <div className="bg-bg-elevated border border-border-subtle rounded-lg p-3 shadow-lg">
                        <p className="text-sm text-text-muted">{label}</p>
                        <p className="text-lg font-bold font-mono text-accent-primary">
                          {formatCurrency(payload[0].value as number)}
                        </p>
                      </div>
                    )
                  }
                  return null
                }}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke="#22c55e"
                strokeWidth={2}
                fill="url(#netWorthGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <WidgetEmptyState />
      )}
    </WidgetCard>
  )
}

