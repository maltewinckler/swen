import { createFileRoute, useNavigate, useSearch } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Spinner } from '@/components/ui'
import { AccountStatsModal } from '@/components/accounts'
import { AccountsEmptyState } from '@/components/accounts/AccountsEmptyState'
import { AccountsGroupList } from '@/components/accounts/AccountsGroupList'
import { AccountsNoBankBanner } from '@/components/accounts/AccountsNoBankBanner'
import { AccountsPageHeader } from '@/components/accounts/AccountsPageHeader'
import { ChartOfAccountsInitModal } from '@/components/accounts/ChartOfAccountsInitModal'
import { CreateAccountModal } from '@/components/accounts/CreateAccountModal'
import { listAccounts, listCredentials } from '@/api'

type AccountsSearch = {
  accountId?: string
}

export const Route = createFileRoute('/_app/accounts')({
  component: AccountsPage,
  validateSearch: (search: Record<string, unknown>): AccountsSearch => {
    return {
      accountId: typeof search.accountId === 'string' ? search.accountId : undefined,
    }
  },
})


function AccountsPage() {
  const navigate = useNavigate()
  const { accountId: urlAccountId } = useSearch({ from: '/_app/accounts' })

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showChartTemplateModal, setShowChartTemplateModal] = useState(false)
  const [showInactive, setShowInactive] = useState(false)

  // Queries
  const { data, isLoading, error } = useQuery({
    queryKey: ['accounts', showInactive],
    queryFn: () => listAccounts({ active_only: !showInactive, size: 100 }),
  })

  const { data: credentialsData } = useQuery({
    queryKey: ['credentials'],
    queryFn: listCredentials,
  })
  const accounts = data?.items ?? []
  const credentials = credentialsData?.credentials ?? []

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Spinner size="lg" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6 text-center text-accent-danger">
        Failed to load accounts
      </div>
    )
  }

  return (
    <div className="space-y-8 animate-fade-in">
      <AccountsPageHeader
        accountsCount={accounts.length}
        showInactive={showInactive}
        onOpenInitAccounts={() => setShowChartTemplateModal(true)}
        onToggleShowInactive={() => setShowInactive(!showInactive)}
        onAddAccount={() => setShowCreateModal(true)}
      />

      {/* Bank connection info banner */}
      {credentials.length === 0 && accounts.length > 0 && (
        <AccountsNoBankBanner onGoToSettings={() => navigate({ to: '/settings', search: { section: null } })} />
      )}

      {accounts.length > 0 && (
        <AccountsGroupList
          accounts={accounts}
          onOpenAccount={(accountId) => navigate({ to: '/accounts', search: { accountId } })}
        />
      )}

      {accounts.length === 0 && (
        <AccountsEmptyState
          onInitializeAccounts={() => setShowChartTemplateModal(true)}
          onConnectBank={() => navigate({ to: '/settings', search: { section: null } })}
        />
      )}

      {/* Chart Template Selection Modal */}
      <ChartOfAccountsInitModal
        key={showChartTemplateModal ? 'open' : 'closed'}
        isOpen={showChartTemplateModal}
        onClose={() => setShowChartTemplateModal(false)}
      />

      <CreateAccountModal
        key={showCreateModal ? 'open' : 'closed'}
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
      />

      {/* Account Stats Modal */}
      <AccountStatsModal
        accountId={urlAccountId ?? null}
        onClose={() => navigate({ to: '/accounts', search: {}, replace: true })}
      />
    </div>
  )
}
