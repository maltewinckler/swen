/**
 * Shared hook for sync operations with streaming progress.
 *
 * Provides:
 * - Streaming sync execution with real-time progress via SSE
 * - Progress state (phase, current/total transactions, account info)
 * - Error handling
 *
 * Usage:
 * ```tsx
 * const {
 *   progress,
 *   result,
 *   error,
 *   startSync,
 * } = useSyncProgress({
 *   onSuccess: () => queryClient.invalidateQueries({ queryKey: ['accounts'] }),
 * })
 * ```
 */

import { useState, useCallback, useRef } from 'react'
import {
  runSyncStreaming,
  type SyncEvent,
  type SyncResultEvent,
  type SyncRunRequest,
} from '@/api'
import { resolveErrorKey } from '@/api/syncErrorKeys'

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
}

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
  result: SyncResultEvent | null
  /** Error message (empty when no error) */
  error: string
  /** BLZ filter for bank-specific sync */
  syncBlz: string | undefined
  /** Whether modal is open */
  isOpen: boolean

  // === Actions ===
  /**
   * Start sync directly.
   * Use this when you already know the parameters.
   */
  startSync: (options?: SyncRunRequest) => Promise<void>

  /** Skip sync (close modal without syncing) */
  skip: () => void

  /** Reset all state (close modal and clear results) */
  reset: () => void
}

/**
 * Hook for managing sync operations with streaming progress.
 */
export function useSyncProgress(
  options?: UseSyncProgressOptions
): UseSyncProgressReturn {
  // State
  const [isOpen, setIsOpen] = useState(false)
  const [progress, setProgress] = useState<SyncProgress | null>(null)
  const [result, setResult] = useState<SyncResultEvent | null>(null)
  const [error, setError] = useState('')
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
    setProgress(null)
    setResult(null)
    setError('')
    setSyncBlz(undefined)
    // Clear event queue refs
    currentAccountRef.current = null
    eventQueueRef.current = []
    processingRef.current = false
  }, [])

  /**
   * Skip sync and close modal
   */
  const skip = useCallback(() => {
    syncAbortRef.current?.abort()
    syncAbortRef.current = null

    setIsOpen(false)
  }, [])

  /**
   * Process a single event immediately
   */
  const processEvent = useCallback((event: SyncEvent) => {
    switch (event.event_type) {
      case 'batch_sync_started':
        currentAccountRef.current = null
        setProgress({
          currentAccount: '',
          currentAccountName: '',
          accountIndex: 0,
          totalAccounts: event.total_accounts,
          transactionsCurrent: 0,
          transactionsTotal: 0,
          phase: 'connecting',
          lastMessage: '',
        })
        break

      case 'account_sync_started':
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
          lastMessage: '',
        }))
        break

      case 'account_sync_fetched':
        setProgress(prev => ({
          ...prev!,
          transactionsTotal: event.new_transactions,
          phase: event.new_transactions > 0 ? 'fetching' : 'complete',
          lastMessage: '',
        }))
        break

      case 'classification_started':
        // ML batch classification starting — transactionsTotal already set from account_sync_fetched
        setProgress(prev => ({
          ...prev!,
          transactionsCurrent: 0,
          phase: 'classifying',
          lastMessage: '',
        }))
        break

      case 'classification_progress':
        // ML batch classification progress
        setProgress(prev => ({
          ...prev!,
          transactionsCurrent: event.current,
          transactionsTotal: event.total,
          phase: 'classifying',
          lastMessage: '',
        }))
        break

      case 'classification_completed':
        // ML batch classification completed, import phase starts
        setProgress(prev => ({
          ...prev!,
          transactionsCurrent: event.total,
          transactionsTotal: event.total,
          phase: 'classifying',
          lastMessage: '',
        }))
        break

      case 'account_sync_completed':
        setProgress(prev => ({
          ...prev!,
          phase: 'complete',
          lastMessage: '',
        }))
        break

      case 'account_sync_failed':
        setProgress(prev => ({
          ...prev!,
          lastMessage: resolveErrorKey(event.error_key),
        }))
        break

      case 'batch_sync_failed':
        setError(resolveErrorKey(event.error_key))
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

      // If this is an account_sync_started event and we already have an account,
      // add a delay so user can see the previous account's completion
      if (
        event.event_type === 'account_sync_started' &&
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

    // Open modal to show progress
    setIsOpen(true)
    setProgress(null)
    setError('')
    setResult(null)

    try {
      const streamResult = await runSyncStreaming(handleProgressEvent, request, {
        signal: controller.signal,
      })

      setResult(streamResult)
      setProgress(null)

      options?.onSuccess?.(streamResult)
    } catch (err) {
      // Ignore aborts (usually caused by reset/unmount)
      if (controller.signal.aborted || syncAbortRef.current !== controller) {
        return
      }

      const errorMessage = err instanceof Error ? err.message : 'Sync failed'
      setError(errorMessage)
      setProgress(null)
      options?.onError?.(errorMessage)
    } finally {
      if (syncAbortRef.current === controller) {
        syncAbortRef.current = null
      }
    }
  }, [handleProgressEvent, options, setIsOpen])

  return {
    // State
    progress,
    result,
    error,
    syncBlz,
    isOpen,

    // Actions
    startSync,
    skip,
    reset,
  }
}
