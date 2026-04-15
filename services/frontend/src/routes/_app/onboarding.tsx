import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Card, StepIndicator, useToast } from '@/components/ui'
import { useBankConnection } from '@/hooks'
import { initChartOfAccounts, listCredentials, createExternalAccount, saveLocalFinTSConfig, getBankingProviderStatus, saveGeldstromApiConfig, activateProvider } from '@/api'
import { useAuthStore } from '@/stores'
import {
  OnboardingAccountsSetupStep,
  OnboardingCompleteStep,
  OnboardingConnectBankStep,
  OnboardingBankingProviderStep,
  OnboardingManualAccountsStep,
  OnboardingWelcomeStep,
  type ManualAccount,
  type BankingProviderSaveParams,
} from '@/components/onboarding'

export const Route = createFileRoute('/_app/onboarding')({
  component: OnboardingPage,
})

type OnboardingStep = 'welcome' | 'banking_provider' | 'accounts' | 'connect_bank' | 'manual_accounts' | 'complete'

function OnboardingPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const toast = useToast()
  const { user } = useAuthStore()
  const isAdmin = user?.role === 'admin'

  const [currentStep, setCurrentStep] = useState<OnboardingStep>('welcome')

  const bankConnection = useBankConnection({
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['onboarding'] })
    },
  })

  // Manual accounts state
  const [manualAccounts, setManualAccounts] = useState<ManualAccount[]>([])
  const [newManualAccount, setNewManualAccount] = useState<ManualAccount>({ name: '', iban: '' })
  const [manualAccountError, setManualAccountError] = useState('')
  const [isAddingManualAccount, setIsAddingManualAccount] = useState(false)

  // Query for existing credentials
  const { data: credentialsData } = useQuery({
    queryKey: ['credentials'],
    queryFn: listCredentials,
  })
  const credentials = credentialsData?.credentials ?? []

  // Mutations
  const initChartMutation = useMutation({
    mutationFn: () => initChartOfAccounts('minimal'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
      queryClient.invalidateQueries({ queryKey: ['onboarding'] })
      setCurrentStep('connect_bank')
    },
    onError: (err) => {
      toast.danger({
        title: 'Failed to initialize accounts',
        description: err instanceof Error ? err.message : 'Unknown error',
      })
    },
  })

  const addManualAccountMutation = useMutation({
    mutationFn: (data: ManualAccount) =>
      createExternalAccount({
        iban: data.iban.replace(/\s/g, ''),
        name: data.name.trim(),
        currency: 'EUR',
        reconcile: true,
      }),
    onSuccess: (_, variables) => {
      setManualAccounts((prev) => [...prev, variables])
      setNewManualAccount({ name: '', iban: '' })
      setManualAccountError('')
      setIsAddingManualAccount(false)
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
      queryClient.invalidateQueries({ queryKey: ['mappings'] })
    },
    onError: (err) => {
      setManualAccountError(err instanceof Error ? err.message : 'Failed to add account')
    },
  })

  const handleAddManualAccount = () => {
    setManualAccountError('')
    if (!newManualAccount.name.trim()) {
      setManualAccountError('Account name is required')
      return
    }
    const iban = newManualAccount.iban.replace(/\s/g, '')
    if (iban.length < 15 || iban.length > 34) {
      setManualAccountError('IBAN must be between 15 and 34 characters')
      return
    }
    addManualAccountMutation.mutate(newManualAccount)
  }

  const handleContinueToManualAccounts = () => {
    bankConnection.reset()
    setCurrentStep('manual_accounts')
  }

  const handleComplete = () => {
    navigate({ to: '/dashboard' })
  }

  // Banking provider mutation (admin only)
  const [bankingProviderError, setBankingProviderError] = useState<string | null>(null)
  // Track whether the banking_provider step was shown this session so the step
  // indicator and back-navigation remain stable after the provider is saved.
  const [providerStepWasShown, setProviderStepWasShown] = useState(false)
  const bankingProviderMutation = useMutation({
    mutationFn: async (params: BankingProviderSaveParams) => {
      if (params.mode === 'api') {
        await saveGeldstromApiConfig(params.apiKey, params.endpointUrl)
      } else {
        await saveLocalFinTSConfig(params.productId, params.file)
      }
      await activateProvider(params.mode)
    },
    onSuccess: () => {
      toast.success({ description: 'Banking provider configured' })
      setBankingProviderError(null)
      queryClient.invalidateQueries({ queryKey: ['admin', 'fints-provider'] })
      queryClient.invalidateQueries({ queryKey: ['admin', 'fints-config'] })
      setCurrentStep('accounts')
    },
    onError: (err) => {
      setBankingProviderError(err instanceof Error ? err.message : 'Failed to save banking provider configuration')
    },
  })

  // Check if a banking provider is already active (admin only)
  const { data: providerStatus } = useQuery({
    queryKey: ['admin', 'fints-provider', 'status'],
    queryFn: getBankingProviderStatus,
    enabled: isAdmin,
  })
  // Show the provider step when no provider is active yet, OR when we already
  // navigated to it this session (so it stays stable after save).
  const showBankingProviderStep = isAdmin && (!providerStatus?.active_provider || providerStepWasShown)

  // Navigate from welcome: admins who need provider setup go to banking_provider, others go to accounts
  const handleWelcomeNext = () => {
    if (showBankingProviderStep) {
      setProviderStepWasShown(true)
      setCurrentStep('banking_provider')
    } else {
      setCurrentStep('accounts')
    }
  }

  const ONBOARDING_STEPS = [
    { id: 'welcome', label: 'Welcome' },
    ...(showBankingProviderStep ? [{ id: 'banking_provider', label: 'Provider' }] : []),
    { id: 'accounts', label: 'Accounts' },
    { id: 'connect_bank', label: 'Banks' },
    { id: 'manual_accounts', label: 'Manual' },
    { id: 'complete', label: 'Done' },
  ]

  return (
    <div className="min-h-[80vh] flex flex-col items-center justify-center px-4 py-8 animate-fade-in">
      <div className="w-full max-w-2xl mb-8">
        <StepIndicator steps={ONBOARDING_STEPS} currentStepId={currentStep} />
      </div>

      <Card className="w-full max-w-2xl animate-scale-in">
        {currentStep === 'welcome' && (
          <OnboardingWelcomeStep onNext={handleWelcomeNext} />
        )}

        {currentStep === 'banking_provider' && (
          <OnboardingBankingProviderStep
            onSkip={() => setCurrentStep('accounts')}
            onSave={(params) => bankingProviderMutation.mutate(params)}
            isSaving={bankingProviderMutation.isPending}
            saveError={bankingProviderError}
          />
        )}

        {currentStep === 'accounts' && (
          <OnboardingAccountsSetupStep
            isLoading={initChartMutation.isPending}
            onBack={() => setCurrentStep(showBankingProviderStep ? 'banking_provider' : 'welcome')}
            onCreateAccounts={() => initChartMutation.mutate()}
            onSkipToNext={() => setCurrentStep('connect_bank')}
          />
        )}

        {currentStep === 'connect_bank' && (
          <OnboardingConnectBankStep
            bankConnection={bankConnection}
            credentialsCount={credentials.length}
            onBackToAccounts={() => setCurrentStep('accounts')}
            onSkipToManualAccounts={handleContinueToManualAccounts}
            onDone={handleContinueToManualAccounts}
          />
        )}

        {currentStep === 'manual_accounts' && (
          <OnboardingManualAccountsStep
            manualAccounts={manualAccounts}
            isAddingManualAccount={isAddingManualAccount}
            newManualAccount={newManualAccount}
            manualAccountError={manualAccountError}
            isSubmitting={addManualAccountMutation.isPending}
            onStartAdd={() => setIsAddingManualAccount(true)}
            onCancelAdd={() => {
              setIsAddingManualAccount(false)
              setNewManualAccount({ name: '', iban: '' })
              setManualAccountError('')
            }}
            onChangeName={(name) => setNewManualAccount((prev) => ({ ...prev, name }))}
            onChangeIban={(iban) => setNewManualAccount((prev) => ({ ...prev, iban }))}
            onAdd={handleAddManualAccount}
            onBack={() => setCurrentStep('connect_bank')}
            onContinue={() => setCurrentStep('complete')}
          />
        )}

        {currentStep === 'complete' && (
          <OnboardingCompleteStep
            credentialsCount={credentials.length}
            manualAccountsCount={manualAccounts.length}
            onFinish={handleComplete}
          />
        )}
      </Card>
    </div>
  )
}
