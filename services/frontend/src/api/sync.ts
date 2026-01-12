import { api, API_BASE, LONG_TIMEOUT, getAccessToken, tryRefreshToken } from './client'

// Types
export interface SyncRunRequest {
  /**
   * Number of days to sync (1-730).
   * If omitted/null, uses adaptive mode:
   * - First sync: 90 days default
   * - Subsequent: from last sync date to today
   */
  days?: number | null
  /** Sync only this specific account by IBAN */
  iban?: string
  /** Sync only accounts from this bank (by BLZ/bank code) */
  blz?: string
  auto_post?: boolean
}

export interface AccountSyncStats {
  iban: string
  fetched: number
  imported: number
  skipped: number
  failed: number
}

export interface OpeningBalance {
  iban: string
  amount: string | null
}

export interface SyncRunResponse {
  success: boolean
  synced_at: string
  start_date: string
  end_date: string
  auto_post: boolean
  total_fetched: number
  total_imported: number
  total_skipped: number
  total_failed: number
  accounts_synced: number
  account_stats: AccountSyncStats[]
  opening_balances: OpeningBalance[]
  errors: string[]
  opening_balance_account_missing: boolean
}

export interface SyncStatusResponse {
  success_count: number
  failed_count: number
  pending_count: number
  duplicate_count: number
  skipped_count: number
  total_count: number
}

/**
 * Sync recommendation for a single account
 */
export interface AccountSyncRecommendation {
  iban: string
  /** True if this account has never been synced */
  is_first_sync: boolean
  /** Recommended start date (null for first sync - user should specify) */
  recommended_start_date: string | null
  /** Date of last successfully imported transaction */
  last_successful_sync_date: string | null
  /** Number of transactions successfully imported */
  successful_import_count: number
}

/**
 * Response from sync recommendation endpoint
 */
export interface SyncRecommendationResponse {
  accounts: AccountSyncRecommendation[]
  /** True if any account needs first-time sync */
  has_first_sync_accounts: boolean
  total_accounts: number
}

/**
 * Get sync recommendations for adaptive synchronization.
 *
 * Use this to determine whether to show a "first sync" dialog:
 * - If has_first_sync_accounts is true: ask user for days
 * - Otherwise: use adaptive sync (no days parameter)
 */
export async function getSyncRecommendation(): Promise<SyncRecommendationResponse> {
  return api.get<SyncRecommendationResponse>('/sync/recommendation')
}

/**
 * Run bank transaction sync.
 *
 * For adaptive sync (recommended for regular use), omit the request
 * or pass undefined for days. This will:
 * - First sync: use 90 days as default
 * - Subsequent syncs: sync from last import date + 1 day
 *
 * Note: This can take up to 5 minutes if TAN approval is required
 */
export async function runSync(request?: SyncRunRequest): Promise<SyncRunResponse> {
  return api.post<SyncRunResponse>('/sync/run', request ?? {}, { timeout: LONG_TIMEOUT })
}

/**
 * Run adaptive sync (no fixed date range).
 * Each account syncs from its last successful import date.
 */
export async function runAdaptiveSync(): Promise<SyncRunResponse> {
  return runSync({})  // No days = adaptive mode
}

/**
 * Run first-time sync with specified number of days.
 * Use this when user specifies how much history to load.
 */
export async function runFirstSync(days: number): Promise<SyncRunResponse> {
  return runSync({ days })
}

/**
 * Get sync status and statistics
 */
export async function getSyncStatus(): Promise<SyncStatusResponse> {
  return api.get<SyncStatusResponse>('/sync/status')
}

// ==================== SSE Streaming Sync ====================

/**
 * Event types emitted during sync
 */
export type SyncEventType =
  | 'sync_started'
  | 'sync_completed'
  | 'sync_failed'
  | 'account_started'
  | 'account_fetched'
  | 'account_classifying'
  | 'account_completed'
  | 'account_failed'
  | 'transaction_classified'
  | 'result'

/**
 * Base sync progress event
 */
export interface SyncProgressEvent {
  event_type: SyncEventType
  message: string
  timestamp: string
}

/**
 * Sync started event
 */
export interface SyncStartedEvent extends SyncProgressEvent {
  event_type: 'sync_started'
  total_accounts: number
}

/**
 * Sync completed event
 */
export interface SyncCompletedEvent extends SyncProgressEvent {
  event_type: 'sync_completed'
  total_imported: number
  total_skipped: number
  total_failed: number
  accounts_synced: number
}

/**
 * Account started event
 */
export interface AccountStartedEvent extends SyncProgressEvent {
  event_type: 'account_started'
  iban: string
  account_name: string
  account_index: number
  total_accounts: number
}

/**
 * Account fetched event
 */
export interface AccountFetchedEvent extends SyncProgressEvent {
  event_type: 'account_fetched'
  iban: string
  transactions_fetched: number
  new_transactions: number
}

/**
 * Account classifying event
 */
export interface AccountClassifyingEvent extends SyncProgressEvent {
  event_type: 'account_classifying'
  iban: string
  current: number
  total: number
}

/**
 * Transaction classified event
 */
export interface TransactionClassifiedEvent extends SyncProgressEvent {
  event_type: 'transaction_classified'
  iban: string
  current: number
  total: number
  description: string
  counter_account_name: string
  transaction_id: string | null
}

/**
 * Account completed event
 */
export interface AccountCompletedEvent extends SyncProgressEvent {
  event_type: 'account_completed'
  iban: string
  imported: number
  skipped: number
  failed: number
}

/**
 * Account failed event
 */
export interface AccountFailedEvent extends SyncProgressEvent {
  event_type: 'account_failed'
  iban: string
  error: string
}

/**
 * Sync failed event
 */
export interface SyncFailedEvent extends SyncProgressEvent {
  event_type: 'sync_failed'
  error: string
}

/**
 * Final result event
 */
export interface SyncResultEvent {
  event_type: 'result'
  success: boolean
  total_imported: number
  total_skipped: number
  total_failed: number
  accounts_synced: number
}

/**
 * All possible sync events
 */
export type SyncEvent =
  | SyncStartedEvent
  | SyncCompletedEvent
  | SyncFailedEvent
  | AccountStartedEvent
  | AccountFetchedEvent
  | AccountClassifyingEvent
  | AccountCompletedEvent
  | AccountFailedEvent
  | TransactionClassifiedEvent
  | SyncResultEvent

/**
 * Callback type for sync progress events
 */
export type SyncProgressCallback = (event: SyncEvent) => void

export interface RunSyncStreamingOptions {
  /** Optional abort signal to cancel the streaming request */
  signal?: AbortSignal
}

/**
 * Run sync with streaming progress updates via SSE.
 *
 * @param onEvent Callback for each progress event
 * @param request Optional sync request parameters
 * @param options Optional configuration (abort signal)
 * @returns Promise that resolves when sync completes or rejects on error
 */
export async function runSyncStreaming(
  onEvent: SyncProgressCallback,
  request?: SyncRunRequest,
  options?: RunSyncStreamingOptions
): Promise<SyncResultEvent> {
  // NOTE: We don't use the shared api client here because we need access to the
  // raw Response stream. We still mirror its refresh-token behavior for 401s.
  const url = `${API_BASE}/sync/run/stream`

  // Create a controller so we can enforce LONG_TIMEOUT and optionally chain an external signal
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
      body: JSON.stringify(request ?? {}),
      signal: controller.signal,
    })
  }

  try {
    let response = await fetchStream()

    // Handle 401 - try refresh and retry once
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
      throw new Error(`Sync failed (${response.status}): ${errorText || response.statusText}`)
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('No response body')
    }

    const decoder = new TextDecoder()
    let buffer = ''
    let finalResult: SyncResultEvent | null = null

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // Parse SSE events from buffer
      const lines = buffer.split('\n')
      buffer = lines.pop() || '' // Keep incomplete line in buffer

      let currentEventType = ''
      let currentData = ''

      for (const line of lines) {
        if (line.startsWith('event: ')) {
          currentEventType = line.slice(7).trim()
        } else if (line.startsWith('data: ')) {
          currentData = line.slice(6)
        } else if (line === '' && currentEventType && currentData) {
          // End of event
          try {
            const eventData = JSON.parse(currentData) as SyncEvent
            eventData.event_type = currentEventType as SyncEventType
            onEvent(eventData)

            // Capture final result
            if (currentEventType === 'result') {
              finalResult = eventData as SyncResultEvent
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
      throw new Error('Sync completed without result')
    }

    return finalResult
  } finally {
    clearTimeout(timeoutId)
    if (externalSignal) externalSignal.removeEventListener('abort', onAbort)
  }
}
