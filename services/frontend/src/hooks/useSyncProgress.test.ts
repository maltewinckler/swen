import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useSyncProgress } from './useSyncProgress'
import * as api from '@/api'

// Mock the API module
vi.mock('@/api', () => ({
  getSyncRecommendation: vi.fn(),
  runSyncStreaming: vi.fn(),
}))

describe('useSyncProgress', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('initial state', () => {
    it('starts in idle step', () => {
      const { result } = renderHook(() => useSyncProgress())

      expect(result.current.step).toBe('idle')
    })

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

    it('has default first sync days of 90', () => {
      const { result } = renderHook(() => useSyncProgress())

      expect(result.current.firstSyncDays).toBe(90)
    })
  })

  describe('open', () => {
    it('sets isOpen to true', () => {
      const { result } = renderHook(() => useSyncProgress())

      act(() => {
        result.current.open()
      })

      expect(result.current.isOpen).toBe(true)
    })

    it('stores BLZ when provided', () => {
      const { result } = renderHook(() => useSyncProgress())

      act(() => {
        result.current.open('12345678')
      })

      expect(result.current.syncBlz).toBe('12345678')
    })

    it('resets step to idle', () => {
      const { result } = renderHook(() => useSyncProgress())

      act(() => {
        result.current.open()
      })

      expect(result.current.step).toBe('idle')
    })
  })

  describe('skip', () => {
    it('closes the modal', () => {
      const { result } = renderHook(() => useSyncProgress())

      act(() => {
        result.current.open()
      })

      expect(result.current.isOpen).toBe(true)

      act(() => {
        result.current.skip()
      })

      expect(result.current.isOpen).toBe(false)
    })

    it('sets step to idle', () => {
      const { result } = renderHook(() => useSyncProgress())

      act(() => {
        result.current.skip()
      })

      expect(result.current.step).toBe('idle')
    })
  })

  describe('reset', () => {
    it('resets all state', () => {
      const { result } = renderHook(() => useSyncProgress())

      // Set up some state
      act(() => {
        result.current.open('12345678')
        result.current.setFirstSyncDays(365)
      })

      // Reset
      act(() => {
        result.current.reset()
      })

      expect(result.current.isOpen).toBe(false)
      expect(result.current.step).toBe('idle')
      expect(result.current.progress).toBeNull()
      expect(result.current.result).toBeNull()
      expect(result.current.error).toBe('')
      expect(result.current.firstSyncDays).toBe(90)
      expect(result.current.syncBlz).toBeUndefined()
    })
  })

  describe('setFirstSyncDays', () => {
    it('updates first sync days', () => {
      const { result } = renderHook(() => useSyncProgress())

      act(() => {
        result.current.setFirstSyncDays(365)
      })

      expect(result.current.firstSyncDays).toBe(365)
    })
  })

  describe('checkAndSync', () => {
    it('opens modal and checks recommendation', async () => {
      const mockRecommendation = {
        accounts: [{ iban: 'DE123', is_first_sync: false }],
      }
      vi.mocked(api.getSyncRecommendation).mockResolvedValue(mockRecommendation)
      vi.mocked(api.runSyncStreaming).mockResolvedValue({
        success: true,
        total_imported: 10,
        total_skipped: 2,
        total_failed: 0,
        accounts_synced: 1,
      })

      const { result } = renderHook(() => useSyncProgress())

      await act(async () => {
        await result.current.checkAndSync()
      })

      expect(result.current.isOpen).toBe(true)
      expect(api.getSyncRecommendation).toHaveBeenCalled()
    })

    it('shows first sync prompt when first sync is needed', async () => {
      const mockRecommendation = {
        accounts: [{ iban: 'DE123', is_first_sync: true }],
      }
      vi.mocked(api.getSyncRecommendation).mockResolvedValue(mockRecommendation)

      const { result } = renderHook(() => useSyncProgress())

      await act(async () => {
        await result.current.checkAndSync()
      })

      expect(result.current.step).toBe('first_sync_prompt')
    })

    it('starts sync directly when no first sync needed', async () => {
      const mockRecommendation = {
        accounts: [{ iban: 'DE123', is_first_sync: false }],
      }
      vi.mocked(api.getSyncRecommendation).mockResolvedValue(mockRecommendation)
      vi.mocked(api.runSyncStreaming).mockResolvedValue({
        success: true,
        total_imported: 10,
        total_skipped: 2,
        total_failed: 0,
        accounts_synced: 1,
      })

      const { result } = renderHook(() => useSyncProgress())

      await act(async () => {
        await result.current.checkAndSync()
      })

      expect(api.runSyncStreaming).toHaveBeenCalled()
    })

    it('filters accounts by BLZ when provided', async () => {
      const mockRecommendation = {
        accounts: [
          { iban: 'DE12123456780000001234', is_first_sync: true },
          { iban: 'DE12999999990000005678', is_first_sync: false },
        ],
      }
      vi.mocked(api.getSyncRecommendation).mockResolvedValue(mockRecommendation)
      vi.mocked(api.runSyncStreaming).mockResolvedValue({
        success: true,
        total_imported: 0,
        total_skipped: 0,
        total_failed: 0,
        accounts_synced: 0,
      })

      const { result } = renderHook(() => useSyncProgress())

      await act(async () => {
        await result.current.checkAndSync('12345678')
      })

      // Should show first sync prompt because the matching account needs first sync
      expect(result.current.step).toBe('first_sync_prompt')
    })

    it('handles check error', async () => {
      vi.mocked(api.getSyncRecommendation).mockRejectedValue(new Error('Network error'))

      const { result } = renderHook(() => useSyncProgress())

      await act(async () => {
        await result.current.checkAndSync()
      })

      expect(result.current.step).toBe('error')
      expect(result.current.error).toBe('Network error')
    })
  })

  describe('startSync', () => {
    it('transitions to syncing step', async () => {
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

      // Should end in success after completing
      expect(result.current.step).toBe('success')
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

      expect(result.current.step).toBe('error')
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

  describe('confirmFirstSync', () => {
    it('starts sync with selected days', async () => {
      vi.mocked(api.runSyncStreaming).mockResolvedValue({
        success: true,
        total_imported: 10,
        total_skipped: 2,
        total_failed: 0,
        accounts_synced: 1,
      })

      const { result } = renderHook(() => useSyncProgress())

      act(() => {
        result.current.setFirstSyncDays(365)
      })

      await act(async () => {
        result.current.confirmFirstSync()
      })

      expect(api.runSyncStreaming).toHaveBeenCalledWith(
        expect.any(Function),
        { days: 365 },
        expect.objectContaining({ signal: expect.any(AbortSignal) })
      )
    })

    it('includes BLZ when set', async () => {
      vi.mocked(api.runSyncStreaming).mockResolvedValue({
        success: true,
        total_imported: 10,
        total_skipped: 2,
        total_failed: 0,
        accounts_synced: 1,
      })

      const { result } = renderHook(() => useSyncProgress())

      act(() => {
        result.current.open('12345678')
        result.current.setFirstSyncDays(90)
      })

      await act(async () => {
        result.current.confirmFirstSync()
      })

      expect(api.runSyncStreaming).toHaveBeenCalledWith(
        expect.any(Function),
        { days: 90, blz: '12345678' },
        expect.objectContaining({ signal: expect.any(AbortSignal) })
      )
    })
  })
})
