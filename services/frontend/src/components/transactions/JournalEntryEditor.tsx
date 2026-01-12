/**
 * JournalEntryEditor - Edit journal entries for an existing transaction.
 *
 * Features:
 * - Shows protected entries as locked (for bank imports)
 * - Allows adding/removing/editing unprotected entries
 * - Real-time balance validation
 * - Integrates with the transaction update API
 */

import { useState, useMemo, useCallback, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Plus,
  Trash2,
  AlertCircle,
  Lock,
} from 'lucide-react'
import { Button, Input, Select, Amount, Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui'
import type { SelectOption } from '@/components/ui'
import { listAccounts } from '@/api'
import type { JournalEntry } from '@/types/api'

interface EditableEntry {
  id: string
  accountId: string
  accountName: string
  accountType: string
  debit: string
  credit: string
  isProtected: boolean
  isNew: boolean
}

interface JournalEntryEditorProps {
  entries: JournalEntry[]
  isBankImport: boolean
  onChange: (entries: EditableEntry[]) => void
  disabled?: boolean
}

function generateId(): string {
  return `new_${Math.random().toString(36).substring(2, 9)}`
}

export function JournalEntryEditor({
  entries: originalEntries,
  isBankImport,
  onChange,
  disabled = false,
}: JournalEntryEditorProps) {
  // Convert original entries to editable format
  const [editableEntries, setEditableEntries] = useState<EditableEntry[]>(() =>
    originalEntries.map((e) => ({
      id: e.account_id + '_' + (e.debit || e.credit),
      accountId: e.account_id,
      accountName: e.account_name,
      accountType: e.account_type,
      debit: e.debit || '',
      credit: e.credit || '',
      // Asset entries are protected for bank imports
      isProtected: isBankImport && e.account_type === 'asset',
      isNew: false,
    }))
  )

  // Sync with parent
  useEffect(() => {
    onChange(editableEntries)
  }, [editableEntries, onChange])

  // Reset when original entries change (e.g., when navigating to different transaction)
  useEffect(() => {
    setEditableEntries(
      originalEntries.map((e) => ({
        id: e.account_id + '_' + (e.debit || e.credit),
        accountId: e.account_id,
        accountName: e.account_name,
        accountType: e.account_type,
        debit: e.debit || '',
        credit: e.credit || '',
        isProtected: isBankImport && e.account_type === 'asset',
        isNew: false,
      }))
    )
  }, [originalEntries, isBankImport])

  // Fetch all accounts for dropdowns
  const { data: allAccounts } = useQuery({
    queryKey: ['accounts', 'all'],
    queryFn: () => listAccounts({ is_active: true, size: 200 }),
  })

  // Build account options (grouped by type)
  const accountOptions: SelectOption[] = useMemo(() => {
    if (!allAccounts?.items) return []

    const grouped: Record<string, SelectOption[]> = {}

    allAccounts.items.forEach((acc) => {
      const type = acc.account_type.toUpperCase()
      if (!grouped[type]) {
        grouped[type] = []
      }
      const numDisplay = acc.account_number?.slice(0, 5) || ''
      grouped[type].push({
        value: acc.id,
        label: numDisplay ? `${numDisplay} · ${acc.name}` : acc.name,
      })
    })

    const options: SelectOption[] = []
    const typeOrder = ['ASSET', 'EXPENSE', 'INCOME', 'LIABILITY', 'EQUITY']

    typeOrder.forEach((type) => {
      if (grouped[type]?.length) {
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

    editableEntries.forEach((entry) => {
      const debit = parseFloat(entry.debit) || 0
      const credit = parseFloat(entry.credit) || 0
      totalDebit += debit
      totalCredit += credit
    })

    return {
      debit: totalDebit,
      credit: totalCredit,
      isBalanced: Math.abs(totalDebit - totalCredit) < 0.001 && totalDebit > 0,
    }
  }, [editableEntries])

  // Add new entry
  const addEntry = useCallback(() => {
    setEditableEntries((prev) => [
      ...prev,
      {
        id: generateId(),
        accountId: '',
        accountName: '',
        accountType: '',
        debit: '',
        credit: '',
        isProtected: false,
        isNew: true,
      },
    ])
  }, [])

  // Remove entry (only unprotected)
  const removeEntry = useCallback((id: string) => {
    setEditableEntries((prev) => {
      const entry = prev.find((e) => e.id === id)
      if (entry?.isProtected) return prev

      // Count non-protected entries
      const unprotectedCount = prev.filter((e) => !e.isProtected).length
      if (unprotectedCount <= 1) return prev // Keep at least 1 category entry

      return prev.filter((e) => e.id !== id)
    })
  }, [])

  // Update entry
  const updateEntry = useCallback(
    (id: string, field: keyof EditableEntry, value: string) => {
      setEditableEntries((prev) =>
        prev.map((entry) => {
          if (entry.id !== id || entry.isProtected) return entry

          // If setting debit, clear credit (and vice versa)
          if (field === 'debit' && value) {
            return { ...entry, debit: value, credit: '' }
          }
          if (field === 'credit' && value) {
            return { ...entry, credit: value, debit: '' }
          }

          // Update account name when account changes
          if (field === 'accountId') {
            const account = allAccounts?.items.find((a) => a.id === value)
            return {
              ...entry,
              accountId: value,
              accountName: account?.name || '',
              accountType: account?.account_type || '',
            }
          }

          return { ...entry, [field]: value }
        })
      )
    },
    [allAccounts]
  )

  const protectedCount = editableEntries.filter((e) => e.isProtected).length
  const unprotectedCount = editableEntries.filter((e) => !e.isProtected).length

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-text-primary">
            Journal Entries
          </span>
          {isBankImport && protectedCount > 0 && (
            <span className="text-xs text-text-muted flex items-center gap-1">
              <Lock className="h-3 w-3" />
              {protectedCount} protected
            </span>
          )}
        </div>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={addEntry}
          disabled={disabled}
          className="text-xs"
        >
          <Plus className="h-3 w-3" />
          Add Entry
        </Button>
      </div>

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
          {editableEntries.map((entry) => (
            <div
              key={entry.id}
              className={`
                grid grid-cols-[1fr,100px,100px,40px] gap-2 px-3 py-2 items-center
                ${entry.isProtected ? 'bg-bg-base/50' : ''}
              `}
            >
              {entry.isProtected ? (
                // Protected entry - read-only
                <>
                  <div className="h-10 flex items-center text-sm min-w-0">
                    <span className="text-text-primary truncate">{entry.accountName}</span>
                  </div>
                  <div className="text-right text-sm font-mono text-text-muted">
                    {entry.debit ? <Amount value={entry.debit} colorize={false} /> : '—'}
                  </div>
                  <div className="text-right text-sm font-mono text-text-muted">
                    {entry.credit ? <Amount value={entry.credit} colorize={false} /> : '—'}
                  </div>
                  <div className="flex justify-center">
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span className="inline-flex">
                          <Lock className="h-4 w-4 text-text-muted" aria-hidden="true" />
                        </span>
                      </TooltipTrigger>
                      <TooltipContent>Protected (bank import)</TooltipContent>
                    </Tooltip>
                  </div>
                </>
              ) : (
                // Editable entry
                <>
                  <Select
                    options={accountOptions}
                    value={entry.accountId}
                    onChange={(value) => updateEntry(entry.id, 'accountId', value)}
                    placeholder="Select account..."
                    className="text-sm"
                    disabled={disabled}
                  />
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="0.00"
                    value={entry.debit}
                    onChange={(e) => updateEntry(entry.id, 'debit', e.target.value)}
                    className="text-right text-sm [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                    disabled={disabled}
                  />
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="0.00"
                    value={entry.credit}
                    onChange={(e) => updateEntry(entry.id, 'credit', e.target.value)}
                    className="text-right text-sm [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                    disabled={disabled}
                  />
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span className="inline-flex">
                        <button
                          type="button"
                          onClick={() => removeEntry(entry.id)}
                          disabled={disabled || unprotectedCount <= 1}
                          className={`
                            p-1.5 rounded transition-colors
                            ${disabled || unprotectedCount <= 1
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
                      {unprotectedCount <= 1 ? 'Must have at least 1 category entry' : 'Remove entry'}
                    </TooltipContent>
                  </Tooltip>
                </>
              )}
            </div>
          ))}
        </div>

        {/* Totals Row */}
        <div
          className={`
            grid grid-cols-[1fr,100px,100px,40px] gap-2 px-3 py-2.5
            border-t-2 border-border-subtle
            ${!totals.isBalanced ? 'bg-accent-danger/5' : ''}
          `}
        >
          <div className="flex items-center gap-2 text-sm font-medium">
            {totals.isBalanced ? (
              <span className="text-text-muted">Balanced</span>
            ) : (
              <>
                <AlertCircle className="h-4 w-4 text-accent-danger" />
                <span className="text-accent-danger">Unbalanced</span>
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

      {isBankImport && (
        <p className="text-xs text-text-muted flex items-center gap-1">
          <Lock className="h-3 w-3" />
          Bank account entries are protected to preserve reconciliation. Only category entries can be modified.
        </p>
      )}
    </div>
  )
}

export type { EditableEntry }
