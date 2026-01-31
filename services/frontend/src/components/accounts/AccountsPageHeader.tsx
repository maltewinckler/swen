import { Plus, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui'

interface AccountsPageHeaderProps {
  accountsCount: number
  showInactive: boolean
  onOpenInitAccounts: () => void
  onToggleShowInactive: () => void
  onAddAccount: () => void
}

export function AccountsPageHeader({
  accountsCount,
  showInactive,
  onOpenInitAccounts,
  onToggleShowInactive,
  onAddAccount,
}: AccountsPageHeaderProps) {
  return (
    <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-display text-text-primary">Accounts</h1>
        <p className="text-text-secondary mt-1">Manage your chart of accounts</p>
      </div>
      <div className="flex flex-wrap gap-2">
        {accountsCount === 0 && (
          <Button variant="primary" onClick={onOpenInitAccounts} className="whitespace-nowrap">
            <Sparkles className="h-4 w-4" />
            Initialize Accounts
          </Button>
        )}
        <Button
          variant={showInactive ? 'primary' : 'ghost'}
          onClick={onToggleShowInactive}
          className="whitespace-nowrap"
        >
          {showInactive ? 'Showing Inactive' : 'Show Inactive'}
        </Button>
        <Button variant="secondary" onClick={onAddAccount} className="whitespace-nowrap">
          <Plus className="h-4 w-4" />
          Add Account
        </Button>
      </div>
    </div>
  )
}
