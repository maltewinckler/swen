import { ArrowDownRight, ArrowLeftRight, ArrowUpRight, Calendar, ChevronRight } from 'lucide-react'
import { Amount, Badge, Card, CardContent, CardHeader, CardTitle, Spinner } from '@/components/ui'
import { formatDate, truncate } from '@/lib/utils'
import type { TransactionListItem } from '@/types/api'

function StatusBadge({ isPosted }: { isPosted: boolean }) {
  return isPosted ? <Badge variant="success">Posted</Badge> : <Badge variant="warning">Draft</Badge>
}

interface TransactionsListCardProps {
  transactions: TransactionListItem[]
  total: number | undefined
  isLoading: boolean
  hasError: boolean
  isReviewMode: boolean
  onSelectTransaction: (transactionId: string) => void
}

export function TransactionsListCard({
  transactions,
  total,
  isLoading,
  hasError,
  isReviewMode,
  onSelectTransaction,
}: TransactionsListCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          Recent Transactions
          {transactions.length > 0 && <span className="text-text-muted font-normal ml-2">({transactions.length})</span>}
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="flex items-center justify-center h-48">
            <Spinner size="lg" />
          </div>
        ) : hasError ? (
          <div className="p-6 text-center text-accent-danger">Failed to load transactions</div>
        ) : transactions.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-text-muted">No transactions found</p>
            <p className="text-xs text-text-muted mt-2">
              {total === 0 ? 'Sync your bank accounts to import transactions' : 'Try adjusting your filters'}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-border-subtle">
            {transactions.map((txn) => {
              const isExpense = !txn.is_income
              const isTransfer = txn.is_internal_transfer
              const amount = parseFloat(txn.amount)

              return (
                <button
                  type="button"
                  key={txn.id}
                  onClick={() => onSelectTransaction(txn.id)}
                  className={`
                    w-full text-left flex items-center gap-4 p-4 hover:bg-bg-hover transition-colors cursor-pointer group
                    focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary/50 focus-visible:ring-offset-2 focus-visible:ring-offset-bg-surface
                    ${isReviewMode ? 'hover:bg-accent-primary/5 border-l-2 border-transparent hover:border-accent-primary' : ''}
                  `}
                  aria-haspopup="dialog"
                >
                  <div
                    className={`
                      flex items-center justify-center h-10 w-10 rounded-full
                      ${isTransfer ? 'bg-accent-primary/10' : isExpense ? 'bg-accent-danger/10' : 'bg-accent-success/10'}
                    `}
                  >
                    {isTransfer ? (
                      <ArrowLeftRight className="h-5 w-5 text-accent-primary" />
                    ) : isExpense ? (
                      <ArrowDownRight className="h-5 w-5 text-accent-danger" />
                    ) : (
                      <ArrowUpRight className="h-5 w-5 text-accent-success" />
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-text-primary truncate">{truncate(txn.description, 50)}</p>
                      {isTransfer && <Badge variant="default">Transfer</Badge>}
                      <StatusBadge isPosted={txn.is_posted} />
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                      <Calendar className="h-3 w-3 text-text-muted" />
                      <span className="text-xs text-text-muted">{formatDate(txn.date)}</span>
                      {txn.counterparty && (
                        <>
                          <span className="text-text-muted">•</span>
                          <span className="text-xs text-text-muted truncate">{txn.counterparty}</span>
                        </>
                      )}
                      {(txn.credit_account || txn.debit_account) && (
                        <span className="hidden sm:contents">
                          <span className="text-text-muted">•</span>
                          <span className="text-xs text-text-secondary truncate max-w-[120px] md:max-w-[180px]">
                            {txn.credit_account || '?'}
                          </span>
                          <span className="text-text-muted">→</span>
                          <span className="text-xs text-text-secondary truncate max-w-[120px] md:max-w-[180px]">
                            {txn.debit_account || '?'}
                          </span>
                        </span>
                      )}
                    </div>
                  </div>

                  <Amount
                    value={isTransfer ? amount : isExpense ? -amount : amount}
                    currency={txn.currency}
                    showSign={!isTransfer}
                    className={`text-sm font-medium ${isTransfer ? 'text-text-secondary' : ''}`}
                  />

                  <ChevronRight
                    className={`
                      h-4 w-4 text-text-muted transition-opacity
                      ${isReviewMode ? 'opacity-100 text-accent-primary' : 'opacity-0 group-hover:opacity-100'}
                    `}
                  />
                </button>
              )
            })}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
