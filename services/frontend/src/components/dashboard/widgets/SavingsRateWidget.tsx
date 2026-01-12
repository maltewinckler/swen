/**
 * Savings Rate Widget
 *
 * Shows savings rate (percentage of income saved) over time as an area chart.
 * Uses shared utilities for loading/empty states and axis formatting.
 */

import { useQuery } from '@tanstack/react-query'
import { getSavingsRate } from '@/api'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from 'recharts'
import {
  WidgetCard,
  WidgetLoadingState,
  WidgetEmptyState,
  RotatedAxisTick,
} from './shared'
import type { WidgetProps } from './index'

export default function SavingsRateWidget({ settings }: WidgetProps) {
  const months = settings.months ?? 12

  const { data, isLoading } = useQuery({
    queryKey: ['analytics', 'savings-rate', { months }],
    queryFn: () => getSavingsRate({ months, include_drafts: true }),
  })

  const chartData = data?.data_points.map((dp) => ({
    period: dp.period_label,
    value: parseFloat(dp.value),
  })) ?? []

  const averageRate = data?.average ? parseFloat(data.average) : 0

  if (isLoading) {
    return <WidgetLoadingState title="Savings Rate" subtitle={`Last ${months} months`} />
  }

  const headerRight = (
    <div className="text-right">
      <p className={`text-2xl font-bold font-mono ${averageRate >= 0 ? 'text-accent-success' : 'text-accent-danger'}`}>
        {averageRate.toFixed(1)}%
      </p>
      <p className="text-xs text-text-muted">Average</p>
    </div>
  )

  return (
    <WidgetCard title="Savings Rate" subtitle={`Last ${months} months`} headerRight={headerRight}>
      {chartData.length > 0 ? (
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="savingsRateGradient" x1="0" y1="0" x2="0" y2="1">
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
                tickFormatter={(v) => `${v}%`}
                axisLine={false}
                tickLine={false}
                width={50}
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
                          {value.toFixed(1)}%
                        </p>
                      </div>
                    )
                  }
                  return null
                }}
              />
              <ReferenceLine y={0} stroke="var(--border-default)" />
              <ReferenceLine
                y={20}
                stroke="var(--accent-success)"
                strokeDasharray="5 5"
                strokeOpacity={0.5}
                label={{ value: '20% goal', fill: 'var(--text-muted)', fontSize: 10, position: 'right' }}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke="#22c55e"
                strokeWidth={2}
                fill="url(#savingsRateGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <WidgetEmptyState height="h-48" />
      )}
    </WidgetCard>
  )
}
