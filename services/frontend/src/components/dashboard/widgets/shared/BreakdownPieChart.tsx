/**
 * Generic Breakdown Pie Chart Component
 *
 * Reusable pie chart for category breakdowns (spending, income, etc.)
 * Eliminates duplication between SpendingPieWidget and IncomeBreakdownWidget.
 */

import { useQuery } from '@tanstack/react-query'
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
} from 'recharts'
import { formatCurrency } from '@/lib/utils'
import {
  WidgetCard,
  WidgetLoadingState,
  WidgetEmptyState,
  getPeriodSubtitle,
  SPENDING_COLORS,
} from './chart-utils'

// =============================================================================
// Types
// =============================================================================

interface BreakdownItem {
  category: string
  amount: string
}

interface BreakdownResponse {
  items: BreakdownItem[]
  total?: string
}

interface BreakdownPieChartProps {
  /** Widget title */
  title: string
  /** Number of months to show */
  months: number
  /** React Query key prefix */
  queryKeyPrefix: string
  /** API function to fetch data */
  queryFn: (params: { days: number; include_drafts: boolean }) => Promise<BreakdownResponse>
  /** Color palette for pie slices */
  colors?: string[]
  /** Color class for values in tooltip (e.g., 'text-accent-success') */
  valueColorClass?: string
  /** Empty state message */
  emptyMessage?: string
  /** Chart height class */
  chartHeight?: string
  /** Inner radius of the pie */
  innerRadius?: number
  /** Outer radius of the pie */
  outerRadius?: number
}

// =============================================================================
// Component
// =============================================================================

export function BreakdownPieChart({
  title,
  months,
  queryKeyPrefix,
  queryFn,
  colors = SPENDING_COLORS,
  valueColorClass = 'text-text-secondary',
  emptyMessage = 'No data for this period',
  chartHeight = 'h-64',
  innerRadius = 50,
  outerRadius = 80,
}: BreakdownPieChartProps) {
  const { data: breakdown, isLoading } = useQuery({
    queryKey: ['analytics', queryKeyPrefix, { months }],
    queryFn: () => queryFn({ days: months === 1 ? 30 : months * 30, include_drafts: true }),
  })

  // Transform data for chart
  const chartData = breakdown?.items.map((item, index) => ({
    name: item.category,
    value: parseFloat(item.amount),
    color: colors[index % colors.length],
  })) ?? []

  const total = chartData.reduce((sum, d) => sum + d.value, 0)

  if (isLoading) {
    return <WidgetLoadingState title={title} subtitle={getPeriodSubtitle(months)} />
  }

  return (
    <WidgetCard title={title} subtitle={getPeriodSubtitle(months)}>
      {chartData.length > 0 ? (
        <div className={chartHeight}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart margin={{ top: 10, right: 10, bottom: 10, left: 10 }}>
              <Pie
                data={chartData}
                cx="50%"
                cy="42%"
                innerRadius={innerRadius}
                outerRadius={outerRadius}
                paddingAngle={2}
                dataKey="value"
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                isAnimationActive={false}
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload as { name: string; value: number }
                    const percentage = ((data.value / total) * 100).toFixed(1)
                    return (
                      <div className="bg-bg-elevated border border-border-subtle rounded-lg p-3 shadow-lg">
                        <p className="text-sm font-medium text-text-primary">{data.name}</p>
                        <p className={`text-sm font-mono ${valueColorClass}`}>
                          {formatCurrency(data.value)}
                        </p>
                        <p className="text-xs text-text-muted">{percentage}% of total</p>
                      </div>
                    )
                  }
                  return null
                }}
              />
              <Legend
                layout="horizontal"
                verticalAlign="bottom"
                align="center"
                formatter={(value) => (
                  <span className="text-text-secondary text-xs">{value}</span>
                )}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <WidgetEmptyState message={emptyMessage} height={chartHeight} />
      )}
    </WidgetCard>
  )
}

