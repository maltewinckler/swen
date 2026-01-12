/**
 * Account Edit Modal
 *
 * Modal for editing account details including name, description, and parent.
 * Uses explicit parent_action to control parent relationship changes.
 */

import { useState, useCallback } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Pencil, AlertTriangle, Loader2 } from 'lucide-react'
import {
  Modal,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  Input,
  FormField,
  Textarea,
  ConfirmDialog,
  useToast,
} from '@/components/ui'
import { updateAccount, deactivateAccount, ApiRequestError } from '@/api'
import type { Account, AccountType, ParentAction } from '@/types/api'
import { ParentAccountSelect } from './ParentAccountSelect'
import {
  normalizeAccountType,
  getAccountIcon,
  getAccountColor,
} from './account-utils'
import { cn } from '@/lib/utils'

interface AccountEditModalProps {
  /** Account to edit */
  account: Account
  /** Whether the modal is open */
  isOpen: boolean
  /** Called when modal is closed */
  onClose: () => void
}

/**
 * Inner form component that resets when account changes.
 * Using a separate component with key={account.id} ensures clean state reset.
 */
function AccountEditForm({
  account,
  onClose,
}: {
  account: Account
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const toast = useToast()

  // Form state - initialized from account props
  const [name, setName] = useState(account.name)
  const [accountNumber, setAccountNumber] = useState(account.account_number)
  const [description, setDescription] = useState(account.description ?? '')
  const [selectedParentId, setSelectedParentId] = useState<string | null>(
    account.parent_id ?? null
  )
  const [showDeactivateConfirm, setShowDeactivateConfirm] = useState(false)

  // Field-level error state
  interface FieldErrors {
    name?: string
    accountNumber?: string
    parent?: string
    general?: string
  }
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})

  // Clear field error when user modifies the field
  const handleNameChange = useCallback((value: string) => {
    setName(value)
    if (fieldErrors.name) {
      setFieldErrors(prev => ({ ...prev, name: undefined }))
    }
  }, [fieldErrors.name])

  const handleAccountNumberChange = useCallback((value: string) => {
    setAccountNumber(value)
    if (fieldErrors.accountNumber) {
      setFieldErrors(prev => ({ ...prev, accountNumber: undefined }))
    }
  }, [fieldErrors.accountNumber])

  const handleParentChange = useCallback((value: string | null) => {
    setSelectedParentId(value)
    if (fieldErrors.parent) {
      setFieldErrors(prev => ({ ...prev, parent: undefined }))
    }
  }, [fieldErrors.parent])

  /**
   * Parse API error and map to field-level errors based on error code
   */
  const parseApiError = (error: unknown): FieldErrors => {
    if (error instanceof ApiRequestError) {
      const code = error.code
      const message = error.message

      // Map error codes to specific fields
      switch (code) {
        case 'DUPLICATE_ACCOUNT':
          return { name: message }
        case 'DUPLICATE_ACCOUNT_NUMBER':
          return { accountNumber: message }
        case 'VALIDATION_ERROR':
          // Check message content to identify field
          if (message.toLowerCase().includes('parent') ||
              message.toLowerCase().includes('hierarchy') ||
              message.toLowerCase().includes('circular')) {
            return { parent: message }
          }
          if (message.toLowerCase().includes('account number')) {
            return { accountNumber: message }
          }
          if (message.toLowerCase().includes('name')) {
            return { name: message }
          }
          return { general: message }
        default:
          return { general: message }
      }
    }

    if (error instanceof Error) {
      return { general: error.message }
    }

    return { general: 'An unexpected error occurred' }
  }

  // Determine what parent action to send based on changes
  const getParentAction = (): ParentAction => {
    const originalParentId = account.parent_id ?? null

    if (selectedParentId === originalParentId) {
      return 'keep' // No change to parent
    }
    if (selectedParentId === null) {
      return 'remove' // User selected "(None)"
    }
    return 'set' // User selected a new parent
  }

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: async () => {
      const parentAction = getParentAction()

      // Only include fields that changed
      const data: Parameters<typeof updateAccount>[1] = {}

      if (name !== account.name) {
        data.name = name
      }

      if (accountNumber !== account.account_number) {
        data.account_number = accountNumber
      }

      if (description !== (account.description ?? '')) {
        data.description = description.trim() || null
      }

      // Always include parent_action, and parent_id when setting
      data.parent_action = parentAction
      if (parentAction === 'set') {
        data.parent_id = selectedParentId
      }

      return updateAccount(account.id, data)
    },
    onSuccess: () => {
      // Clear any field errors on success
      setFieldErrors({})
      // Invalidate queries to refresh data
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
      queryClient.invalidateQueries({ queryKey: ['account', account.id] })
      queryClient.invalidateQueries({ queryKey: ['accountStats', account.id] })
      // Also invalidate transactions since they display account names
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['transaction'] })
      onClose()
    },
    onError: (error) => {
      // Parse error and set field-level errors
      const errors = parseApiError(error)
      setFieldErrors(errors)
    },
  })

  // Deactivate mutation
  const deactivateMutation = useMutation({
    mutationFn: () => deactivateAccount(account.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
      queryClient.invalidateQueries({ queryKey: ['account', account.id] })
      toast.success({ title: 'Account deactivated', description: `"${account.name}" was deactivated.` })
      onClose()
    },
  })

  const handleDeactivate = () => {
    setShowDeactivateConfirm(true)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    updateMutation.mutate()
  }

  const hasChanges =
    name !== account.name ||
    accountNumber !== account.account_number ||
    description !== (account.description ?? '') ||
    selectedParentId !== (account.parent_id ?? null)

  const normalizedType = normalizeAccountType(account.account_type)

  return (
    <form onSubmit={handleSubmit}>
      <ModalHeader onClose={onClose}>
        <div className="flex items-center gap-3">
          <div
            className={cn(
              'flex items-center justify-center h-10 w-10 rounded-lg',
              getAccountColor(normalizedType)
            )}
          >
            {getAccountIcon(normalizedType)}
          </div>
          <div className="flex items-center gap-2">
            <Pencil className="h-4 w-4 text-text-muted" />
            <span>Edit Account</span>
          </div>
        </div>
      </ModalHeader>

      <ModalBody>
        <div className="space-y-4">
          {/* Account type (read-only) */}
          <div className="text-sm text-text-muted">
            {account.account_type}
          </div>

          {/* Account number field */}
          <FormField
            label="Account Number"
            required
            helperText={fieldErrors.accountNumber ? undefined : "Unique chart of accounts code (e.g., 1000, 4900)"}
            error={fieldErrors.accountNumber}
          >
            <Input
              value={accountNumber}
              onChange={(e) => handleAccountNumberChange(e.target.value)}
              placeholder="e.g., 1000"
              required
              minLength={1}
              maxLength={50}
              hasError={!!fieldErrors.accountNumber}
            />
          </FormField>

          {/* Name field */}
          <FormField
            label="Name"
            required
            error={fieldErrors.name}
          >
            <Input
              value={name}
              onChange={(e) => handleNameChange(e.target.value)}
              placeholder="Account name"
              required
              minLength={1}
              maxLength={255}
              hasError={!!fieldErrors.name}
            />
          </FormField>

          {/* Description field */}
          <FormField
            label="Description"
            helperText="Add keywords to help AI classify transactions (e.g., 'Supermarkets: REWE, Lidl, EDEKA')"
          >
            <Textarea
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Keywords for AI classification..."
              maxLength={500}
            />
          </FormField>

          {/* Parent account field */}
          <FormField
            label="Parent Account"
            helperText={fieldErrors.parent ? undefined : "Organize accounts in a hierarchy (max 3 levels)"}
            error={fieldErrors.parent}
          >
            <ParentAccountSelect
              accountId={account.id}
              accountType={account.account_type.toUpperCase() as AccountType}
              value={selectedParentId}
              onChange={handleParentChange}
              disabled={updateMutation.isPending}
              hasError={!!fieldErrors.parent}
            />
          </FormField>

          {/* General error display (for errors not tied to a specific field) */}
          {fieldErrors.general && (
            <div className="p-3 bg-accent-danger/10 border border-accent-danger/20 rounded-lg">
              <p className="text-sm text-accent-danger">
                {fieldErrors.general}
              </p>
            </div>
          )}

          {/* Danger Zone (collapsed by default) */}
          <details className="group pt-4 mt-4 border-t border-accent-danger/30">
            <summary className="flex items-center gap-2 cursor-pointer text-sm font-medium text-accent-danger hover:text-accent-danger/80 list-none">
              <span className="group-open:rotate-90 transition-transform text-xs">▶</span>
              <AlertTriangle className="h-4 w-4" />
              Danger Zone
            </summary>

            <div className="mt-3 rounded-xl border border-accent-danger/30 bg-accent-danger/5 p-4 space-y-3">
              <div>
                <p className="text-sm font-medium text-text-primary">Deactivate this account</p>
                <p className="text-xs text-text-muted mt-0.5">
                  The account will be hidden from lists but preserved in the database.
                  You can reactivate it later if needed.
                </p>
              </div>

              {deactivateMutation.isError && (
                <p className="text-xs text-accent-danger">
                  {deactivateMutation.error instanceof Error
                    ? deactivateMutation.error.message
                    : 'Failed to deactivate account'}
                </p>
              )}

              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={handleDeactivate}
                disabled={deactivateMutation.isPending || updateMutation.isPending}
                className="border-accent-danger text-accent-danger hover:bg-accent-danger hover:text-white"
              >
                {deactivateMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-1.5" />
                    Deactivating...
                  </>
                ) : (
                  'Deactivate Account'
                )}
              </Button>
            </div>
          </details>

          <ConfirmDialog
            isOpen={showDeactivateConfirm}
            title="Deactivate account?"
            description={
              <span>
                Deactivate <strong>{account.name}</strong>? The account will be hidden but can be reactivated later.
              </span>
            }
            confirmLabel="Deactivate"
            cancelLabel="Cancel"
            variant="danger"
            isLoading={deactivateMutation.isPending}
            onCancel={() => setShowDeactivateConfirm(false)}
            onConfirm={() => {
              deactivateMutation.mutate(undefined, {
                onSuccess: () => setShowDeactivateConfirm(false),
                onError: (err) => {
                  toast.danger({
                    title: 'Failed to deactivate account',
                    description: err instanceof Error ? err.message : 'Unknown error',
                  })
                },
              })
            }}
          />
        </div>
      </ModalBody>

      <ModalFooter>
        <Button
          type="button"
          variant="ghost"
          onClick={onClose}
          disabled={updateMutation.isPending}
        >
          Cancel
        </Button>
        <Button
          type="submit"
          variant="primary"
          disabled={!hasChanges || !name.trim() || !accountNumber.trim()}
          isLoading={updateMutation.isPending}
        >
          Save Changes
        </Button>
      </ModalFooter>
    </form>
  )
}

/**
 * Account Edit Modal wrapper.
 * Uses key={account.id} to reset form state when switching accounts.
 */
export function AccountEditModal({ account, isOpen, onClose }: AccountEditModalProps) {
  if (!isOpen) return null

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl">
      <AccountEditForm key={account.id} account={account} onClose={onClose} />
    </Modal>
  )
}
