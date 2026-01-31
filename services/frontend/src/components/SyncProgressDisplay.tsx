/**
 * Reusable sync progress display component.
 *
 * Shows the current state of a sync operation with:
 * - Phase steps (Fetching from bank, Classifying transactions)
 * - Progress bar during classification
 * - TAN approval notice during bank connection
 *
 * Used by:
 * - SyncProgressModal (sync all banks)
 * - Settings page (initial bank setup sync)
 * - Accounts page (single account sync)
 */

import { CheckCircle2, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { TANApprovalNotice } from '@/components/TANApprovalNotice'
import type { SyncProgress } from '@/hooks/useSyncProgress'

interface SyncProgressDisplayProps {
  /** Current sync progress state (null = initializing) */
  progress: SyncProgress | null
  /** Additional CSS classes */
  className?: string
}

export function SyncProgressDisplay({
  progress,
  className,
}: SyncProgressDisplayProps) {
  if (!progress) {
    return (
      <div className={cn('flex flex-col items-center justify-center py-8 gap-4', className)}>
        <Loader2 className="h-8 w-8 animate-spin text-accent-primary" />
        <p className="text-text-secondary">Initializing sync...</p>
      </div>
    )
  }

  const {
    phase,
    accountIndex,
    totalAccounts,
    transactionsCurrent,
    transactionsTotal,
    currentAccountName,
  } = progress

  const progressPercent = transactionsTotal > 0 ? (transactionsCurrent / transactionsTotal) * 100 : 0

  return (
    <div className={cn('space-y-6', className)}>
      {/* Account info */}
      {currentAccountName && (
        <div className="text-center">
          <p className="text-text-muted text-sm">
            Account {accountIndex} of {totalAccounts}
          </p>
          <p className="text-text-primary font-medium">{currentAccountName}</p>
        </div>
      )}

      {/* Phase steps - simplified to 2 meaningful phases */}
      <div className="space-y-3">
        <PhaseStep
          label={transactionsTotal > 0 ? `Fetched ${transactionsTotal} transactions from bank` : 'Fetching transactions from bank'}
          status={getFetchPhaseStatus(phase)}
        />
        <PhaseStep
          label={getClassifyLabel(phase, transactionsCurrent, transactionsTotal)}
          status={getClassifyPhaseStatus(phase, transactionsTotal)}
        />
      </div>

      {/* Progress bar (only during classification) */}
      {phase === 'classifying' && transactionsTotal > 0 && (
        <div className="space-y-2">
          <div className="h-2 bg-bg-elevated rounded-full overflow-hidden">
            <div
              className="h-full bg-accent-primary transition-all duration-300 ease-out"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          <p className="text-center text-sm text-text-muted">
            {transactionsCurrent} / {transactionsTotal}
          </p>
        </div>
      )}

      {/* TAN notice - shown during fetch phase (connecting + fetching) */}
      {(phase === 'connecting' || phase === 'fetching') && (
        <TANApprovalNotice variant="compact" />
      )}
    </div>
  )
}

/** Individual phase step indicator */
function PhaseStep({
  label,
  status,
}: {
  label: string
  status: 'pending' | 'active' | 'complete'
}) {
  return (
    <div className="flex items-center gap-3">
      {status === 'complete' && (
        <CheckCircle2 className="h-5 w-5 text-accent-success flex-shrink-0" />
      )}
      {status === 'active' && (
        <Loader2 className="h-5 w-5 text-accent-primary animate-spin flex-shrink-0" />
      )}
      {status === 'pending' && (
        <div className="h-5 w-5 rounded-full border-2 border-border-subtle flex-shrink-0" />
      )}
      <span
        className={cn(
          'text-sm',
          status === 'complete' && 'text-text-primary',
          status === 'active' && 'text-text-primary font-medium',
          status === 'pending' && 'text-text-muted'
        )}
      >
        {label}
      </span>
    </div>
  )
}

/**
 * Get status for the "Fetching from bank" step.
 * This combines connecting + fetching phases (they happen as one operation).
 */
function getFetchPhaseStatus(
  currentPhase: SyncProgress['phase']
): 'pending' | 'active' | 'complete' {
  // Fetching is active during connecting and fetching phases
  if (currentPhase === 'connecting' || currentPhase === 'fetching') {
    return 'active'
  }
  // Complete once we move to classifying or complete
  if (currentPhase === 'classifying' || currentPhase === 'complete') {
    return 'complete'
  }
  return 'pending'
}

/**
 * Get status for the "Classifying transactions" step.
 * When there are 0 transactions, we still show "complete" (skipped).
 */
function getClassifyPhaseStatus(
  currentPhase: SyncProgress['phase'],
  transactionsTotal: number
): 'pending' | 'active' | 'complete' {
  if (currentPhase === 'classifying') {
    return 'active'
  }
  // When complete (either finished classifying or skipped due to 0 transactions)
  if (currentPhase === 'complete') {
    return 'complete'
  }
  // If we're still fetching but already know there are 0 transactions,
  // show as complete (will be skipped)
  if (currentPhase === 'fetching' && transactionsTotal === 0) {
    return 'complete'
  }
  return 'pending'
}

/**
 * Get label for the classify step based on state.
 */
function getClassifyLabel(
  phase: SyncProgress['phase'],
  current: number,
  total: number
): string {
  // No transactions to classify - show "skipped" message
  if (phase === 'complete' && total === 0) {
    return 'No new transactions to classify'
  }
  // During classification, show progress
  if (phase === 'classifying' && total > 0) {
    return `Classifying transactions (${current}/${total})`
  }
  // After classification, show completed count
  if (phase === 'complete' && total > 0) {
    return `Classified ${total} transactions`
  }
  // Default/pending state
  return 'Classifying transactions'
}
