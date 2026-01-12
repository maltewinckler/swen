/**
 * Account Balances Widget
 *
 * Displays a clean list of account balances with totals.
 * Clicking an account opens a stats modal.
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardHeader, CardTitle, CardContent, Spinner } from '@/components/ui'
import { getDashboardBalances } from '@/api'
import { formatCurrency } from '@/lib/utils'
import { Wallet, ChevronRight } from 'lucide-react'
import { AccountStatsModal } from '@/components/accounts'
import type { WidgetProps } from './index'

export default function AccountBalancesWidget(props: WidgetProps) {
  // WidgetProps currently unused (kept for interface consistency with registry)
  void props
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(null)
  const [selectedAccountName, setSelectedAccountName] = useState<string | undefined>(undefined)

  const { data: balances, isLoading } = useQuery({
    queryKey: ['dashboard', 'balances'],
    queryFn: getDashboardBalances,
  })

  // Sort by balance descending (highest first)
  const sortedBalances = [...(balances ?? [])]
    .sort((a, b) => parseFloat(b.balance) - parseFloat(a.balance))

  // Calculate total
  const total = sortedBalances.reduce((sum, b) => sum + parseFloat(b.balance), 0)

  if (isLoading) {
    return (
      <Card className="h-full">
        <CardHeader>
          <CardTitle>Account Balances</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center py-8">
          <Spinner size="lg" />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="h-full flex flex-col">
      <CardHeader>
        <CardTitle>Account Balances</CardTitle>
        <p className="text-sm text-text-muted">Current balances</p>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col">
        {sortedBalances.length > 0 ? (
          <div className="flex flex-col flex-1">
            {/* Account list */}
            <div className="space-y-1 flex-1">
              {sortedBalances.map((account) => {
                const balance = parseFloat(account.balance)
                const isPositive = balance >= 0

                return (
                  <button
                    key={account.id}
                    onClick={() => {
                      setSelectedAccountId(account.id)
                      setSelectedAccountName(account.name)
                    }}
                    className="w-full flex items-center justify-between py-2.5 px-3 rounded-lg hover:bg-bg-hover transition-colors cursor-pointer group text-left"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className={`p-1.5 rounded-md ${isPositive ? 'bg-accent-success/10' : 'bg-accent-danger/10'}`}>
                        <Wallet className={`w-4 h-4 ${isPositive ? 'text-accent-success' : 'text-accent-danger'}`} />
                      </div>
                      <span className="text-sm text-text-primary truncate">
                        {account.name}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`text-sm font-mono font-medium tabular-nums ${
                        isPositive ? 'text-accent-success' : 'text-accent-danger'
                      }`}>
                        {formatCurrency(balance)}
                      </span>
                      <ChevronRight className="w-4 h-4 text-text-muted opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                  </button>
                )
              })}
            </div>

            {/* Total - pushed to bottom */}
            <div className="border-t border-border-subtle pt-3 mt-auto">
              <div className="flex items-center justify-between px-3">
                <span className="text-sm font-medium text-text-secondary">Total</span>
                <span className={`text-lg font-mono font-bold tabular-nums ${
                  total >= 0 ? 'text-accent-success' : 'text-accent-danger'
                }`}>
                  {formatCurrency(total)}
                </span>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center text-text-muted">
            No accounts found
          </div>
        )}
      </CardContent>

      {/* Account Stats Modal */}
      <AccountStatsModal
        accountId={selectedAccountId}
        accountName={selectedAccountName}
        onClose={() => setSelectedAccountId(null)}
      />
    </Card>
  )
}
