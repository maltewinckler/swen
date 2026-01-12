import { Building2, Sparkles, Wallet } from 'lucide-react'
import { Button, Card, CardContent } from '@/components/ui'

interface AccountsEmptyStateProps {
  onInitializeAccounts: () => void
  onConnectBank: () => void
}

export function AccountsEmptyState({ onInitializeAccounts, onConnectBank }: AccountsEmptyStateProps) {
  return (
    <Card>
      <CardContent className="py-12 text-center">
        <Wallet className="h-12 w-12 text-text-muted mx-auto mb-4" />
        <p className="text-text-secondary mb-2">No accounts found</p>
        <p className="text-sm text-text-muted mb-6">
          Initialize your chart of accounts to get started with personal finance tracking, or connect
          your bank to automatically import accounts.
        </p>
        <div className="flex flex-col sm:flex-row justify-center gap-3">
          <Button variant="primary" onClick={onInitializeAccounts}>
            <Sparkles className="h-4 w-4" />
            Initialize Accounts
          </Button>
          <Button variant="secondary" onClick={onConnectBank}>
            <Building2 className="h-4 w-4" />
            Connect Bank
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
