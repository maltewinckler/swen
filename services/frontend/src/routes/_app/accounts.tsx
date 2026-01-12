import { createFileRoute, useNavigate, useSearch } from '@tanstack/react-router'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Spinner } from '@/components/ui'
import { AccountStatsModal } from '@/components/accounts'
import { AccountsEmptyState } from '@/components/accounts/AccountsEmptyState'
import { AccountsGroupList } from '@/components/accounts/AccountsGroupList'
import { AccountsNoBankBanner } from '@/components/accounts/AccountsNoBankBanner'
import { AccountsPageHeader } from '@/components/accounts/AccountsPageHeader'
import { ChartOfAccountsInitModal } from '@/components/accounts/ChartOfAccountsInitModal'
import { CreateAccountModal } from '@/components/accounts/CreateAccountModal'
import { SyncProgressModal } from '@/components/SyncProgressModal'
import { useSyncProgress } from '@/hooks'
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
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { accountId: urlAccountId } = useSearch({ from: '/_app/accounts' })

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showChartTemplateModal, setShowChartTemplateModal] = useState(false)
  const [showInactive, setShowInactive] = useState(false)

  // Sync state (using shared hook)
  const {
    isOpen: showSyncModal,
    step: syncStep,
    progress: syncProgress,
    result: syncResult,
    error: syncError,
    firstSyncDays,
    setFirstSyncDays,
    checkAndSync,
    confirmFirstSync,
    reset: closeSyncModal,
  } = useSyncProgress({
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['analytics'] })
    },
  })

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

  const handleSync = (blz?: string) => {
    checkAndSync(blz)
  }

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
        hasCredentials={credentials.length > 0}
        showInactive={showInactive}
        isSyncing={syncStep === 'syncing' || syncStep === 'checking'}
        onOpenInitAccounts={() => setShowChartTemplateModal(true)}
        onToggleShowInactive={() => setShowInactive(!showInactive)}
        onSyncAllBanks={() => handleSync()}
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
        onRequestManualSetup={() => setShowCreateModal(true)}
      />

      <CreateAccountModal
        key={showCreateModal ? 'open' : 'closed'}
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
      />

      {/* Sync Modal - using shared SyncProgressModal component */}
      <SyncProgressModal
        open={showSyncModal}
        onClose={closeSyncModal}
        step={syncStep}
        progress={syncProgress}
        result={syncResult}
        error={syncError}
        firstSyncDays={firstSyncDays}
        onSetFirstSyncDays={setFirstSyncDays}
        onConfirmFirstSync={confirmFirstSync}
      />


      {/* Account Stats Modal */}
      <AccountStatsModal
        accountId={urlAccountId ?? null}
        onClose={() => navigate({ to: '/accounts', search: {}, replace: true })}
      />
    </div>
  )
}
