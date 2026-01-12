import * as React from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ChevronRight } from 'lucide-react'
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, ConfirmDialog, useToast } from '@/components/ui'
import { deleteAccountPermanently, reactivateAccount } from '@/api'
import type { Account } from '@/types/api'
import { cn } from '@/lib/utils'
import {
  accountTypeLabels,
  accountTypeOrder,
  getAccountColor,
  getAccountIcon,
  normalizeAccountType,
  type NormalizedAccountType,
} from './account-utils'

type HierarchicalAccount = { account: Account; depth: number }

function buildHierarchy(accountList: Account[]): HierarchicalAccount[] {
  const result: HierarchicalAccount[] = []
  const processed = new Set<string>()

  const addWithChildren = (account: Account, depth: number) => {
    if (processed.has(account.id)) return
    processed.add(account.id)
    result.push({ account, depth })

    const children = accountList.filter((a) => a.parent_id === account.id)
    children
      .sort((a, b) => a.account_number.localeCompare(b.account_number))
      .forEach((child) => addWithChildren(child, depth + 1))
  }

  const topLevel = accountList
    .filter((a) => !a.parent_id)
    .sort((a, b) => a.account_number.localeCompare(b.account_number))

  topLevel.forEach((account) => addWithChildren(account, 0))

  accountList
    .filter((a) => !processed.has(a.id))
    .sort((a, b) => a.account_number.localeCompare(b.account_number))
    .forEach((account) => result.push({ account, depth: 0 }))

  return result
}

interface AccountsGroupListProps {
  accounts: Account[]
  onOpenAccount: (accountId: string) => void
}

export function AccountsGroupList({ accounts, onOpenAccount }: AccountsGroupListProps) {
  const queryClient = useQueryClient()
  const toast = useToast()

  const [deleteCandidate, setDeleteCandidate] = React.useState<{ id: string; name: string } | null>(null)

  const reactivateMutation = useMutation({
    mutationFn: (accountId: string) => reactivateAccount(accountId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
      toast.success({ title: 'Account reactivated', description: 'The account is active again.' })
    },
    onError: (err) => {
      toast.danger({
        title: 'Failed to reactivate account',
        description: err instanceof Error ? err.message : 'Unknown error',
      })
    },
  })

  const deletePermanentlyMutation = useMutation({
    mutationFn: (accountId: string) => deleteAccountPermanently(accountId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
      toast.success({ title: 'Account deleted', description: 'The account was permanently deleted.' })
      setDeleteCandidate(null)
    },
    onError: (err) => {
      toast.danger({
        title: 'Failed to delete account',
        description: err instanceof Error ? err.message : 'Unknown error',
      })
    },
  })

  const groupedAccounts = accounts.reduce((groups, account) => {
    const type = normalizeAccountType(account.account_type)
    if (!groups[type]) groups[type] = []
    groups[type].push(account)
    return groups
  }, {} as Record<NormalizedAccountType, Account[]>)

  const hierarchicalGroups = Object.entries(groupedAccounts).reduce((result, [type, accountList]) => {
    result[type as NormalizedAccountType] = buildHierarchy(accountList)
    return result
  }, {} as Record<NormalizedAccountType, HierarchicalAccount[]>)

  const accountTypes = accountTypeOrder

  return (
    <>
      <div className="grid gap-6">
        {accountTypes.map((type, typeIndex) => {
          const typeAccounts = groupedAccounts[type] ?? []
          const hierarchicalAccounts = hierarchicalGroups[type] ?? []
          if (typeAccounts.length === 0) return null

          return (
            <Card
              key={type}
              className={cn(
                'animate-slide-up',
                typeIndex === 0 && 'animate-stagger-1',
                typeIndex === 1 && 'animate-stagger-2',
                typeIndex === 2 && 'animate-stagger-3',
                typeIndex === 3 && 'animate-stagger-4',
                typeIndex === 4 && 'animate-stagger-5'
              )}
            >
              <CardHeader className="pb-3">
                <div className="flex items-center gap-3">
                  <div className={cn('flex items-center justify-center h-10 w-10 rounded-lg', getAccountColor(type))}>
                    {getAccountIcon(type)}
                  </div>
                  <div>
                    <CardTitle>{accountTypeLabels[type]}</CardTitle>
                    <p className="text-sm text-text-muted">
                      {typeAccounts.length} account{typeAccounts.length !== 1 ? 's' : ''}
                    </p>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="divide-y divide-border-subtle">
                  {hierarchicalAccounts.map(({ account, depth }) => (
                    <div
                      key={account.id}
                      role="button"
                      tabIndex={0}
                      aria-haspopup="dialog"
                      aria-label={`View account: ${account.account_number} ${account.name}`}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault()
                          onOpenAccount(account.id)
                        }
                      }}
                      className="flex items-center justify-between py-3 hover:bg-bg-hover -mx-6 px-6 transition-colors cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary/50 focus-visible:ring-offset-2 focus-visible:ring-offset-bg-surface"
                      onClick={() => onOpenAccount(account.id)}
                      style={{ paddingLeft: `${1.5 + depth * 1.5}rem` }}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        {depth > 0 && <span className="text-text-muted text-xs">└</span>}
                        <span className="text-xs font-mono text-text-muted bg-bg-elevated px-2 py-1 rounded">
                          {account.account_number}
                        </span>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <p
                              className={cn(
                                'text-sm font-medium truncate',
                                account.is_active ? 'text-text-primary' : 'text-text-muted line-through'
                              )}
                            >
                              {account.name}
                            </p>
                            {!account.is_active && <Badge variant="warning">Inactive</Badge>}
                            {account.is_placeholder && <Badge variant="info">Placeholder</Badge>}
                          </div>
                          {account.description && (
                            <p className="text-xs text-text-muted truncate max-w-md">{account.description}</p>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {!account.is_active && (
                          <>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation()
                                reactivateMutation.mutate(account.id)
                              }}
                              disabled={reactivateMutation.isPending}
                            >
                              Reactivate
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation()
                                setDeleteCandidate({ id: account.id, name: account.name })
                              }}
                              disabled={deletePermanentlyMutation.isPending}
                              className="text-accent-danger hover:text-accent-danger"
                            >
                              Delete
                            </Button>
                          </>
                        )}
                        <span className="text-xs text-text-muted">{account.currency}</span>
                        <ChevronRight className="h-4 w-4 text-text-muted" />
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      <ConfirmDialog
        isOpen={!!deleteCandidate}
        title="Delete account permanently?"
        description={
          deleteCandidate ? (
            <span>
              This will permanently delete <strong>{deleteCandidate.name}</strong>. This cannot be undone.
            </span>
          ) : null
        }
        confirmLabel="Delete permanently"
        cancelLabel="Cancel"
        variant="danger"
        isLoading={deletePermanentlyMutation.isPending}
        onCancel={() => setDeleteCandidate(null)}
        onConfirm={() => {
          if (!deleteCandidate) return
          deletePermanentlyMutation.mutate(deleteCandidate.id)
        }}
      />
    </>
  )
}
