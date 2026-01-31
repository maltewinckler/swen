import { ClipboardCheck, Plus, RefreshCw } from 'lucide-react'
import { Button, Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui'

interface TransactionsPageHeaderProps {
  postedCount?: number
  draftCount?: number
  isReviewMode: boolean
  onToggleReviewMode: () => void
  onAddTransaction: () => void
  onSyncBank: () => void
  isSyncing?: boolean
}

export function TransactionsPageHeader({
  postedCount,
  draftCount,
  isReviewMode,
  onToggleReviewMode,
  onAddTransaction,
  onSyncBank,
  isSyncing = false,
}: TransactionsPageHeaderProps) {
  const hasCounts = typeof postedCount === 'number' && typeof draftCount === 'number'

  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h1 className="text-display text-text-primary">Transactions</h1>
        <p className="text-text-secondary mt-1">
          View and manage your transactions
          {hasCounts && (
            <span className="text-text-muted ml-2">
              ({postedCount} posted, {draftCount} draft)
            </span>
          )}
        </p>
      </div>
      <div className="flex items-center gap-2">
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="secondary" onClick={onToggleReviewMode}>
              <ClipboardCheck className="h-4 w-4" />
              {isReviewMode ? 'Exit Review' : 'Review Mode'}
            </Button>
          </TooltipTrigger>
          <TooltipContent>Review and edit draft transactions</TooltipContent>
        </Tooltip>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="secondary" onClick={onSyncBank} disabled={isSyncing}>
              <RefreshCw className={`h-4 w-4 ${isSyncing ? 'animate-spin' : ''}`} />
              Sync Bank
            </Button>
          </TooltipTrigger>
          <TooltipContent>Sync transactions from your bank accounts</TooltipContent>
        </Tooltip>
        <Button onClick={onAddTransaction}>
          <Plus className="h-4 w-4" />
          Add Transaction
        </Button>
      </div>
    </div>
  )
}
