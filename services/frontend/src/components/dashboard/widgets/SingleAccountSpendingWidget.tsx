/**
 * Single Account Spending Widget
 *
 * Shows spending trend for a specific expense category over time.
 * User can select which category to track via a dropdown.
 * Uses shared utilities for loading/empty states and axis formatting.
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardHeader, CardTitle, CardContent, Spinner } from '@/components/ui'
import { getSingleAccountSpending, listAccounts } from '@/api'
import { formatCurrency } from '@/lib/utils'
import { ChevronDown } from 'lucide-react'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts'
import { RotatedAxisTick, WidgetEmptyState } from './shared'
import type { WidgetProps } from './index'

export default function SingleAccountSpendingWidget({ settings }: WidgetProps) {
  const months = settings.months ?? 12
  const [selectedAccountId, setSelectedAccountId] = useState<string | undefined>(
    settings.account_id as string | undefined
  )
  const [dropdownOpen, setDropdownOpen] = useState(false)

  // Fetch expense accounts for dropdown
  const { data: accountsData } = useQuery({
    queryKey: ['accounts', 'expense-list'],
    queryFn: () => listAccounts({ account_type: 'EXPENSE', is_active: true, size: 100 }),
  })

  const expenseAccounts = accountsData?.items ?? []

  // Fetch spending data for selected account
  const { data, isLoading } = useQuery({
    queryKey: ['analytics', 'single-account-spending', selectedAccountId, { months }],
    queryFn: () => getSingleAccountSpending(selectedAccountId!, { months, include_drafts: true }),
    enabled: !!selectedAccountId,
  })

  const chartData = data?.data_points.map((dp) => ({
    period: dp.period_label,
    value: parseFloat(dp.value),
  })) ?? []

  const selectedAccount = expenseAccounts.find(a => a.id === selectedAccountId)

  return (
    <Card className="h-full flex flex-col">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Category Spending</CardTitle>
            <p className="text-sm text-text-muted">Last {months} months</p>
          </div>

          {/* Account selector dropdown */}
          <div className="relative">
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg border border-border-default hover:border-border-focus bg-bg-elevated text-text-primary transition-colors"
            >
              <span className="max-w-32 truncate">
                {selectedAccount?.name ?? 'Select category'}
              </span>
              <ChevronDown className="w-4 h-4 text-text-muted" />
            </button>

            {dropdownOpen && (
              <>
                <div
                  className="fixed inset-0 z-10"
                  onClick={() => setDropdownOpen(false)}
                />
                <div className="absolute right-0 top-full mt-1 z-20 w-56 max-h-64 overflow-y-auto bg-bg-elevated border border-border-default rounded-lg shadow-lg py-1">
                  {expenseAccounts.map((account) => (
                    <button
                      key={account.id}
                      onClick={() => {
                        setSelectedAccountId(account.id)
                        setDropdownOpen(false)
                      }}
                      className={`w-full text-left px-3 py-2 text-sm hover:bg-bg-hover transition-colors ${
                        account.id === selectedAccountId ? 'bg-accent-primary/10 text-accent-primary' : 'text-text-primary'
                      }`}
                    >
                      {account.name}
                    </button>
                  ))}
                  {expenseAccounts.length === 0 && (
                    <div className="px-3 py-2 text-sm text-text-muted">
                      No expense categories found
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex-1">
        {!selectedAccountId ? (
          <WidgetEmptyState message="Select a category to track" height="h-48" />
        ) : isLoading ? (
          <div className="h-48 flex items-center justify-center">
            <Spinner size="lg" />
          </div>
        ) : chartData.length > 0 ? (
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
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
                  width={60}
                />
                <Tooltip
                  isAnimationActive={false}
                  content={({ active, payload, label }) => {
                    if (active && payload && payload.length) {
                      return (
                        <div className="bg-bg-elevated border border-border-subtle rounded-lg p-3 shadow-lg">
                          <p className="text-sm text-text-muted">{label}</p>
                          <p className="text-lg font-bold font-mono text-accent-danger">
                            {formatCurrency(payload[0].value as number)}
                          </p>
                        </div>
                      )
                    }
                    return null
                  }}
                />
                <Bar dataKey="value" fill="#ef4444" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <WidgetEmptyState message="No spending data for this category" height="h-48" />
        )}

        {/* Summary stats */}
        {data && chartData.length > 0 && (
          <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-border-subtle">
            <div className="text-center">
              <p className="text-lg font-mono font-bold text-accent-danger">
                {formatCurrency(parseFloat(data.total))}
              </p>
              <p className="text-xs text-text-muted">Total</p>
            </div>
            <div className="text-center">
              <p className="text-lg font-mono font-bold text-text-primary">
                {formatCurrency(parseFloat(data.average))}
              </p>
              <p className="text-xs text-text-muted">Monthly avg</p>
            </div>
            <div className="text-center">
              <p className="text-lg font-mono font-bold text-text-primary">
                {formatCurrency(parseFloat(data.max_value))}
              </p>
              <p className="text-xs text-text-muted">Peak</p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
