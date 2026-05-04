/**
 * Hook for reclassifying draft transactions via ML with streaming progress.
 *
 * Usage:
 * ```tsx
 * const {
 *   progress,
 *   result,
 *   error,
 *   isRunning,
 *   startReclassify,
 *   cancel,
 *   reset,
 * } = useReclassifyProgress({ onSuccess: () => invalidate() })
 * ```
 */

import { useState, useCallback, useRef } from 'react'
import {
  reclassifyDraftsStreaming,
  type ReclassifyDraftsRequest,
  type ReclassifyEvent,
  type ReclassifyResultEvent,
} from '@/api/transactions'

export interface ReclassifyProgress {
  phase: 'classifying' | 'applying' | 'complete'
  current: number
  total: number
  lastMessage: string
  lastDescription?: string
  lastOldAccount?: string
  lastNewAccount?: string
  reclassifiedCount: number
}

export type ReclassifyStep = 'idle' | 'running' | 'success' | 'error'

export interface UseReclassifyProgressOptions {
  onSuccess?: (result: ReclassifyResultEvent) => void
  onError?: (error: string) => void
}

export interface UseReclassifyProgressReturn {
  progress: ReclassifyProgress | null
  result: ReclassifyResultEvent | null
  error: string
  step: ReclassifyStep
  isRunning: boolean
  startReclassify: (request: ReclassifyDraftsRequest) => Promise<void>
  cancel: () => void
  reset: () => void
}

export function useReclassifyProgress(
  options?: UseReclassifyProgressOptions
): UseReclassifyProgressReturn {
  const [step, setStep] = useState<ReclassifyStep>('idle')
  const [progress, setProgress] = useState<ReclassifyProgress | null>(null)
  const [result, setResult] = useState<ReclassifyResultEvent | null>(null)
  const [error, setError] = useState('')
  const abortRef = useRef<AbortController | null>(null)

  const reset = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    setStep('idle')
    setProgress(null)
    setResult(null)
    setError('')
  }, [])

  const cancel = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    setStep('idle')
    setProgress(null)
  }, [])

  const processEvent = useCallback((event: ReclassifyEvent) => {
    switch (event.event_type) {
      case 'reclassify_started':
        setProgress({
          phase: 'classifying',
          current: 0,
          total: event.total,
          lastMessage: event.message,
          reclassifiedCount: 0,
        })
        break

      case 'reclassify_progress':
        setProgress(prev => prev ? {
          ...prev,
          phase: 'classifying',
          current: event.current,
          total: event.total,
          lastMessage: event.message,
        } : prev)
        break

      case 'reclassify_transaction':
        setProgress(prev => prev ? {
          ...prev,
          phase: 'applying',
          lastMessage: event.message,
          lastDescription: event.description,
          lastOldAccount: event.old_account,
          lastNewAccount: event.new_account,
          reclassifiedCount: (prev.reclassifiedCount || 0) + 1,
        } : prev)
        break

      case 'reclassify_completed':
        setProgress(prev => prev ? {
          ...prev,
          phase: 'complete',
          current: event.total,
          total: event.total,
          lastMessage: event.message,
          reclassifiedCount: event.reclassified,
        } : prev)
        break

      case 'reclassify_failed':
        setError(event.error || event.message)
        setStep('error')
        break
    }
  }, [])

  const startReclassify = useCallback(async (request: ReclassifyDraftsRequest) => {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setStep('running')
    setProgress(null)
    setResult(null)
    setError('')

    try {
      const finalResult = await reclassifyDraftsStreaming(
        processEvent,
        request,
        { signal: controller.signal }
      )
      setResult(finalResult)
      setStep('success')
      options?.onSuccess?.(finalResult)
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        setStep('idle')
        return
      }
      const message = err instanceof Error ? err.message : 'Reclassification failed'
      setError(message)
      setStep('error')
      options?.onError?.(message)
    } finally {
      abortRef.current = null
    }
  }, [processEvent, options])

  return {
    progress,
    result,
    error,
    step,
    isRunning: step === 'running',
    startReclassify,
    cancel,
    reset,
  }
}
