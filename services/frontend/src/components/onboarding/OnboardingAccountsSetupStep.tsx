import { ArrowLeft, Sparkles } from 'lucide-react'
import { Button, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui'

interface OnboardingAccountsSetupStepProps {
  isLoading: boolean
  onBack: () => void
  onCreateAccounts: () => void
}

export function OnboardingAccountsSetupStep({
  isLoading,
  onBack,
  onCreateAccounts,
}: OnboardingAccountsSetupStepProps) {
  return (
    <>
      <CardHeader>
        <CardTitle>Set Up Your Accounts</CardTitle>
        <CardDescription>
          We'll create simple expense and income accounts for everyday personal finance. You can customize these later.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="p-4 rounded-lg border border-border-default bg-bg-subtle">
          <p className="font-medium text-text-primary mb-2">What we'll create (~15 accounts):</p>
          <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-sm text-text-muted">
            <span>• Gehalt & Lohn</span>
            <span>• Miete</span>
            <span>• Lebensmittel</span>
            <span>• Restaurants & Bars</span>
            <span>• Transport</span>
            <span>• Sport & Fitness</span>
            <span>• Abonnements</span>
            <span>• Sonstiges</span>
          </div>
        </div>

        <div className="flex gap-3 pt-4">
          <Button variant="secondary" onClick={onBack}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          <Button className="flex-1" onClick={onCreateAccounts} isLoading={isLoading}>
            <Sparkles className="h-4 w-4 mr-2" />
            Create Accounts
          </Button>
        </div>
      </CardContent>
    </>
  )
}
