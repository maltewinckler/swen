/**
 * Reusable modal for displaying sync progress with streaming updates.
 *
 * Shows:
 * 1. First-sync prompt (if applicable) with days selector
 * 2. Progress indicator with phases (connecting → fetching → classifying)
 * 3. Transaction counter with progress bar
 * 4. Success/error states with summary
 */

import { CheckCircle2, XCircle, RefreshCw, Loader2, ArrowRight, CloudOff } from 'lucide-react'
import {
  Modal,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
} from '@/components/ui'
import { TANApprovalNotice } from '@/components/TANApprovalNotice'
import { SyncProgressDisplay } from '@/components/SyncProgressDisplay'
import { cn } from '@/lib/utils'
import type { SyncProgress, SyncStep } from '@/hooks/useSyncProgress'
import type { SyncRunResponse } from '@/api'

interface SyncProgressModalProps {
  /** Whether the modal is open */
  open: boolean
  /** Close the modal */
  onClose: () => void

  // === State from useSyncProgress ===
  /** Current step in the workflow */
  step: SyncStep
  /** Progress data (null when not syncing) */
  progress: SyncProgress | null
  /** Final result (null until success) */
  result: SyncRunResponse | null
  /** Error message */
  error: string
  /** Days for first-sync */
  firstSyncDays: number

  // === Actions ===
  /** Update days for first-sync */
  onSetFirstSyncDays: (days: number) => void
  /** Confirm first-sync with selected days */
  onConfirmFirstSync: () => void
  /** Skip sync option (optional) */
  onSkipSync?: () => void

  // === Customization ===
  /** Bank name for context (e.g., "Sparkasse") */
  bankName?: string
  /** Show skip button */
  showSkipOption?: boolean
}

/** Preset options for first-sync days */
const FIRST_SYNC_OPTIONS = [
  { days: 30, label: '1 month' },
  { days: 90, label: '3 months' },
  { days: 180, label: '6 months' },
  { days: 365, label: '1 year' },
  { days: 730, label: '2 years' },
]

export function SyncProgressModal({
  open,
  onClose,
  step,
  progress,
  result,
  error,
  firstSyncDays,
  onSetFirstSyncDays,
  onConfirmFirstSync,
  onSkipSync,
  bankName,
  showSkipOption = false,
}: SyncProgressModalProps) {
  // Don't allow closing during sync
  const canClose = step !== 'syncing'

  const handleClose = () => {
    if (canClose) {
      onClose()
    }
  }

  return (
    <Modal isOpen={open} onClose={handleClose}>
      <ModalHeader onClose={canClose ? handleClose : undefined}>
        {getModalTitle(step, bankName)}
      </ModalHeader>

      <ModalBody>
        {/* Checking state */}
        {step === 'checking' && <CheckingState />}

        {/* First sync prompt */}
        {step === 'first_sync_prompt' && (
          <FirstSyncPrompt
            days={firstSyncDays}
            onSetDays={onSetFirstSyncDays}
            bankName={bankName}
          />
        )}

        {/* Syncing state with progress */}
        {step === 'syncing' && <SyncProgressDisplay progress={progress} />}

        {/* Success state */}
        {step === 'success' && result && <SuccessState result={result} />}

        {/* Error state */}
        {step === 'error' && <ErrorState error={error} />}
      </ModalBody>

      <ModalFooter>
        {/* First sync prompt actions */}
        {step === 'first_sync_prompt' && (
          <>
            {showSkipOption && onSkipSync && (
              <Button variant="ghost" onClick={onSkipSync}>
                Skip for now
              </Button>
            )}
            <Button onClick={onConfirmFirstSync}>
              Start Sync
              <ArrowRight className="h-4 w-4 ml-1" />
            </Button>
          </>
        )}

        {/* Syncing - no actions, just show progress */}
        {step === 'syncing' && (
          <p className="text-sm text-text-muted">
            Please wait while we sync your transactions...
          </p>
        )}

        {/* Success actions */}
        {step === 'success' && (
          <Button onClick={onClose}>
            Done
          </Button>
        )}

        {/* Error actions */}
        {step === 'error' && (
          <>
            <Button variant="ghost" onClick={onClose}>
              Close
            </Button>
            <Button onClick={onConfirmFirstSync}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </>
        )}
      </ModalFooter>
    </Modal>
  )
}

/** Get modal title based on current step */
function getModalTitle(step: SyncStep, bankName?: string): string {
  const bank = bankName ? ` from ${bankName}` : ''
  switch (step) {
    case 'checking':
      return 'Preparing Sync'
    case 'first_sync_prompt':
      return 'Initial Sync'
    case 'syncing':
      return `Syncing Transactions${bank}`
    case 'success':
      return 'Sync Complete'
    case 'error':
      return 'Sync Failed'
    default:
      return 'Sync Transactions'
  }
}

/** Loading state while checking sync recommendations */
function CheckingState() {
  return (
    <div className="flex flex-col items-center justify-center py-8 gap-4">
      <Loader2 className="h-8 w-8 animate-spin text-accent-primary" />
      <p className="text-text-secondary">Checking sync status...</p>
    </div>
  )
}

/** First sync prompt with days selector */
function FirstSyncPrompt({
  days,
  onSetDays,
  bankName,
}: {
  days: number
  onSetDays: (days: number) => void
  bankName?: string
}) {
  return (
    <div className="space-y-6">
      <p className="text-text-secondary">
        This is the first time syncing{bankName ? ` with ${bankName}` : ''}.
        How much transaction history would you like to import?
      </p>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {FIRST_SYNC_OPTIONS.map(option => (
          <button
            key={option.days}
            onClick={() => onSetDays(option.days)}
            className={cn(
              'p-4 rounded-xl border-2 transition-all text-center',
              days === option.days
                ? 'border-accent-primary bg-accent-primary/10 text-text-primary'
                : 'border-border-subtle bg-bg-elevated hover:border-border-focus text-text-secondary'
            )}
          >
            <div className="text-lg font-semibold">{option.label}</div>
            <div className="text-xs text-text-muted">{option.days} days</div>
          </button>
        ))}
      </div>

      <TANApprovalNotice
        variant="compact"
        message="Longer periods may require TAN approval and take more time to process."
      />
    </div>
  )
}

/** Success state with summary */
function SuccessState({ result }: { result: SyncRunResponse }) {
  return (
    <div className="space-y-6">
      <div className="flex flex-col items-center justify-center py-4 gap-3">
        <CheckCircle2 className="h-12 w-12 text-accent-success" />
        <p className="text-text-primary font-medium">Sync completed successfully!</p>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-4">
        <StatCard
          label="Imported"
          value={result.total_imported}
          color="text-accent-success"
        />
        <StatCard
          label="Skipped"
          value={result.total_skipped}
          color="text-text-muted"
        />
        <StatCard
          label="Failed"
          value={result.total_failed}
          color={result.total_failed > 0 ? 'text-accent-danger' : 'text-text-muted'}
        />
      </div>

      {result.accounts_synced > 0 && (
        <p className="text-center text-sm text-text-muted">
          {result.accounts_synced} account{result.accounts_synced !== 1 ? 's' : ''} synchronized
        </p>
      )}
    </div>
  )
}

/** Stat card for success summary */
function StatCard({
  label,
  value,
  color,
}: {
  label: string
  value: number
  color: string
}) {
  return (
    <div className="bg-bg-elevated rounded-lg p-4 text-center">
      <div className={cn('text-2xl font-bold', color)}>{value}</div>
      <div className="text-xs text-text-muted">{label}</div>
    </div>
  )
}

/** Error state */
function ErrorState({ error }: { error: string }) {
  return (
    <div className="space-y-6">
      <div className="flex flex-col items-center justify-center py-4 gap-3">
        <XCircle className="h-12 w-12 text-accent-danger" />
        <p className="text-text-primary font-medium">Sync failed</p>
      </div>

      <div className="bg-accent-danger/10 border border-accent-danger/20 rounded-lg p-4">
        <p className="text-sm text-accent-danger">{error}</p>
      </div>

      <div className="flex items-start gap-3 text-sm text-text-muted">
        <CloudOff className="h-5 w-5 flex-shrink-0 mt-0.5" />
        <p>
          This could be due to a network issue or a problem with your bank connection.
          Please try again. If the problem persists, check your bank credentials.
        </p>
      </div>
    </div>
  )
}
