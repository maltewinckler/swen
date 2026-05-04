/**
 * Modal for reclassifying draft transactions via ML with streaming progress.
 *
 * Shows:
 * 1. ML classification progress bar
 * 2. Live feed of reclassified transactions (old → new account)
 * 3. Success summary with counts
 * 4. Error state
 */

import { CheckCircle2, XCircle, RefreshCw, Loader2, ArrowRight } from 'lucide-react'
import {
  Modal,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
} from '@/components/ui'
import { cn } from '@/lib/utils'
import type { ReclassifyProgress, ReclassifyStep } from '@/hooks/useReclassifyProgress'
import type { ReclassifyResultEvent } from '@/api/transactions'

interface ReclassifyProgressModalProps {
  open: boolean
  onClose: () => void
  step: ReclassifyStep
  progress: ReclassifyProgress | null
  result: ReclassifyResultEvent | null
  error: string
  onRetry?: () => void
}

export function ReclassifyProgressModal({
  open,
  onClose,
  step,
  progress,
  result,
  error,
  onRetry,
}: ReclassifyProgressModalProps) {
  const canClose = step !== 'running'

  const handleClose = () => {
    if (canClose) onClose()
  }

  return (
    <Modal isOpen={open} onClose={handleClose}>
      <ModalHeader onClose={canClose ? handleClose : undefined}>
        {getTitle(step)}
      </ModalHeader>

      <ModalBody>
        {step === 'running' && <RunningState progress={progress} />}
        {step === 'success' && result && <SuccessState result={result} />}
        {step === 'error' && <ErrorState error={error} />}
      </ModalBody>

      <ModalFooter>
        {step === 'running' && (
          <p className="text-sm text-text-muted">
            Reclassifying transactions...
          </p>
        )}
        {step === 'success' && (
          <Button onClick={onClose}>Done</Button>
        )}
        {step === 'error' && (
          <>
            <Button variant="ghost" onClick={onClose}>Close</Button>
            {onRetry && (
              <Button onClick={onRetry}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Retry
              </Button>
            )}
          </>
        )}
      </ModalFooter>
    </Modal>
  )
}

function getTitle(step: ReclassifyStep): string {
  switch (step) {
    case 'running': return 'Reclassifying Drafts'
    case 'success': return 'Reclassification Complete'
    case 'error': return 'Reclassification Failed'
    default: return 'Reclassify Drafts'
  }
}

function RunningState({ progress }: { progress: ReclassifyProgress | null }) {
  if (!progress) {
    return (
      <div className="flex flex-col items-center justify-center py-8 gap-4">
        <Loader2 className="h-8 w-8 animate-spin text-accent-primary" />
        <p className="text-text-secondary">Initializing...</p>
      </div>
    )
  }

  const { phase, current, total, lastMessage, lastDescription, lastOldAccount, lastNewAccount, reclassifiedCount } = progress
  const progressPercent = total > 0 ? (current / total) * 100 : 0

  return (
    <div className="space-y-6">
      {/* Phase steps */}
      <div className="space-y-3">
        <PhaseStep
          label={phase === 'classifying'
            ? `Classifying ${current} / ${total} transactions`
            : `Classified ${total} transactions`}
          status={phase === 'classifying' ? 'active' : 'done'}
        />
        <PhaseStep
          label={reclassifiedCount > 0
            ? `${reclassifiedCount} transaction${reclassifiedCount !== 1 ? 's' : ''} reclassified`
            : 'Applying new classifications'}
          status={phase === 'applying' ? 'active' : phase === 'complete' ? 'done' : 'pending'}
        />
      </div>

      {/* Progress bar */}
      {total > 0 && (
        <div className="space-y-2">
          <div className="h-2 bg-bg-elevated rounded-full overflow-hidden">
            <div
              className="h-full bg-accent-primary transition-all duration-300 ease-out"
              style={{ width: `${Math.min(progressPercent, 100)}%` }}
            />
          </div>
          <p className="text-xs text-text-muted text-right">{Math.round(progressPercent)}%</p>
        </div>
      )}

      {/* Live reclassification feed */}
      {lastDescription && lastNewAccount && (
        <div className="bg-bg-elevated rounded-lg p-3 space-y-1">
          <p className="text-xs text-text-muted">Last reclassified</p>
          <p className="text-sm text-text-primary truncate">{lastDescription}</p>
          <div className="flex items-center gap-2 text-xs">
            <span className="text-text-muted">{lastOldAccount}</span>
            <ArrowRight className="h-3 w-3 text-text-muted flex-shrink-0" />
            <span className="text-accent-primary font-medium">{lastNewAccount}</span>
          </div>
        </div>
      )}

      {/* Status message */}
      <p className="text-sm text-text-secondary text-center">{lastMessage}</p>
    </div>
  )
}

function SuccessState({ result }: { result: ReclassifyResultEvent }) {
  return (
    <div className="flex flex-col items-center py-6 gap-4">
      <CheckCircle2 className="h-12 w-12 text-accent-success" />
      <div className="text-center space-y-2">
        <p className="text-lg font-medium text-text-primary">
          {result.reclassified_count > 0
            ? `${result.reclassified_count} transaction${result.reclassified_count !== 1 ? 's' : ''} reclassified`
            : 'No changes needed'}
        </p>
        <div className="text-sm text-text-secondary space-y-1">
          <p>{result.total_drafts} draft{result.total_drafts !== 1 ? 's' : ''} analyzed</p>
          {result.unchanged_count > 0 && (
            <p>{result.unchanged_count} unchanged</p>
          )}
          {result.failed_count > 0 && (
            <p className="text-accent-danger">{result.failed_count} failed</p>
          )}
        </div>
      </div>
    </div>
  )
}

function ErrorState({ error }: { error: string }) {
  return (
    <div className="flex flex-col items-center py-6 gap-4">
      <XCircle className="h-12 w-12 text-accent-danger" />
      <div className="text-center">
        <p className="text-text-primary font-medium">Reclassification failed</p>
        <p className="text-sm text-text-secondary mt-1">{error}</p>
      </div>
    </div>
  )
}

function PhaseStep({
  label,
  status,
}: {
  label: string
  status: 'pending' | 'active' | 'done'
}) {
  return (
    <div className="flex items-center gap-3">
      {status === 'done' && (
        <CheckCircle2 className="h-5 w-5 text-accent-success flex-shrink-0" />
      )}
      {status === 'active' && (
        <Loader2 className="h-5 w-5 text-accent-primary animate-spin flex-shrink-0" />
      )}
      {status === 'pending' && (
        <div className="h-5 w-5 rounded-full border-2 border-border-default flex-shrink-0" />
      )}
      <span className={cn(
        'text-sm',
        status === 'active' && 'text-text-primary font-medium',
        status === 'done' && 'text-text-secondary',
        status === 'pending' && 'text-text-muted',
      )}>
        {label}
      </span>
    </div>
  )
}
