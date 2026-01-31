import { createFileRoute } from '@tanstack/react-router'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, useMemo, useCallback } from 'react'
import {
  AddTransactionModal,
  TransactionDetailModal,
  TransactionsFiltersCard,
  TransactionsListCard,
  TransactionsPageHeader,
  TransactionsReviewBanner,
} from '@/components/transactions'
import { SyncProgressModal } from '@/components/SyncProgressModal'
import { useSyncProgress } from '@/hooks/useSyncProgress'
import { listTransactions } from '@/api'
import type { TransactionListItem } from '@/types/api'

export const Route = createFileRoute('/_app/transactions')({
  component: TransactionsPage,
})

function TransactionsPage() {
  const queryClient = useQueryClient()
  const [searchQuery, setSearchQuery] = useState('')
  const [days, setDays] = useState(30)
  const [statusFilter, setStatusFilter] = useState<'all' | 'posted' | 'draft'>('all')
  const [showTransfers, setShowTransfers] = useState(false)
  const [selectedTransactionId, setSelectedTransactionId] = useState<string | null>(null)
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)
  const [isReviewMode, setIsReviewMode] = useState(false)

  // Sync progress hook
  const sync = useSyncProgress({
    onSuccess: () => {
      // Invalidate queries to refresh data after sync
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
    },
  })

  // Toggle Review Mode - automatically filter to drafts
  const toggleReviewMode = () => {
    if (!isReviewMode) {
      // Entering Review Mode: switch to drafts only
      setStatusFilter('draft')
    }
    setIsReviewMode(!isReviewMode)
  }

  const { data, isLoading, error } = useQuery({
    queryKey: ['transactions', { days, statusFilter, showTransfers }],
    queryFn: () => listTransactions({
      days,
      limit: 100,
      status_filter: statusFilter === 'all' ? undefined : statusFilter,
      exclude_transfers: !showTransfers,
    }),
  })

  const transactions = useMemo<TransactionListItem[]>(() => data?.transactions ?? [], [data?.transactions])

  // Filter by search query client-side (backend doesn't support search yet)
  const filteredTransactions = useMemo(() => {
    if (!searchQuery) return transactions
    const q = searchQuery.toLowerCase()
    return transactions.filter(
      (txn) =>
        txn.description.toLowerCase().includes(q) ||
        (txn.counterparty?.toLowerCase().includes(q) ?? false)
    )
  }, [transactions, searchQuery])

  // Get list of transaction IDs for navigation in modal
  const transactionIds = useMemo(
    () => filteredTransactions.map((txn) => txn.id),
    [filteredTransactions]
  )

  // Check if selected transaction is a draft (for review mode)
  const isSelectedTransactionDraft = useMemo(() => {
    const selectedTxn = filteredTransactions.find((t) => t.id === selectedTransactionId)
    return selectedTxn ? !selectedTxn.is_posted : false
  }, [filteredTransactions, selectedTransactionId])

  // Handle navigation between transactions in modal
  const handleNavigate = useCallback((transactionId: string) => {
    setSelectedTransactionId(transactionId)
  }, [])

  return (
    <div className="space-y-6 animate-fade-in">
      <TransactionsPageHeader
        postedCount={data?.posted_count}
        draftCount={data?.draft_count}
        isReviewMode={isReviewMode}
        onToggleReviewMode={toggleReviewMode}
        onAddTransaction={() => setIsAddModalOpen(true)}
        onSyncBank={() => sync.checkAndSync()}
        isSyncing={sync.step === 'syncing'}
      />

      <TransactionsReviewBanner isReviewMode={isReviewMode} onExit={toggleReviewMode} />

      <TransactionsFiltersCard
        searchQuery={searchQuery}
        onSearchQueryChange={setSearchQuery}
        days={days}
        onDaysChange={(d) => setDays(d)}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        showTransfers={showTransfers}
        onToggleShowTransfers={() => setShowTransfers(!showTransfers)}
      />

      <TransactionsListCard
        transactions={filteredTransactions}
        total={data?.total}
        isLoading={isLoading}
        hasError={!!error}
        isReviewMode={isReviewMode}
        onSelectTransaction={setSelectedTransactionId}
      />

      {/* Transaction Detail Modal */}
      <TransactionDetailModal
        transactionId={selectedTransactionId}
        transactionIds={transactionIds}
        onClose={() => setSelectedTransactionId(null)}
        onNavigate={handleNavigate}
        isReviewMode={isReviewMode && isSelectedTransactionDraft}
      />

      {/* Add Transaction Modal */}
      <AddTransactionModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
      />

      {/* Sync Progress Modal */}
      <SyncProgressModal
        open={sync.isOpen}
        onClose={sync.reset}
        step={sync.step}
        progress={sync.progress}
        result={sync.result}
        error={sync.error}
        firstSyncDays={sync.firstSyncDays}
        onSetFirstSyncDays={sync.setFirstSyncDays}
        onConfirmFirstSync={sync.confirmFirstSync}
        onSkipSync={sync.skip}
      />
    </div>
  )
}
