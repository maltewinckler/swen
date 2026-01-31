/**
 * Cash Expense Modal
 *
 * A minimal, mobile-optimized form for quickly recording cash expenses.
 * Uses the Bargeld (Cash) account as the source automatically.
 *
 * Features:
 * - Large touch-friendly amount input
 * - Simple description field
 * - Optional category selection (defaults to Sonstiges)
 * - Remembers last used category
 * - Haptic feedback on submit (if supported)
 */

import { useState, useEffect, useRef } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Banknote, Check } from 'lucide-react'
import {
  Modal,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  Input,
  Select,
  FormField,
  InlineAlert,
} from '@/components/ui'
import type { SelectOption } from '@/components/ui'
import { createSimpleTransaction, listAccounts } from '@/api'

interface CashExpenseModalProps {
  isOpen: boolean
  onClose: () => void
}

const CASH_ACCOUNT_NUMBER = '1000' // Bargeld
const DEFAULT_EXPENSE_ACCOUNT = '4900' // Sonstiges
const LAST_CATEGORY_KEY = 'swen:lastCashCategory'

export function CashExpenseModal({ isOpen, onClose }: CashExpenseModalProps) {
  const queryClient = useQueryClient()
  const amountInputRef = useRef<HTMLInputElement>(null)

  // Form state
  const [amount, setAmount] = useState('')
  const [description, setDescription] = useState('')
  const [categoryId, setCategoryId] = useState(() => {
    return localStorage.getItem(LAST_CATEGORY_KEY) || DEFAULT_EXPENSE_ACCOUNT
  })
  const [error, setError] = useState('')
  const [showSuccess, setShowSuccess] = useState(false)

  // Focus amount input when modal opens
  useEffect(() => {
    if (isOpen) {
      // Small delay to ensure modal animation is complete
      const timer = setTimeout(() => {
        amountInputRef.current?.focus()
      }, 100)
      return () => clearTimeout(timer)
    }
  }, [isOpen])

  // Fetch expense accounts for category selection
  const { data: expenseAccounts } = useQuery({
    queryKey: ['accounts', 'expense'],
    queryFn: () => listAccounts({ account_type: 'EXPENSE', is_active: true, size: 100 }),
    enabled: isOpen,
  })

  // Build category options
  const categoryOptions: SelectOption[] = (expenseAccounts?.items || []).map((acc) => ({
    value: acc.account_number,
    label: acc.name,
  }))

  // Reset form
  const resetForm = () => {
    setAmount('')
    setDescription('')
    setError('')
    setShowSuccess(false)
    // Keep categoryId to remember user preference
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
      // Remember last used category
      localStorage.setItem(LAST_CATEGORY_KEY, categoryId)

      // Invalidate queries
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['analytics'] })

      // Show success state briefly
      setShowSuccess(true)

      // Haptic feedback if supported
      if (navigator.vibrate) {
        navigator.vibrate(50)
      }

      // Close after brief success display
      setTimeout(() => {
        handleClose()
      }, 600)
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Failed to create expense')
    },
  })

  // Handle submit
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    // Validate amount
    const absAmount = Math.abs(parseFloat(amount))
    if (!amount || isNaN(absAmount) || absAmount === 0) {
      setError('Please enter a valid amount')
      return
    }

    // Description is optional for cash - use generic if empty
    const desc = description.trim() || 'Bargeld'

    createMutation.mutate({
      description: desc,
      amount: `-${absAmount.toFixed(2)}`, // Negative for expense
      date: new Date().toISOString().split('T')[0],
      asset_account: CASH_ACCOUNT_NUMBER,
      category_account: categoryId,
      auto_post: true,
    })
  }

  // Success state
  if (showSuccess) {
    return (
      <Modal isOpen={isOpen} onClose={handleClose}>
        <div className="flex flex-col items-center justify-center py-12">
          <div className="w-16 h-16 rounded-full bg-accent-success/20 flex items-center justify-center mb-4">
            <Check className="h-8 w-8 text-accent-success" />
          </div>
          <p className="text-lg font-medium text-text-primary">Expense Saved</p>
        </div>
      </Modal>
    )
  }

  return (
    <Modal isOpen={isOpen} onClose={handleClose}>
      <form onSubmit={handleSubmit}>
        <ModalHeader onClose={handleClose}>
          <span className="flex items-center gap-2">
            <Banknote className="h-5 w-5 text-accent-primary" />
            Cash Expense
          </span>
        </ModalHeader>
        <ModalBody className="space-y-4">
          {error && <InlineAlert variant="danger">{error}</InlineAlert>}

          {/* Amount - large input for mobile */}
          <FormField label="Amount">
            <div className="relative">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-2xl text-text-muted">
                €
              </span>
              <Input
                ref={amountInputRef}
                type="number"
                inputMode="decimal"
                step="0.01"
                min="0"
                placeholder="0.00"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="pl-10 text-2xl h-14 font-medium text-center"
              />
            </div>
          </FormField>

          {/* Description - optional */}
          <FormField label="What for?" helperText="Optional">
            <Input
              placeholder="e.g., Coffee, Bakery, Tip"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={200}
            />
          </FormField>

          {/* Category - defaults to last used or Sonstiges */}
          <FormField label="Category">
            <Select
              value={categoryId}
              onChange={(value) => setCategoryId(value)}
              options={categoryOptions}
              placeholder="Select category..."
            />
          </FormField>
        </ModalBody>
        <ModalFooter>
          <Button
            type="button"
            variant="secondary"
            onClick={handleClose}
            disabled={createMutation.isPending}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            isLoading={createMutation.isPending}
            disabled={!amount || createMutation.isPending}
            className="flex-1"
          >
            Save Expense
          </Button>
        </ModalFooter>
      </form>
    </Modal>
  )
}
