import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useBankConnection } from './useBankConnection'
import * as api from '@/api'
import type { ReactNode } from 'react'

// Mock the API module
vi.mock('@/api', () => ({
  lookupBank: vi.fn(),
  storeCredentials: vi.fn(),
  discoverBankAccounts: vi.fn(),
  setupBankAccounts: vi.fn(),
  queryTANMethods: vi.fn(),
}))

// Mock useSyncProgress
vi.mock('./useSyncProgress', () => ({
  useSyncProgress: () => ({
    progress: null,
    result: null,
    error: null,
    startSync: vi.fn(),
  }),
}))

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    )
  }
}

describe('useBankConnection', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('initial state', () => {
    it('starts with find_bank step', () => {
      const { result } = renderHook(() => useBankConnection(), {
        wrapper: createWrapper(),
      })

      expect(result.current.step).toBe('find_bank')
    })

    it('has empty bank form', () => {
      const { result } = renderHook(() => useBankConnection(), {
        wrapper: createWrapper(),
      })

      expect(result.current.bankForm).toEqual({
        blz: '',
        username: '',
        pin: '',
        tan_method: '',
        tan_medium: '',
      })
    })

    it('has no bank lookup result', () => {
      const { result } = renderHook(() => useBankConnection(), {
        wrapper: createWrapper(),
      })

      expect(result.current.bankLookup).toBeNull()
    })

    it('has empty discovered accounts', () => {
      const { result } = renderHook(() => useBankConnection(), {
        wrapper: createWrapper(),
      })

      expect(result.current.discoveredAccounts).toEqual([])
    })

    it('has default sync days of 90', () => {
      const { result } = renderHook(() => useBankConnection(), {
        wrapper: createWrapper(),
      })

      expect(result.current.syncDays).toBe(90)
    })
  })

  describe('setBankForm', () => {
    it('updates bank form values', () => {
      const { result } = renderHook(() => useBankConnection(), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.setBankForm(prev => ({
          ...prev,
          blz: '12345678',
          username: 'testuser',
        }))
      })

      expect(result.current.bankForm.blz).toBe('12345678')
      expect(result.current.bankForm.username).toBe('testuser')
    })
  })

  describe('handleBankLookup', () => {
    it('validates BLZ length', async () => {
      const { result } = renderHook(() => useBankConnection(), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.setBankForm(prev => ({ ...prev, blz: '1234' }))
      })

      await act(async () => {
        await result.current.handleBankLookup()
      })

      expect(result.current.bankLookupError).toBe('Please enter a valid 8-digit BLZ')
      expect(api.lookupBank).not.toHaveBeenCalled()
    })

    it('calls lookupBank API with valid BLZ', async () => {
      const mockBankData = { name: 'Test Bank', blz: '12345678', fints_url: 'https://fints.test.de' }
      vi.mocked(api.lookupBank).mockResolvedValue(mockBankData)

      const { result } = renderHook(() => useBankConnection(), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.setBankForm(prev => ({ ...prev, blz: '12345678' }))
      })

      await act(async () => {
        await result.current.handleBankLookup()
      })

      expect(api.lookupBank).toHaveBeenCalledWith('12345678')
      expect(result.current.bankLookup).toEqual(mockBankData)
      expect(result.current.step).toBe('credentials')
    })

    it('handles lookup error', async () => {
      vi.mocked(api.lookupBank).mockRejectedValue(new Error('Bank not found'))

      const { result } = renderHook(() => useBankConnection(), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.setBankForm(prev => ({ ...prev, blz: '99999999' }))
      })

      await act(async () => {
        await result.current.handleBankLookup()
      })

      expect(result.current.bankLookupError).toBe('Bank not found')
      expect(result.current.step).toBe('find_bank')
    })

    it('sets isLookingUp during lookup', async () => {
      let resolvePromise: (value: unknown) => void
      const lookupPromise = new Promise(resolve => {
        resolvePromise = resolve
      })
      vi.mocked(api.lookupBank).mockReturnValue(lookupPromise as Promise<unknown>)

      const { result } = renderHook(() => useBankConnection(), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.setBankForm(prev => ({ ...prev, blz: '12345678' }))
      })

      // Start lookup without waiting
      act(() => {
        result.current.handleBankLookup()
      })

      // Should be loading
      expect(result.current.isLookingUp).toBe(true)

      // Resolve and wait
      await act(async () => {
        resolvePromise!({ name: 'Bank', blz: '12345678', fints_url: 'https://test.de' })
        await lookupPromise
      })

      expect(result.current.isLookingUp).toBe(false)
    })
  })

  describe('handleDiscoverTanMethods', () => {
    it('validates required credentials', async () => {
      const { result } = renderHook(() => useBankConnection(), {
        wrapper: createWrapper(),
      })

      await act(async () => {
        await result.current.handleDiscoverTanMethods()
      })

      expect(result.current.tanDiscoveryError).toBe('Please enter username and PIN')
    })

    it('calls queryTANMethods API with credentials', async () => {
      const mockTanMethods = {
        tan_methods: [
          { code: '920', name: 'Push TAN', is_decoupled: true },
        ],
        default_method: '920',
      }
      vi.mocked(api.queryTANMethods).mockResolvedValue(mockTanMethods)

      const { result } = renderHook(() => useBankConnection(), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.setBankForm({
          blz: '12345678',
          username: 'testuser',
          pin: 'secret',
          tan_method: '',
          tan_medium: '',
        })
      })

      await act(async () => {
        await result.current.handleDiscoverTanMethods()
      })

      expect(api.queryTANMethods).toHaveBeenCalledWith({
        blz: '12345678',
        username: 'testuser',
        pin: 'secret',
      })
      expect(result.current.discoveredTanMethods).toEqual(mockTanMethods.tan_methods)
      expect(result.current.step).toBe('tan_discovery')
    })

    it('selects default TAN method', async () => {
      const mockTanMethods = {
        tan_methods: [
          { code: '900', name: 'SMS TAN', is_decoupled: false },
          { code: '920', name: 'Push TAN', is_decoupled: true },
        ],
        default_method: '920',
      }
      vi.mocked(api.queryTANMethods).mockResolvedValue(mockTanMethods)

      const { result } = renderHook(() => useBankConnection(), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.setBankForm({
          blz: '12345678',
          username: 'testuser',
          pin: 'secret',
          tan_method: '',
          tan_medium: '',
        })
      })

      await act(async () => {
        await result.current.handleDiscoverTanMethods()
      })

      expect(result.current.bankForm.tan_method).toBe('920')
    })
  })

  describe('handleDiscoverAccounts', () => {
    it('stores credentials and discovers accounts', async () => {
      const mockAccounts = {
        accounts: [
          { iban: 'DE123', default_name: 'Girokonto', balance: '1000.00', currency: 'EUR' },
        ],
      }
      vi.mocked(api.storeCredentials).mockResolvedValue({ message: 'ok' })
      vi.mocked(api.discoverBankAccounts).mockResolvedValue(mockAccounts)

      const { result } = renderHook(() => useBankConnection(), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.setBankForm({
          blz: '12345678',
          username: 'testuser',
          pin: 'secret',
          tan_method: '920',
          tan_medium: 'Push TAN',
        })
      })

      await act(async () => {
        await result.current.handleDiscoverAccounts()
      })

      expect(api.storeCredentials).toHaveBeenCalledWith({
        blz: '12345678',
        username: 'testuser',
        pin: 'secret',
        tan_method: '920',
        tan_medium: 'Push TAN',
      })
      expect(api.discoverBankAccounts).toHaveBeenCalledWith('12345678')
      expect(result.current.discoveredAccounts).toEqual(mockAccounts.accounts)
      expect(result.current.step).toBe('review_accounts')
    })

    it('initializes account names with defaults', async () => {
      const mockAccounts = {
        accounts: [
          { iban: 'DE123', default_name: 'Girokonto', balance: '1000.00', currency: 'EUR' },
          { iban: 'DE456', default_name: 'Sparkonto', balance: '5000.00', currency: 'EUR' },
        ],
      }
      vi.mocked(api.storeCredentials).mockResolvedValue({ message: 'ok' })
      vi.mocked(api.discoverBankAccounts).mockResolvedValue(mockAccounts)

      const { result } = renderHook(() => useBankConnection(), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.setBankForm({
          blz: '12345678',
          username: 'testuser',
          pin: 'secret',
          tan_method: '920',
          tan_medium: '',
        })
      })

      await act(async () => {
        await result.current.handleDiscoverAccounts()
      })

      expect(result.current.accountNames).toEqual({
        DE123: 'Girokonto',
        DE456: 'Sparkonto',
      })
    })
  })

  describe('handleConnect', () => {
    it('sets up accounts and transitions to initial_sync', async () => {
      const mockResult = {
        message: 'Accounts imported',
        accounts_imported: [{ iban: 'DE123', account_name: 'Checking' }],
      }
      vi.mocked(api.setupBankAccounts).mockResolvedValue(mockResult)

      const { result } = renderHook(() => useBankConnection(), {
        wrapper: createWrapper(),
      })

      // Set up required state
      act(() => {
        result.current.setBankForm({
          blz: '12345678',
          username: 'testuser',
          pin: 'secret',
          tan_method: '920',
          tan_medium: '',
        })
      })

      // Simulate discovered accounts (normally set by handleDiscoverAccounts)
      // We need to manually set this for the test

      await act(async () => {
        await result.current.handleConnect()
      })

      expect(result.current.step).toBe('initial_sync')
      expect(result.current.connectionResult).toEqual(mockResult)
    })

    it('handles connection error', async () => {
      vi.mocked(api.setupBankAccounts).mockRejectedValue(new Error('Connection failed'))

      const { result } = renderHook(() => useBankConnection(), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.setBankForm({
          blz: '12345678',
          username: 'testuser',
          pin: 'secret',
          tan_method: '920',
          tan_medium: '',
        })
      })

      await act(async () => {
        await result.current.handleConnect()
      })

      expect(result.current.step).toBe('error')
      expect(result.current.bankError).toBe('Connection failed')
    })
  })

  describe('handleSkipSync', () => {
    it('transitions to success state', () => {
      const onSuccess = vi.fn()
      const { result } = renderHook(() => useBankConnection({ onSuccess }), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.handleSkipSync()
      })

      expect(result.current.step).toBe('success')
      expect(onSuccess).toHaveBeenCalled()
    })
  })

  describe('setSyncDays', () => {
    it('updates sync days', () => {
      const { result } = renderHook(() => useBankConnection(), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.setSyncDays(365)
      })

      expect(result.current.syncDays).toBe(365)
    })
  })

  describe('reset', () => {
    it('resets all state to initial values', async () => {
      vi.mocked(api.lookupBank).mockResolvedValue({
        name: 'Test Bank',
        blz: '12345678',
        fints_url: 'https://test.de',
      })

      const { result } = renderHook(() => useBankConnection(), {
        wrapper: createWrapper(),
      })

      // Modify some state
      act(() => {
        result.current.setBankForm(prev => ({ ...prev, blz: '12345678' }))
      })

      await act(async () => {
        await result.current.handleBankLookup()
      })

      // Reset
      act(() => {
        result.current.reset()
      })

      expect(result.current.step).toBe('find_bank')
      expect(result.current.bankForm.blz).toBe('')
      expect(result.current.bankLookup).toBeNull()
      expect(result.current.syncDays).toBe(90)
    })
  })

  describe('setStep', () => {
    it('allows manual step changes', () => {
      const { result } = renderHook(() => useBankConnection(), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.setStep('credentials')
      })

      expect(result.current.step).toBe('credentials')
    })
  })

  describe('setAccountNames', () => {
    it('updates account names', () => {
      const { result } = renderHook(() => useBankConnection(), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.setAccountNames({
          DE123: 'My Checking Account',
          DE456: 'My Savings',
        })
      })

      expect(result.current.accountNames).toEqual({
        DE123: 'My Checking Account',
        DE456: 'My Savings',
      })
    })
  })
})
