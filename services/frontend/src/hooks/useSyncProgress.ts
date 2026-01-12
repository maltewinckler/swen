/**
 * Shared hook for sync operations with streaming progress.
 *
 * Provides:
 * - Streaming sync execution with real-time progress via SSE
 * - Progress state (phase, current/total transactions, account info)
 * - First-sync detection and days prompt handling
 * - Error handling
 *
 * Usage:
 * ```tsx
 * const {
 *   progress,
 *   result,
 *   error,
 *   step,
 *   startSync,
 *   checkAndSync,
 * } = useSyncProgress({
 *   onSuccess: () => queryClient.invalidateQueries({ queryKey: ['accounts'] }),
 * })
 * ```
 */

import { useState, useCallback, useRef } from 'react'
import {
  getSyncRecommendation,
  runSyncStreaming,
  type SyncEvent,
  type SyncRunResponse,
  type SyncResultEvent,
  type SyncRunRequest,
} from '@/api'

/** Delay (ms) before transitioning to next account, so user can see completion */
const ACCOUNT_TRANSITION_DELAY = 800

/**
 * Current sync progress state
 */
export interface SyncProgress {
  /** Current phase of the sync operation */
  phase: 'connecting' | 'fetching' | 'classifying' | 'complete'
  /** IBAN of the account currently being synced */
  currentAccount: string
  /** Display name of the current account */
  currentAccountName: string
  /** 1-based index of current account */
  accountIndex: number
  /** Total number of accounts to sync */
  totalAccounts: number
  /** Number of transactions classified so far */
  transactionsCurrent: number
  /** Total transactions to classify */
  transactionsTotal: number
  /** Human-readable message from the last event */
  lastMessage: string
  /** Last classified transaction description (for live feed) */
  lastTransactionDescription?: string
  /** Counter account name for last classified transaction */
  lastCounterAccountName?: string
}

/**
 * Step in the sync workflow
 */
export type SyncStep =
  | 'idle'           // Not started
  | 'checking'       // Checking if first-sync is needed
  | 'first_sync_prompt'  // Waiting for user to confirm days
  | 'syncing'        // Actively syncing
  | 'success'        // Completed successfully
  | 'error'          // Failed

/**
 * Options for the useSyncProgress hook
 */
export interface UseSyncProgressOptions {
  /** Called when sync completes successfully */
  onSuccess?: (result: SyncResultEvent) => void
  /** Called when sync fails */
  onError?: (error: string) => void
}

/**
 * Return type for the useSyncProgress hook
 */
export interface UseSyncProgressReturn {
  // === State ===
  /** Current sync progress (null when not syncing) */
  progress: SyncProgress | null
  /** Final sync result (null until success) */
  result: SyncRunResponse | null
  /** Error message (empty when no error) */
  error: string
  /** Current step in the sync workflow */
  step: SyncStep
  /** Days to sync for first-sync (user-configurable) */
  firstSyncDays: number
  /** BLZ filter for bank-specific sync */
  syncBlz: string | undefined
  /** Whether modal is open */
  isOpen: boolean

  // === Actions ===
  /**
   * Start sync directly without checking for first-sync.
   * Use this when you already know the parameters.
   */
  startSync: (options?: SyncRunRequest) => Promise<void>

  /**
   * Check if first-sync is needed, then start sync.
   * Shows first-sync prompt if needed, otherwise syncs adaptively.
   */
  checkAndSync: (blz?: string) => Promise<void>

  /** Update the number of days for first-sync */
  setFirstSyncDays: (days: number) => void

  /** Confirm first-sync with the selected number of days */
  confirmFirstSync: () => void

  /** Skip sync (close modal without syncing) */
  skip: () => void

  /** Reset all state (close modal and clear results) */
  reset: () => void

  /** Open the sync modal (for external control) */
  open: (blz?: string) => void
}

/**
 * Hook for managing sync operations with streaming progress.
 */
export function useSyncProgress(
  options?: UseSyncProgressOptions
): UseSyncProgressReturn {
  // State
  const [isOpen, setIsOpen] = useState(false)
  const [step, setStep] = useState<SyncStep>('idle')
  const [progress, setProgress] = useState<SyncProgress | null>(null)
  const [result, setResult] = useState<SyncRunResponse | null>(null)
  const [error, setError] = useState('')
  const [firstSyncDays, setFirstSyncDays] = useState(90)
  const [syncBlz, setSyncBlz] = useState<string | undefined>(undefined)

  // Track if we have an account in progress (for transition delays)
  const currentAccountRef = useRef<string | null>(null)
  // Queue for delayed events
  const eventQueueRef = useRef<SyncEvent[]>([])
  const processingRef = useRef(false)
  // Abort controller for in-flight streaming sync
  const syncAbortRef = useRef<AbortController | null>(null)

  /**
   * Reset all state
   */
  const reset = useCallback(() => {
    // Cancel any in-flight sync request
    syncAbortRef.current?.abort()
    syncAbortRef.current = null

    setIsOpen(false)
    setStep('idle')
    setProgress(null)
    setResult(null)
    setError('')
    setFirstSyncDays(90)
    setSyncBlz(undefined)
    // Clear event queue refs
    currentAccountRef.current = null
    eventQueueRef.current = []
    processingRef.current = false
  }, [])

  /**
   * Open the sync modal
   */
  const open = useCallback((blz?: string) => {
    // If something is still running, cancel it before reopening
    syncAbortRef.current?.abort()
    syncAbortRef.current = null

    setIsOpen(true)
    setStep('idle')
    setProgress(null)
    setResult(null)
    setError('')
    setSyncBlz(blz)
  }, [])

  /**
   * Skip sync and close modal
   */
  const skip = useCallback(() => {
    syncAbortRef.current?.abort()
    syncAbortRef.current = null

    setIsOpen(false)
    setStep('idle')
  }, [])

  /**
   * Process a single event immediately
   */
  const processEvent = useCallback((event: SyncEvent) => {
    switch (event.event_type) {
      case 'sync_started':
        currentAccountRef.current = null
        setProgress({
          currentAccount: '',
          currentAccountName: '',
          accountIndex: 0,
          totalAccounts: event.total_accounts,
          transactionsCurrent: 0,
          transactionsTotal: 0,
          phase: 'connecting',
          lastMessage: event.message,
        })
        break

      case 'account_started':
        currentAccountRef.current = event.iban
        setProgress(prev => ({
          ...prev!,
          currentAccount: event.iban,
          currentAccountName: event.account_name,
          accountIndex: event.account_index,
          totalAccounts: event.total_accounts,
          transactionsCurrent: 0,
          transactionsTotal: 0,
          phase: 'connecting',
          lastMessage: event.message,
          // Clear last transaction info when switching accounts
          lastTransactionDescription: undefined,
          lastCounterAccountName: undefined,
        }))
        break

      case 'account_fetched':
        setProgress(prev => ({
          ...prev!,
          transactionsTotal: event.new_transactions,
          phase: event.new_transactions > 0 ? 'fetching' : 'complete',
          lastMessage: event.message,
        }))
        break

      case 'account_classifying':
        setProgress(prev => ({
          ...prev!,
          transactionsCurrent: event.current,
          transactionsTotal: event.total,
          phase: 'classifying',
          lastMessage: event.message,
        }))
        break

      case 'transaction_classified':
        setProgress(prev => ({
          ...prev!,
          transactionsCurrent: event.current,
          transactionsTotal: event.total,
          phase: 'classifying',
          lastMessage: event.message,
          lastTransactionDescription: event.description,
          lastCounterAccountName: event.counter_account_name,
        }))
        break

      case 'account_completed':
        setProgress(prev => ({
          ...prev!,
          phase: 'complete',
          lastMessage: event.message,
        }))
        break

      case 'account_failed':
        setProgress(prev => ({
          ...prev!,
          lastMessage: `Error: ${event.error}`,
        }))
        break

      case 'sync_failed':
        setError(event.error || event.message)
        break
    }
  }, [])

  /**
   * Process queued events with delays for smooth transitions
   */
  const processQueue = useCallback(async () => {
    if (processingRef.current) return
    processingRef.current = true

    while (eventQueueRef.current.length > 0) {
      const event = eventQueueRef.current.shift()!

      // If this is an account_started event and we already have an account,
      // add a delay so user can see the previous account's completion
      if (
        event.event_type === 'account_started' &&
        currentAccountRef.current !== null &&
        currentAccountRef.current !== event.iban
      ) {
        await new Promise(resolve => setTimeout(resolve, ACCOUNT_TRANSITION_DELAY))
      }

      processEvent(event)
    }

    processingRef.current = false
  }, [processEvent])

  /**
   * Handle SSE progress events - queue and process with delays
   */
  const handleProgressEvent = useCallback((event: SyncEvent) => {
    eventQueueRef.current.push(event)
    processQueue()
  }, [processQueue])

  /**
   * Execute sync with streaming
   */
  const startSync = useCallback(async (request?: SyncRunRequest) => {
    // Cancel any previous run
    syncAbortRef.current?.abort()
    const controller = new AbortController()
    syncAbortRef.current = controller

    setStep('syncing')
    setProgress(null)
    setError('')

    try {
      const streamResult = await runSyncStreaming(handleProgressEvent, request, {
        signal: controller.signal,
      })

      // Convert streaming result to SyncRunResponse format
      const fullResult: SyncRunResponse = {
        success: streamResult.success,
        synced_at: new Date().toISOString(),
        start_date: '',
        end_date: '',
        auto_post: false,
        total_fetched: 0,
        total_imported: streamResult.total_imported,
        total_skipped: streamResult.total_skipped,
        total_failed: streamResult.total_failed,
        accounts_synced: streamResult.accounts_synced,
        account_stats: [],
        opening_balances: [],
        errors: [],
        opening_balance_account_missing: false,
      }

      setResult(fullResult)
      setStep('success')
      setProgress(null)

      options?.onSuccess?.(streamResult)
    } catch (err) {
      // Ignore aborts (usually caused by reset/unmount)
      if (controller.signal.aborted || syncAbortRef.current !== controller) {
        return
      }

      const errorMessage = err instanceof Error ? err.message : 'Sync failed'
      setError(errorMessage)
      setStep('error')
      setProgress(null)
      options?.onError?.(errorMessage)
    } finally {
      if (syncAbortRef.current === controller) {
        syncAbortRef.current = null
      }
    }
  }, [handleProgressEvent, options])

  /**
   * Check if first-sync is needed, then start sync
   */
  const checkAndSync = useCallback(async (blz?: string) => {
    setIsOpen(true)
    setStep('checking')
    setResult(null)
    setError('')
    setSyncBlz(blz)

    try {
      const recommendation = await getSyncRecommendation()

      // Filter by BLZ if specified (check IBAN prefix for German accounts)
      const relevantAccounts = blz
        ? recommendation.accounts.filter(
            acc => acc.iban.startsWith('DE') && acc.iban.slice(4, 12) === blz
          )
        : recommendation.accounts

      const hasFirstSync = relevantAccounts.some(acc => acc.is_first_sync)

      if (hasFirstSync) {
        // Show dialog to ask for days
        setStep('first_sync_prompt')
        setFirstSyncDays(90) // Reset to default
      } else {
        // Use adaptive sync (no days parameter)
        const request: SyncRunRequest = {}
        if (blz) request.blz = blz
        await startSync(request)
      }
    } catch (err) {
      setStep('error')
      setError(err instanceof Error ? err.message : 'Failed to check sync status')
    }
  }, [startSync])

  /**
   * Confirm first-sync with selected days
   */
  const confirmFirstSync = useCallback(() => {
    const request: SyncRunRequest = { days: firstSyncDays }
    if (syncBlz) request.blz = syncBlz
    startSync(request)
  }, [firstSyncDays, syncBlz, startSync])

  return {
    // State
    progress,
    result,
    error,
    step,
    firstSyncDays,
    syncBlz,
    isOpen,

    // Actions
    startSync,
    checkAndSync,
    setFirstSyncDays,
    confirmFirstSync,
    skip,
    reset,
    open,
  }
}
