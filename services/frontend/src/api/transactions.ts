import type { Transaction, TransactionListResponse, TransactionListItem } from '@/types/api'
import { api } from './client'
import { buildQueryString } from '@/lib/utils'

interface ListTransactionsParams {
  days?: number
  limit?: number
  status_filter?: 'posted' | 'draft'  // Backend parameter name
  account_number?: string  // Backend uses account_number, not account_id
  exclude_transfers?: boolean
  search?: string
}

/**
 * List transactions with optional filters
 */
export async function listTransactions(params?: ListTransactionsParams): Promise<TransactionListResponse> {
  const query = buildQueryString(params ?? {})
  return api.get<TransactionListResponse>(`/transactions${query}`)
}

export type { TransactionListItem }

/**
 * Get single transaction by ID
 */
export async function getTransaction(id: string): Promise<Transaction> {
  return api.get<Transaction>(`/transactions/${id}`)
}

interface CreateTransactionData {
  description: string
  date: string
  entries: Array<{
    account_id: string
    debit: string
    credit: string
  }>
  counterparty?: string
  reference?: string
  metadata?: Record<string, unknown>
  auto_post?: boolean
}

/**
 * Create manual transaction with explicit entries
 */
export async function createTransaction(data: CreateTransactionData): Promise<Transaction> {
  return api.post<Transaction>('/transactions', data)
}

interface CreateSimpleTransactionData {
  description: string
  amount: string
  date?: string
  asset_account?: string
  category_account?: string
  counterparty?: string
  reference?: string
  metadata?: Record<string, unknown>
  auto_post?: boolean
}

/**
 * Create simple transaction (auto-resolved accounts)
 */
export async function createSimpleTransaction(data: CreateSimpleTransactionData): Promise<Transaction> {
  return api.post<Transaction>('/transactions/simple', data)
}

interface UpdateTransactionData {
  description?: string
  counterparty?: string
  category_account_id?: string
  /** Replace all journal entries (for multi-entry edits).
   * Mutually exclusive with category_account_id.
   * For bank imports, protected (asset) entries are preserved automatically. */
  entries?: Array<{
    account_id: string
    debit: string
    credit: string
  }>
  metadata?: Record<string, unknown>
}

/**
 * Update transaction
 */
export async function updateTransaction(id: string, data: UpdateTransactionData): Promise<Transaction> {
  return api.put<Transaction>(`/transactions/${id}`, data)
}

/**
 * Post transaction
 */
export async function postTransaction(id: string): Promise<Transaction> {
  return api.post<Transaction>(`/transactions/${id}/post`)
}

/**
 * Unpost transaction
 */
export async function unpostTransaction(id: string): Promise<Transaction> {
  return api.post<Transaction>(`/transactions/${id}/unpost`)
}

/**
 * Delete transaction permanently
 * @param id Transaction ID
 * @param force If true, automatically unpost before deleting (for posted transactions)
 */
export async function deleteTransaction(id: string, force: boolean = false): Promise<void> {
  const query = force ? '?force=true' : ''
  await api.delete(`/transactions/${id}${query}`)
}
