/**
 * Reusable modal for displaying sync progress with streaming updates.
 *
 * Shows:
 * 1. Progress indicator with phases (connecting → fetching → classifying)
 * 2. Transaction counter with progress bar
 * 3. Success/error states with summary
 */

import { CheckCircle2, XCircle, CloudOff } from 'lucide-react'
import {
  Modal,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
} from '@/components/ui'
import { SyncProgressDisplay } from '@/components/SyncProgressDisplay'
import { cn } from '@/lib/utils'
import type { SyncProgress } from '@/hooks/useSyncProgress'
import type { SyncResultEvent } from '@/api'

interface SyncProgressModalProps {
  /** Whether the modal is open */
  open: boolean
  /** Close the modal */
  onClose: () => void

  // === State from useSyncProgress ===
  /** Progress data (null when not syncing) */
  progress: SyncProgress | null
  /** Final result (null until success) */
  result: SyncResultEvent | null
  /** Error message */
  error: string

  // === Actions ===
  /** Skip sync option (optional) */
  onSkipSync?: () => void

  // === Customization ===
  /** Bank name for context (e.g., "Sparkasse") */
  bankName?: string
  /** Show skip button */
  showSkipOption?: boolean
}

/** Sync step for display purposes */
type SyncDisplayStep = 'syncing' | 'success' | 'error' | 'nothing_to_sync'

export function SyncProgressModal({
  open,
  onClose,
  progress,
  result,
  error,
  onSkipSync,
  bankName,
  showSkipOption = false,
}: SyncProgressModalProps) {
  // Determine current display step
  const step: SyncDisplayStep = error
    ? 'error'
    : result
      ? result.accounts_synced === 0 && result.total_imported === 0
        ? 'nothing_to_sync'
        : 'success'
      : 'syncing'

  const handleClose = () => {
    onClose()
  }

  return (
    <Modal isOpen={open} onClose={handleClose}>
      <ModalHeader onClose={handleClose}>
        {getModalTitle(step, bankName)}
      </ModalHeader>

      <ModalBody>
        {/* Syncing state with progress */}
        {step === 'syncing' && <SyncProgressDisplay progress={progress} />}

        {/* Success state */}
        {step === 'success' && result && <SuccessState result={result} />}

        {/* Nothing to sync state */}
        {step === 'nothing_to_sync' && <NothingToSyncState />}

        {/* Error state */}
        {step === 'error' && <ErrorState error={error} />}
      </ModalBody>

      <ModalFooter>
        {/* Syncing - no actions, just show progress */}
        {step === 'syncing' && (
          <p className="text-sm text-text-muted">
            Please wait while we sync your transactions...
          </p>
        )}

        {/* Success actions */}
        {(step === 'success' || step === 'nothing_to_sync') && (
          <Button onClick={onClose}>
            Done
          </Button>
        )}

        {/* Error actions */}
        {step === 'error' && (
          <>
            {showSkipOption && onSkipSync && (
              <Button variant="ghost" onClick={onSkipSync}>
                Skip
              </Button>
            )}
            <Button variant="ghost" onClick={onClose}>
              Close
            </Button>
          </>
        )}
      </ModalFooter>
    </Modal>
  )
}

/** Success state with summary */
function SuccessState({ result }: { result: SyncResultEvent }) {
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

/** Nothing to sync state - all accounts are up to date */
function NothingToSyncState() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col items-center justify-center py-4 gap-3">
        <CheckCircle2 className="h-12 w-12 text-accent-success" />
        <p className="text-text-primary font-medium">All accounts are up to date</p>
      </div>

      <div className="text-center text-sm text-text-secondary">
        <p>
          Your transactions are already synchronized with your bank.
          No new transactions were found.
        </p>
      </div>
    </div>
  )
}

/** Get modal title based on current step */
function getModalTitle(step: SyncDisplayStep, bankName?: string): string {
  const bank = bankName ? ` from ${bankName}` : ''
  switch (step) {
    case 'syncing':
      return `Syncing Transactions${bank}`
    case 'success':
      return 'Sync Complete'
    case 'nothing_to_sync':
      return 'Sync Status'
    case 'error':
      return 'Sync Failed'
  }
}
