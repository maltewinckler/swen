/**
 * Parent Account Select
 *
 * Dropdown component for selecting a parent account.
 * Filters to show only compatible accounts (same type).
 */

import { useQuery } from '@tanstack/react-query'
import { listAccounts } from '@/api'
import { Select } from '@/components/ui'
import type { AccountType } from '@/types/api'

interface ParentAccountSelectProps {
  /** Current account ID (to exclude from options) */
  accountId: string
  /** Account type to filter by (only same-type accounts can be parents) */
  accountType: AccountType
  /** Currently selected parent ID (null = no parent) */
  value: string | null
  /** Called when selection changes */
  onChange: (parentId: string | null) => void
  /** Whether the select is disabled */
  disabled?: boolean
  /** Whether the select is in an error state */
  hasError?: boolean
}

export function ParentAccountSelect({
  accountId,
  accountType,
  value,
  onChange,
  disabled,
  hasError,
}: ParentAccountSelectProps) {
  // Fetch accounts of the same type
  const { data, isLoading } = useQuery({
    queryKey: ['accounts', { account_type: accountType.toLowerCase() }],
    queryFn: () => listAccounts({ account_type: accountType }),
  })

  // Filter eligible parents:
  // - Not the account itself
  // - Active accounts only
  // - Same account type (already filtered by query)
  const eligibleParents = (data?.items ?? []).filter(
    (account) => account.id !== accountId && account.is_active
  )

  // Build options for Select component
  const options = [
    { value: '', label: '(None - Top Level)' },
    ...eligibleParents.map((account) => ({
      value: account.id,
      label: `${account.account_number} - ${account.name}`,
    })),
  ]

  const handleChange = (newValue: string) => {
    // Empty string means "None" was selected
    onChange(newValue === '' ? null : newValue)
  }

  return (
    <Select
      options={options}
      value={value ?? ''}
      onChange={handleChange}
      disabled={disabled || isLoading}
      placeholder={isLoading ? 'Loading...' : undefined}
      error={hasError}
    />
  )
}
