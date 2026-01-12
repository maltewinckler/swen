import { useState, useEffect, useCallback, useRef, useImperativeHandle, forwardRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Calendar,
  ArrowUpRight,
  ArrowDownRight,
  Sparkles,
  Brain,
  Building2,
  Hash,
  Clock,
  FileText,
  ArrowRight,
  AlertCircle,
  AlertTriangle,
  Check,
  ChevronLeft,
  ChevronRight,
  Loader2,
  Pencil,
  Save,
} from 'lucide-react'
import { Modal, ModalHeader, ModalBody, ModalFooter } from '@/components/ui/modal'
import { Badge, Amount, Spinner, Button, Input, FormField, ConfirmDialog, Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui'
import { getTransaction, updateTransaction, postTransaction, deleteTransaction } from '@/api'
import { formatDate, formatIban } from '@/lib/utils'
import type { Transaction, JournalEntry } from '@/types/api'
import { JournalEntryEditor, type EditableEntry } from './JournalEntryEditor'

interface TransactionDetailModalProps {
  transactionId: string | null
  transactionIds?: string[] // List of all transaction IDs for navigation
  onClose: () => void
  onNavigate?: (transactionId: string) => void // Callback when navigating to a different transaction
  isReviewMode?: boolean // When true, opens in edit mode
}

export function TransactionDetailModal({
  transactionId,
  transactionIds = [],
  onClose,
  onNavigate,
  isReviewMode = false,
}: TransactionDetailModalProps) {
  const queryClient = useQueryClient()

  // Local edit mode state (can be toggled even without review mode)
  const [isEditMode, setIsEditMode] = useState(false)

  // Ref to access TransactionContent imperative methods
  const contentRef = useRef<TransactionContentHandle>(null)
  // State to track content's save state for footer buttons
  const [contentState, setContentState] = useState({ hasChanges: false, isSaving: false, isBalanced: true })

  // When review mode is active, always start in edit mode
  useEffect(() => {
    if (isReviewMode && transactionId) {
      setIsEditMode(true)
    }
  }, [isReviewMode, transactionId])

  // Reset edit mode when modal closes
  useEffect(() => {
    if (!transactionId) {
      setIsEditMode(false)
    }
  }, [transactionId])

  const { data: transaction, isLoading, error } = useQuery({
    queryKey: ['transaction', transactionId],
    queryFn: () => getTransaction(transactionId!),
    enabled: !!transactionId,
  })

  const isOpen = !!transactionId

  // Navigation logic
  const currentIndex = transactionId ? transactionIds.indexOf(transactionId) : -1
  const hasPrevious = currentIndex > 0
  const hasNext = currentIndex >= 0 && currentIndex < transactionIds.length - 1

  const navigateToPrevious = useCallback(() => {
    if (hasPrevious && onNavigate) {
      onNavigate(transactionIds[currentIndex - 1])
    }
  }, [hasPrevious, onNavigate, transactionIds, currentIndex])

  const navigateToNext = useCallback(() => {
    if (hasNext && onNavigate) {
      onNavigate(transactionIds[currentIndex + 1])
    }
  }, [hasNext, onNavigate, transactionIds, currentIndex])

  // Post mutation
  const postMutation = useMutation({
    mutationFn: () => postTransaction(transactionId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transaction', transactionId] })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: () => deleteTransaction(transactionId!, transaction?.is_posted ?? false),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      onClose()
    },
  })

  if (!isOpen) return null

  // Navigation indicator
  const navigationInfo =
    transactionIds.length > 1
      ? `${currentIndex + 1} of ${transactionIds.length}`
      : null

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl">
      <ModalHeader onClose={onClose}>
        <div className="flex items-center gap-3">
          {isEditMode ? (
            <>
              <Pencil className="h-4 w-4 text-accent-primary" />
              <span>Edit Transaction</span>
            </>
          ) : (
            <span>Transaction Details</span>
          )}
          {navigationInfo && (
            <span className="text-sm font-normal text-text-muted">
              ({navigationInfo})
            </span>
          )}
          {isReviewMode && (
            <Badge variant="info" className="ml-2">Review Mode</Badge>
          )}
        </div>
      </ModalHeader>
      <ModalBody className="space-y-6">
        {isLoading ? (
          <div className="flex items-center justify-center h-48">
            <Spinner size="lg" />
          </div>
        ) : error ? (
          <div className="text-center text-accent-danger py-8">
            Failed to load transaction details
          </div>
        ) : transaction ? (
          <TransactionContent
            ref={contentRef}
            transaction={transaction}
            isEditMode={isEditMode}
            isReviewMode={isReviewMode}
            onDelete={() => deleteMutation.mutate()}
            isDeleting={deleteMutation.isPending}
            onSaveAndNext={navigateToNext}
            onEditModeChange={setIsEditMode}
            onStateChange={setContentState}
          />
        ) : null}
      </ModalBody>
      <ModalFooter>
        <div className="flex items-center justify-between w-full gap-4">
          {/* Navigation buttons - compact in edit mode */}
          <div className="flex items-center gap-1 flex-shrink-0">
            <Tooltip>
              <TooltipTrigger asChild>
                <span className="inline-flex">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={navigateToPrevious}
                    disabled={!hasPrevious}
                    aria-label="Previous transaction"
                    className="px-2"
                  >
                    <ChevronLeft className="h-4 w-4" />
                    {!isEditMode && <span className="hidden sm:inline">Previous</span>}
                  </Button>
                </span>
              </TooltipTrigger>
              <TooltipContent>Previous transaction (←)</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <span className="inline-flex">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={navigateToNext}
                    disabled={!hasNext}
                    aria-label="Next transaction"
                    className="px-2"
                  >
                    {!isEditMode && <span className="hidden sm:inline">Next</span>}
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </span>
              </TooltipTrigger>
              <TooltipContent>Next transaction (→)</TooltipContent>
            </Tooltip>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2 flex-shrink-0">
            {/* Edit mode: Save buttons */}
            {isEditMode && transaction && (
              <>
                {contentState.hasChanges && (
                  <span className="text-xs text-accent-warning whitespace-nowrap hidden sm:inline">
                    Unsaved
                  </span>
                )}
                {!isReviewMode && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => contentRef.current?.cancel()}
                    disabled={contentState.isSaving}
                    className="whitespace-nowrap"
                  >
                    Cancel
                  </Button>
                )}
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span className="inline-flex">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => contentRef.current?.save()}
                        disabled={!contentState.hasChanges || contentState.isSaving || !contentState.isBalanced}
                        aria-label="Save"
                        className="whitespace-nowrap"
                      >
                        {contentState.isSaving ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <>
                            <Save className="h-4 w-4" />
                            <span className="hidden sm:inline">Save</span>
                          </>
                        )}
                      </Button>
                    </span>
                  </TooltipTrigger>
                  <TooltipContent>
                    {!contentState.isBalanced ? 'Entries must be balanced' : 'Save (Ctrl+S)'}
                  </TooltipContent>
                </Tooltip>
                {hasNext && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span className="inline-flex">
                        <Button
                          variant="primary"
                          size="sm"
                          onClick={() => contentRef.current?.saveAndNext()}
                          disabled={contentState.isSaving || !contentState.isBalanced}
                          aria-label="Save & Next"
                          className="whitespace-nowrap"
                        >
                          {contentState.isSaving ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <>
                              <span className="hidden sm:inline">Save &</span> Next
                              <ChevronRight className="h-4 w-4" />
                            </>
                          )}
                        </Button>
                      </span>
                    </TooltipTrigger>
                    <TooltipContent>
                      {!contentState.isBalanced ? 'Entries must be balanced' : 'Save and go to next (Ctrl+Enter)'}
                    </TooltipContent>
                  </Tooltip>
                )}
              </>
            )}
            {/* View mode: Edit button */}
            {!isEditMode && transaction && (
              <Button
                variant="secondary"
                onClick={() => setIsEditMode(true)}
              >
                <Pencil className="h-4 w-4" />
                Edit
              </Button>
            )}
            {/* Post button (only for drafts in view mode) */}
            {!isEditMode && transaction && !transaction.is_posted && (
              <Button
                variant="primary"
                onClick={() => postMutation.mutate()}
                disabled={postMutation.isPending}
                className="whitespace-nowrap"
              >
                {postMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Posting...
                  </>
                ) : (
                  <>
                    <Check className="h-4 w-4" />
                    Post
                  </>
                )}
              </Button>
            )}
          </div>
        </div>
      </ModalFooter>
    </Modal>
  )
}

interface TransactionContentProps {
  transaction: Transaction
  isEditMode: boolean
  isReviewMode: boolean
  onDelete: () => void
  isDeleting: boolean
  onSaveAndNext: () => void
  onEditModeChange: (isEdit: boolean) => void
  onStateChange?: (state: { hasChanges: boolean; isSaving: boolean; isBalanced: boolean }) => void
}

// Handle for imperative actions from parent
interface TransactionContentHandle {
  save: () => Promise<void>
  saveAndNext: () => Promise<void>
  cancel: () => void
  hasChanges: boolean
  isSaving: boolean
  isBalanced: boolean
  saveError: Error | null
}

const TransactionContent = forwardRef<TransactionContentHandle, TransactionContentProps>(
  function TransactionContent(
    {
      transaction,
      isEditMode,
      isReviewMode,
      onDelete,
      isDeleting,
      onSaveAndNext,
      onEditModeChange,
      onStateChange,
    },
    ref
  ) {
  const queryClient = useQueryClient()

  // Editable fields state
  const [editDescription, setEditDescription] = useState(transaction.description)
  const [editCounterparty, setEditCounterparty] = useState(transaction.counterparty || '')

  // Entry editing state
  const [editableEntries, setEditableEntries] = useState<EditableEntry[]>([])

  // State for delete confirmation
  const [deleteConfirmAmount, setDeleteConfirmAmount] = useState('')
  const [showDeleteDraftConfirm, setShowDeleteDraftConfirm] = useState(false)

  // Derived values
  const isExpense = transaction.entries.some(
    (e) => e.account_type === 'expense' && e.debit
  )
  // Check if this is a bank import (now a first-class field on transaction)
  const isBankImport = transaction.source === 'bank_import'

  // Find the main amount from entries
  const mainEntry = transaction.entries.find(
    (e) => e.account_type === 'asset'
  )
  const getAmount = (entry: JournalEntry | undefined) => {
    if (!entry) return 0
    const debit = parseFloat(entry.debit || '0')
    const credit = parseFloat(entry.credit || '0')
    return debit > 0 ? debit : credit
  }
  const amount = getAmount(mainEntry)
  const currency = mainEntry?.currency || 'EUR'

  // Display title truncation for very long descriptions (use explicit "[...]" marker)
  const titleSuffix = '[...]'
  const titleMaxLen = 80
  const isTitleTruncated = transaction.description.length > titleMaxLen
  const displayTitle = isTitleTruncated
    ? transaction.description.slice(0, Math.max(0, titleMaxLen - titleSuffix.length)) + titleSuffix
    : transaction.description

  // Initialize when transaction changes
  useEffect(() => {
    setEditDescription(transaction.description)
    setEditCounterparty(transaction.counterparty || '')
    setEditableEntries([])
    setDeleteConfirmAmount('')
    setShowDeleteDraftConfirm(false)
  }, [transaction.id, transaction.description, transaction.counterparty])

  const aiResolution = transaction.metadata?.ai_resolution

  // Check if entries have changed
  const entriesHaveChanged = useCallback(() => {
    if (editableEntries.length === 0) return false

    // Check if any new entries were added or existing entries modified
    const originalNonProtected = transaction.entries.filter(
      (e) => !(isBankImport && e.account_type === 'asset')
    )
    const editedNonProtected = editableEntries.filter((e) => !e.isProtected)

    if (originalNonProtected.length !== editedNonProtected.length) return true

    // Check for value changes
    for (const edited of editedNonProtected) {
      if (edited.isNew) return true
      const original = originalNonProtected.find(
        (o) => o.account_id === edited.accountId
      )
      if (!original) return true
      if ((original.debit || '') !== edited.debit) return true
      if ((original.credit || '') !== edited.credit) return true
    }

    return false
  }, [editableEntries, transaction.entries, isBankImport])

  // Check if there are changes
  const hasChanges =
    editDescription !== transaction.description ||
    editCounterparty !== (transaction.counterparty || '') ||
    entriesHaveChanged()

  // Validate entries are balanced
  const entriesAreBalanced = useCallback(() => {
    if (editableEntries.length === 0) return true

    let totalDebit = 0
    let totalCredit = 0

    editableEntries.forEach((entry) => {
      totalDebit += parseFloat(entry.debit) || 0
      totalCredit += parseFloat(entry.credit) || 0
    })

    return Math.abs(totalDebit - totalCredit) < 0.001 && totalDebit > 0
  }, [editableEntries])

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: async () => {
      const updates: Parameters<typeof updateTransaction>[1] = {}

      if (editDescription !== transaction.description) {
        updates.description = editDescription
      }
      if (editCounterparty !== (transaction.counterparty || '')) {
        updates.counterparty = editCounterparty || undefined
      }

      if (entriesHaveChanged()) {
        // Send only non-protected entries for bank imports
        // The backend will preserve protected entries automatically
        const entriesToSend = editableEntries
          .filter((e) => !e.isProtected && e.accountId)
          .map((e) => ({
            account_id: e.accountId,
            debit: e.debit || '0',
            credit: e.credit || '0',
          }))
        updates.entries = entriesToSend
      }

      return updateTransaction(transaction.id, updates)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transaction', transaction.id] })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      // Exit edit mode after save (unless in review mode)
      if (!isReviewMode) {
        onEditModeChange(false)
      }
    },
  })

  // Notify parent of state changes for footer buttons
  useEffect(() => {
    onStateChange?.({
      hasChanges,
      isSaving: updateMutation.isPending,
      isBalanced: entriesAreBalanced(),
    })
  }, [hasChanges, updateMutation.isPending, entriesAreBalanced, onStateChange])

  // Handle save
  const handleSave = () => {
    if (hasChanges) {
      updateMutation.mutate()
    }
  }

  // Handle save and next
  const handleSaveAndNext = async () => {
    if (hasChanges) {
      await updateMutation.mutateAsync()
    }
    onSaveAndNext()
  }

  // Handle cancel
  const handleCancel = () => {
    setEditDescription(transaction.description)
    setEditCounterparty(transaction.counterparty || '')
    setEditableEntries([])
    onEditModeChange(false)
  }

  // Expose imperative handle for parent component
  useImperativeHandle(ref, () => ({
    save: async () => {
      if (hasChanges) {
        await updateMutation.mutateAsync()
      }
    },
    saveAndNext: handleSaveAndNext,
    cancel: handleCancel,
    hasChanges,
    isSaving: updateMutation.isPending,
    isBalanced: entriesAreBalanced(),
    saveError: updateMutation.isError ? (updateMutation.error as Error) : null,
  }), [hasChanges, updateMutation.isPending, updateMutation.isError, updateMutation.error, entriesAreBalanced])

  // Keyboard shortcuts for edit mode
  useEffect(() => {
    if (!isEditMode) return

    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl+S or Cmd+S to save
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault()
        handleSave()
      }
      // Ctrl+Enter or Cmd+Enter to save and next
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault()
        handleSaveAndNext()
      }
      // Escape to cancel (only if not in an input)
      if (e.key === 'Escape' && !isReviewMode) {
        handleCancel()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isEditMode, hasChanges, isReviewMode])

  return (
    <div className="space-y-6">
      {/* Header with amount */}
      <div className="flex items-start gap-4">
        <div className={`
          flex items-center justify-center h-14 w-14 rounded-2xl
          ${isExpense ? 'bg-accent-danger/10' : 'bg-accent-success/10'}
        `}>
          {isExpense ? (
            <ArrowDownRight className="h-7 w-7 text-accent-danger" />
          ) : (
            <ArrowUpRight className="h-7 w-7 text-accent-success" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          {isEditMode ? (
            <Input
              value={editDescription}
              onChange={(e) => setEditDescription(e.target.value)}
              className="text-lg font-semibold"
              placeholder="Transaction description"
            />
          ) : (
            isTitleTruncated ? (
              <Tooltip>
                <TooltipTrigger asChild>
                  <h3 className="text-xl font-semibold text-text-primary">
                    {displayTitle}
                  </h3>
                </TooltipTrigger>
                <TooltipContent className="max-w-md break-words">
                  {transaction.description}
                </TooltipContent>
              </Tooltip>
            ) : (
              <h3 className="text-xl font-semibold text-text-primary">
                {displayTitle}
              </h3>
            )
          )}
          <div className="flex items-center gap-2 mt-1">
            <Badge variant={transaction.is_posted ? 'success' : 'warning'}>
              {transaction.is_posted ? 'Posted' : 'Draft'}
            </Badge>
            {isBankImport && (
              <Badge variant="default">Bank Import</Badge>
            )}
            {transaction.is_internal_transfer && (
              <Badge variant="info">Internal Transfer</Badge>
            )}
          </div>
        </div>
        <Amount
          value={isExpense ? -amount : amount}
          currency={currency}
          showSign
          className="text-2xl font-bold"
        />
      </div>

      {/* Editable fields in edit mode */}
      {isEditMode && (
        <div className="space-y-4 p-4 bg-bg-base rounded-xl border border-border-subtle">
          <FormField label="Counterparty" helperText="Merchant, employer, or payer">
            <Input
              value={editCounterparty}
              onChange={(e) => setEditCounterparty(e.target.value)}
              placeholder="e.g., REWE, Amazon"
              leftIcon={<Building2 className="h-4 w-4" />}
            />
          </FormField>

          {/* Journal Entry Editor - only shown for draft transactions in normal edit area */}
          {!transaction.is_internal_transfer && !transaction.is_posted && (
            <JournalEntryEditor
              entries={transaction.entries}
              isBankImport={isBankImport}
              onChange={setEditableEntries}
              disabled={updateMutation.isPending}
            />
          )}
        </div>
      )}

      {/* Basic Info (read-only in view mode, hidden in edit mode since we show editable fields) */}
      {!isEditMode && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <InfoItem
              icon={<Calendar className="h-4 w-4" />}
              label="Date"
              value={formatDate(transaction.date)}
            />
            <InfoItem
              icon={<Clock className="h-4 w-4" />}
              label="Created"
              value={formatDate(transaction.created_at)}
            />
            <InfoItem
              icon={<Building2 className="h-4 w-4" />}
              label="Counterparty"
              value={transaction.counterparty || '—'}
            />
            {transaction.bank_reference ? (
              <InfoItem
                icon={<FileText className="h-4 w-4" />}
                label="Bank Reference"
                value={transaction.bank_reference}
              />
            ) : (
              <InfoItem
                icon={<Hash className="h-4 w-4" />}
                label="Transaction ID"
                value={transaction.id.slice(0, 8)}
                mono
              />
            )}
          </div>
          {transaction.counterparty_iban && (
            <div className="flex items-center gap-3 p-3 bg-bg-base rounded-lg">
              <div className="text-text-muted">
                <Hash className="h-4 w-4" />
              </div>
              <div>
                <p className="text-xs text-text-muted">Counterparty IBAN</p>
                <p className="text-sm text-text-primary font-medium font-mono">
                  {formatIban(transaction.counterparty_iban)}
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Journal Entries (read-only when not in edit mode) */}
      {!isEditMode && (
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-text-secondary flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Journal Entries
          </h4>
          <div className="bg-bg-base rounded-xl border border-border-subtle overflow-hidden">
            <table className="w-full text-sm table-fixed">
              <colgroup>
                <col className="w-auto" />
                <col className="w-28 sm:w-32" />
                <col className="w-28 sm:w-32" />
              </colgroup>
              <thead>
                <tr className="bg-bg-hover text-text-secondary">
                  <th className="text-left p-3 font-medium">Account</th>
                  <th className="text-center py-3 px-2 font-medium">Debit</th>
                  <th className="text-center py-3 px-2 font-medium">Credit</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle">
                {transaction.entries.map((entry, idx) => (
                  <JournalEntryRow
                    key={idx}
                    entry={entry}
                    isProtected={isBankImport && entry.account_type === 'asset'}
                  />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* AI Resolution Info */}
      {aiResolution && (
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-text-secondary flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-accent-primary" />
            AI Classification
          </h4>
          <div className="bg-gradient-to-br from-accent-primary/5 to-accent-secondary/5 rounded-xl border border-accent-primary/20 p-4 space-y-4">
            {/* Confidence */}
            <div className="flex items-center justify-between">
              <span className="text-sm text-text-secondary">Confidence</span>
              <div className="flex items-center gap-2">
                <div className="w-24 h-2 bg-bg-base rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      (aiResolution.confidence || 0) >= 0.8
                        ? 'bg-accent-success'
                        : (aiResolution.confidence || 0) >= 0.6
                        ? 'bg-accent-warning'
                        : 'bg-accent-danger'
                    }`}
                    style={{ width: `${(aiResolution.confidence || 0) * 100}%` }}
                  />
                </div>
                <span className="text-sm font-medium text-text-primary">
                  {Math.round((aiResolution.confidence || 0) * 100)}%
                </span>
              </div>
            </div>

            {/* Suggested Account */}
            {aiResolution.suggested_counter_account_name && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">Suggested Account</span>
                <span className="text-sm font-medium text-text-primary flex items-center gap-1">
                  <ArrowRight className="h-3 w-3" />
                  {aiResolution.suggested_counter_account_name}
                </span>
              </div>
            )}

            {/* Reasoning */}
            {aiResolution.reasoning && (
              <div className="space-y-1">
                <span className="text-sm text-text-secondary flex items-center gap-1">
                  <Brain className="h-3 w-3" />
                  Reasoning
                </span>
                <p className="text-sm text-text-primary bg-bg-base/50 rounded-lg p-3 italic">
                  "{aiResolution.reasoning}"
                </p>
              </div>
            )}

            {/* Model & Timestamp */}
            <div className="flex items-center justify-between pt-2 border-t border-border-subtle text-xs text-text-muted">
              <span>Model: {aiResolution.model || 'Unknown'}</span>
              {aiResolution.resolved_at && (
                <span>Resolved: {formatDate(aiResolution.resolved_at)}</span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* No AI metadata notice */}
      {!aiResolution && !isEditMode && (
        <div className="flex items-center gap-3 p-4 bg-bg-base rounded-xl border border-border-subtle">
          <AlertCircle className="h-5 w-5 text-text-muted" />
          <div>
            <p className="text-sm text-text-secondary">No AI classification data</p>
            <p className="text-xs text-text-muted">
              This transaction was imported before AI was enabled or was manually created
            </p>
          </div>
        </div>
      )}

      {/* Danger Zone (at the bottom, only in edit mode) */}
      {isEditMode && (
        <details className="group pt-4 mt-2 border-t border-accent-danger/30">
          <summary className="flex items-center gap-2 cursor-pointer text-sm font-medium text-accent-danger hover:text-accent-danger/80 list-none">
            <span className="group-open:rotate-90 transition-transform text-xs">▶</span>
            <AlertTriangle className="h-4 w-4" />
            Danger Zone
          </summary>

          <div className="mt-3 rounded-lg border border-accent-danger/30 bg-accent-danger/5 p-4 space-y-6">
            {/* Edit Journal Entries - only for posted transactions */}
            {transaction.is_posted && !transaction.is_internal_transfer && (
              <div className="space-y-3">
                <div>
                  <p className="text-sm font-medium text-text-primary">Edit Journal Entries</p>
                  <p className="text-xs text-text-muted mt-0.5">
                    Modify the accounting entries of this posted transaction.
                    This affects your account balances.
                  </p>
                </div>

                <div className="p-3 bg-bg-surface rounded-lg border border-border-subtle">
                  <JournalEntryEditor
                    entries={transaction.entries}
                    isBankImport={isBankImport}
                    onChange={setEditableEntries}
                    disabled={updateMutation.isPending}
                  />
                </div>
              </div>
            )}

            {/* Divider between sections if both are shown */}
            {transaction.is_posted && !transaction.is_internal_transfer && (
              <div className="border-t border-accent-danger/20" />
            )}

            {/* Delete Transaction */}
            <div>
              <p className="text-sm font-medium text-text-primary">Delete this transaction</p>
              <p className="text-xs text-text-muted mt-0.5">
                {transaction.is_posted
                  ? 'This transaction is posted and affects your account balances. Deletion is permanent.'
                  : 'This draft transaction has not been posted yet. Deletion is permanent.'}
              </p>
            </div>

            {/* For posted transactions: require typing the amount */}
            {transaction.is_posted ? (
              <div className="space-y-2">
                <p className="text-xs text-text-secondary">
                  To confirm, type the amount: <span className="font-mono font-medium text-text-primary">{amount.toFixed(2)}</span>
                </p>
                <div className="flex gap-2">
                  <Input
                    type="text"
                    value={deleteConfirmAmount}
                    onChange={(e) => setDeleteConfirmAmount(e.target.value)}
                    className="flex-1 font-mono"
                    placeholder="0.00"
                    data-testid="delete-confirm-amount"
                  />
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={onDelete}
                    disabled={
                      isDeleting ||
                      parseFloat(deleteConfirmAmount.replace(',', '.')) !== amount
                    }
                    className="border-accent-danger text-accent-danger hover:bg-accent-danger hover:text-white disabled:opacity-50"
                  >
                    {isDeleting ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      'Delete'
                    )}
                  </Button>
                </div>
              </div>
            ) : (
              /* For draft transactions: simple confirmation */
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setShowDeleteDraftConfirm(true)}
                disabled={isDeleting}
                className="border-accent-danger text-accent-danger hover:bg-accent-danger hover:text-white"
              >
                {isDeleting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Deleting...
                  </>
                ) : (
                  'Delete Draft'
                )}
              </Button>
            )}

            <ConfirmDialog
              isOpen={showDeleteDraftConfirm}
              title="Delete draft transaction?"
              description="This will permanently delete the draft transaction. This cannot be undone."
              confirmLabel="Delete"
              cancelLabel="Cancel"
              variant="danger"
              isLoading={isDeleting}
              onCancel={() => setShowDeleteDraftConfirm(false)}
              onConfirm={() => {
                onDelete()
                setShowDeleteDraftConfirm(false)
              }}
            />
          </div>
        </details>
      )}

      {/* Error message for save failures */}
      {isEditMode && updateMutation.isError && (
        <div className="p-3 bg-accent-danger/10 border border-accent-danger/20 rounded-lg">
          <p className="text-sm text-accent-danger">
            {updateMutation.error instanceof Error
              ? updateMutation.error.message
              : 'Failed to save changes'}
          </p>
        </div>
      )}
    </div>
  )
})

function InfoItem({
  icon,
  label,
  value,
  className,
  mono = false,
  title,
}: {
  icon: React.ReactNode
  label: string
  value: string
  className?: string
  mono?: boolean
  title?: string
}) {
  return (
    <div className={`flex items-start gap-3 p-3 bg-bg-base rounded-lg ${className || ''}`}>
      <div className="text-text-muted mt-0.5">{icon}</div>
      <div className="min-w-0">
        <p className="text-xs text-text-muted">{label}</p>
        <p
          className={`text-sm text-text-primary font-medium whitespace-nowrap ${mono ? 'font-mono' : ''}`}
          title={title}
        >
          {value}
        </p>
      </div>
    </div>
  )
}

function JournalEntryRow({
  entry,
  isProtected = false,
}: {
  entry: JournalEntry
  isProtected?: boolean
}) {
  const getAccountTypeColor = (type: string) => {
    switch (type) {
      case 'asset':
        return 'text-blue-400'
      case 'liability':
        return 'text-purple-400'
      case 'expense':
        return 'text-red-400'
      case 'income':
        return 'text-green-400'
      case 'equity':
        return 'text-yellow-400'
      default:
        return 'text-text-secondary'
    }
  }

  return (
    <tr className={`hover:bg-bg-hover/50 ${isProtected ? 'bg-bg-base/50' : ''}`}>
      <td className="p-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-text-primary truncate">{entry.account_name}</span>
          <span className={`text-xs shrink-0 ${getAccountTypeColor(entry.account_type)}`}>
            {entry.account_type}
          </span>
        </div>
      </td>
      <td className="py-3 px-2 text-center whitespace-nowrap align-middle">
        {entry.debit ? (
          <Amount value={entry.debit} currency={entry.currency} colorize={false} className="text-text-primary" />
        ) : (
          <span className="text-text-muted">—</span>
        )}
      </td>
      <td className="py-3 px-2 text-center whitespace-nowrap align-middle">
        {entry.credit ? (
          <Amount value={entry.credit} currency={entry.currency} colorize={false} className="text-text-primary" />
        ) : (
          <span className="text-text-muted">—</span>
        )}
      </td>
    </tr>
  )
}
