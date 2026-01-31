import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft,
  CheckCircle2,
  CreditCard,
  Plus,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Wallet,
} from 'lucide-react'
import {
  Button,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  FormField,
  InlineAlert,
  Input,
  Textarea,
} from '@/components/ui'
import { createAccount } from '@/api'
import { cn } from '@/lib/utils'
import type { AccountType } from '@/types/api'

interface OnboardingAccountsSetupStepProps {
  isLoading: boolean
  onBack: () => void
  onCreateAccounts: () => void
  onSkipToNext: () => void
}

type SetupMode = 'choose' | 'template-confirm' | 'manual-build'

interface CreatedAccount {
  name: string
  accountType: AccountType
}

const ACCOUNT_TYPE_OPTIONS = [
  { type: 'EXPENSE' as const, icon: TrendingDown, label: 'Expense', desc: 'Where money goes' },
  { type: 'INCOME' as const, icon: TrendingUp, label: 'Income', desc: 'Where money comes from' },
  { type: 'ASSET' as const, icon: Wallet, label: 'Asset', desc: 'Bank accounts, savings' },
  { type: 'LIABILITY' as const, icon: CreditCard, label: 'Liability', desc: 'Credit cards, loans' },
]

const TEMPLATE_ACCOUNTS = [
  { name: 'Gehalt & Lohn', type: 'Income' },
  { name: 'Miete', type: 'Expense' },
  { name: 'Lebensmittel', type: 'Expense' },
  { name: 'Restaurants & Bars', type: 'Expense' },
  { name: 'Transport', type: 'Expense' },
  { name: 'Sport & Fitness', type: 'Expense' },
  { name: 'Abonnements', type: 'Expense' },
  { name: 'Sonstiges', type: 'Expense' },
]

export function OnboardingAccountsSetupStep({
  isLoading,
  onBack,
  onCreateAccounts,
  onSkipToNext,
}: OnboardingAccountsSetupStepProps) {
  const queryClient = useQueryClient()
  const [mode, setMode] = useState<SetupMode>('choose')
  const [selectedOption, setSelectedOption] = useState<'template' | 'manual'>('template')

  // Manual build state
  const [createdAccounts, setCreatedAccounts] = useState<CreatedAccount[]>([])
  const [formData, setFormData] = useState({
    name: '',
    account_number: '',
    account_type: 'EXPENSE' as AccountType,
    description: '',
  })
  const [formError, setFormError] = useState('')

  const createAccountMutation = useMutation({
    mutationFn: (data: { name: string; account_number: string; account_type: AccountType; description?: string }) =>
      createAccount({
        account_number: data.account_number.trim() || data.name.trim().substring(0, 10).replace(/\s/g, '_'),
        name: data.name.trim(),
        account_type: data.account_type,
        currency: 'EUR',
        description: data.description?.trim() || undefined,
      }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
      setCreatedAccounts((prev) => [...prev, { name: variables.name, accountType: variables.account_type }])
      setFormData({ name: '', account_number: '', account_type: formData.account_type, description: '' })
      setFormError('')
    },
    onError: (err) => {
      setFormError(err instanceof Error ? err.message : 'Failed to create account')
    },
  })

  const handleAddAccount = () => {
    setFormError('')
    if (!formData.name.trim()) {
      setFormError('Account name is required')
      return
    }
    createAccountMutation.mutate(formData)
  }

  const handleContinue = () => {
    if (selectedOption === 'template') {
      setMode('template-confirm')
    } else {
      setMode('manual-build')
    }
  }

  const getTitle = () => {
    switch (mode) {
      case 'choose':
        return 'Set Up Your Accounts'
      case 'template-confirm':
        return 'Review Template'
      case 'manual-build':
        return 'Build Your Accounts'
    }
  }

  const getDescription = () => {
    switch (mode) {
      case 'choose':
        return 'Choose how to set up your expense and income categories'
      case 'template-confirm':
        return 'These accounts will be created for you'
      case 'manual-build':
        return 'Add income and expense categories for your needs'
    }
  }

  return (
    <>
      <CardHeader>
        <CardTitle>{getTitle()}</CardTitle>
        <CardDescription>{getDescription()}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Step 1: Choose */}
        {mode === 'choose' && (
          <>
            {/* Template Option */}
            <button
              type="button"
              autoFocus
              className={cn(
                'w-full p-4 rounded-lg border-2 cursor-pointer transition-all text-left',
                'focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary/50 focus-visible:ring-offset-2 focus-visible:ring-offset-bg-surface',
                selectedOption === 'template'
                  ? 'border-accent-primary bg-accent-primary/5'
                  : 'border-border-default hover:border-border-hover'
              )}
              onClick={() => setSelectedOption('template')}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && selectedOption === 'template') {
                  e.preventDefault()
                  handleContinue()
                }
              }}
            >
              <div className="flex items-start gap-3">
                <div
                  className={cn(
                    'w-5 h-5 rounded-full border-2 flex items-center justify-center mt-0.5 flex-shrink-0',
                    selectedOption === 'template' ? 'border-accent-primary' : 'border-border-default'
                  )}
                >
                  {selectedOption === 'template' && <div className="w-2.5 h-2.5 rounded-full bg-accent-primary" />}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-accent-primary" />
                    <p className="font-medium text-text-primary">Quick Start Template</p>
                  </div>
                  <p className="text-sm text-text-muted mt-1">
                    Common expense and income categories for personal finance. Ready in seconds.
                  </p>
                </div>
              </div>
            </button>

            {/* Manual Option */}
            <button
              type="button"
              className={cn(
                'w-full p-4 rounded-lg border-2 cursor-pointer transition-all text-left',
                'focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary/50 focus-visible:ring-offset-2 focus-visible:ring-offset-bg-surface',
                selectedOption === 'manual'
                  ? 'border-accent-primary bg-accent-primary/5'
                  : 'border-border-default hover:border-border-hover'
              )}
              onClick={() => setSelectedOption('manual')}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && selectedOption === 'manual') {
                  e.preventDefault()
                  handleContinue()
                }
              }}
            >
              <div className="flex items-start gap-3">
                <div
                  className={cn(
                    'w-5 h-5 rounded-full border-2 flex items-center justify-center mt-0.5 flex-shrink-0',
                    selectedOption === 'manual' ? 'border-accent-primary' : 'border-border-default'
                  )}
                >
                  {selectedOption === 'manual' && <div className="w-2.5 h-2.5 rounded-full bg-accent-primary" />}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <Plus className="h-4 w-4 text-text-secondary" />
                    <p className="font-medium text-text-primary">Build Custom</p>
                  </div>
                  <p className="text-sm text-text-muted mt-1">
                    Create your own categories step by step. Full control over your chart of accounts.
                  </p>
                </div>
              </div>
            </button>

            <div className="flex gap-3 pt-4">
              <Button variant="secondary" onClick={onBack}>
                <ArrowLeft className="h-4 w-4" />
                Back
              </Button>
              <Button className="flex-1" onClick={handleContinue}>
                Continue
              </Button>
            </div>
          </>
        )}

        {/* Step 2a: Template Confirmation */}
        {mode === 'template-confirm' && (
          <>
            <div className="p-4 rounded-lg bg-bg-subtle border border-border-default max-h-48 overflow-y-auto">
              <div className="grid grid-cols-2 gap-2">
                {TEMPLATE_ACCOUNTS.map((acc, i) => (
                  <div key={i} className="flex items-center gap-2 text-sm">
                    {acc.type === 'Income' ? (
                      <TrendingUp className="h-3.5 w-3.5 text-accent-success flex-shrink-0" />
                    ) : (
                      <TrendingDown className="h-3.5 w-3.5 text-accent-danger flex-shrink-0" />
                    )}
                    <span className="text-text-primary">{acc.name}</span>
                  </div>
                ))}
              </div>
            </div>

            <p className="text-xs text-text-muted text-center">
              You can always add, rename, or remove accounts later.
            </p>

            <div className="flex gap-3 pt-4">
              <Button variant="secondary" onClick={() => setMode('choose')}>
                <ArrowLeft className="h-4 w-4" />
                Back
              </Button>
              <Button className="flex-1" onClick={onCreateAccounts} isLoading={isLoading}>
                <Sparkles className="h-4 w-4" />
                Create Accounts
              </Button>
            </div>
          </>
        )}

        {/* Step 2b: Manual Build */}
        {mode === 'manual-build' && (
          <>
            {/* Created accounts list */}
            {createdAccounts.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm font-medium text-text-secondary">Created ({createdAccounts.length})</p>
                <div className="space-y-1.5 max-h-28 overflow-y-auto">
                  {createdAccounts.map((acc, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between p-2 rounded-lg bg-accent-success/5 border border-accent-success/20"
                    >
                      <div className="flex items-center gap-2">
                        {acc.accountType === 'INCOME' && <TrendingUp className="h-4 w-4 text-accent-success" />}
                        {acc.accountType === 'EXPENSE' && <TrendingDown className="h-4 w-4 text-accent-danger" />}
                        {acc.accountType === 'ASSET' && <Wallet className="h-4 w-4 text-accent-info" />}
                        {acc.accountType === 'LIABILITY' && <CreditCard className="h-4 w-4 text-accent-warning" />}
                        <span className="text-sm font-medium text-text-primary">{acc.name}</span>
                      </div>
                      <CheckCircle2 className="h-4 w-4 text-accent-success" />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Add account form */}
            <div className="space-y-3 p-4 rounded-lg border border-border-default bg-bg-subtle">
              {formError && <InlineAlert variant="danger">{formError}</InlineAlert>}

              <FormField label="Account Type">
                <div className="grid grid-cols-2 gap-2">
                  {ACCOUNT_TYPE_OPTIONS.map(({ type, icon: Icon, label, desc }) => (
                    <button
                      key={type}
                      type="button"
                      onClick={() => setFormData({ ...formData, account_type: type })}
                      className={cn(
                        'p-2 rounded-lg border text-left transition-all',
                        'focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary/50 focus-visible:ring-offset-2 focus-visible:ring-offset-bg-surface',
                        formData.account_type === type
                          ? 'border-accent-primary bg-accent-primary/5'
                          : 'border-border-default hover:border-border-hover'
                      )}
                    >
                      <div className="flex items-center gap-2">
                        <Icon
                          className={cn(
                            'h-4 w-4',
                            formData.account_type === type ? 'text-accent-primary' : 'text-text-muted'
                          )}
                        />
                        <span
                          className={cn(
                            'text-sm font-medium',
                            formData.account_type === type ? 'text-text-primary' : 'text-text-secondary'
                          )}
                        >
                          {label}
                        </span>
                      </div>
                      <p className="text-xs text-text-muted mt-0.5 ml-6">{desc}</p>
                    </button>
                  ))}
                </div>
              </FormField>

              <FormField label="Name">
                <Input
                  placeholder={
                    formData.account_type === 'INCOME'
                      ? 'e.g., Salary, Freelance'
                      : formData.account_type === 'EXPENSE'
                        ? 'e.g., Groceries, Rent'
                        : formData.account_type === 'ASSET'
                          ? 'e.g., Savings Account'
                          : 'e.g., Credit Card'
                  }
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                />
              </FormField>

              <FormField label="Account Number" helperText="Optional. Auto-generated if not provided.">
                <Input
                  placeholder="e.g., 4200"
                  value={formData.account_number}
                  onChange={(e) => setFormData({ ...formData, account_number: e.target.value })}
                />
              </FormField>

              {(formData.account_type === 'EXPENSE' || formData.account_type === 'INCOME') && (
                <FormField label="Description" helperText="Optional. Keywords help AI classify transactions.">
                  <Textarea
                    rows={2}
                    placeholder="e.g., REWE, Lidl, EDEKA (for groceries)"
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    maxLength={500}
                  />
                </FormField>
              )}

              <Button
                className="w-full"
                onClick={handleAddAccount}
                isLoading={createAccountMutation.isPending}
                disabled={!formData.name.trim()}
              >
                <Plus className="h-4 w-4" />
                Add Account
              </Button>
            </div>

            <div className="flex gap-3 pt-2">
              <Button variant="secondary" onClick={() => setMode('choose')}>
                <ArrowLeft className="h-4 w-4" />
                Back
              </Button>
              <Button
                variant={createdAccounts.length > 0 ? 'primary' : 'secondary'}
                className="flex-1"
                onClick={onSkipToNext}
              >
                {createdAccounts.length > 0 ? (
                  <>
                    <CheckCircle2 className="h-4 w-4" />
                    Continue ({createdAccounts.length} created)
                  </>
                ) : (
                  'Skip for Now'
                )}
              </Button>
            </div>
          </>
        )}
      </CardContent>
    </>
  )
}
