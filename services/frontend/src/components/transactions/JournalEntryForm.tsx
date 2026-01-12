import { useState, useMemo, useCallback } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Calendar,
  Building2,
  FileText,
  Loader2,
  Plus,
  Trash2,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react'
import {
  Button,
  Input,
  Select,
  FormField,
  Amount,
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from '@/components/ui'
import type { SelectOption } from '@/components/ui'
import { createTransaction, listAccounts } from '@/api'

interface JournalEntry {
  id: string
  accountId: string
  debit: string
  credit: string
}

interface JournalEntryFormProps {
  onSuccess: () => void
  onCancel: () => void
}

function generateId(): string {
  return Math.random().toString(36).substring(2, 9)
}

export function JournalEntryForm({ onSuccess, onCancel }: JournalEntryFormProps) {
  const queryClient = useQueryClient()

  // Form state
  const [description, setDescription] = useState('')
  const [date, setDate] = useState(() => new Date().toISOString().split('T')[0])
  const [counterparty, setCounterparty] = useState('')
  const [autoPost, setAutoPost] = useState(true)
  const [entries, setEntries] = useState<JournalEntry[]>(() => [
    { id: generateId(), accountId: '', debit: '', credit: '' },
    { id: generateId(), accountId: '', debit: '', credit: '' },
  ])

  // Form errors
  const [errors, setErrors] = useState<Record<string, string>>({})

  // Fetch all accounts for dropdowns
  const { data: allAccounts } = useQuery({
    queryKey: ['accounts', 'all'],
    queryFn: () => listAccounts({ is_active: true, size: 200 }),
  })

  // Group accounts by type for the dropdown
  const accountOptions: SelectOption[] = useMemo(() => {
    if (!allAccounts?.items) return []

    const grouped: Record<string, SelectOption[]> = {}

    allAccounts.items.forEach((acc) => {
      const type = acc.account_type.toUpperCase()
      if (!grouped[type]) {
        grouped[type] = []
      }
      grouped[type].push({
        value: acc.id,
        label: `${acc.account_number} - ${acc.name}`,
      })
    })

    // Flatten with group headers
    const options: SelectOption[] = []
    const typeOrder = ['ASSET', 'EXPENSE', 'INCOME', 'LIABILITY', 'EQUITY']

    typeOrder.forEach((type) => {
      if (grouped[type]?.length) {
        // Add group header (disabled option)
        options.push({
          value: `__header_${type}`,
          label: `── ${type} ──`,
          disabled: true,
        })
        options.push(...grouped[type])
      }
    })

    return options
  }, [allAccounts])

  // Calculate totals
  const totals = useMemo(() => {
    let totalDebit = 0
    let totalCredit = 0

    entries.forEach((entry) => {
      const debit = parseFloat(entry.debit) || 0
      const credit = parseFloat(entry.credit) || 0
      totalDebit += debit
      totalCredit += credit
    })

    return {
      debit: totalDebit,
      credit: totalCredit,
      isBalanced: Math.abs(totalDebit - totalCredit) < 0.01 && totalDebit > 0,
    }
  }, [entries])

  // Entry management
  const addEntry = useCallback(() => {
    setEntries((prev) => [
      ...prev,
      { id: generateId(), accountId: '', debit: '', credit: '' },
    ])
  }, [])

  const removeEntry = useCallback((id: string) => {
    setEntries((prev) => {
      if (prev.length <= 2) return prev // Minimum 2 entries
      return prev.filter((e) => e.id !== id)
    })
  }, [])

  const updateEntry = useCallback(
    (id: string, field: keyof JournalEntry, value: string) => {
      setEntries((prev) =>
        prev.map((entry) => {
          if (entry.id !== id) return entry

          // If setting debit, clear credit (and vice versa)
          if (field === 'debit' && value) {
            return { ...entry, debit: value, credit: '' }
          }
          if (field === 'credit' && value) {
            return { ...entry, credit: value, debit: '' }
          }

          return { ...entry, [field]: value }
        })
      )
    },
    []
  )

  // Create transaction mutation
  const createMutation = useMutation({
    mutationFn: createTransaction,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['analytics'] })
      onSuccess()
    },
  })

  // Validation
  const validate = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!description.trim()) {
      newErrors.description = 'Description is required'
    }

    if (!date) {
      newErrors.date = 'Date is required'
    }

    // Check entries
    const hasEmptyAccount = entries.some((e) => !e.accountId)
    if (hasEmptyAccount) {
      newErrors.entries = 'All entries must have an account selected'
    }

    const hasEmptyAmount = entries.some((e) => !e.debit && !e.credit)
    if (hasEmptyAmount) {
      newErrors.entries = 'All entries must have a debit or credit amount'
    }

    if (!totals.isBalanced) {
      newErrors.balance = 'Transaction must be balanced (debits = credits)'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  // Handle submit
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!validate()) return

    // Build entries for API
    const apiEntries = entries.map((entry) => ({
      account_id: entry.accountId,
      debit: entry.debit || '0',
      credit: entry.credit || '0',
    }))

    createMutation.mutate({
      description: description.trim(),
      date: new Date(date).toISOString(),
      counterparty: counterparty.trim() || undefined,
      entries: apiEntries,
      auto_post: autoPost,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Description */}
      <FormField label="Description" required error={errors.description}>
        <Input
          placeholder="e.g., Split grocery purchase"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          leftIcon={<FileText className="h-4 w-4" />}
          autoFocus
        />
      </FormField>

      {/* Date and Counterparty Row */}
      <div className="grid grid-cols-2 gap-4">
        <FormField label="Date" required error={errors.date}>
          <Input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            leftIcon={<Calendar className="h-4 w-4" />}
          />
        </FormField>

        <FormField label="Counterparty" helperText="Optional">
          <Input
            placeholder="e.g., REWE, Amazon"
            value={counterparty}
            onChange={(e) => setCounterparty(e.target.value)}
            leftIcon={<Building2 className="h-4 w-4" />}
          />
        </FormField>
      </div>

      {/* Journal Entries Table */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-text-primary">
            Journal Entries <span className="text-accent-danger">*</span>
          </label>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={addEntry}
            className="text-xs"
          >
            <Plus className="h-3 w-3" />
            Add Entry
          </Button>
        </div>

        {errors.entries && (
          <p className="text-xs text-accent-danger">{errors.entries}</p>
        )}

        <div className="border border-border-subtle rounded-lg overflow-hidden">
          {/* Header */}
          <div className="grid grid-cols-[1fr,100px,100px,40px] gap-2 px-3 py-2 bg-bg-base border-b border-border-subtle text-xs font-medium text-text-secondary">
            <div>Account</div>
            <div className="text-right">Debit</div>
            <div className="text-right">Credit</div>
            <div></div>
          </div>

          {/* Entry Rows */}
          <div className="divide-y divide-border-subtle">
            {entries.map((entry) => (
              <div
                key={entry.id}
                className="grid grid-cols-[1fr,100px,100px,40px] gap-2 px-3 py-2 items-center"
              >
                <Select
                  options={accountOptions}
                  value={entry.accountId}
                  onChange={(value) => updateEntry(entry.id, 'accountId', value)}
                  placeholder="Select account..."
                  className="text-sm"
                />
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="0.00"
                  value={entry.debit}
                  onChange={(e) => updateEntry(entry.id, 'debit', e.target.value)}
                  className="text-right text-sm [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                />
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="0.00"
                  value={entry.credit}
                  onChange={(e) => updateEntry(entry.id, 'credit', e.target.value)}
                  className="text-right text-sm [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                />
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span className="inline-flex">
                      <button
                        type="button"
                        onClick={() => removeEntry(entry.id)}
                        disabled={entries.length <= 2}
                        className={`
                          p-1.5 rounded transition-colors
                          ${entries.length <= 2
                            ? 'text-text-muted cursor-not-allowed'
                            : 'text-text-secondary hover:text-accent-danger hover:bg-accent-danger/10'
                          }
                        `}
                        aria-label="Remove entry"
                      >
                        <Trash2 className="h-4 w-4" aria-hidden="true" />
                      </button>
                    </span>
                  </TooltipTrigger>
                  <TooltipContent>
                    {entries.length <= 2 ? 'Minimum 2 entries required' : 'Remove entry'}
                  </TooltipContent>
                </Tooltip>
              </div>
            ))}
          </div>

          {/* Totals Row */}
          <div
            className={`
              grid grid-cols-[1fr,100px,100px,40px] gap-2 px-3 py-2.5
              border-t-2 border-border-subtle
              ${totals.isBalanced ? 'bg-accent-success/5' : 'bg-accent-warning/5'}
            `}
          >
            <div className="flex items-center gap-2 text-sm font-medium">
              {totals.isBalanced ? (
                <>
                  <CheckCircle2 className="h-4 w-4 text-accent-success" />
                  <span className="text-accent-success">Balanced</span>
                </>
              ) : (
                <>
                  <AlertCircle className="h-4 w-4 text-accent-warning" />
                  <span className="text-accent-warning">Unbalanced</span>
                </>
              )}
            </div>
            <div className="text-right text-sm font-semibold text-text-primary">
              <Amount value={totals.debit} colorize={false} />
            </div>
            <div className="text-right text-sm font-semibold text-text-primary">
              <Amount value={totals.credit} colorize={false} />
            </div>
            <div></div>
          </div>
        </div>

        {errors.balance && (
          <p className="text-xs text-accent-danger">{errors.balance}</p>
        )}
      </div>

      {/* Post immediately Toggle */}
      <div className="flex items-center justify-between p-3 bg-bg-base rounded-lg border border-border-subtle">
        <div>
          <span className="text-sm font-medium text-text-primary">
            Post immediately
          </span>
          <p className="text-xs text-text-muted">
            Uncheck to save as draft for review
          </p>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={autoPost}
          onClick={() => setAutoPost(!autoPost)}
          className={`
            relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full
            border-2 border-transparent transition-colors duration-200 ease-in-out
            focus:outline-none focus:ring-2 focus:ring-accent-primary/50 focus:ring-offset-2 focus:ring-offset-bg-surface
            ${autoPost ? 'bg-accent-primary' : 'bg-bg-hover'}
          `}
        >
          <span
            className={`
              pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow-lg
              ring-0 transition duration-200 ease-in-out
              ${autoPost ? 'translate-x-5' : 'translate-x-0'}
            `}
          />
        </button>
      </div>

      {/* Error message */}
      {createMutation.isError && (
        <div className="p-3 bg-accent-danger/10 border border-accent-danger/20 rounded-lg">
          <p className="text-sm text-accent-danger">
            {(createMutation.error as Error)?.message || 'Failed to create transaction'}
          </p>
        </div>
      )}

      {/* Actions */}
      <div className="flex justify-end gap-3 pt-2">
        <Button type="button" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button
          type="submit"
          variant="primary"
          disabled={createMutation.isPending || !totals.isBalanced}
        >
          {createMutation.isPending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Creating...
            </>
          ) : (
            'Create Transaction'
          )}
        </Button>
      </div>
    </form>
  )
}
