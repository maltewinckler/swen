import type { Account, AccountType, AccountStats, ParentAction } from '@/types/api'
import { api } from './client'
import { buildQueryString } from '@/lib/utils'

interface ListAccountsParams {
  account_type?: AccountType
  active_only?: boolean  // true = only active accounts (default), false = include inactive
  is_active?: boolean    // Alias for active_only (for convenience)
  search?: string
  page?: number
  size?: number
}

interface ListAccountsResponse {
  accounts: Account[]
  total: number
  by_type: Record<string, number>
}

interface PaginatedAccountsResponse {
  items: Account[]
  total: number
}

/**
 * List accounts with optional filters
 */
export async function listAccounts(params?: ListAccountsParams): Promise<PaginatedAccountsResponse> {
  const query = buildQueryString(params ?? {})
  const response = await api.get<ListAccountsResponse>(`/accounts${query}`)

  // Transform to expected format
  return {
    items: response.accounts,
    total: response.total,
  }
}

/**
 * Get single account by ID
 */
export async function getAccount(id: string): Promise<Account> {
  return api.get<Account>(`/accounts/${id}`)
}

interface CreateAccountData {
  account_number: string
  name: string
  account_type: AccountType
  parent_id?: string
  currency?: string
  description?: string
}

/**
 * Create new account
 */
export async function createAccount(data: CreateAccountData): Promise<Account> {
  return api.post<Account>('/accounts', data)
}

interface UpdateAccountData {
  name?: string
  account_number?: string      // New account number/code (must be unique per user)
  description?: string | null  // Description with examples for AI classification
  parent_id?: string | null    // Required when parent_action is 'set'
  parent_action?: ParentAction // 'keep' (default) | 'set' | 'remove'
}

/**
 * Update account (name, description, etc.)
 */
export async function updateAccount(id: string, data: UpdateAccountData): Promise<Account> {
  return api.patch<Account>(`/accounts/${id}`, data)
}

/**
 * Deactivate account (soft delete)
 */
export async function deactivateAccount(id: string): Promise<void> {
  await api.delete(`/accounts/${id}`)
}

/**
 * Reactivate a deactivated account
 */
export async function reactivateAccount(id: string): Promise<Account> {
  return api.post<Account>(`/accounts/${id}/reactivate`)
}

/**
 * Permanently delete an account
 * Only works for accounts with no transactions or children
 */
export async function deleteAccountPermanently(id: string): Promise<void> {
  await api.delete(`/accounts/${id}/permanent`)
}

/**
 * Available chart of accounts templates
 */
export type ChartTemplate = 'minimal'

interface InitChartResponse {
  message: string
  skipped: boolean
  accounts_created: number
  template?: string
  by_type?: {
    income: number
    expense: number
    equity: number
    asset: number
    liability: number
  }
}

/**
 * Initialize default chart of accounts
 *
 * @param template - Template to use: 'minimal' for simple categories (~15 accounts)
 */
export async function initChartOfAccounts(
  template: ChartTemplate = 'minimal'
): Promise<InitChartResponse> {
  return api.post<InitChartResponse>('/accounts/init-chart', { template })
}

interface InitEssentialsResponse {
  message: string
  skipped: boolean
  accounts_created: number
}

/**
 * Initialize essential accounts only (Bargeld, Sonstiges, Sonstige Einnahmen)
 *
 * Creates the 3 accounts required for:
 * - Cash transactions (Bargeld)
 * - Fallback expense categorization (Sonstiges)
 * - Fallback income categorization (Sonstige Einnahmen)
 *
 * Idempotent - skips accounts that already exist.
 */
export async function initEssentialAccounts(): Promise<InitEssentialsResponse> {
  return api.post<InitEssentialsResponse>('/accounts/init-essentials')
}

interface GetAccountStatsParams {
  days?: number
  include_drafts?: boolean
}

/**
 * Get account statistics
 */
export async function getAccountStats(
  accountId: string,
  params?: GetAccountStatsParams
): Promise<AccountStats> {
  const query = buildQueryString(params ?? {})
  return api.get<AccountStats>(`/accounts/${accountId}/stats${query}`)
}

// Reconciliation types
export interface AccountReconciliation {
  iban: string
  account_name: string
  accounting_account_id: string
  currency: string
  bank_balance: string
  bank_balance_date: string | null
  last_sync_at: string | null
  bookkeeping_balance: string
  discrepancy: string
  is_reconciled: boolean
}

export interface ReconciliationResult {
  accounts: AccountReconciliation[]
  total_accounts: number
  reconciled_count: number
  discrepancy_count: number
  all_reconciled: boolean
}

/**
 * Get reconciliation status - compare bank balances with bookkeeping
 */
export async function getReconciliation(): Promise<ReconciliationResult> {
  return api.get<ReconciliationResult>('/accounts/reconciliation')
}
