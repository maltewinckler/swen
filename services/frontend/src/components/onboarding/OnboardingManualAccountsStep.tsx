import { ArrowLeft, ArrowRight, CheckCircle2, Plus } from 'lucide-react'
import { Button, CardContent, CardDescription, CardHeader, CardTitle, FormField, InlineAlert, Input } from '@/components/ui'
import { IBANInput } from '@/components/accounts'

export interface ManualAccount {
  name: string
  iban: string
}

interface OnboardingManualAccountsStepProps {
  manualAccounts: ManualAccount[]

  isAddingManualAccount: boolean
  newManualAccount: ManualAccount
  manualAccountError: string
  isSubmitting: boolean

  onStartAdd: () => void
  onCancelAdd: () => void
  onChangeName: (name: string) => void
  onChangeIban: (iban: string) => void
  onAdd: () => void

  onBack: () => void
  onContinue: () => void
}

export function OnboardingManualAccountsStep({
  manualAccounts,
  isAddingManualAccount,
  newManualAccount,
  manualAccountError,
  isSubmitting,
  onStartAdd,
  onCancelAdd,
  onChangeName,
  onChangeIban,
  onAdd,
  onBack,
  onContinue,
}: OnboardingManualAccountsStepProps) {
  return (
    <>
      <CardHeader>
        <CardTitle>Add Manual Accounts</CardTitle>
        <CardDescription>
          Some banks don't offer API access. Add their IBANs here so transfers appear correctly in your reports.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="p-4 rounded-lg bg-bg-subtle border border-border-default">
          <p className="text-sm text-text-secondary mb-3">
            <strong>Examples:</strong> Trade Republic, Wise, N26 (if not using FinTS), crypto exchanges, foreign bank accounts.
          </p>
          <p className="text-xs text-text-muted">
            When you transfer money to these accounts, they'll show as internal transfers instead of expenses.
          </p>
        </div>

        {/* Added accounts */}
        {manualAccounts.length > 0 && (
          <FormField label="Added Accounts">
            <div className="space-y-2">
              {manualAccounts.map((acc, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 rounded-lg bg-accent-success/5 border border-accent-success/20"
                >
                  <div>
                    <p className="font-medium text-text-primary">{acc.name}</p>
                    <p className="text-xs text-text-muted font-mono">{acc.iban}</p>
                  </div>
                  <CheckCircle2 className="h-5 w-5 text-accent-success" />
                </div>
              ))}
            </div>
          </FormField>
        )}

        {/* Add new account form */}
        {isAddingManualAccount ? (
          <div className="space-y-3 p-4 rounded-lg border border-border-default">
            {manualAccountError && <InlineAlert variant="danger">{manualAccountError}</InlineAlert>}

            <FormField label="Account Name">
              <Input
                placeholder="e.g., Trade Republic"
                value={newManualAccount.name}
                onChange={(e) => onChangeName(e.target.value)}
              />
            </FormField>
            <FormField label="IBAN">
              <IBANInput value={newManualAccount.iban} onChange={onChangeIban} />
            </FormField>
            <div className="flex gap-2">
              <Button variant="secondary" onClick={onCancelAdd}>
                Cancel
              </Button>
              <Button onClick={onAdd} isLoading={isSubmitting} className="flex-1">
                <Plus className="h-4 w-4 mr-2" />
                Add Account
              </Button>
            </div>
          </div>
        ) : (
          <Button variant="secondary" className="w-full" onClick={onStartAdd}>
            <Plus className="h-4 w-4 mr-2" />
            Add Manual Account
          </Button>
        )}

        {/* Only show navigation when not adding an account */}
        {!isAddingManualAccount && (
          <div className="flex gap-3 pt-4">
            <Button variant="secondary" onClick={onBack}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
            <Button className="flex-1" onClick={onContinue}>
              {manualAccounts.length > 0 ? 'Continue' : 'Skip'}
              <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
          </div>
        )}
      </CardContent>
    </>
  )
}
