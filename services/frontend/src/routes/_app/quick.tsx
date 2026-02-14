import { createFileRoute } from '@tanstack/react-router'
import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { RefreshCw, Banknote, Plus, ArrowRight } from 'lucide-react'
import { Link } from '@tanstack/react-router'
import { AddTransactionModal } from '@/components/transactions'
import { CashExpenseModal } from '@/components/quick'
import { SyncProgressModal } from '@/components/SyncProgressModal'
import { useSyncProgress } from '@/hooks/useSyncProgress'
import { cn } from '@/lib/utils'

export const Route = createFileRoute('/_app/quick')({
  component: QuickActionsPage,
})

interface QuickActionProps {
  icon: React.ElementType
  label: string
  description: string
  onClick: () => void
  variant?: 'primary' | 'default'
  isLoading?: boolean
  disabled?: boolean
}

function QuickAction({
  icon: Icon,
  label,
  description,
  onClick,
  variant = 'default',
  isLoading = false,
  disabled = false,
}: QuickActionProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled || isLoading}
      className={cn(
        'w-full p-6 rounded-2xl border-2 text-left transition-all',
        'focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary/50 focus-visible:ring-offset-2 focus-visible:ring-offset-bg-base',
        'active:scale-[0.98]',
        variant === 'primary'
          ? 'border-accent-primary bg-accent-primary/10 hover:bg-accent-primary/15'
          : 'border-border-default bg-bg-surface hover:border-border-hover hover:bg-bg-hover',
        disabled && 'opacity-50 cursor-not-allowed'
      )}
    >
      <div className="flex items-center gap-4">
        <div
          className={cn(
            'flex items-center justify-center w-14 h-14 rounded-xl',
            variant === 'primary' ? 'bg-accent-primary/20' : 'bg-bg-hover'
          )}
        >
          {isLoading ? (
            <RefreshCw className="h-7 w-7 text-accent-primary animate-spin" />
          ) : (
            <Icon
              className={cn(
                'h-7 w-7',
                variant === 'primary' ? 'text-accent-primary' : 'text-text-secondary'
              )}
            />
          )}
        </div>
        <div className="flex-1">
          <p className="font-semibold text-lg text-text-primary">{label}</p>
          <p className="text-sm text-text-muted mt-0.5">{description}</p>
        </div>
        <ArrowRight className="h-5 w-5 text-text-muted" />
      </div>
    </button>
  )
}

function QuickActionsPage() {
  const queryClient = useQueryClient()
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)
  const [isCashModalOpen, setIsCashModalOpen] = useState(false)

  // Sync progress hook
  const sync = useSyncProgress({
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })

  return (
    <div className="min-h-[calc(100vh-8rem)] flex flex-col animate-fade-in">
      {/* Header */}
      <div className="text-center pt-6 pb-4">
        <h1 className="text-2xl font-bold text-text-primary">Quick Actions</h1>
        <p className="text-text-muted mt-1">Add data on the go</p>
      </div>

      {/* Actions */}
      <div className="flex-1 space-y-4 px-2">
        <QuickAction
          icon={RefreshCw}
          label="Sync Bank"
          description="Fetch latest transactions from your bank"
          onClick={() => sync.checkAndSync()}
          variant="primary"
          isLoading={sync.step === 'syncing'}
          disabled={sync.step === 'syncing'}
        />

        <QuickAction
          icon={Banknote}
          label="Cash Expense"
          description="Quick entry for cash payments"
          onClick={() => setIsCashModalOpen(true)}
        />

        <QuickAction
          icon={Plus}
          label="Add Transaction"
          description="Full transaction form with all options"
          onClick={() => setIsAddModalOpen(true)}
        />
      </div>

      {/* Footer link to full app */}
      <div className="py-6 text-center">
        <Link
          to="/dashboard"
          className="text-sm text-text-muted hover:text-text-secondary transition-colors"
        >
          Go to full dashboard →
        </Link>
      </div>

      {/* Modals */}
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

      <CashExpenseModal
        isOpen={isCashModalOpen}
        onClose={() => setIsCashModalOpen(false)}
      />

      <AddTransactionModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
      />
    </div>
  )
}
