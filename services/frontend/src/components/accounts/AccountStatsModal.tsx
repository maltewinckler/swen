/**
 * Account Stats Modal
 *
 * Displays detailed statistics for a single account.
 * Can be used from anywhere in the app (dashboard, accounts page, etc.)
 */

import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Wallet, Pencil } from 'lucide-react'
import {
  Modal,
  ModalHeader,
  ModalBody,
  Spinner,
  Button,
} from '@/components/ui'
import { getAccountStats, getAccount } from '@/api'
import type { Account, AccountStats } from '@/types/api'
import { cn, formatCurrency, formatDate, formatIban } from '@/lib/utils'
import {
  normalizeAccountType,
  getAccountIcon,
  getAccountColor,
  accountTypeLabels,
} from './account-utils'
import { AccountEditModal } from './AccountEditModal'

interface AccountStatsModalProps {
  /** Account ID to display stats for */
  accountId: string | null
  /** Optional account name to show while loading */
  accountName?: string
  /** Called when modal is closed */
  onClose: () => void
}

export function AccountStatsModal({ accountId, accountName, onClose }: AccountStatsModalProps) {
  const [statsDays, setStatsDays] = useState<number | undefined>(undefined)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)

  // Reset state when modal opens/closes
  useEffect(() => {
    if (!accountId) {
      setStatsDays(undefined)
      setIsEditModalOpen(false)
    }
  }, [accountId])

  // Fetch full account data
  const { data: account, isLoading: isLoadingAccount } = useQuery({
    queryKey: ['account', accountId],
    queryFn: () => getAccount(accountId!),
    enabled: !!accountId,
  })

  // Fetch parent account if this account has a parent
  const { data: parentAccount } = useQuery({
    queryKey: ['account', account?.parent_id],
    queryFn: () => getAccount(account!.parent_id!),
    enabled: !!account?.parent_id,
  })

  // Account stats query
  const { data: accountStats, isLoading: isLoadingStats } = useQuery({
    queryKey: ['accountStats', accountId, statsDays],
    queryFn: () => getAccountStats(accountId!, { days: statsDays }),
    enabled: !!accountId,
  })

  const handleClose = () => {
    setStatsDays(undefined)
    onClose()
  }

  const isLoading = isLoadingAccount || isLoadingStats

  return (
    <>
    <Modal isOpen={!!accountId} onClose={handleClose} size="xl">
      <ModalHeader onClose={handleClose}>
        {account ? (
          <div className="flex items-center gap-3">
            <div className={cn(
              'flex items-center justify-center h-10 w-10 rounded-lg',
              getAccountColor(normalizeAccountType(account.account_type))
            )}>
              {getAccountIcon(normalizeAccountType(account.account_type))}
            </div>
            <div>
              <span className="text-lg">{account.name}</span>
              <p className="text-sm text-text-muted font-normal">
                {account.account_number} · {accountTypeLabels[normalizeAccountType(account.account_type)]}
                {parentAccount && (
                  <span> · Parent: {parentAccount.account_number} {parentAccount.name}</span>
                )}
              </p>
            </div>
          </div>
        ) : accountName ? (
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center h-10 w-10 rounded-lg bg-bg-elevated">
              <Wallet className="h-5 w-5 text-text-muted" />
            </div>
            <div>
              <span className="text-lg">{accountName}</span>
              <p className="text-sm text-text-muted font-normal">Loading...</p>
            </div>
          </div>
        ) : null}
      </ModalHeader>
      <ModalBody>
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Spinner size="lg" />
          </div>
        ) : account && accountStats ? (
          <AccountStatsContent
            account={account}
            accountStats={accountStats}
            statsDays={statsDays}
            setStatsDays={setStatsDays}
            onEditClick={() => setIsEditModalOpen(true)}
          />
        ) : (
          <div className="flex items-center justify-center py-8 text-text-muted">
            No statistics available
          </div>
        )}
      </ModalBody>
    </Modal>

    {/* Edit Modal */}
    {account && (
      <AccountEditModal
        account={account}
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
      />
    )}
    </>
  )
}

interface AccountStatsContentProps {
  account: Account
  accountStats: AccountStats
  statsDays: number | undefined
  setStatsDays: (days: number | undefined) => void
  onEditClick: () => void
}

function AccountStatsContent({
  account,
  accountStats,
  statsDays,
  setStatsDays,
  onEditClick,
}: AccountStatsContentProps) {
  const accountType = normalizeAccountType(accountStats.account_type)

  return (
    <div className="space-y-6">
      {/* IBAN section */}
      {account.iban && (
        <div className="bg-bg-elevated rounded-lg p-4">
          <div className="flex items-center justify-between gap-3">
            <span className="text-sm font-medium text-text-primary whitespace-nowrap">
              IBAN
            </span>
            <span
              className="text-sm text-text-secondary font-mono tabular-nums whitespace-nowrap overflow-hidden text-ellipsis"
              title={account.iban}
            >
              {formatIban(account.iban)}
            </span>
          </div>
        </div>
      )}

      {/* Description section (read-only) */}
      {account.description && (
        <div className="bg-bg-elevated rounded-lg p-4">
          <p className="text-sm font-medium text-text-primary mb-1">Description</p>
          <p className="text-sm text-text-secondary">{account.description}</p>
        </div>
      )}

      {/* Period filter */}
      <div className="flex gap-2">
        <Button
          variant={statsDays === undefined ? 'primary' : 'secondary'}
          size="sm"
          onClick={() => setStatsDays(undefined)}
        >
          All Time
        </Button>
        <Button
          variant={statsDays === 30 ? 'primary' : 'secondary'}
          size="sm"
          onClick={() => setStatsDays(30)}
        >
          30 Days
        </Button>
        <Button
          variant={statsDays === 90 ? 'primary' : 'secondary'}
          size="sm"
          onClick={() => setStatsDays(90)}
        >
          90 Days
        </Button>
        <Button
          variant={statsDays === 365 ? 'primary' : 'secondary'}
          size="sm"
          onClick={() => setStatsDays(365)}
        >
          1 Year
        </Button>
      </div>

      {/* Balance */}
      <div className="bg-bg-elevated rounded-lg p-4">
        <p className="text-sm text-text-muted mb-1">
          {accountType === 'LIABILITY' ? 'Amount Owed' : 'Current Balance'}
        </p>
        <p className={cn(
          "text-2xl font-bold font-mono",
          // For LIABILITY: positive balance = you owe money (warning/danger)
          // For ASSET: positive balance = you have money (success)
          // For EXPENSE: positive balance = you've spent money (neutral)
          // For INCOME: positive balance = you've earned money (success)
          accountType === 'LIABILITY'
            ? (parseFloat(accountStats.balance) > 0 ? 'text-accent-warning' : 'text-accent-success')
            : accountType === 'EXPENSE'
              ? 'text-text-primary'
              : (parseFloat(accountStats.balance) >= 0 ? 'text-accent-success' : 'text-accent-danger')
        )}>
          {accountType === 'LIABILITY' && parseFloat(accountStats.balance) > 0
            ? formatCurrency(parseFloat(accountStats.balance), accountStats.currency)
            : formatCurrency(parseFloat(accountStats.balance), accountStats.currency)
          }
        </p>
        {accountStats.balance_includes_drafts && (
          <p className="text-xs text-text-muted mt-1">Including draft transactions</p>
        )}
        {accountType === 'LIABILITY' && parseFloat(accountStats.balance) <= 0 && (
          <p className="text-xs text-accent-success mt-1">No outstanding balance</p>
        )}
      </div>

      {/* Transaction stats */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-bg-elevated rounded-lg p-3 text-center">
          <p className="text-xl font-bold text-text-primary font-mono">
            {accountStats.transaction_count}
          </p>
          <p className="text-xs text-text-muted">Transactions</p>
        </div>
        <div className="bg-bg-elevated rounded-lg p-3 text-center">
          <p className="text-xl font-bold text-accent-success font-mono">
            {accountStats.posted_count}
          </p>
          <p className="text-xs text-text-muted">Posted</p>
        </div>
        <div className="bg-bg-elevated rounded-lg p-3 text-center">
          <p className="text-xl font-bold text-yellow-500 font-mono">
            {accountStats.draft_count}
          </p>
          <p className="text-xs text-text-muted">Draft</p>
        </div>
      </div>

      {/* Flow stats */}
      {(() => {
        const debitIsPositive = accountType === 'ASSET' || accountType === 'LIABILITY'
        const debitColor = debitIsPositive ? 'text-accent-success' : 'text-accent-danger'
        const creditColor = debitIsPositive ? 'text-accent-danger' : 'text-accent-success'

        return (
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-bg-elevated rounded-lg p-3">
              <p className="text-xs text-text-muted mb-1">Total Debits</p>
              <p className={cn("text-sm font-mono", debitColor)}>
                {formatCurrency(parseFloat(accountStats.total_debits), accountStats.currency)}
              </p>
            </div>
            <div className="bg-bg-elevated rounded-lg p-3">
              <p className="text-xs text-text-muted mb-1">Total Credits</p>
              <p className={cn("text-sm font-mono", creditColor)}>
                {formatCurrency(parseFloat(accountStats.total_credits), accountStats.currency)}
              </p>
            </div>
            <div className="bg-bg-elevated rounded-lg p-3">
              <p className="text-xs text-text-muted mb-1">Net Flow</p>
              <p className={cn(
                "text-sm font-mono",
                (parseFloat(accountStats.net_flow) >= 0) === debitIsPositive
                  ? 'text-accent-success'
                  : 'text-accent-danger'
              )}>
                {parseFloat(accountStats.net_flow) >= 0 ? '+' : ''}
                {formatCurrency(parseFloat(accountStats.net_flow), accountStats.currency)}
              </p>
            </div>
          </div>
        )
      })()}

      {/* Activity dates */}
      {(accountStats.first_transaction_date || accountStats.last_transaction_date) && (
        <div className="bg-bg-elevated rounded-lg p-4">
          <p className="text-sm font-medium text-text-primary mb-2">Activity</p>
          <div className="grid grid-cols-2 gap-4 text-sm">
            {accountStats.first_transaction_date && (
              <div>
                <p className="text-text-muted">First Transaction</p>
                <p className="text-text-primary">
                  {formatDate(accountStats.first_transaction_date, { year: 'numeric', month: '2-digit', day: '2-digit' })}
                </p>
              </div>
            )}
            {accountStats.last_transaction_date && (
              <div>
                <p className="text-text-muted">Last Transaction</p>
                <p className="text-text-primary">
                  {formatDate(accountStats.last_transaction_date, { year: 'numeric', month: '2-digit', day: '2-digit' })}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Period info */}
      {accountStats.period_days && (
        <p className="text-xs text-text-muted text-center">
          Showing data from {formatDate(accountStats.period_start!, { year: 'numeric', month: '2-digit', day: '2-digit' })} to {formatDate(accountStats.period_end!, { year: 'numeric', month: '2-digit', day: '2-digit' })}
        </p>
      )}

      {/* Actions section */}
      <div className="pt-4 border-t border-border-subtle flex justify-end">
        <Button
          variant="secondary"
          size="sm"
          onClick={onEditClick}
        >
          <Pencil className="h-4 w-4 mr-1.5" />
          Edit Account
        </Button>
      </div>
    </div>
  )
}
