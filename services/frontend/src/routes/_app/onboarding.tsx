import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Card, StepIndicator, useToast } from '@/components/ui'
import { useBankConnection } from '@/hooks'
import { initChartOfAccounts, listCredentials, createExternalAccount, saveInitialFinTSConfig, getFinTSConfigStatus } from '@/api'
import { useAuthStore } from '@/stores'
import {
  OnboardingAccountsSetupStep,
  OnboardingCompleteStep,
  OnboardingConnectBankStep,
  OnboardingFinTSConfigStep,
  OnboardingManualAccountsStep,
  OnboardingWelcomeStep,
  type ManualAccount,
} from '@/components/onboarding'

export const Route = createFileRoute('/_app/onboarding')({
  component: OnboardingPage,
})

type OnboardingStep = 'welcome' | 'fints_config' | 'accounts' | 'connect_bank' | 'manual_accounts' | 'complete'

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

  // FinTS config mutation (admin only)
  const [fintsError, setFintsError] = useState<string | null>(null)
  const fintsConfigMutation = useMutation({
    mutationFn: ({ productId, file }: { productId: string; file: File }) =>
      saveInitialFinTSConfig(productId, file),
    onSuccess: (data) => {
      toast.success({
        title: 'FinTS configured',
        description: `${data.institute_count} institutes loaded`,
      })
      setFintsError(null)
      queryClient.invalidateQueries({ queryKey: ['admin', 'fints-config'] })
      setCurrentStep('accounts')
    },
    onError: (err) => {
      setFintsError(err instanceof Error ? err.message : 'Failed to save FinTS configuration')
    },
  })

  // Check if FinTS is already configured (admin only)
  const { data: fintsStatus } = useQuery({
    queryKey: ['admin', 'fints-config', 'status'],
    queryFn: getFinTSConfigStatus,
    enabled: isAdmin,
  })
  const showFinTSStep = isAdmin && !fintsStatus?.is_configured

  // Navigate from welcome: admins who need FinTS go to fints_config, others go to accounts
  const handleWelcomeNext = () => {
    if (showFinTSStep) {
      setCurrentStep('fints_config')
    } else {
      setCurrentStep('accounts')
    }
  }

  const ONBOARDING_STEPS = [
    { id: 'welcome', label: 'Welcome' },
    ...(showFinTSStep ? [{ id: 'fints_config', label: 'FinTS' }] : []),
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

        {currentStep === 'fints_config' && (
          <OnboardingFinTSConfigStep
            onSkip={() => setCurrentStep('accounts')}
            onSave={(productId, file) => fintsConfigMutation.mutate({ productId, file })}
            isSaving={fintsConfigMutation.isPending}
            saveError={fintsError}
          />
        )}

        {currentStep === 'accounts' && (
          <OnboardingAccountsSetupStep
            isLoading={initChartMutation.isPending}
            onBack={() => setCurrentStep(showFinTSStep ? 'fints_config' : 'welcome')}
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
