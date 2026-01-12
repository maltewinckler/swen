import { useState, useMemo } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Calendar,
  ArrowUpRight,
  ArrowDownRight,
  ArrowRight,
  Building2,
  FileText,
  Loader2,
  Wallet,
  BookOpen,
  Zap,
} from 'lucide-react'
import {
  Modal,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  Input,
  Select,
  FormField,
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from '@/components/ui'
import type { SelectOption } from '@/components/ui'
import { createSimpleTransaction, listAccounts } from '@/api'
import { JournalEntryForm } from './JournalEntryForm'

interface AddTransactionModalProps {
  isOpen: boolean
  onClose: () => void
}

type TransactionType = 'expense' | 'income'
type FormMode = 'simple' | 'journal'

export function AddTransactionModal({ isOpen, onClose }: AddTransactionModalProps) {
  const queryClient = useQueryClient()

  // Tab state
  const [mode, setMode] = useState<FormMode>('simple')

  // Simple form state
  const [type, setType] = useState<TransactionType>('expense')
  const [amount, setAmount] = useState('')
  const [description, setDescription] = useState('')
  const [date, setDate] = useState(() => new Date().toISOString().split('T')[0])
  const [counterparty, setCounterparty] = useState('')
  const [assetAccountId, setAssetAccountId] = useState('')
  const [counterAccountId, setCounterAccountId] = useState('')
  const [autoPost, setAutoPost] = useState(true)

  // Form errors
  const [errors, setErrors] = useState<Record<string, string>>({})

  // Fetch accounts for dropdowns
  const { data: assetAccounts } = useQuery({
    queryKey: ['accounts', 'asset'],
    queryFn: () => listAccounts({ account_type: 'ASSET', is_active: true, size: 100 }),
    enabled: isOpen,
  })

  const { data: liabilityAccounts } = useQuery({
    queryKey: ['accounts', 'liability'],
    queryFn: () => listAccounts({ account_type: 'LIABILITY', is_active: true, size: 100 }),
    enabled: isOpen,
  })

  const { data: expenseAccounts } = useQuery({
    queryKey: ['accounts', 'expense'],
    queryFn: () => listAccounts({ account_type: 'EXPENSE', is_active: true, size: 100 }),
    enabled: isOpen,
  })

  const { data: incomeAccounts } = useQuery({
    queryKey: ['accounts', 'income'],
    queryFn: () => listAccounts({ account_type: 'INCOME', is_active: true, size: 100 }),
    enabled: isOpen,
  })

  // Build payment account options (assets + liabilities like credit cards)
  const paymentAccountOptions: SelectOption[] = useMemo(() => {
    const options: SelectOption[] = []

    const assets = assetAccounts?.items || []
    const liabilities = liabilityAccounts?.items || []

    if (assets.length > 0) {
      options.push({ value: '__header_asset', label: '── ASSET ──', disabled: true })
      assets.forEach((acc) => {
        options.push({
          value: acc.account_number,
          label: `${acc.account_number.slice(0, 5)} · ${acc.name}`,
        })
      })
    }

    if (liabilities.length > 0) {
      options.push({ value: '__header_liability', label: '── LIABILITY ──', disabled: true })
      liabilities.forEach((acc) => {
        options.push({
          value: acc.account_number,
          label: `${acc.account_number.slice(0, 5)} · ${acc.name}`,
        })
      })
    }

    return options
  }, [assetAccounts, liabilityAccounts])

  // Build counter-account options based on transaction type
  const counterAccountOptions: SelectOption[] = useMemo(() => {
    const accounts = type === 'expense' ? expenseAccounts : incomeAccounts
    return [
      ...(accounts?.items || []).map((acc) => ({
        value: acc.account_number,
        label: `${acc.account_number.slice(0, 5)} · ${acc.name}`,
      })),
    ]
  }, [type, expenseAccounts, incomeAccounts])

  // Reset form
  const resetForm = () => {
    setMode('simple')
    setType('expense')
    setAmount('')
    setDescription('')
    setDate(new Date().toISOString().split('T')[0])
    setCounterparty('')
    setAssetAccountId('')
    setCounterAccountId('')
    setAutoPost(true)
    setErrors({})
  }

  // Handle close
  const handleClose = () => {
    resetForm()
    onClose()
  }

  // Create transaction mutation
  const createMutation = useMutation({
    mutationFn: createSimpleTransaction,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['analytics'] })
      handleClose()
    },
  })

  // Validate form
  const validate = (): boolean => {
    const newErrors: Record<string, string> = {}

    const absAmount = Math.abs(parseFloat(amount))
    if (!amount || isNaN(absAmount) || absAmount === 0) {
      newErrors.amount = 'Please enter a valid amount'
    }

    if (!assetAccountId) {
      newErrors.assetAccount = 'Please select a payment account'
    }

    if (!counterAccountId) {
      newErrors.counterAccount = 'Please select a counter-account'
    }

    if (!description.trim()) {
      newErrors.description = 'Description is required'
    }

    if (!date) {
      newErrors.date = 'Date is required'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  // Handle submit (simple mode)
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!validate()) return

    // Use absolute value (sign is determined by expense/income toggle)
    const absAmount = Math.abs(parseFloat(amount))

    // Calculate signed amount (negative for expenses, positive for income)
    const signedAmount = type === 'expense'
      ? `-${absAmount.toFixed(2)}`
      : absAmount.toFixed(2)

    createMutation.mutate({
      description: description.trim(),
      amount: signedAmount,
      date: new Date(date).toISOString(),
      counterparty: counterparty.trim() || undefined,
      asset_account: assetAccountId || undefined,
      category_account: counterAccountId || undefined,
      auto_post: autoPost,
    })
  }

  return (
    <Modal isOpen={isOpen} onClose={handleClose} size="xl">
      <ModalHeader
        onClose={handleClose}
        description={
          mode === 'simple'
            ? 'Record a manual expense or income'
            : 'Create a transaction with explicit journal entries'
        }
      >
        Add Transaction
      </ModalHeader>

      {/* Tab Switcher */}
      <div className="px-6 pb-4">
        <div className="flex gap-1 p-1 bg-bg-base rounded-xl">
          <button
            type="button"
            onClick={() => setMode('simple')}
            className={`
              flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg
              text-sm font-medium transition-all
              ${mode === 'simple'
                ? 'bg-bg-surface text-text-primary shadow-sm'
                : 'text-text-secondary hover:text-text-primary hover:bg-bg-hover'
              }
            `}
          >
            <Zap className="h-4 w-4" />
            Simple
          </button>
          <button
            type="button"
            onClick={() => setMode('journal')}
            className={`
              flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg
              text-sm font-medium transition-all
              ${mode === 'journal'
                ? 'bg-bg-surface text-text-primary shadow-sm'
                : 'text-text-secondary hover:text-text-primary hover:bg-bg-hover'
              }
            `}
          >
            <BookOpen className="h-4 w-4" />
            Journal Entries
          </button>
        </div>
      </div>

      {mode === 'journal' ? (
        <ModalBody>
          <JournalEntryForm onSuccess={handleClose} onCancel={handleClose} />
        </ModalBody>
      ) : (
        <form onSubmit={handleSubmit} className="flex flex-col flex-1 min-h-0">
          <ModalBody className="space-y-5">
            {/* Amount with inline type toggle */}
            <FormField
              label="Amount"
              required
              error={errors.amount}
            >
              <div className="flex gap-2">
                {/* Type Toggle Button */}
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      type="button"
                      onClick={() => setType(type === 'expense' ? 'income' : 'expense')}
                      data-testid="type-toggle"
                      aria-label={`Switch to ${type === 'expense' ? 'income' : 'expense'}`}
                      className={`
                        flex items-center gap-1.5 px-3 py-2 rounded-lg border
                        text-sm font-medium transition-all shrink-0
                        ${type === 'expense'
                          ? 'bg-accent-danger/10 border-accent-danger/30 text-accent-danger hover:bg-accent-danger/15'
                          : 'bg-accent-success/10 border-accent-success/30 text-accent-success hover:bg-accent-success/15'
                        }
                      `}
                    >
                      {type === 'expense' ? (
                        <>
                          <ArrowDownRight className="h-4 w-4" aria-hidden="true" />
                          <span className="hidden sm:inline">Expense</span>
                        </>
                      ) : (
                        <>
                          <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
                          <span className="hidden sm:inline">Income</span>
                        </>
                      )}
                    </button>
                  </TooltipTrigger>
                  <TooltipContent>
                    Click to switch to {type === 'expense' ? 'income' : 'expense'}
                  </TooltipContent>
                </Tooltip>

                {/* Amount Input */}
                <div className="relative flex-1">
                  <Input
                    type="number"
                    step="0.01"
                    placeholder="0.00"
                    value={amount}
                    onChange={(e) => {
                      const value = e.target.value
                      setAmount(value)
                      // Auto-switch type based on sign (only when sign is explicit)
                      if (value.startsWith('-')) {
                        setType('expense')
                      } else if (value.startsWith('+')) {
                        setType('income')
                      }
                    }}
                    className="pl-8 text-lg font-semibold [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                    autoFocus
                  />
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted">
                    €
                  </span>
                </div>
              </div>
            </FormField>

            {/* Description */}
            <FormField label="Description" required error={errors.description}>
              <Input
                placeholder={type === 'expense' ? 'e.g., Coffee at Starbucks' : 'e.g., Salary December'}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                leftIcon={<FileText className="h-4 w-4" />}
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

              <FormField
                label="Counterparty"
                helperText={type === 'expense' ? 'Merchant or store' : 'Payer'}
              >
                <Input
                  placeholder={type === 'expense' ? 'e.g., REWE' : 'e.g., ACME Corp'}
                  value={counterparty}
                  onChange={(e) => setCounterparty(e.target.value)}
                  leftIcon={<Building2 className="h-4 w-4" />}
                />
              </FormField>
            </div>

            {/* Account Selection - Table-like layout */}
            <div className="space-y-3">
              <label className="text-sm font-medium text-text-primary">
                Accounts <span className="text-accent-danger">*</span>
              </label>

              <div className="border border-border-subtle rounded-lg overflow-hidden">
                {/* Header */}
                <div className="grid grid-cols-2 gap-2 px-3 py-2 bg-bg-base border-b border-border-subtle text-xs font-medium text-text-secondary">
                  <div className="flex items-center gap-2">
                    <Wallet className="h-3.5 w-3.5" />
                    Payment Account
                  </div>
                  <div className="flex items-center gap-2">
                    <ArrowRight className="h-3.5 w-3.5" />
                    {type === 'expense' ? 'Expense Account' : 'Income Account'}
                  </div>
                </div>

                {/* Account Selects */}
                <div className="grid grid-cols-2 gap-2 px-3 py-3">
                  <div>
                    <Select
                      options={paymentAccountOptions}
                      value={assetAccountId}
                      onChange={setAssetAccountId}
                      placeholder="Select account..."
                      className="text-sm"
                    />
                    {errors.assetAccount && (
                      <p className="text-xs text-accent-danger mt-1">{errors.assetAccount}</p>
                    )}
                  </div>
                  <div>
                    <Select
                      options={counterAccountOptions}
                      value={counterAccountId}
                      onChange={setCounterAccountId}
                      placeholder="Select account..."
                      className="text-sm"
                    />
                    {errors.counterAccount && (
                      <p className="text-xs text-accent-danger mt-1">{errors.counterAccount}</p>
                    )}
                  </div>
                </div>

                {/* Flow Indicator */}
                <div className="px-3 py-2 bg-bg-base border-t border-border-subtle">
                  <div className="flex items-center justify-center gap-2 text-xs text-text-muted">
                    {type === 'expense' ? (
                      <>
                        <span className="font-medium text-text-secondary">
                          {assetAccountId ? paymentAccountOptions.find(o => o.value === assetAccountId)?.label : 'Payment'}
                        </span>
                        <ArrowRight className="h-3.5 w-3.5 text-accent-danger" />
                        <span className="font-medium text-text-secondary">
                          {counterAccountId ? counterAccountOptions.find(o => o.value === counterAccountId)?.label : 'Expense'}
                        </span>
                      </>
                    ) : (
                      <>
                        <span className="font-medium text-text-secondary">
                          {counterAccountId ? counterAccountOptions.find(o => o.value === counterAccountId)?.label : 'Income'}
                        </span>
                        <ArrowRight className="h-3.5 w-3.5 text-accent-success" />
                        <span className="font-medium text-text-secondary">
                          {assetAccountId ? paymentAccountOptions.find(o => o.value === assetAccountId)?.label : 'Payment'}
                        </span>
                      </>
                    )}
                  </div>
                </div>
              </div>
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
          </ModalBody>

          <ModalFooter>
            <Button type="button" variant="ghost" onClick={handleClose}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              disabled={createMutation.isPending}
            >
              {createMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  {type === 'expense' ? (
                    <ArrowDownRight className="h-4 w-4" />
                  ) : (
                    <ArrowUpRight className="h-4 w-4" />
                  )}
                  Add {type === 'expense' ? 'Expense' : 'Income'}
                </>
              )}
            </Button>
          </ModalFooter>
        </form>
      )}
    </Modal>
  )
}
