import { Building2 } from 'lucide-react'
import { Button, Card, CardContent } from '@/components/ui'

interface AccountsNoBankBannerProps {
  onGoToSettings: () => void
}

export function AccountsNoBankBanner({ onGoToSettings }: AccountsNoBankBannerProps) {
  return (
    <Card className="animate-slide-up border-accent-info/30 bg-accent-info/5">
      <CardContent className="py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Building2 className="h-5 w-5 text-accent-info" />
            <div>
              <p className="text-sm font-medium text-text-primary">No bank connections yet</p>
              <p className="text-xs text-text-muted">
                Connect your bank in Settings to sync transactions automatically
              </p>
            </div>
          </div>
          <Button variant="secondary" size="sm" onClick={onGoToSettings}>
            Go to Settings
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
