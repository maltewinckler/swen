import { ArrowRight, Building2, Plus, Sparkles, Wallet } from 'lucide-react'
import { Button, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui'

interface OnboardingWelcomeStepProps {
  onNext: () => void
}

export function OnboardingWelcomeStep({ onNext }: OnboardingWelcomeStepProps) {
  return (
    <>
      <CardHeader className="text-center pb-2">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-accent-primary to-accent-info">
          <Sparkles className="h-8 w-8 text-white" />
        </div>
        <CardTitle className="text-2xl">Welcome to SWEN!</CardTitle>
        <CardDescription className="text-base mt-2">
          Let's set up your personal finance tracker in a few easy steps.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-4 pt-4">
          <div className="flex items-start gap-4 p-4 rounded-lg bg-bg-subtle">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-accent-primary/10">
              <Wallet className="h-5 w-5 text-accent-primary" />
            </div>
            <div>
              <p className="font-medium text-text-primary">1. Set Up Your Chart of Accounts</p>
              <p className="text-sm text-text-muted">
                Create income and expense accounts for organizing your transactions.
              </p>
            </div>
          </div>
          <div className="flex items-start gap-4 p-4 rounded-lg bg-bg-subtle">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-accent-info/10">
              <Building2 className="h-5 w-5 text-accent-info" />
            </div>
            <div>
              <p className="font-medium text-text-primary">2. Connect Your Banks</p>
              <p className="text-sm text-text-muted">
                Link your bank accounts to automatically import transactions.
              </p>
            </div>
          </div>
          <div className="flex items-start gap-4 p-4 rounded-lg bg-bg-subtle">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-accent-success/10">
              <Plus className="h-5 w-5 text-accent-success" />
            </div>
            <div>
              <p className="font-medium text-text-primary">3. Add Manual Accounts</p>
              <p className="text-sm text-text-muted">Add accounts at banks without API access (optional).</p>
            </div>
          </div>
        </div>
        <Button className="w-full" size="lg" onClick={onNext}>
          Get Started
          <ArrowRight className="h-4 w-4 ml-2" />
        </Button>
      </CardContent>
    </>
  )
}
