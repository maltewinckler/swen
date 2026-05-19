import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useSyncProgress } from './useSyncProgress'
import * as api from '@/api'

// Mock the API module
vi.mock('@/api', () => ({
  runSyncStreaming: vi.fn(),
}))

describe('useSyncProgress', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('initial state', () => {
    it('has no progress initially', () => {
      const { result } = renderHook(() => useSyncProgress())

      expect(result.current.progress).toBeNull()
    })

    it('has no result initially', () => {
      const { result } = renderHook(() => useSyncProgress())

      expect(result.current.result).toBeNull()
    })

    it('has empty error initially', () => {
      const { result } = renderHook(() => useSyncProgress())

      expect(result.current.error).toBe('')
    })

    it('is not open initially', () => {
      const { result } = renderHook(() => useSyncProgress())

      expect(result.current.isOpen).toBe(false)
    })

    it('has undefined syncBlz initially', () => {
      const { result } = renderHook(() => useSyncProgress())

      expect(result.current.syncBlz).toBeUndefined()
    })
  })

  describe('skip', () => {
    it('closes the modal', () => {
      const { result } = renderHook(() => useSyncProgress())

      // Open the modal first
      act(() => {
        result.current.startSync()
      })

      expect(result.current.isOpen).toBe(true)

      act(() => {
        result.current.skip()
      })

      expect(result.current.isOpen).toBe(false)
    })
  })

  describe('reset', () => {
    it('resets all state', () => {
      const { result } = renderHook(() => useSyncProgress())

      // Set up some state by starting a sync
      act(() => {
        result.current.startSync()
      })

      // Reset
      act(() => {
        result.current.reset()
      })

      expect(result.current.isOpen).toBe(false)
      expect(result.current.progress).toBeNull()
      expect(result.current.result).toBeNull()
      expect(result.current.error).toBe('')
      expect(result.current.syncBlz).toBeUndefined()
    })
  })

  describe('startSync', () => {
    it('opens modal and starts syncing', async () => {
      vi.mocked(api.runSyncStreaming).mockResolvedValue({
        success: true,
        total_imported: 10,
        total_skipped: 2,
        total_failed: 0,
        accounts_synced: 1,
      })

      const { result } = renderHook(() => useSyncProgress())

      await act(async () => {
        await result.current.startSync()
      })

      expect(result.current.isOpen).toBe(true)
      expect(api.runSyncStreaming).toHaveBeenCalled()
    })

    it('passes sync options to API', async () => {
      vi.mocked(api.runSyncStreaming).mockResolvedValue({
        success: true,
        total_imported: 10,
        total_skipped: 2,
        total_failed: 0,
        accounts_synced: 1,
      })

      const { result } = renderHook(() => useSyncProgress())

      await act(async () => {
        await result.current.startSync({ days: 90, blz: '12345678' })
      })

      expect(api.runSyncStreaming).toHaveBeenCalledWith(
        expect.any(Function),
        { days: 90, blz: '12345678' },
        expect.objectContaining({ signal: expect.any(AbortSignal) })
      )
    })

    it('sets result on success', async () => {
      const mockResult = {
        success: true,
        total_imported: 50,
        total_skipped: 5,
        total_failed: 0,
        accounts_synced: 2,
      }
      vi.mocked(api.runSyncStreaming).mockResolvedValue(mockResult)

      const { result } = renderHook(() => useSyncProgress())

      await act(async () => {
        await result.current.startSync()
      })

      expect(result.current.result).toBeDefined()
      expect(result.current.result?.total_imported).toBe(50)
      expect(result.current.result?.accounts_synced).toBe(2)
    })

    it('calls onSuccess callback', async () => {
      const onSuccess = vi.fn()
      vi.mocked(api.runSyncStreaming).mockResolvedValue({
        success: true,
        total_imported: 10,
        total_skipped: 2,
        total_failed: 0,
        accounts_synced: 1,
      })

      const { result } = renderHook(() => useSyncProgress({ onSuccess }))

      await act(async () => {
        await result.current.startSync()
      })

      expect(onSuccess).toHaveBeenCalled()
    })

    it('handles sync error', async () => {
      vi.mocked(api.runSyncStreaming).mockRejectedValue(new Error('Sync failed'))

      const { result } = renderHook(() => useSyncProgress())

      await act(async () => {
        await result.current.startSync()
      })

      expect(result.current.error).toBe('Sync failed')
    })

    it('calls onError callback on failure', async () => {
      const onError = vi.fn()
      vi.mocked(api.runSyncStreaming).mockRejectedValue(new Error('Sync failed'))

      const { result } = renderHook(() => useSyncProgress({ onError }))

      await act(async () => {
        await result.current.startSync()
      })

      expect(onError).toHaveBeenCalledWith('Sync failed')
    })
  })
})
