import * as React from 'react'
import { AlertTriangle } from 'lucide-react'
import { Modal, ModalHeader, ModalBody, ModalFooter } from './modal'
import { Button } from './button'
import { cn } from '@/lib/utils'

type ConfirmVariant = 'default' | 'danger'

export interface ConfirmDialogProps {
  isOpen: boolean
  title: React.ReactNode
  description?: React.ReactNode

  confirmLabel?: string
  cancelLabel?: string
  variant?: ConfirmVariant

  isLoading?: boolean
  onConfirm: () => void
  onCancel: () => void

  /** When true, clicking backdrop closes the dialog (disabled while loading). */
  closeOnBackdropClick?: boolean
}

export function ConfirmDialog({
  isOpen,
  title,
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'default',
  isLoading = false,
  onConfirm,
  onCancel,
  closeOnBackdropClick = true,
}: ConfirmDialogProps) {
  const canClose = !isLoading
  const handleClose = () => {
    if (!canClose) return
    onCancel()
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      size="md"
      closeOnBackdropClick={closeOnBackdropClick && canClose}
    >
      <ModalHeader onClose={canClose ? handleClose : undefined}>
        {title}
      </ModalHeader>

      <ModalBody className="space-y-3">
        <div className="flex items-start gap-3">
          <div
            className={cn(
              'flex h-10 w-10 items-center justify-center rounded-full flex-shrink-0',
              variant === 'danger'
                ? 'bg-accent-danger/10'
                : 'bg-accent-warning/10'
            )}
          >
            <AlertTriangle
              className={cn(
                'h-5 w-5',
                variant === 'danger' ? 'text-accent-danger' : 'text-accent-warning'
              )}
            />
          </div>
          <div className="text-sm text-text-secondary">
            {description ?? 'Are you sure you want to continue?'}
          </div>
        </div>
      </ModalBody>

      <ModalFooter>
        <Button
          type="button"
          variant="secondary"
          onClick={handleClose}
          disabled={!canClose}
        >
          {cancelLabel}
        </Button>
        <Button
          type="button"
          variant={variant === 'danger' ? 'danger' : 'primary'}
          onClick={onConfirm}
          isLoading={isLoading}
        >
          {confirmLabel}
        </Button>
      </ModalFooter>
    </Modal>
  )
}
