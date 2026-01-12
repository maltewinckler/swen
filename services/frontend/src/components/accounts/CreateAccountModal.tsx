import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  CheckCircle2,
  CreditCard,
  RefreshCw,
  TrendingDown,
  TrendingUp,
  Wallet,
} from 'lucide-react'
import {
  Button,
  InlineAlert,
  Input,
  Modal,
  ModalBody,
  ModalHeader,
  FormField,
  Textarea,
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui'
import { createAccount, createExternalAccount } from '@/api'
import type { AccountType } from '@/types/api'
import { cn } from '@/lib/utils'
import { IBANInput, accountTypeLabels, normalizeAccountType } from '@/components/accounts'

type CreateStep = 'form' | 'success'

type CreateFormState = {
  name: string
  account_type: AccountType
  iban: string
  account_number: string
  currency: string
  description: string
}

type CreateResult = {
  accountName: string
  accountType: AccountType
  transactionsReconciled: number
  hasIban: boolean
}

interface CreateAccountModalProps {
  isOpen: boolean
  onClose: () => void
}

const INITIAL_FORM: CreateFormState = {
  name: '',
  account_type: 'EXPENSE',
  iban: '',
  account_number: '',
  currency: 'EUR',
  description: '',
}

function supportsIban(type: AccountType) {
  return type === 'ASSET' || type === 'LIABILITY'
}

export function CreateAccountModal({ isOpen, onClose }: CreateAccountModalProps) {
  const queryClient = useQueryClient()

  const [step, setStep] = useState<CreateStep>('form')
  const [form, setForm] = useState<CreateFormState>(INITIAL_FORM)
  const [error, setError] = useState('')
  const [result, setResult] = useState<CreateResult | null>(null)

  const createAccountMutation = useMutation({
    mutationFn: async (data: CreateFormState): Promise<CreateResult> => {
      const hasIban = data.iban.trim().length > 0
      const currency = 'EUR'

      if (hasIban && supportsIban(data.account_type)) {
        const externalType = data.account_type === 'LIABILITY' ? 'liability' : 'asset'
        const res = await createExternalAccount({
          iban: data.iban.trim().toUpperCase().replace(/\s/g, ''),
          name: data.name.trim(),
          currency,
          account_type: externalType,
          reconcile: true,
        })
        return {
          accountName: res.mapping.account_name,
          accountType: data.account_type,
          transactionsReconciled: res.transactions_reconciled,
          hasIban: true,
        }
      }

      await createAccount({
        account_number: data.account_number.trim() || data.name.trim().substring(0, 10).replace(/\s/g, '_'),
        name: data.name.trim(),
        account_type: data.account_type,
        currency,
        description: data.description?.trim() || undefined,
      })
      return {
        accountName: data.name.trim(),
        accountType: data.account_type,
        transactionsReconciled: 0,
        hasIban: false,
      }
    },
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
      queryClient.invalidateQueries({ queryKey: ['mappings'] })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      setResult(res)
      setStep('success')
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Failed to create account')
    },
  })

  const handleClose = () => {
    setStep('form')
    setForm(INITIAL_FORM)
    setError('')
    setResult(null)
    onClose()
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!form.name.trim()) {
      setError('Account name is required')
      return
    }

    const iban = form.iban.trim().toUpperCase().replace(/\s/g, '')
    if (iban && supportsIban(form.account_type)) {
      if (iban.length < 15 || iban.length > 34) {
        setError('IBAN must be between 15 and 34 characters')
        return
      }
    }

    createAccountMutation.mutate(form)
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      size="lg"
      closeOnBackdropClick={!createAccountMutation.isPending}
    >
      <ModalHeader
        onClose={createAccountMutation.isPending ? undefined : handleClose}
        description={step === 'form' ? 'Create a new account for tracking' : 'Account created successfully'}
      >
        Add Account
      </ModalHeader>
      <ModalBody>
        {step === 'success' && result ? (
          <div className="space-y-4">
            <div className="p-4 rounded-lg bg-accent-success/10 border border-accent-success/20">
              <div className="flex items-start gap-3">
                <CheckCircle2 className="h-6 w-6 text-accent-success flex-shrink-0" />
                <div className="flex-1">
                  <p className="font-medium text-text-primary">
                    {result.hasIban ? 'Bank account added' : 'Account created'}
                  </p>
                  <p className="text-sm text-text-secondary mt-1">
                    "{result.accountName}" has been added to your{' '}
                    {accountTypeLabels[normalizeAccountType(result.accountType)]}.
                  </p>
                </div>
              </div>
            </div>

            {result.transactionsReconciled > 0 && (
              <div className="p-4 rounded-lg bg-accent-info/10 border border-accent-info/20">
                <div className="flex items-start gap-3">
                  <RefreshCw className="h-5 w-5 text-accent-info flex-shrink-0" />
                  <div>
                    <p className="text-sm font-medium text-text-primary">
                      {result.transactionsReconciled} transaction{result.transactionsReconciled !== 1 ? 's' : ''}{' '}
                      updated
                    </p>
                    <p className="text-xs text-text-muted mt-1">
                      Previously categorized as expenses, now correctly tracked as internal transfers to this
                      account.
                    </p>
                  </div>
                </div>
              </div>
            )}

            <Button className="w-full" onClick={handleClose}>
              <CheckCircle2 className="h-4 w-4" />
              Done
            </Button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-5">
            {error && <InlineAlert variant="danger">{error}</InlineAlert>}

            <FormField label="What kind of account?">
              <div className="grid grid-cols-2 gap-2">
                {[
                  { type: 'ASSET' as const, icon: Wallet, label: 'Bank / Savings', desc: 'Bank accounts, investments' },
                  { type: 'LIABILITY' as const, icon: CreditCard, label: 'Credit / Loan', desc: 'Credit cards, mortgages' },
                  { type: 'INCOME' as const, icon: TrendingUp, label: 'Income Source', desc: 'Salary, freelance, dividends' },
                  { type: 'EXPENSE' as const, icon: TrendingDown, label: 'Expense Category', desc: 'Groceries, rent, subscriptions' },
                ].map(({ type, icon: Icon, label, desc }) => (
                  <button
                    key={type}
                    type="button"
                    onClick={() => setForm({ ...form, account_type: type, iban: '' })}
                    className={cn(
                      'p-3 rounded-lg border-2 text-left transition-all',
                      form.account_type === type
                        ? 'border-accent-primary bg-accent-primary/5'
                        : 'border-border-default hover:border-border-hover'
                    )}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <Icon
                        className={cn(
                          'h-4 w-4',
                          form.account_type === type ? 'text-accent-primary' : 'text-text-muted'
                        )}
                      />
                      <span
                        className={cn(
                          'text-sm font-medium',
                          form.account_type === type ? 'text-text-primary' : 'text-text-secondary'
                        )}
                      >
                        {label}
                      </span>
                    </div>
                    <p className="text-xs text-text-muted">{desc}</p>
                  </button>
                ))}
              </div>
            </FormField>

            <FormField label="Account Name">
              <Input
                placeholder={
                  form.account_type === 'ASSET'
                    ? 'e.g., Deutsche Bank Depot'
                    : form.account_type === 'LIABILITY'
                      ? 'e.g., VISA Credit Card'
                      : form.account_type === 'INCOME'
                        ? 'e.g., Freelance Income'
                        : 'e.g., Groceries'
                }
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                required
              />
            </FormField>

            {(form.account_type === 'EXPENSE' || form.account_type === 'INCOME') && (
              <FormField
                label="Description"
                helperText="Optional. Add keywords to help AI classify transactions (e.g., 'Supermarkets: REWE, Lidl, EDEKA')"
              >
                <Textarea
                  rows={2}
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  placeholder="Keywords for AI classification..."
                  maxLength={500}
                />
              </FormField>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {supportsIban(form.account_type) && (
                <FormField
                  label="IBAN"
                  helperText="Optional. Add IBAN to track transfers to this account as internal transfers instead of expenses."
                  className="sm:col-span-2"
                >
                  <IBANInput
                    placeholder="DE89 3704 0044 0532 0130 00"
                    value={form.iban}
                    onChange={(iban) => setForm({ ...form, iban })}
                  />
                </FormField>
              )}

              <FormField label="Account Number" helperText="Optional. Auto-generated if not provided.">
                <Input
                  placeholder="e.g., 4200"
                  value={form.account_number}
                  onChange={(e) => setForm({ ...form, account_number: e.target.value })}
                />
              </FormField>

              <FormField label="Currency">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className="cursor-not-allowed">
                      <Input value="EUR" disabled />
                    </div>
                  </TooltipTrigger>
                  <TooltipContent>Only EUR is supported yet.</TooltipContent>
                </Tooltip>
              </FormField>
            </div>

            <div className="flex gap-3 pt-2">
              <Button
                type="button"
                variant="secondary"
                className="flex-1"
                onClick={handleClose}
                disabled={createAccountMutation.isPending}
              >
                Cancel
              </Button>
              <Button type="submit" className="flex-1" isLoading={createAccountMutation.isPending}>
                Create Account
              </Button>
            </div>
          </form>
        )}
      </ModalBody>
    </Modal>
  )
}
