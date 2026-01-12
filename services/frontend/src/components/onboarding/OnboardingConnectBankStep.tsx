import { CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui'
import { BankConnectionWizard } from '@/components/bank-connection'
import type { UseBankConnectionReturn } from '@/hooks'

interface OnboardingConnectBankStepProps {
  bankConnection: UseBankConnectionReturn
  credentialsCount: number
  onBackToAccounts: () => void
  onSkipToManualAccounts: () => void
  onDone: () => void
}

export function OnboardingConnectBankStep({
  bankConnection,
  credentialsCount,
  onBackToAccounts,
  onSkipToManualAccounts,
  onDone,
}: OnboardingConnectBankStepProps) {
  const title =
    bankConnection.step === 'success'
      ? 'Bank Connected!'
      : credentialsCount > 0
        ? 'Add Another Bank'
        : 'Connect Your Bank'

  const description =
    bankConnection.step === 'find_bank'
      ? 'Enter your bank code (BLZ) to get started.'
      : bankConnection.step === 'credentials'
        ? 'Enter your online banking credentials.'
        : bankConnection.step === 'tan_discovery' && !bankConnection.isDiscoveringAccounts
          ? 'Select your preferred TAN method.'
          : bankConnection.step === 'tan_discovery' && bankConnection.isDiscoveringAccounts
            ? 'Discovering your accounts...'
            : bankConnection.step === 'review_accounts'
              ? 'Review and name your accounts.'
              : bankConnection.step === 'connecting'
                ? 'Importing your accounts...'
                : bankConnection.step === 'initial_sync'
                  ? 'Choose how much history to sync.'
                  : bankConnection.step === 'syncing'
                    ? 'Syncing transactions...'
                    : bankConnection.step === 'success'
                      ? bankConnection.syncResult
                        ? `Synced ${bankConnection.syncResult.total_imported} transactions`
                        : `Imported ${bankConnection.connectionResult?.accounts_imported.length ?? 0} accounts`
                      : bankConnection.step === 'error'
                        ? 'Connection failed'
                        : ''

  return (
    <>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <BankConnectionWizard
          connection={bankConnection}
          existingCredentialsCount={credentialsCount}
          onBack={bankConnection.step === 'find_bank' ? onBackToAccounts : undefined}
          onSkip={bankConnection.step === 'find_bank' ? onSkipToManualAccounts : undefined}
          onDone={onDone}
          onAddAnother={() => bankConnection.reset()}
          showAddAnother={true}
          labels={{
            doneButton: 'Continue',
            skipButton: 'Skip for Now',
          }}
        />
      </CardContent>
    </>
  )
}
