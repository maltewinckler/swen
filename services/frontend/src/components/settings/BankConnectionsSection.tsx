import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, Building2, CheckCircle2, ChevronRight, Plus, Trash2 } from 'lucide-react'
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  ConfirmDialog,
  Modal,
  ModalBody,
  ModalHeader,
  Spinner,
  StepIndicator,
  Tooltip,
  TooltipContent,
  TooltipTrigger,
  useToast,
} from '@/components/ui'
import { BankConnectionWizard } from '@/components/bank-connection'
import { useBankConnection } from '@/hooks'
import {
  deleteCredentials,
  getBankConnectionDetails,
  listAccounts,
  listCredentials,
} from '@/api'
import type { BankCredential } from '@/api/credentials'
import { cn, formatCurrency, formatDate } from '@/lib/utils'

// Bank connection steps for the step indicator
const BANK_CONNECTION_STEPS = [
  { id: 'find_bank', label: 'Bank' },
  { id: 'credentials', label: 'Login' },
  { id: 'tan_discovery', label: 'TAN' },
  { id: 'review_accounts', label: 'Review' },
  { id: 'initial_sync', label: 'Sync' },
]

interface BankConnectionsSectionProps {
  onGoToAccounts: () => void
}

export function BankConnectionsSection({ onGoToAccounts }: BankConnectionsSectionProps) {
  const queryClient = useQueryClient()
  const toast = useToast()

  // Bank connection modal state
  const [showAddBankModal, setShowAddBankModal] = useState(false)

  // Bank connection hook
  const bankConnection = useBankConnection({
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['credentials'] })
    },
  })

  // Bank connection details modal state
  const [selectedConnectionBlz, setSelectedConnectionBlz] = useState<string | null>(null)
  const [disconnectCandidate, setDisconnectCandidate] = useState<{ blz: string; label: string } | null>(null)

  // Queries
  const { data: credentialsData, isLoading: credentialsLoading } = useQuery({
    queryKey: ['credentials'],
    queryFn: listCredentials,
  })

  // Check if expense accounts exist (required before adding bank connections)
  const { data: accountsData } = useQuery({
    queryKey: ['accounts', 'expense-check'],
    queryFn: () => listAccounts({ account_type: 'EXPENSE', is_active: true, size: 1 }),
  })

  const hasExpenseAccounts = (accountsData?.items?.length ?? 0) > 0

  // Fetch bank connection details when a connection is selected
  const { data: connectionDetails, isLoading: connectionDetailsLoading } = useQuery({
    queryKey: ['connectionDetails', selectedConnectionBlz],
    queryFn: () => getBankConnectionDetails(selectedConnectionBlz!),
    enabled: !!selectedConnectionBlz,
  })

  const credentials = credentialsData?.credentials ?? []

  // Mutations
  const deleteCredentialsMutation = useMutation({
    mutationFn: deleteCredentials,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['credentials'] })
      queryClient.invalidateQueries({ queryKey: ['reconciliation'] })
    },
    onError: (err) => {
      toast.danger({
        title: 'Failed to disconnect bank',
        description: err instanceof Error ? err.message : 'Unknown error',
      })
    },
  })

  // Close modal and reset bank connection state
  const handleCloseAddBankModal = () => {
    setShowAddBankModal(false)
    bankConnection.reset()
  }

  // Check if modal can be closed (not during loading states)
  const canCloseModal =
    bankConnection.step !== 'connecting' &&
    bankConnection.step !== 'syncing' &&
    !bankConnection.isDiscoveringAccounts

  // Get modal description based on step
  const getModalDescription = () => {
    const { step, isDiscoveringAccounts, syncResult, connectionResult, syncError } = bankConnection
    if (step === 'find_bank') return 'Step 1: Find your bank'
    if (step === 'credentials') return 'Step 2: Enter your credentials'
    if (step === 'tan_discovery' && !isDiscoveringAccounts) return 'Step 3: Select your TAN method'
    if (step === 'tan_discovery' && isDiscoveringAccounts) return 'Discovering your accounts...'
    if (step === 'review_accounts') return 'Step 4: Review and name your accounts'
    if (step === 'connecting') return 'Importing your accounts...'
    if (step === 'initial_sync') return 'Step 5: Initial transaction sync'
    if (step === 'syncing') return 'Syncing transactions...'
    if (step === 'success') {
      return syncResult
        ? `Synced ${syncResult.total_imported} transaction${syncResult.total_imported !== 1 ? 's' : ''}`
        : `Imported ${connectionResult?.accounts_imported.length ?? 0} bank account(s)`
    }
    if (step === 'error') return syncError ? 'Sync failed' : 'Connection failed'
    return ''
  }

  // Check if step indicator should be shown
  const showStepIndicator = [
    'find_bank',
    'credentials',
    'tan_discovery',
    'review_accounts',
    'initial_sync',
  ].includes(bankConnection.step)

  return (
    <div className="space-y-6">
      {/* Warning: No expense accounts */}
      {!hasExpenseAccounts && (
        <Card className="animate-slide-up border-accent-warning/30 bg-accent-warning/5">
          <CardContent className="py-4">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-accent-warning flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm font-medium text-text-primary">Initialize expense accounts first</p>
                <p className="text-sm text-text-muted mt-1">
                  Before connecting your bank, you need to set up expense categories (like "Groceries",
                  "Rent", etc.) so transactions can be properly categorized.
                </p>
                <Button variant="secondary" size="sm" className="mt-3" onClick={onGoToAccounts}>
                  Go to Accounts
                  <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <Card className="animate-slide-up">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Bank Connections</CardTitle>
              <CardDescription>Manage your linked bank accounts</CardDescription>
            </div>
            {hasExpenseAccounts ? (
              <Button onClick={() => setShowAddBankModal(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Bank
              </Button>
            ) : (
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="inline-flex">
                    <Button onClick={() => setShowAddBankModal(true)} disabled aria-label="Add bank (disabled)">
                      <Plus className="h-4 w-4 mr-2" />
                      Add Bank
                    </Button>
                  </span>
                </TooltipTrigger>
                <TooltipContent>Initialize expense accounts first</TooltipContent>
              </Tooltip>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {credentialsLoading ? (
            <div className="flex items-center justify-center py-8">
              <Spinner size="lg" />
            </div>
          ) : credentials.length === 0 ? (
            <div className="text-center py-8">
              <Building2 className="h-12 w-12 text-text-muted mx-auto mb-4" />
              <p className="text-text-secondary mb-2">No bank accounts connected yet</p>
              {hasExpenseAccounts ? (
                <>
                  <p className="text-sm text-text-muted mb-4">
                    Connect your bank to automatically sync transactions
                  </p>
                  <Button onClick={() => setShowAddBankModal(true)}>
                    <Plus className="h-4 w-4 mr-2" />
                    Connect Bank Account
                  </Button>
                </>
              ) : (
                <p className="text-sm text-text-muted">
                  Initialize your expense accounts first, then come back to connect your bank.
                </p>
              )}
            </div>
          ) : (
            <div className="divide-y divide-border-subtle">
              {credentials.map((cred: BankCredential) => (
                <div
                  key={cred.credential_id}
                  className="py-4 first:pt-0 last:pb-0 cursor-pointer hover:bg-bg-subtle/50 -mx-4 px-4 transition-colors rounded-lg"
                  onClick={() => setSelectedConnectionBlz(cred.blz)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex items-center justify-center h-10 w-10 rounded-lg bg-accent-primary/10">
                        <Building2 className="h-5 w-5 text-accent-primary" />
                      </div>
                      <div>
                        <p className="font-medium text-text-primary">{cred.label}</p>
                        <p className="text-xs text-text-muted font-mono">BLZ: {cred.blz}</p>
                      </div>
                    </div>
                    <ChevronRight className="h-4 w-4 text-text-muted" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Add Bank Connection Modal */}
      <Modal
        isOpen={showAddBankModal}
        onClose={handleCloseAddBankModal}
        size="lg"
        closeOnBackdropClick={canCloseModal}
      >
        <ModalHeader onClose={canCloseModal ? handleCloseAddBankModal : undefined} description={getModalDescription()}>
          {bankConnection.step === 'success' ? 'Setup Complete!' : 'Add Bank Connection'}
        </ModalHeader>
        <ModalBody>
          {showStepIndicator && (
            <StepIndicator steps={BANK_CONNECTION_STEPS} currentStepId={bankConnection.step} className="mb-6" />
          )}
          <BankConnectionWizard
            connection={bankConnection}
            onDone={handleCloseAddBankModal}
            onAddAnother={() => bankConnection.reset()}
            showAddAnother={false}
            labels={{ doneButton: 'Done' }}
          />
        </ModalBody>
      </Modal>

      {/* Bank Connection Details Modal */}
      <Modal isOpen={!!selectedConnectionBlz} onClose={() => setSelectedConnectionBlz(null)} size="2xl">
        <ModalHeader onClose={() => setSelectedConnectionBlz(null)}>
          <div className="flex items-center gap-2">
            <Building2 className="h-5 w-5 text-accent-primary" />
            {connectionDetails?.bank_name || `Bank ${selectedConnectionBlz}`}
          </div>
        </ModalHeader>
        <ModalBody>
          <p className="text-sm text-text-muted font-mono mb-4">BLZ: {selectedConnectionBlz}</p>

          {connectionDetailsLoading ? (
            <div className="flex items-center justify-center py-8">
              <Spinner size="lg" />
            </div>
          ) : connectionDetails ? (
            <div className="space-y-4">
              {/* Summary */}
              <div className="flex items-center gap-4 p-3 rounded-lg bg-bg-subtle">
                <div className="flex-1">
                  <p className="text-sm text-text-muted">Accounts</p>
                  <p className="text-lg font-semibold text-text-primary">{connectionDetails.total_accounts}</p>
                </div>
                <div className="flex-1">
                  <p className="text-sm text-text-muted">Reconciled</p>
                  <p className="text-lg font-semibold text-accent-success">{connectionDetails.reconciled_count}</p>
                </div>
                <div className="flex-1">
                  <p className="text-sm text-text-muted">Discrepancies</p>
                  <p
                    className={cn(
                      'text-lg font-semibold',
                      connectionDetails.discrepancy_count > 0 ? 'text-accent-warning' : 'text-text-muted'
                    )}
                  >
                    {connectionDetails.discrepancy_count}
                  </p>
                </div>
              </div>

              {/* Disconnect button */}
              <div className="flex justify-end">
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-accent-danger hover:text-accent-danger hover:bg-accent-danger/10"
                  onClick={() => {
                    if (!selectedConnectionBlz) return
                    const credLabel =
                      credentials.find((c) => c.blz === selectedConnectionBlz)?.label || selectedConnectionBlz
                    setDisconnectCandidate({ blz: selectedConnectionBlz, label: credLabel })
                  }}
                  disabled={deleteCredentialsMutation.isPending}
                >
                  <Trash2 className="h-4 w-4 mr-1" />
                  Disconnect
                </Button>
              </div>

              {/* Account List */}
              {connectionDetails.accounts.length === 0 ? (
                <div className="text-center py-8">
                  <AlertCircle className="h-12 w-12 text-text-muted mx-auto mb-4" />
                  <p className="text-text-secondary">No accounts found. Try syncing your bank connection first.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {connectionDetails.accounts.map((acc) => (
                    <div
                      key={acc.iban}
                      className={cn(
                        'p-4 rounded-lg border',
                        acc.is_reconciled ? 'border-accent-success/30 bg-accent-success/5' : 'border-accent-warning/30 bg-accent-warning/5'
                      )}
                    >
                      <div className="flex items-center justify-between mb-3">
                        <div>
                          <p className="font-medium text-text-primary">{acc.account_name}</p>
                          <p className="text-xs text-text-muted font-mono">{acc.iban}</p>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant="default">{acc.account_type}</Badge>
                          <Badge variant={acc.is_reconciled ? 'success' : 'warning'}>
                            {acc.is_reconciled ? (
                              <>
                                <CheckCircle2 className="h-3 w-3 mr-1" /> Reconciled
                              </>
                            ) : (
                              <>
                                <AlertCircle className="h-3 w-3 mr-1" /> Discrepancy
                              </>
                            )}
                          </Badge>
                        </div>
                      </div>
                      <div className="grid grid-cols-3 gap-4 text-sm">
                        <div>
                          <p className="text-text-muted mb-1">Bank Balance</p>
                          <p className="font-mono text-text-primary font-medium">
                            {formatCurrency(acc.bank_balance, acc.currency)}
                          </p>
                          {acc.bank_balance_date && (
                            <p className="text-xs text-text-muted mt-1">
                              as of {formatDate(acc.bank_balance_date, { year: 'numeric', month: '2-digit', day: '2-digit' })}
                            </p>
                          )}
                        </div>
                        <div>
                          <p className="text-text-muted mb-1">Bookkeeping</p>
                          <p className="font-mono text-text-primary font-medium">
                            {formatCurrency(acc.bookkeeping_balance, acc.currency)}
                          </p>
                        </div>
                        <div>
                          <p className="text-text-muted mb-1">Difference</p>
                          <p
                            className={cn(
                              'font-mono font-medium',
                              acc.is_reconciled ? 'text-accent-success' : 'text-accent-warning'
                            )}
                          >
                            {formatCurrency(acc.discrepancy, acc.currency)}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8">
              <AlertCircle className="h-12 w-12 text-text-muted mx-auto mb-4" />
              <p className="text-text-secondary">No account data available for this connection.</p>
            </div>
          )}
        </ModalBody>
      </Modal>

      {/* Confirm disconnect */}
      <ConfirmDialog
        isOpen={!!disconnectCandidate}
        title="Disconnect bank?"
        description={
          disconnectCandidate ? (
            <span>
              Disconnect <strong>{disconnectCandidate.label}</strong>? This removes stored credentials but keeps your
              transaction history.
            </span>
          ) : null
        }
        confirmLabel="Disconnect"
        cancelLabel="Cancel"
        variant="danger"
        isLoading={deleteCredentialsMutation.isPending}
        onCancel={() => setDisconnectCandidate(null)}
        onConfirm={() => {
          if (!disconnectCandidate) return
          deleteCredentialsMutation.mutate(disconnectCandidate.blz, {
            onSuccess: () => {
              toast.success({ title: 'Disconnected', description: 'Bank credentials removed.' })
              setDisconnectCandidate(null)
              setSelectedConnectionBlz(null)
            },
          })
        }}
      />
    </div>
  )
}
