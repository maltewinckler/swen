import { ArrowLeft, ArrowRight, Brain, Check, Download, SkipForward } from 'lucide-react'
import {
  Badge,
  Button,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  InlineAlert,
  Spinner,
} from '@/components/ui'
import { cn } from '@/lib/utils'
import type { AIModel } from '@/api/ai'

interface OnboardingAIModelStepProps {
  aiStatusLoading: boolean
  aiServiceHealthy: boolean
  aiModelsLoading: boolean
  aiModels: AIModel[] | undefined
  hasInstalledModel: boolean

  selectedAIModel: string | null
  downloadingModel: string | null
  downloadProgress: number
  downloadStatus: string
  downloadError: string | null

  onBack: () => void
  onSkipAISetup: () => void
  onSelectModel: (modelName: string) => void
  onDownloadModel: (modelName: string) => void
  onContinue: () => void
}

export function OnboardingAIModelStep({
  aiStatusLoading,
  aiServiceHealthy,
  aiModelsLoading,
  aiModels,
  hasInstalledModel,
  selectedAIModel,
  downloadingModel,
  downloadProgress,
  downloadStatus,
  downloadError,
  onBack,
  onSkipAISetup,
  onSelectModel,
  onDownloadModel,
  onContinue,
}: OnboardingAIModelStepProps) {
  return (
    <>
      <CardHeader>
        <div className="flex items-center gap-3 mb-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent-primary/10">
            <Brain className="h-5 w-5 text-accent-primary" />
          </div>
          <div>
            <CardTitle>AI Classification</CardTitle>
            <CardDescription>
              Choose an AI model to automatically classify your transactions
            </CardDescription>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {aiStatusLoading ? (
          <div className="flex items-center justify-center py-8">
            <Spinner size="lg" />
          </div>
        ) : !aiServiceHealthy ? (
          <div className="space-y-4">
            <InlineAlert variant="warning">
              AI service (Ollama) is not running. You can skip this step and set up AI later in Settings.
            </InlineAlert>
            <div className="flex gap-3">
              <Button variant="secondary" onClick={onBack}>
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back
              </Button>
              <Button className="flex-1" onClick={onSkipAISetup}>
                <SkipForward className="h-4 w-4 mr-2" />
                Skip AI Setup
              </Button>
            </div>
          </div>
        ) : aiModelsLoading ? (
          <div className="flex items-center justify-center py-8">
            <Spinner size="lg" />
          </div>
        ) : (
          <div className="space-y-4">
            {downloadError && <InlineAlert variant="danger">{downloadError}</InlineAlert>}

            <p className="text-sm text-text-muted">
              {hasInstalledModel
                ? 'Click a model to select it for classification.'
                : 'Select a model to download. Larger models are more accurate but slower.'}
            </p>

            <div className="space-y-3">
              {aiModels?.map((model) => {
                const isSelected = selectedAIModel === model.name
                const isAvailable = model.status === 'available'

                return (
                  <div
                    key={model.name}
                    onClick={() => isAvailable && onSelectModel(model.name)}
                    className={cn(
                      'p-4 rounded-lg border transition-colors',
                      isAvailable && 'cursor-pointer',
                      isSelected
                        ? 'border-accent-primary bg-accent-primary/10 ring-2 ring-accent-primary'
                        : 'border-border-subtle hover:border-border-default'
                    )}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <p className="font-medium text-text-primary">{model.display_name}</p>
                          {model.is_recommended && <Badge variant="default" className="text-xs">Recommended</Badge>}
                          {isAvailable && <Badge variant="success" className="text-xs">Ready</Badge>}
                        </div>
                        <p className="text-sm text-text-muted mt-1">{model.description}</p>
                        <p className="text-xs text-text-muted font-mono mt-1">{model.size_display}</p>
                      </div>

                      <div className="ml-4">
                        {isAvailable ? (
                          <div
                            className={cn(
                              'h-6 w-6 rounded-full border-2 flex items-center justify-center transition-colors',
                              isSelected ? 'border-accent-primary bg-accent-primary' : 'border-border-default bg-transparent'
                            )}
                          >
                            {isSelected && <Check className="h-4 w-4 text-white" />}
                          </div>
                        ) : downloadingModel === model.name ? (
                          <div className="w-24 space-y-1">
                            <div className="bg-bg-hover rounded-full h-2 overflow-hidden">
                              <div
                                className="bg-accent-primary h-full transition-all duration-300"
                                style={{ width: `${downloadProgress}%` }}
                              />
                            </div>
                            <p className="text-[10px] text-text-muted text-center truncate">
                              {downloadStatus || 'Downloading...'}
                            </p>
                            <p className="text-xs text-text-muted text-center">{downloadProgress.toFixed(0)}%</p>
                          </div>
                        ) : (
                          <Button
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation()
                              onDownloadModel(model.name)
                            }}
                            disabled={downloadingModel !== null}
                          >
                            <Download className="h-4 w-4 mr-1" />
                            Download
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>

            <div className="flex gap-3 pt-4">
              <Button variant="secondary" onClick={onBack}>
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back
              </Button>
              {selectedAIModel ? (
                <Button className="flex-1" onClick={onContinue}>
                  Continue with {aiModels?.find((m) => m.name === selectedAIModel)?.display_name || selectedAIModel}
                  <ArrowRight className="h-4 w-4 ml-2" />
                </Button>
              ) : (
                <Button
                  variant="ghost"
                  className="flex-1"
                  onClick={onSkipAISetup}
                  disabled={downloadingModel !== null}
                >
                  <SkipForward className="h-4 w-4 mr-2" />
                  Skip for Now
                </Button>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </>
  )
}
