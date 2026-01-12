import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Card, StepIndicator, useToast } from '@/components/ui'
import { useBankConnection } from '@/hooks'
import {
  initChartOfAccounts,
  listCredentials,
  createExternalAccount,
  getAIStatus,
  listAIModels,
  pullModel,
  updateAISettings,
} from '@/api'
import {
  OnboardingAIModelStep,
  OnboardingAccountsSetupStep,
  OnboardingCompleteStep,
  OnboardingConnectBankStep,
  OnboardingManualAccountsStep,
  OnboardingWelcomeStep,
  type ManualAccount,
} from '@/components/onboarding'

export const Route = createFileRoute('/_app/onboarding')({
  component: OnboardingPage,
})

type OnboardingStep = 'welcome' | 'ai_model' | 'accounts' | 'connect_bank' | 'manual_accounts' | 'complete'

function OnboardingPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const toast = useToast()

  // Main wizard step
  const [currentStep, setCurrentStep] = useState<OnboardingStep>('welcome')

  // Bank connection hook
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

  // AI model selection state
  const [selectedAIModel, setSelectedAIModel] = useState<string | null>(null)
  const [aiSkipped, setAISkipped] = useState(false)
  const [downloadingModel, setDownloadingModel] = useState<string | null>(null)
  const [downloadProgress, setDownloadProgress] = useState<number>(0)
  const [downloadStatus, setDownloadStatus] = useState<string>('')
  const [downloadError, setDownloadError] = useState<string | null>(null)

  // Query for existing credentials
  const { data: credentialsData } = useQuery({
    queryKey: ['credentials'],
    queryFn: listCredentials,
  })
  const credentials = credentialsData?.credentials ?? []

  // Query for AI status
  const { data: aiStatus, isLoading: aiStatusLoading } = useQuery({
    queryKey: ['ai', 'status'],
    queryFn: getAIStatus,
  })

  // Query for AI models (only when on AI step and service is healthy)
  const { data: aiModelsData, isLoading: aiModelsLoading, refetch: refetchAIModels } = useQuery({
    queryKey: ['ai', 'models'],
    queryFn: listAIModels,
    enabled: currentStep === 'ai_model' && aiStatus?.service_healthy === true,
  })

  // Auto-select recommended model (qwen2.5:3b) when models load
  useEffect(() => {
    if (aiModelsData?.models && !selectedAIModel) {
      const recommendedModel = 'qwen2.5:3b'
      const model = aiModelsData.models.find((m) => m.name === recommendedModel)
      if (model?.status === 'available') {
        setSelectedAIModel(recommendedModel)
      }
    }
  }, [aiModelsData, selectedAIModel])

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
        iban: data.iban.replace(/\s/g, ''), // Remove spaces from formatted IBAN
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

  // Handle adding manual account
  const handleAddManualAccount = () => {
    setManualAccountError('')
    if (!newManualAccount.name.trim()) {
      setManualAccountError('Account name is required')
      return
    }
    const iban = newManualAccount.iban.replace(/\s/g, '') // Remove spaces
    if (iban.length < 15 || iban.length > 34) {
      setManualAccountError('IBAN must be between 15 and 34 characters')
      return
    }
    addManualAccountMutation.mutate(newManualAccount)
  }

  // Handle continue to manual accounts from bank connection
  const handleContinueToManualAccounts = () => {
    bankConnection.reset()
    setCurrentStep('manual_accounts')
  }

  // Handle AI model download
  const handleDownloadAIModel = (modelName: string) => {
    setSelectedAIModel(modelName)
    setDownloadingModel(modelName)
    setDownloadProgress(0)
    setDownloadStatus('Starting...')
    setDownloadError(null)

    let maxProgress = 0

    pullModel(
      modelName,
      (progress) => {
        if (progress.status && progress.status !== 'success') {
          const statusText = progress.status
            .replace('pulling ', '')
            .replace('downloading ', 'Downloading ')
            .replace('verifying ', 'Verifying ')
            .replace('writing ', 'Writing ')
          setDownloadStatus(statusText)
        }

        if (progress.progress !== null) {
          const newProgress = progress.progress * 100
          if (newProgress > maxProgress) {
            maxProgress = newProgress
            setDownloadProgress(newProgress)
          }
        }

        if (progress.is_complete) {
          setDownloadProgress(100)
          setDownloadStatus('Complete!')
        }
      },
      (error) => {
        setDownloadError(error)
        setDownloadingModel(null)
        setDownloadProgress(0)
        setDownloadStatus('')
      },
      async () => {
        setDownloadingModel(null)
        setDownloadStatus('')
        // Update user settings to use this model
        try {
          await updateAISettings({ model_name: modelName, enabled: true })
        } catch {
          // Ignore - user can update later
        }
        refetchAIModels()
      }
    )
  }

  // Handle skipping AI
  const handleSkipAI = async () => {
    setAISkipped(true)
    try {
      await updateAISettings({ enabled: false })
    } catch {
      // Ignore - user can update later
    }
    setCurrentStep('accounts')
  }

  // Handle continuing from AI step
  const handleContinueFromAI = async () => {
    if (selectedAIModel) {
      try {
        await updateAISettings({ model_name: selectedAIModel, enabled: true })
      } catch {
        // Ignore - user can update later in settings
      }
    }
    setCurrentStep('accounts')
  }

  // Complete onboarding
  const handleComplete = () => {
    navigate({ to: '/dashboard' })
  }

  const ONBOARDING_STEPS = [
    { id: 'welcome', label: 'Welcome' },
    { id: 'ai_model', label: 'AI' },
    { id: 'accounts', label: 'Accounts' },
    { id: 'connect_bank', label: 'Banks' },
    { id: 'manual_accounts', label: 'Manual' },
    { id: 'complete', label: 'Done' },
  ]

  const hasInstalledModel = aiModelsData?.models.some((m) => m.status === 'available') ?? false

  return (
    <div className="min-h-[80vh] flex flex-col items-center justify-center px-4 py-8 animate-fade-in">
      <div className="w-full max-w-2xl mb-8">
        <StepIndicator steps={ONBOARDING_STEPS} currentStepId={currentStep} />
      </div>

      <Card className="w-full max-w-2xl animate-scale-in">
        {currentStep === 'welcome' && (
          <OnboardingWelcomeStep onNext={() => setCurrentStep('ai_model')} />
        )}

        {currentStep === 'ai_model' && (
          <OnboardingAIModelStep
            aiStatusLoading={aiStatusLoading}
            aiServiceHealthy={aiStatus?.service_healthy === true}
            aiModelsLoading={aiModelsLoading}
            aiModels={aiModelsData?.models}
            hasInstalledModel={hasInstalledModel}
            selectedAIModel={selectedAIModel}
            downloadingModel={downloadingModel}
            downloadProgress={downloadProgress}
            downloadStatus={downloadStatus}
            downloadError={downloadError}
            onBack={() => setCurrentStep('welcome')}
            onSkipAISetup={handleSkipAI}
            onSelectModel={(modelName) => setSelectedAIModel(modelName)}
            onDownloadModel={handleDownloadAIModel}
            onContinue={handleContinueFromAI}
          />
        )}

        {currentStep === 'accounts' && (
          <OnboardingAccountsSetupStep
            isLoading={initChartMutation.isPending}
            onBack={() => setCurrentStep('ai_model')}
            onCreateAccounts={() => initChartMutation.mutate()}
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
            selectedAIModel={selectedAIModel}
            aiSkipped={aiSkipped}
            aiModels={aiModelsData?.models}
            credentialsCount={credentials.length}
            manualAccountsCount={manualAccounts.length}
            onFinish={handleComplete}
          />
        )}
      </Card>
    </div>
  )
}
