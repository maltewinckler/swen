/**
 * Summary Cards Widget
 *
 * Displays key financial metrics: Total Assets, Income, Expenses, Net Income
 */

import { useQuery } from '@tanstack/react-query'
import { TrendingUp, TrendingDown, Wallet, ArrowUpRight, ArrowDownRight } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent, Amount } from '@/components/ui'
import { getDashboardSummary, getDashboardBalances } from '@/api'
import { formatCurrency } from '@/lib/utils'
import type { WidgetProps } from './index'

export default function SummaryCardsWidget({ settings }: WidgetProps) {
  const days = settings.days ?? 30

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['dashboard', 'summary', { days }],
    queryFn: () => getDashboardSummary({ days }),
  })

  const { data: balances, isLoading: balancesLoading } = useQuery({
    queryKey: ['dashboard', 'balances'],
    queryFn: getDashboardBalances,
  })

  const isLoading = summaryLoading || balancesLoading

  // Calculate total assets
  const totalAssets = balances?.reduce((sum, b) => sum + parseFloat(b.balance), 0) ?? 0

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i} className="animate-pulse">
            <CardContent className="h-24" />
          </Card>
        ))}
      </div>
    )
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {/* Total Assets */}
      <Card className="animate-slide-up animate-stagger-1">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium text-text-secondary">
            Total Assets
          </CardTitle>
          <Wallet className="h-4 w-4 text-accent-primary" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-text-primary font-mono">
            {formatCurrency(totalAssets)}
          </div>
        </CardContent>
      </Card>

      {/* Income */}
      <Card className="animate-slide-up animate-stagger-2">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium text-text-secondary">
            Income
          </CardTitle>
          <ArrowUpRight className="h-4 w-4 text-accent-success" />
        </CardHeader>
        <CardContent>
          <Amount
            value={summary?.total_income ?? 0}
            className="text-2xl font-bold"
            colorize={false}
          />
          <p className="text-xs text-text-muted mt-1">Last {days} days</p>
        </CardContent>
      </Card>

      {/* Expenses */}
      <Card className="animate-slide-up animate-stagger-3">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium text-text-secondary">
            Expenses
          </CardTitle>
          <ArrowDownRight className="h-4 w-4 text-accent-danger" />
        </CardHeader>
        <CardContent>
          <Amount
            value={summary?.total_expenses ?? 0}
            className="text-2xl font-bold"
            colorize={false}
          />
          <p className="text-xs text-text-muted mt-1">Last {days} days</p>
        </CardContent>
      </Card>

      {/* Net Income */}
      <Card className="animate-slide-up animate-stagger-4">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium text-text-secondary">
            Net Income
          </CardTitle>
          {parseFloat(summary?.net_income ?? '0') >= 0 ? (
            <TrendingUp className="h-4 w-4 text-accent-success" />
          ) : (
            <TrendingDown className="h-4 w-4 text-accent-danger" />
          )}
        </CardHeader>
        <CardContent>
          <Amount
            value={summary?.net_income ?? 0}
            className="text-2xl font-bold"
            showSign
          />
          <p className="text-xs text-text-muted mt-1">Last {days} days</p>
        </CardContent>
      </Card>
    </div>
  )
}
