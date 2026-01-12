/**
 * AI Settings Section
 *
 * Manages AI classification settings, model selection, and testing.
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Download, Cpu, TestTube2, RefreshCw, CheckCircle2 } from 'lucide-react'
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  FormField,
  Input,
  Button,
  Spinner,
  Badge,
  InlineAlert,
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from '@/components/ui'
import {
  getAIStatus,
  listAIModels,
  getAISettings,
  updateAISettings,
  pullModel,
  testAIClassification,
  getAITestExamples,
  type AITestExample,
} from '@/api'
import { cn, formatSignedCurrency } from '@/lib/utils'

export function AISettingsSection() {
  const queryClient = useQueryClient()

  // Fetch AI status
  const {
    data: aiStatus,
    isLoading: statusLoading,
    error: statusError,
  } = useQuery({
    queryKey: ['ai', 'status'],
    queryFn: getAIStatus,
    refetchInterval: 30000, // Refresh every 30s
  })

  // Fetch available models
  const {
    data: modelsData,
    isLoading: modelsLoading,
    refetch: refetchModels,
  } = useQuery({
    queryKey: ['ai', 'models'],
    queryFn: listAIModels,
    enabled: aiStatus?.service_healthy === true,
  })

  // Fetch user settings
  const { data: userSettings, isLoading: settingsLoading } = useQuery({
    queryKey: ['ai', 'settings'],
    queryFn: getAISettings,
  })

  // Fetch test examples
  const { data: testExamples } = useQuery({
    queryKey: ['ai', 'test-examples'],
    queryFn: getAITestExamples,
    enabled: aiStatus?.service_healthy === true,
  })

  // Download state
  const [downloadingModel, setDownloadingModel] = useState<string | null>(null)
  const [downloadProgress, setDownloadProgress] = useState<number | null>(null)
  const [downloadStatus, setDownloadStatus] = useState<string>('')
  const [downloadError, setDownloadError] = useState<string | null>(null)

  // Test AI state
  const [testForm, setTestForm] = useState({
    counterparty_name: '',
    purpose: '',
    amount: '',
  })
  const [testResult, setTestResult] = useState<{
    model_used: string
    suggestion: { account_name: string; confidence: number; reasoning: string | null } | null
    meets_confidence_threshold: boolean
    processing_time_ms: number
  } | null>(null)
  const [isTesting, setIsTesting] = useState(false)
  const [testError, setTestError] = useState<string | null>(null)

  // Settings mutation
  const updateSettingsMutation = useMutation({
    mutationFn: updateAISettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai', 'settings'] })
      queryClient.invalidateQueries({ queryKey: ['ai', 'status'] })
    },
  })

  // Handle model download
  const handleDownloadModel = (modelName: string) => {
    setDownloadingModel(modelName)
    setDownloadProgress(0)
    setDownloadStatus('Starting...')
    setDownloadError(null)

    // Track max progress to avoid jumps when phases change
    let maxProgress = 0

    pullModel(
      modelName,
      (progress) => {
        // Update status text (e.g., "downloading", "verifying")
        if (progress.status && progress.status !== 'success') {
          // Clean up status text for display
          const statusText = progress.status
            .replace('pulling ', '')
            .replace('downloading ', 'Downloading ')
            .replace('verifying ', 'Verifying ')
            .replace('writing ', 'Writing ')
          setDownloadStatus(statusText)
        }

        // Only update progress if it's higher (prevents jumps between phases)
        if (progress.progress !== null) {
          const newProgress = progress.progress * 100
          if (newProgress > maxProgress) {
            maxProgress = newProgress
            setDownloadProgress(newProgress)
          }
        }

        // Show 100% only on actual completion
        if (progress.is_complete) {
          setDownloadProgress(100)
          setDownloadStatus('Complete!')
        }
      },
      (error) => {
        setDownloadError(error)
        setDownloadingModel(null)
        setDownloadProgress(null)
        setDownloadStatus('')
      },
      () => {
        setDownloadingModel(null)
        setDownloadProgress(null)
        setDownloadStatus('')
        refetchModels()
        queryClient.invalidateQueries({ queryKey: ['ai', 'status'] })
      }
    )
  }

  // Handle selecting an example transaction
  const handleSelectExample = (example: AITestExample) => {
    setTestForm({
      counterparty_name: example.counterparty_name,
      purpose: example.purpose,
      amount: example.amount.toString(),
    })
    setTestResult(null)
    setTestError(null)
  }

  // Handle test classification
  const handleTestClassification = async () => {
    if (!testForm.counterparty_name || !testForm.amount) return

    setIsTesting(true)
    setTestError(null)
    setTestResult(null)

    try {
      const result = await testAIClassification({
        counterparty_name: testForm.counterparty_name,
        purpose: testForm.purpose,
        amount: parseFloat(testForm.amount),
      })
      setTestResult(result)
    } catch (err) {
      setTestError(err instanceof Error ? err.message : 'Test failed')
    } finally {
      setIsTesting(false)
    }
  }

  // Handle model selection
  const handleSelectModel = async (modelName: string) => {
    try {
      await updateSettingsMutation.mutateAsync({ model_name: modelName })
    } catch {
      // Error handled by mutation
    }
  }

  // Handle enable/disable toggle
  const handleToggleEnabled = async () => {
    if (!userSettings) return
    try {
      await updateSettingsMutation.mutateAsync({ enabled: !userSettings.enabled })
    } catch {
      // Error handled by mutation
    }
  }

  const isLoading = statusLoading || settingsLoading

  if (isLoading) {
    return (
      <Card className="animate-slide-up">
        <CardContent className="flex items-center justify-center py-12">
          <Spinner size="lg" />
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Status Card */}
      <Card className="animate-slide-up">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div
                className={cn(
                  'flex items-center justify-center h-10 w-10 rounded-lg',
                  aiStatus?.service_healthy ? 'bg-accent-success/10' : 'bg-accent-danger/10'
                )}
              >
                <Cpu
                  className={cn(
                    'h-5 w-5',
                    aiStatus?.service_healthy ? 'text-accent-success' : 'text-accent-danger'
                  )}
                />
              </div>
              <div>
                <CardTitle>AI Service Status</CardTitle>
                <CardDescription>
                  {aiStatus?.provider ? `Provider: ${aiStatus.provider}` : 'Checking service...'}
                </CardDescription>
              </div>
            </div>
            <Badge variant={aiStatus?.service_healthy ? 'success' : 'danger'}>
              {aiStatus?.service_healthy ? 'Online' : 'Offline'}
            </Badge>
          </div>
        </CardHeader>
        {statusError ? (
          <CardContent>
            <InlineAlert variant="danger">
              Could not connect to AI service. Ensure Ollama is running.
            </InlineAlert>
          </CardContent>
        ) : (
          aiStatus?.service_healthy && (
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-3 rounded-lg bg-bg-subtle">
                <div>
                  <p className="text-sm font-medium text-text-primary">AI Classification</p>
                  <p className="text-xs text-text-muted">Automatically classify transactions</p>
                </div>
                <button
                  onClick={handleToggleEnabled}
                  disabled={updateSettingsMutation.isPending}
                  className={cn(
                    'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                    userSettings?.enabled ? 'bg-accent-primary' : 'bg-bg-hover'
                  )}
                >
                  <span
                    className={cn(
                      'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                      userSettings?.enabled ? 'translate-x-6' : 'translate-x-1'
                    )}
                  />
                </button>
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div className="p-3 rounded-lg bg-bg-subtle">
                  <p className="text-text-muted">Current Model</p>
                  <p className="font-medium text-text-primary font-mono">
                    {userSettings?.model_name || aiStatus?.current_model || '-'}
                  </p>
                </div>
                <div className="p-3 rounded-lg bg-bg-subtle">
                  <p className="text-text-muted">Min Confidence</p>
                  <p className="font-medium text-text-primary">
                    {userSettings ? `${(userSettings.min_confidence * 100).toFixed(0)}%` : '-'}
                  </p>
                </div>
              </div>
            </CardContent>
          )
        )}
      </Card>

      {/* Models Card */}
      {aiStatus?.service_healthy && (
        <Card className="animate-slide-up">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Available Models</CardTitle>
                <CardDescription>Download and switch between AI models</CardDescription>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => refetchModels()}
                disabled={modelsLoading}
              >
                <RefreshCw className={cn('h-4 w-4', modelsLoading && 'animate-spin')} />
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {downloadError && (
              <InlineAlert variant="danger" className="mb-4">
                {downloadError}
              </InlineAlert>
            )}

            {modelsLoading ? (
              <div className="flex items-center justify-center py-8">
                <Spinner size="lg" />
              </div>
            ) : (
              <div className="space-y-3">
                {modelsData?.models.map((model) => (
                  <div
                    key={model.name}
                    className={cn(
                      'p-4 rounded-lg border transition-colors',
                      model.name === userSettings?.model_name
                        ? 'border-accent-primary/50 bg-accent-primary/5'
                        : 'border-border-subtle hover:border-border-default'
                    )}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <p className="font-medium text-text-primary">{model.display_name}</p>
                          {model.is_recommended && (
                            <Badge variant="default" className="text-xs">
                              Recommended
                            </Badge>
                          )}
                          {model.name === userSettings?.model_name && (
                            <Badge variant="success" className="text-xs">
                              Active
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm text-text-muted mt-1">{model.description}</p>
                        <p className="text-xs text-text-muted font-mono mt-1">
                          {model.size_display}
                        </p>
                      </div>

                      <div className="flex items-center gap-2 ml-4">
                        {model.status === 'available' ? (
                          <Button
                            variant={
                              model.name === userSettings?.model_name ? 'secondary' : 'primary'
                            }
                            size="sm"
                            onClick={() => handleSelectModel(model.name)}
                            disabled={
                              model.name === userSettings?.model_name ||
                              updateSettingsMutation.isPending
                            }
                          >
                            {model.name === userSettings?.model_name ? (
                              <>
                                <CheckCircle2 className="h-4 w-4 mr-1" />
                                Selected
                              </>
                            ) : (
                              'Use Model'
                            )}
                          </Button>
                        ) : model.status === 'downloading' || downloadingModel === model.name ? (
                          <div className="flex flex-col items-end gap-1 min-w-[140px]">
                            <div className="flex items-center gap-2 w-full">
                              <div className="flex-1 bg-bg-hover rounded-full h-2 overflow-hidden">
                                <div
                                  className="bg-accent-primary h-full transition-all duration-300"
                                  style={{ width: `${downloadProgress ?? 0}%` }}
                                />
                              </div>
                              <span className="text-xs text-text-muted w-10 text-right">
                                {downloadProgress?.toFixed(0) ?? 0}%
                              </span>
                            </div>
                            {downloadStatus && (
                              <span className="text-xs text-text-muted truncate max-w-[140px]">
                                {downloadStatus}
                              </span>
                            )}
                          </div>
                        ) : (
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => handleDownloadModel(model.name)}
                            disabled={downloadingModel !== null}
                          >
                            <Download className="h-4 w-4 mr-1" />
                            Download
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Test Classification Card */}
      {aiStatus?.service_healthy && userSettings?.enabled && (
        <Card className="animate-slide-up">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center h-10 w-10 rounded-lg bg-accent-primary/10">
                <TestTube2 className="h-5 w-5 text-accent-primary" />
              </div>
              <div>
                <CardTitle>Test Classification</CardTitle>
                <CardDescription>Try the AI with sample transaction data</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {testError && <InlineAlert variant="danger">{testError}</InlineAlert>}

            {/* Example Transactions */}
            {testExamples && testExamples.length > 0 && (
              <div>
                <p className="text-sm font-medium text-text-primary mb-2">Quick Examples</p>
                <div className="flex flex-wrap gap-2">
                  {testExamples.map((example) => (
                    <Tooltip key={example.id}>
                      <TooltipTrigger asChild>
                        <button
                          onClick={() => handleSelectExample(example)}
                          className={cn(
                            'px-3 py-1.5 text-xs rounded-full border transition-colors',
                            'hover:bg-accent-primary/10 hover:border-accent-primary hover:text-accent-primary',
                            testForm.counterparty_name === example.counterparty_name
                              ? 'bg-accent-primary/10 border-accent-primary text-accent-primary'
                              : 'bg-bg-subtle border-border-subtle text-text-secondary'
                          )}
                        >
                          {example.label}
                        </button>
                      </TooltipTrigger>
                      <TooltipContent>
                        {example.counterparty_name} • {formatSignedCurrency(example.amount, 'EUR')}
                      </TooltipContent>
                    </Tooltip>
                  ))}
                </div>
              </div>
            )}

            {/* Two-column layout: Input on left, Result on right */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Input Column */}
              <div className="space-y-3">
                <FormField label="Counterparty Name">
                  <Input
                    placeholder="e.g., REWE SAGT DANKE"
                    value={testForm.counterparty_name}
                    onChange={(e) => setTestForm({ ...testForm, counterparty_name: e.target.value })}
                  />
                </FormField>
                <FormField label="Amount (EUR)">
                  <Input
                    type="number"
                    step="0.01"
                    placeholder="e.g., -45.67"
                    value={testForm.amount}
                    onChange={(e) => setTestForm({ ...testForm, amount: e.target.value })}
                  />
                </FormField>
                <FormField label="Purpose / Description (optional)">
                  <Input
                    placeholder="e.g., KARTENZAHLUNG EC"
                    value={testForm.purpose}
                    onChange={(e) => setTestForm({ ...testForm, purpose: e.target.value })}
                  />
                </FormField>
                <Button
                  onClick={handleTestClassification}
                  disabled={!testForm.counterparty_name || !testForm.amount || isTesting}
                  className="w-full"
                >
                  {isTesting ? (
                    <Spinner size="sm" className="mr-2" />
                  ) : (
                    <TestTube2 className="h-4 w-4 mr-2" />
                  )}
                  {isTesting ? 'Classifying...' : 'Test Classification'}
                </Button>
              </div>

              {/* Result Column */}
              <div
                className={cn(
                  'rounded-lg border p-4 transition-all duration-200',
                  testResult
                    ? 'border-border-default bg-bg-subtle'
                    : 'border-dashed border-border-subtle bg-transparent'
                )}
              >
                {isTesting ? (
                  <div className="h-full flex items-center justify-center">
                    <div className="flex items-center gap-2 text-text-muted">
                      <Spinner size="sm" />
                      <span>Analyzing transaction...</span>
                    </div>
                  </div>
                ) : testResult ? (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-text-muted uppercase tracking-wide">Result</span>
                      <span className="text-xs text-text-muted">
                        {testResult.processing_time_ms.toFixed(0)}ms
                      </span>
                    </div>
                    {testResult.suggestion ? (
                      <>
                        <div className="flex items-center gap-3">
                          <span className="text-lg font-semibold text-text-primary">
                            {testResult.suggestion.account_name}
                          </span>
                          <Badge
                            variant={testResult.meets_confidence_threshold ? 'success' : 'warning'}
                          >
                            {(testResult.suggestion.confidence * 100).toFixed(0)}%
                          </Badge>
                        </div>
                        {testResult.suggestion.reasoning && (
                          <p className="text-sm text-text-secondary leading-relaxed">
                            {testResult.suggestion.reasoning}
                          </p>
                        )}
                      </>
                    ) : (
                      <p className="text-text-muted">
                        AI could not classify this transaction with sufficient confidence.
                      </p>
                    )}
                  </div>
                ) : (
                  <div className="h-full flex items-center justify-center text-center py-4">
                    <p className="text-sm text-text-muted">
                      Select an example or enter transaction details to test the AI classification
                    </p>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
