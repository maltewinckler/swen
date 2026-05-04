import { createFileRoute } from '@tanstack/react-router'
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import { useState, useMemo, useCallback } from 'react'
import {
  AddTransactionModal,
  ReclassifyProgressModal,
  TransactionDetailModal,
  TransactionsFiltersCard,
  TransactionsListCard,
  TransactionsPageHeader,
  TransactionsReviewBanner,
} from '@/components/transactions'
import { ConfirmDialog, useToast } from '@/components/ui'
import { SyncProgressModal } from '@/components/SyncProgressModal'
import { useSyncProgress } from '@/hooks/useSyncProgress'
import { useReclassifyProgress } from '@/hooks/useReclassifyProgress'
import { listTransactions, bulkPostTransactions } from '@/api'
import type { TransactionListItem } from '@/types/api'

export const Route = createFileRoute('/_app/transactions')({
  component: TransactionsPage,
})

function TransactionsPage() {
  const queryClient = useQueryClient()
  const toast = useToast()
  const [searchQuery, setSearchQuery] = useState('')
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState<'all' | 'posted' | 'draft'>('all')
  const [showTransfers, setShowTransfers] = useState(false)
  const [selectedTransactionId, setSelectedTransactionId] = useState<string | null>(null)
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)
  const [isReviewMode, setIsReviewMode] = useState(false)
  const [showReclassifyConfirm, setShowReclassifyConfirm] = useState(false)
  const [showPostAllConfirm, setShowPostAllConfirm] = useState(false)
  const [showReclassifyModal, setShowReclassifyModal] = useState(false)

  // Sync progress hook
  const sync = useSyncProgress({
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
    },
  })

  // Reclassify progress hook
  const reclassify = useReclassifyProgress({
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
    },
    onError: (err) => {
      toast.danger({ title: 'Reclassification failed', description: err })
    },
  })

  // Bulk post mutation
  const bulkPostMutation = useMutation({
    mutationFn: () => bulkPostTransactions({ post_all_drafts: true }),
    onSuccess: (data) => {
      toast.success({
        title: `${data.posted_count} transaction${data.posted_count !== 1 ? 's' : ''} posted`,
      })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
    },
    onError: (err) => {
      toast.danger({
        title: 'Posting failed',
        description: err instanceof Error ? err.message : 'Unknown error',
      })
    },
  })

  const handleReclassifyConfirm = () => {
    setShowReclassifyConfirm(false)
    setShowReclassifyModal(true)
    reclassify.startReclassify({ reclassify_all: true, only_fallback: true })
  }

  const handlePostAllConfirm = () => {
    setShowPostAllConfirm(false)
    bulkPostMutation.mutate()
  }

  // Toggle Review Mode - automatically filter to drafts
  const toggleReviewMode = () => {
    if (!isReviewMode) {
      // Entering Review Mode: switch to drafts only
      setStatusFilter('draft')
      setPage(1)
    }
    setIsReviewMode(!isReviewMode)
  }

  const { data, isLoading, error } = useQuery({
    queryKey: ['transactions', { page, statusFilter, showTransfers }],
    queryFn: () => listTransactions({
      page,
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
        onReclassify={() => setShowReclassifyConfirm(true)}
        isReclassifying={reclassify.isRunning}
      />

      <TransactionsReviewBanner
        isReviewMode={isReviewMode}
        onExit={toggleReviewMode}
        onReclassify={() => setShowReclassifyConfirm(true)}
        isReclassifying={reclassify.isRunning}
        onPostAll={() => setShowPostAllConfirm(true)}
        isPostingAll={bulkPostMutation.isPending}
      />

      <TransactionsFiltersCard
        searchQuery={searchQuery}
        onSearchQueryChange={setSearchQuery}
        statusFilter={statusFilter}
        onStatusFilterChange={(s) => { setStatusFilter(s); setPage(1) }}
        showTransfers={showTransfers}
        onToggleShowTransfers={() => { setShowTransfers(!showTransfers); setPage(1) }}
      />

      <TransactionsListCard
        transactions={filteredTransactions}
        total={data?.filtered_count}
        isLoading={isLoading}
        hasError={!!error}
        isReviewMode={isReviewMode}
        onSelectTransaction={setSelectedTransactionId}
        page={data?.page ?? 1}
        totalPages={data?.total_pages ?? 1}
        onPageChange={setPage}
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

      {/* Reclassify Confirm Dialog */}
      <ConfirmDialog
        isOpen={showReclassifyConfirm}
        title="Reclassify Draft Transactions"
        description="Re-run ML classification on all uncategorised draft transactions. This will update counter-accounts based on examples from your posted transactions. Posted transactions will not be changed."
        confirmLabel="Reclassify"
        onConfirm={handleReclassifyConfirm}
        onCancel={() => setShowReclassifyConfirm(false)}
      />

      {/* Reclassify Progress Modal */}
      <ReclassifyProgressModal
        open={showReclassifyModal}
        onClose={() => { setShowReclassifyModal(false); reclassify.reset() }}
        step={reclassify.step}
        progress={reclassify.progress}
        result={reclassify.result}
        error={reclassify.error}
        onRetry={handleReclassifyConfirm}
      />

      {/* Post All Confirm Dialog */}
      <ConfirmDialog
        isOpen={showPostAllConfirm}
        title="Post All Draft Transactions"
        description="This will post all remaining draft transactions. Each posted transaction will also be submitted as a training example for the ML classification model."
        confirmLabel="Post All"
        onConfirm={handlePostAllConfirm}
        onCancel={() => setShowPostAllConfirm(false)}
        isLoading={bulkPostMutation.isPending}
      />
    </div>
  )
}
