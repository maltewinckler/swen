import type { Transaction, TransactionListResponse, TransactionListItem } from '@/types/api'
import { api, API_BASE, LONG_TIMEOUT, getAccessToken, tryRefreshToken } from './client'
import { buildQueryString } from '@/lib/utils'

interface ListTransactionsParams {
  page?: number
  status_filter?: 'posted' | 'draft'  // Backend parameter name
  account_number?: string  // Backend uses account_number, not account_id
  exclude_transfers?: boolean
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


// ==================== Reclassify Drafts (SSE) ====================

export interface ReclassifyDraftsRequest {
  transaction_ids?: string[]
  reclassify_all?: boolean
  only_fallback?: boolean
}

export type ReclassifyEventType =
  | 'reclassify_started'
  | 'reclassify_progress'
  | 'reclassify_transaction'
  | 'reclassify_completed'
  | 'reclassify_failed'
  | 'result'

export interface ReclassifyStartedEvent {
  event_type: 'reclassify_started'
  message: string
  total: number
}

export interface ReclassifyProgressEvent {
  event_type: 'reclassify_progress'
  message: string
  current: number
  total: number
}

export interface ReclassifyTransactionEvent {
  event_type: 'reclassify_transaction'
  message: string
  transaction_id: string
  description: string
  old_account: string
  new_account: string
  confidence: number
  current: number
  total: number
}

export interface ReclassifyCompletedEvent {
  event_type: 'reclassify_completed'
  message: string
  total: number
  reclassified: number
  unchanged: number
  failed: number
}

export interface ReclassifyFailedEvent {
  event_type: 'reclassify_failed'
  message: string
  error?: string
}

export interface ReclassifyResultEvent {
  event_type: 'result'
  total_drafts: number
  reclassified_count: number
  unchanged_count: number
  failed_count: number
}

export type ReclassifyEvent =
  | ReclassifyStartedEvent
  | ReclassifyProgressEvent
  | ReclassifyTransactionEvent
  | ReclassifyCompletedEvent
  | ReclassifyFailedEvent
  | ReclassifyResultEvent

export type ReclassifyProgressCallback = (event: ReclassifyEvent) => void

export interface ReclassifyStreamingOptions {
  signal?: AbortSignal
}

/**
 * Reclassify draft transactions via ML with streaming progress (SSE).
 */
export async function reclassifyDraftsStreaming(
  onEvent: ReclassifyProgressCallback,
  request: ReclassifyDraftsRequest,
  options?: ReclassifyStreamingOptions
): Promise<ReclassifyResultEvent> {
  const url = `${API_BASE}/transactions/reclassify-drafts/stream`

  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), LONG_TIMEOUT)

  const externalSignal = options?.signal
  const onAbort = () => controller.abort()
  if (externalSignal) {
    if (externalSignal.aborted) {
      controller.abort()
    } else {
      externalSignal.addEventListener('abort', onAbort, { once: true })
    }
  }

  const fetchStream = async (): Promise<Response> => {
    const token = getAccessToken()
    return fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      credentials: 'include',
      body: JSON.stringify(request),
      signal: controller.signal,
    })
  }

  try {
    let response = await fetchStream()

    if (response.status === 401) {
      const refreshed = await tryRefreshToken()
      if (refreshed) {
        response = await fetchStream()
      } else {
        throw new Error('Session expired. Please log in again.')
      }
    }

    if (!response.ok) {
      const errorText = await response.text().catch(() => response.statusText)
      throw new Error(`Reclassification failed (${response.status}): ${errorText || response.statusText}`)
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('No response body')
    }

    const decoder = new TextDecoder()
    let buffer = ''
    let finalResult: ReclassifyResultEvent | null = null

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      let currentEventType = ''
      let currentData = ''

      for (const line of lines) {
        if (line.startsWith('event: ')) {
          currentEventType = line.slice(7).trim()
        } else if (line.startsWith('data: ')) {
          currentData = line.slice(6)
        } else if (line === '' && currentEventType && currentData) {
          try {
            const eventData = JSON.parse(currentData) as ReclassifyEvent
            eventData.event_type = currentEventType as ReclassifyEventType
            onEvent(eventData)

            if (currentEventType === 'result') {
              finalResult = eventData as ReclassifyResultEvent
            }
          } catch (e) {
            console.warn('Failed to parse SSE event:', currentData, e)
          }
          currentEventType = ''
          currentData = ''
        }
      }
    }

    if (!finalResult) {
      throw new Error('Reclassification completed without result')
    }

    return finalResult
  } finally {
    clearTimeout(timeoutId)
    if (externalSignal) externalSignal.removeEventListener('abort', onAbort)
  }
}


// ==================== Bulk Post ====================

export interface BulkPostRequest {
  transaction_ids?: string[]
  post_all_drafts?: boolean
}

export interface BulkPostResponse {
  posted_count: number
  transaction_ids: string[]
}

/**
 * Post multiple draft transactions at once
 */
export async function bulkPostTransactions(request: BulkPostRequest): Promise<BulkPostResponse> {
  return api.post<BulkPostResponse>('/transactions/bulk-post', request)
}
