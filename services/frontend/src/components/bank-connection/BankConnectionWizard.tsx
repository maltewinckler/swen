/**
 * BankConnectionWizard - Reusable multi-step bank connection flow
 *
 * This component provides the complete UI for connecting a bank account:
 * 1. Find bank by BLZ
 * 2. Enter credentials
 * 3. Select TAN method
 * 4. Review discovered accounts
 * 5. Initial sync
 *
 * Usage:
 * ```tsx
 * const bankConnection = useBankConnection({ onSuccess: () => ... })
 *
 * <BankConnectionWizard
 *   connection={bankConnection}
 *   existingCredentialsCount={credentials.length}
 *   onBack={() => ...}
 *   onDone={() => ...}
 *   onAddAnother={() => bankConnection.reset()}
 * />
 * ```
 */

import {
  Building2,
  CheckCircle2,
  Loader2,
  Search,
  Plus,
  Pencil,
  RefreshCw,
  AlertCircle,
  ArrowLeft,
  ArrowRight
} from 'lucide-react'
import {
  Button,
  Input,
  FormField
} from '@/components/ui'
import { TANApprovalNotice } from '@/components/TANApprovalNotice'
import { SyncProgressDisplay } from '@/components/SyncProgressDisplay'
import type { UseBankConnectionReturn } from '@/hooks'
import { cn, formatCurrency } from '@/lib/utils'

export interface BankConnectionWizardProps {
  /** The bank connection state from useBankConnection hook */
  connection: UseBankConnectionReturn
  /** Number of existing bank credentials (for messaging) */
  existingCredentialsCount?: number
  /** Called when user clicks "Back" on the first step */
  onBack?: () => void
  /** Called when user clicks "Skip" on the first step (skips bank connection) */
  onSkip?: () => void
  /** Called when user clicks "Done" or "Continue" after success */
  onDone?: () => void
  /** Called when user wants to add another bank */
  onAddAnother?: () => void
  /** Whether to show the "Add Another Bank" button on success */
  showAddAnother?: boolean
  /** Custom labels */
  labels?: {
    doneButton?: string
    skipButton?: string
    searchButton?: string
  }
}

export function BankConnectionWizard({
  connection,
  existingCredentialsCount = 0,
  onBack,
  onSkip,
  onDone,
  onAddAnother,
  showAddAnother = true,
  labels = {},
}: BankConnectionWizardProps) {
  const {
    step,
    bankForm,
    bankLookup,
    bankLookupError,
    bankError,
    isLookingUp,
    discoveredTanMethods,
    isDiscoveringTan,
    tanDiscoveryError,
    discoveredAccounts,
    accountNames,
    isDiscoveringAccounts,
    accountDiscoveryError,
    connectionResult,
    syncDays,
    syncProgress,
    syncResult,
    syncError,
    setStep,
    setBankForm,
    setAccountNames,
    setSyncDays,
    handleBankLookup,
    handleDiscoverTanMethods,
    handleDiscoverAccounts,
    handleConnect,
    handleInitialSync,
    handleSkipSync,
    reset,
  } = connection

  const doneButtonLabel = labels.doneButton || 'Done'

  return (
    <div className="space-y-4">
      {/* Step 1: Find Bank */}
      {step === 'find_bank' && (
        <form
          className="space-y-4"
          onSubmit={(e) => { e.preventDefault(); handleBankLookup(); }}
        >
          {existingCredentialsCount > 0 && (
            <div className="p-3 rounded-lg bg-accent-success/10 border border-accent-success/20 mb-4">
              <p className="text-sm text-text-primary">
                <CheckCircle2 className="h-4 w-4 inline mr-2 text-accent-success" />
                You have {existingCredentialsCount} bank{existingCredentialsCount > 1 ? 's' : ''} connected
              </p>
            </div>
          )}
          <FormField label="Bank Code (BLZ)" error={bankLookupError}>
              <Input
                placeholder="e.g., 12030000"
                value={bankForm.blz}
                onChange={(e) => setBankForm({ ...bankForm, blz: e.target.value.replace(/\D/g, '').slice(0, 8) })}
                maxLength={8}
              />
          </FormField>
          <div className="flex gap-3 pt-2">
          {onBack && (
              <Button type="button" variant="secondary" onClick={onBack}>
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back
              </Button>
            )}
            {onSkip && (
              <Button type="button" variant="ghost" className="border border-border-subtle" onClick={onSkip}>
                {labels.skipButton || 'Skip'}
              </Button>
            )}
            <Button
              type="submit"
              disabled={isLookingUp || bankForm.blz.length !== 8}
              className="flex-1"
            >
              {isLookingUp ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Search className="h-4 w-4 mr-2" />}
              {labels.searchButton || 'Search Bank'}
              </Button>
            </div>
        </form>
      )}

      {/* Step 2: Credentials */}
      {step === 'credentials' && (
        <form
          className="space-y-4"
          onSubmit={(e) => { e.preventDefault(); handleDiscoverTanMethods(); }}
        >
          <div className="p-3 rounded-lg bg-accent-primary/10 border border-accent-primary/20">
            <div className="flex items-center gap-2">
              <Building2 className="h-5 w-5 text-accent-primary" />
              <span className="font-medium text-text-primary">{bankLookup?.name}</span>
            </div>
          </div>
          <FormField label="Username / Login ID">
            <Input
              value={bankForm.username}
              onChange={(e) => setBankForm({ ...bankForm, username: e.target.value })}
              placeholder="Your online banking username"
            />
          </FormField>
          <FormField label="PIN / Password" error={tanDiscoveryError}>
            <Input
              type="password"
              value={bankForm.pin}
              onChange={(e) => setBankForm({ ...bankForm, pin: e.target.value })}
              placeholder="Your online banking PIN"
            />
          </FormField>
          <div className="flex gap-3 pt-2">
            <Button type="button" variant="secondary" onClick={() => setStep('find_bank')}>
              Back
            </Button>
            <Button type="submit" disabled={isDiscoveringTan} className="flex-1">
              {isDiscoveringTan ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Continue
            </Button>
          </div>
        </form>
      )}

      {/* Step 3: TAN Method Selection */}
      {step === 'tan_discovery' && !isDiscoveringAccounts && (
        <form
          className="space-y-4"
          onSubmit={(e) => { e.preventDefault(); handleDiscoverAccounts(); }}
        >
          <FormField label="Select TAN Method" error={accountDiscoveryError}>
            <div className="space-y-2">
              {discoveredTanMethods.map((method) => (
                <label
                  key={method.code}
                  className={cn(
                    "flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors",
                    "focus-within:outline-none focus-within:ring-2 focus-within:ring-accent-primary/50 focus-within:ring-offset-2 focus-within:ring-offset-bg-surface",
                    bankForm.tan_method === method.code
                      ? "border-accent-primary bg-accent-primary/5"
                      : "border-border-default hover:border-border-hover"
                  )}
                >
                  <input
                    type="radio"
                    name="tan_method"
                    value={method.code}
                    checked={bankForm.tan_method === method.code}
                    onChange={() => setBankForm({
                      ...bankForm,
                      tan_method: method.code,
                      tan_medium: method.is_decoupled ? method.name : '',
                    })}
                    className="sr-only"
                  />
                  <div className={cn(
                    "w-4 h-4 rounded-full border-2 flex items-center justify-center",
                    bankForm.tan_method === method.code ? "border-accent-primary" : "border-border-default"
                  )}>
                    {bankForm.tan_method === method.code && (
                      <div className="w-2 h-2 rounded-full bg-accent-primary" />
                    )}
                  </div>
                  <div>
                    <p className="font-medium text-text-primary">{method.name}</p>
                  </div>
                </label>
              ))}
            </div>
          </FormField>
          <div className="flex gap-3 pt-2">
            <Button type="button" variant="secondary" onClick={() => setStep('credentials')}>
              Back
            </Button>
            <Button type="submit" className="flex-1">
              Continue
            </Button>
          </div>
        </form>
      )}

      {/* Discovering Accounts State */}
      {step === 'tan_discovery' && isDiscoveringAccounts && (
        <div className="py-8 text-center">
          <Loader2 className="h-12 w-12 text-accent-primary animate-spin mx-auto mb-4" />
          <p className="text-text-primary font-medium mb-2">Connecting to {bankLookup?.name}...</p>
          <TANApprovalNotice showTimingNote className="text-left" />
        </div>
      )}

      {/* Step 4: Review Accounts */}
      {step === 'review_accounts' && (
        <div className="space-y-4">
          <div className="p-3 rounded-lg bg-accent-primary/10 border border-accent-primary/20">
            <div className="flex items-center gap-2">
              <Building2 className="h-5 w-5 text-accent-primary" />
              <span className="font-medium text-text-primary">{bankLookup?.name}</span>
            </div>
            <p className="text-sm text-text-secondary mt-1">
              Found {discoveredAccounts.length} account{discoveredAccounts.length !== 1 ? 's' : ''}
            </p>
          </div>
          <FormField label="Review and customize account names">
            <div className="space-y-3">
              {discoveredAccounts.map((acc) => (
                <div key={acc.iban} className="p-3 rounded-lg border border-border-default bg-bg-subtle">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs text-text-muted font-mono">{acc.iban}</p>
                    {acc.balance && (
                      <p className="text-xs text-text-secondary font-mono">
                        {formatCurrency(acc.balance, acc.currency)}
                      </p>
                    )}
                  </div>
                  <div className="relative">
                    <Input
                      value={accountNames[acc.iban] || ''}
                      onChange={(e) => setAccountNames(prev => ({
                        ...prev,
                        [acc.iban]: e.target.value
                      }))}
                      placeholder={acc.default_name}
                      className="pr-8"
                    />
                    <Pencil className="absolute right-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted pointer-events-none" />
                  </div>
                </div>
              ))}
            </div>
          </FormField>
          <div className="flex gap-3 pt-2">
            <Button type="button" variant="secondary" onClick={() => setStep('tan_discovery')}>
              Back
            </Button>
            <Button onClick={handleConnect} className="flex-1">
              Import Accounts
            </Button>
          </div>
        </div>
      )}

      {/* Connecting State */}
      {step === 'connecting' && (
        <div className="py-8 text-center">
          <Loader2 className="h-12 w-12 text-accent-primary animate-spin mx-auto mb-4" />
          <p className="text-text-primary font-medium mb-2">Connecting to {bankLookup?.name}...</p>
          <TANApprovalNotice variant="compact" showTimingNote />
        </div>
      )}

      {/* Step 5: Initial Sync */}
      {step === 'initial_sync' && connectionResult && (
        <div className="space-y-4">
          <div className="p-4 rounded-lg bg-accent-success/10 border border-accent-success/20">
            <div className="flex items-start gap-3">
              <CheckCircle2 className="h-6 w-6 text-accent-success flex-shrink-0" />
              <div>
                <p className="font-medium text-text-primary">{bankLookup?.name}</p>
                <p className="text-sm text-text-secondary mt-1">
                  {connectionResult.accounts_imported.length} account{connectionResult.accounts_imported.length !== 1 ? 's' : ''} imported
                </p>
              </div>
            </div>
          </div>
          <FormField label="How many days of transaction history would you like to sync?">
            <div className="grid grid-cols-4 gap-2">
              {[30, 90, 365, 730].map((days) => (
                <button
                  key={days}
                  onClick={() => setSyncDays(days)}
                  className={cn(
                    "py-3 px-2 rounded-lg border text-sm font-medium transition-colors",
                    syncDays === days
                      ? "border-accent-primary bg-accent-primary/10 text-accent-primary"
                      : "border-border-default hover:border-border-hover text-text-secondary"
                  )}
                >
                  {days < 365 ? `${days} days` : days === 365 ? '1 year' : '2 years'}
                </button>
              ))}
            </div>
            <TANApprovalNotice
              variant="inline"
              message="Larger time ranges may require TAN approval."
              className="mt-2"
            />
          </FormField>
          <div className="flex gap-3 pt-2">
            <Button variant="secondary" onClick={handleSkipSync}>
              Skip
            </Button>
            <Button onClick={handleInitialSync} className="flex-1">
              <RefreshCw className="h-4 w-4 mr-2" />
              Sync Now
            </Button>
          </div>
        </div>
      )}

      {/* Syncing State */}
      {step === 'syncing' && (
        <SyncProgressDisplay progress={syncProgress} className="py-6" />
      )}

      {/* Success State */}
      {step === 'success' && (
        <div className="space-y-4">
          <div className="p-4 rounded-lg bg-accent-success/10 border border-accent-success/20">
            <div className="flex items-start gap-3">
              <CheckCircle2 className="h-6 w-6 text-accent-success flex-shrink-0" />
              <div>
                <p className="font-medium text-text-primary">{bankLookup?.name}</p>
                <p className="text-sm text-text-secondary mt-1">
                  {syncResult
                    ? `Synced ${syncResult.total_imported} transactions`
                    : connectionResult?.message || 'Connection successful'}
                </p>
              </div>
            </div>
          </div>
          {syncResult && (
            <div className="grid grid-cols-3 gap-3">
              <div className="p-3 rounded-lg bg-bg-subtle text-center">
                <p className="text-2xl font-semibold text-accent-success">{syncResult.total_imported}</p>
                <p className="text-xs text-text-muted">Imported</p>
              </div>
              <div className="p-3 rounded-lg bg-bg-subtle text-center">
                <p className="text-2xl font-semibold text-text-secondary">{syncResult.total_skipped}</p>
                <p className="text-xs text-text-muted">Skipped</p>
              </div>
              <div className="p-3 rounded-lg bg-bg-subtle text-center">
                <p className="text-2xl font-semibold text-text-secondary">{syncResult.accounts_synced}</p>
                <p className="text-xs text-text-muted">Accounts</p>
              </div>
            </div>
          )}
          {!syncResult && connectionResult && connectionResult.accounts_imported.length > 0 && (
            <div>
              <p className="text-sm font-medium text-text-primary mb-2">Imported Accounts:</p>
              <div className="space-y-1">
                {connectionResult.accounts_imported.map((acc) => (
                  <div key={acc.iban} className="text-sm text-text-secondary flex items-center gap-2">
                    <CheckCircle2 className="h-3 w-3 text-accent-success" />
                    {acc.account_name}
                  </div>
                ))}
              </div>
            </div>
          )}
          <div className="flex gap-3">
            {showAddAnother && onAddAnother && (
              <Button variant="secondary" className="flex-1" onClick={() => { reset(); onAddAnother(); }}>
                <Plus className="h-4 w-4 mr-2" />
                Add Another Bank
              </Button>
            )}
            {onDone && (
              <Button className="flex-1" onClick={onDone}>
                {doneButtonLabel}
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Error State */}
      {step === 'error' && (
        <div className="space-y-4">
          <div className="p-4 rounded-lg bg-accent-danger/10 border border-accent-danger/20">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-6 w-6 text-accent-danger flex-shrink-0" />
              <div>
                <p className="font-medium text-text-primary">
                  {syncError ? 'Sync Failed' : 'Connection Failed'}
                </p>
                <p className="text-sm text-text-secondary mt-1">{syncError || bankError}</p>
              </div>
            </div>
          </div>
          <div className="flex gap-3">
            <Button variant="secondary" className="flex-1" onClick={reset}>
              Try Again
            </Button>
            {onDone && (
              <Button variant="secondary" className="flex-1" onClick={onDone}>
                Skip
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
