import { ArrowRight, Check, CheckCircle2, SkipForward } from 'lucide-react'
import { Button, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui'
import type { AIModel } from '@/api/ai'

interface OnboardingCompleteStepProps {
  selectedAIModel: string | null
  aiSkipped: boolean
  aiModels: AIModel[] | undefined
  credentialsCount: number
  manualAccountsCount: number
  onFinish: () => void
}

export function OnboardingCompleteStep({
  selectedAIModel,
  aiSkipped,
  aiModels,
  credentialsCount,
  manualAccountsCount,
  onFinish,
}: OnboardingCompleteStepProps) {
  const selectedModelLabel =
    selectedAIModel ? aiModels?.find((m) => m.name === selectedAIModel)?.display_name || selectedAIModel : null

  return (
    <>
      <CardHeader className="text-center pb-2">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-accent-success">
          <Check className="h-8 w-8 text-white" />
        </div>
        <CardTitle className="text-2xl">You're All Set!</CardTitle>
        <CardDescription className="text-base mt-2">Your SWEN account is ready to use.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-3 pt-4">
          {selectedModelLabel && !aiSkipped ? (
            <div className="flex items-center gap-3 p-3 rounded-lg bg-accent-success/5 border border-accent-success/20">
              <CheckCircle2 className="h-5 w-5 text-accent-success flex-shrink-0" />
              <p className="text-sm text-text-primary">AI classification enabled ({selectedModelLabel})</p>
            </div>
          ) : (
            <div className="flex items-center gap-3 p-3 rounded-lg bg-bg-subtle border border-border-subtle">
              <SkipForward className="h-5 w-5 text-text-muted flex-shrink-0" />
              <p className="text-sm text-text-muted">AI classification skipped (can enable in Settings)</p>
            </div>
          )}

          <div className="flex items-center gap-3 p-3 rounded-lg bg-accent-success/5 border border-accent-success/20">
            <CheckCircle2 className="h-5 w-5 text-accent-success flex-shrink-0" />
            <p className="text-sm text-text-primary">Chart of accounts initialized</p>
          </div>

          {credentialsCount > 0 && (
            <div className="flex items-center gap-3 p-3 rounded-lg bg-accent-success/5 border border-accent-success/20">
              <CheckCircle2 className="h-5 w-5 text-accent-success flex-shrink-0" />
              <p className="text-sm text-text-primary">
                {credentialsCount} bank{credentialsCount > 1 ? 's' : ''} connected
              </p>
            </div>
          )}

          {manualAccountsCount > 0 && (
            <div className="flex items-center gap-3 p-3 rounded-lg bg-accent-success/5 border border-accent-success/20">
              <CheckCircle2 className="h-5 w-5 text-accent-success flex-shrink-0" />
              <p className="text-sm text-text-primary">
                {manualAccountsCount} manual account{manualAccountsCount > 1 ? 's' : ''} added
              </p>
            </div>
          )}
        </div>

        <Button className="w-full" size="lg" onClick={onFinish}>
          Go to Dashboard
          <ArrowRight className="h-4 w-4 ml-2" />
        </Button>
      </CardContent>
    </>
  )
}
