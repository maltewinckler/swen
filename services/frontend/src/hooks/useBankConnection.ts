import { useReducer, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useSyncProgress } from './useSyncProgress'
import {
  lookupBank,
  storeCredentials,
  discoverBankAccounts,
  setupBankAccounts,
  queryTANMethods,
  ApiRequestError,
} from '@/api'
import type {
  BankLookupResponse,
  TANMethod,
  DiscoveredAccount
} from '@/api/credentials'

const FINTS_NOT_CONFIGURED_CODE = 'FINTS_NOT_CONFIGURED'

/** Map FINTS_NOT_CONFIGURED errors to a user-friendly message. */
function getUserMessage(err: unknown, fallback: string): string {
  if (err instanceof ApiRequestError && err.code === FINTS_NOT_CONFIGURED_CODE) {
    return 'FinTS is not configured. An administrator must set up the FinTS Product ID and institute directory in Settings → Administration before banking connections can be used.'
  }
  return err instanceof Error ? err.message : fallback
}

// ============================================================================
// Types
// ============================================================================

/** Connection step type - represents the current wizard step */
export type BankConnectionStep =
  | 'find_bank'
  | 'credentials'
  | 'tan_discovery'
  | 'review_accounts'
  | 'connecting'
  | 'initial_sync'
  | 'syncing'
  | 'success'
  | 'error'

/** Bank credentials form data */
export interface BankForm {
  blz: string
  username: string
  pin: string
  tan_method: string
  tan_medium: string
}

/** Result from successful bank connection */
export interface ConnectionResult {
  message: string
  accounts_imported: Array<{ iban: string; account_name: string }>
}

/** Options for the useBankConnection hook */
export interface UseBankConnectionOptions {
  onSuccess?: () => void
  onError?: (error: string) => void
}

// ============================================================================
// State Definition
// ============================================================================

interface BankConnectionState {
  // Current step
  step: BankConnectionStep

  // Form data
  bankForm: BankForm
  accountNames: Record<string, string>
  syncDays: number

  // Lookup results
  bankLookup: BankLookupResponse | null
  discoveredTanMethods: TANMethod[]
  discoveredAccounts: DiscoveredAccount[]
  connectionResult: ConnectionResult | null

  // Loading states
  isLookingUp: boolean
  isDiscoveringTan: boolean
  isDiscoveringAccounts: boolean

  // Error states
  bankLookupError: string
  tanDiscoveryError: string
  accountDiscoveryError: string
  bankError: string
}

const initialBankForm: BankForm = {
  blz: '',
  username: '',
  pin: '',
  tan_method: '',
  tan_medium: '',
}

const initialState: BankConnectionState = {
  step: 'find_bank',
  bankForm: initialBankForm,
  accountNames: {},
  syncDays: 90,
  bankLookup: null,
  discoveredTanMethods: [],
  discoveredAccounts: [],
  connectionResult: null,
  isLookingUp: false,
  isDiscoveringTan: false,
  isDiscoveringAccounts: false,
  bankLookupError: '',
  tanDiscoveryError: '',
  accountDiscoveryError: '',
  bankError: '',
}

// ============================================================================
// Actions
// ============================================================================

type BankConnectionAction =
  // Navigation
  | { type: 'SET_STEP'; payload: BankConnectionStep }
  | { type: 'RESET' }

  // Form updates
  | { type: 'SET_BANK_FORM'; payload: BankForm }
  | { type: 'SET_BANK_FORM_UPDATER'; payload: (prev: BankForm) => BankForm }
  | { type: 'UPDATE_BANK_FORM'; payload: Partial<BankForm> }
  | { type: 'SET_ACCOUNT_NAMES'; payload: Record<string, string> }
  | { type: 'SET_ACCOUNT_NAMES_UPDATER'; payload: (prev: Record<string, string>) => Record<string, string> }
  | { type: 'UPDATE_ACCOUNT_NAME'; payload: { iban: string; name: string } }
  | { type: 'SET_SYNC_DAYS'; payload: number }

  // Bank lookup
  | { type: 'LOOKUP_START' }
  | { type: 'LOOKUP_SUCCESS'; payload: BankLookupResponse }
  | { type: 'LOOKUP_ERROR'; payload: string }

  // TAN discovery
  | { type: 'TAN_DISCOVERY_START' }
  | { type: 'TAN_DISCOVERY_SUCCESS'; payload: { methods: TANMethod[]; defaultMethod: string; defaultMedium: string } }
  | { type: 'TAN_DISCOVERY_ERROR'; payload: string }

  // Account discovery
  | { type: 'ACCOUNT_DISCOVERY_START' }
  | { type: 'ACCOUNT_DISCOVERY_SUCCESS'; payload: { accounts: DiscoveredAccount[]; names: Record<string, string> } }
  | { type: 'ACCOUNT_DISCOVERY_ERROR'; payload: string }

  // Connection
  | { type: 'CONNECT_START' }
  | { type: 'CONNECT_SUCCESS'; payload: ConnectionResult }
  | { type: 'CONNECT_ERROR'; payload: string }

// ============================================================================
// Reducer
// ============================================================================

function bankConnectionReducer(
  state: BankConnectionState,
  action: BankConnectionAction
): BankConnectionState {
  switch (action.type) {
    // Navigation
    case 'SET_STEP':
      return { ...state, step: action.payload }

    case 'RESET':
      return initialState

    // Form updates
    case 'SET_BANK_FORM':
      return { ...state, bankForm: action.payload }

    case 'SET_BANK_FORM_UPDATER':
      return { ...state, bankForm: action.payload(state.bankForm) }

    case 'UPDATE_BANK_FORM':
      return { ...state, bankForm: { ...state.bankForm, ...action.payload } }

    case 'SET_ACCOUNT_NAMES':
      return { ...state, accountNames: action.payload }

    case 'SET_ACCOUNT_NAMES_UPDATER':
      return { ...state, accountNames: action.payload(state.accountNames) }

    case 'UPDATE_ACCOUNT_NAME':
      return {
        ...state,
        accountNames: { ...state.accountNames, [action.payload.iban]: action.payload.name },
      }

    case 'SET_SYNC_DAYS':
      return { ...state, syncDays: action.payload }

    // Bank lookup
    case 'LOOKUP_START':
      return { ...state, isLookingUp: true, bankLookupError: '' }

    case 'LOOKUP_SUCCESS':
      return {
        ...state,
        isLookingUp: false,
        bankLookup: action.payload,
        step: 'credentials',
      }

    case 'LOOKUP_ERROR':
      return { ...state, isLookingUp: false, bankLookupError: action.payload }

    // TAN discovery
    case 'TAN_DISCOVERY_START':
      return { ...state, isDiscoveringTan: true, tanDiscoveryError: '' }

    case 'TAN_DISCOVERY_SUCCESS':
      return {
        ...state,
        isDiscoveringTan: false,
        discoveredTanMethods: action.payload.methods,
        bankForm: {
          ...state.bankForm,
          tan_method: action.payload.defaultMethod,
          tan_medium: action.payload.defaultMedium,
        },
        step: 'tan_discovery',
      }

    case 'TAN_DISCOVERY_ERROR':
      return { ...state, isDiscoveringTan: false, tanDiscoveryError: action.payload }

    // Account discovery
    case 'ACCOUNT_DISCOVERY_START':
      return { ...state, isDiscoveringAccounts: true, accountDiscoveryError: '' }

    case 'ACCOUNT_DISCOVERY_SUCCESS':
      return {
        ...state,
        isDiscoveringAccounts: false,
        discoveredAccounts: action.payload.accounts,
        accountNames: action.payload.names,
        step: 'review_accounts',
      }

    case 'ACCOUNT_DISCOVERY_ERROR':
      return { ...state, isDiscoveringAccounts: false, accountDiscoveryError: action.payload }

    // Connection
    case 'CONNECT_START':
      return { ...state, step: 'connecting', bankError: '' }

    case 'CONNECT_SUCCESS':
      return { ...state, connectionResult: action.payload, step: 'initial_sync' }

    case 'CONNECT_ERROR':
      return { ...state, bankError: action.payload, step: 'error' }

    default:
      return state
  }
}

// ============================================================================
// Return Type (Grouped)
// ============================================================================

export interface UseBankConnectionReturn {
  /** Current wizard state */
  state: {
    step: BankConnectionStep
    bankLookup: BankLookupResponse | null
    discoveredTanMethods: TANMethod[]
    discoveredAccounts: DiscoveredAccount[]
    connectionResult: ConnectionResult | null
  }

  /** Form data and setters */
  form: {
    bankForm: BankForm
    setBankForm: (form: BankForm) => void
    updateBankForm: (partial: Partial<BankForm>) => void
    accountNames: Record<string, string>
    setAccountNames: (names: Record<string, string>) => void
    updateAccountName: (iban: string, name: string) => void
    syncDays: number
    setSyncDays: (days: number) => void
  }

  /** Loading states */
  loading: {
    isLookingUp: boolean
    isDiscoveringTan: boolean
    isDiscoveringAccounts: boolean
  }

  /** Error states */
  errors: {
    bankLookupError: string
    tanDiscoveryError: string
    accountDiscoveryError: string
    bankError: string
  }

  /** Sync-related state (from useSyncProgress) */
  sync: {
    progress: ReturnType<typeof useSyncProgress>['progress']
    result: ReturnType<typeof useSyncProgress>['result']
    error: string | null
  }

  /** Action handlers */
  actions: {
    setStep: (step: BankConnectionStep) => void
    handleBankLookup: () => Promise<void>
    handleDiscoverTanMethods: () => Promise<void>
    handleDiscoverAccounts: () => Promise<void>
    handleConnect: () => Promise<void>
    handleInitialSync: () => Promise<void>
    handleSkipSync: () => void
    reset: () => void
  }

  // Legacy flat access (for backward compatibility)
  step: BankConnectionStep
  bankForm: BankForm
  bankLookup: BankLookupResponse | null
  bankLookupError: string
  bankError: string
  isLookingUp: boolean
  discoveredTanMethods: TANMethod[]
  isDiscoveringTan: boolean
  tanDiscoveryError: string
  discoveredAccounts: DiscoveredAccount[]
  accountNames: Record<string, string>
  isDiscoveringAccounts: boolean
  accountDiscoveryError: string
  connectionResult: ConnectionResult | null
  syncDays: number
  syncProgress: ReturnType<typeof useSyncProgress>['progress']
  syncResult: ReturnType<typeof useSyncProgress>['result']
  syncError: string | null
  setStep: (step: BankConnectionStep) => void
  setBankForm: React.Dispatch<React.SetStateAction<BankForm>>
  setAccountNames: React.Dispatch<React.SetStateAction<Record<string, string>>>
  setSyncDays: (days: number) => void
  handleBankLookup: () => Promise<void>
  handleDiscoverTanMethods: () => Promise<void>
  handleDiscoverAccounts: () => Promise<void>
  handleConnect: () => Promise<void>
  handleInitialSync: () => Promise<void>
  handleSkipSync: () => void
  reset: () => void
}

// ============================================================================
// Hook Implementation
// ============================================================================

export function useBankConnection(
  options: UseBankConnectionOptions = {}
): UseBankConnectionReturn {
  const queryClient = useQueryClient()
  const [state, dispatch] = useReducer(bankConnectionReducer, initialState)

  // Sync progress hook
  const {
    progress: syncProgress,
    result: syncResult,
    error: syncError,
    startSync,
  } = useSyncProgress({
    onSuccess: () => {
      dispatch({ type: 'SET_STEP', payload: 'success' })
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['reconciliation'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['analytics'] })
      options.onSuccess?.()
    },
    onError: () => {
      dispatch({ type: 'SET_STEP', payload: 'error' })
      options.onError?.(syncError || 'Sync failed')
    },
  })

  // -------------------------------------------------------------------------
  // Form Setters (memoized for stability)
  // -------------------------------------------------------------------------

  const setStep = useCallback((step: BankConnectionStep) => {
    dispatch({ type: 'SET_STEP', payload: step })
  }, [])

  const setBankForm = useCallback((formOrUpdater: BankForm | ((prev: BankForm) => BankForm)) => {
    if (typeof formOrUpdater === 'function') {
      // Apply updater in reducer to avoid stale-closure bugs
      dispatch({ type: 'SET_BANK_FORM_UPDATER', payload: formOrUpdater })
    } else {
      dispatch({ type: 'SET_BANK_FORM', payload: formOrUpdater })
    }
  }, [])

  const updateBankForm = useCallback((partial: Partial<BankForm>) => {
    dispatch({ type: 'UPDATE_BANK_FORM', payload: partial })
  }, [])

  const setAccountNames = useCallback((namesOrUpdater: Record<string, string> | ((prev: Record<string, string>) => Record<string, string>)) => {
    if (typeof namesOrUpdater === 'function') {
      // Apply updater in reducer to avoid stale-closure bugs
      dispatch({ type: 'SET_ACCOUNT_NAMES_UPDATER', payload: namesOrUpdater })
    } else {
      dispatch({ type: 'SET_ACCOUNT_NAMES', payload: namesOrUpdater })
    }
  }, [])

  const updateAccountName = useCallback((iban: string, name: string) => {
    dispatch({ type: 'UPDATE_ACCOUNT_NAME', payload: { iban, name } })
  }, [])

  const setSyncDays = useCallback((days: number) => {
    dispatch({ type: 'SET_SYNC_DAYS', payload: days })
  }, [])

  const reset = useCallback(() => {
    dispatch({ type: 'RESET' })
  }, [])

  // -------------------------------------------------------------------------
  // Action Handlers
  // -------------------------------------------------------------------------

  const handleBankLookup = useCallback(async () => {
    if (!state.bankForm.blz || state.bankForm.blz.length !== 8) {
      dispatch({ type: 'LOOKUP_ERROR', payload: 'Please enter a valid 8-digit BLZ' })
      return
    }

    dispatch({ type: 'LOOKUP_START' })

    try {
      const result = await lookupBank(state.bankForm.blz)
      dispatch({ type: 'LOOKUP_SUCCESS', payload: result })
    } catch (err) {
      dispatch({ type: 'LOOKUP_ERROR', payload: getUserMessage(err, 'Bank not found') })
    }
  }, [state.bankForm.blz])

  const handleDiscoverTanMethods = useCallback(async () => {
    if (!state.bankForm.username || !state.bankForm.pin) {
      dispatch({ type: 'TAN_DISCOVERY_ERROR', payload: 'Please enter username and PIN' })
      return
    }

    dispatch({ type: 'TAN_DISCOVERY_START' })

    try {
      const result = await queryTANMethods({
        blz: state.bankForm.blz,
        username: state.bankForm.username,
        pin: state.bankForm.pin,
      })

      let defaultMethod = ''
      let defaultMedium = ''

      if (result.tan_methods.length > 0) {
        const defaultMethodCode = result.default_method || result.tan_methods[0].code
        const defaultMethodObj = result.tan_methods.find(m => m.code === defaultMethodCode) || result.tan_methods[0]
        defaultMethod = defaultMethodCode
        defaultMedium = defaultMethodObj.is_decoupled ? defaultMethodObj.name : ''
      }

      dispatch({
        type: 'TAN_DISCOVERY_SUCCESS',
        payload: { methods: result.tan_methods, defaultMethod, defaultMedium },
      })
    } catch (err) {
      dispatch({ type: 'TAN_DISCOVERY_ERROR', payload: err instanceof Error ? err.message : 'Failed to discover TAN methods' })
    }
  }, [state.bankForm.blz, state.bankForm.username, state.bankForm.pin])

  const handleDiscoverAccounts = useCallback(async () => {
    dispatch({ type: 'ACCOUNT_DISCOVERY_START' })

    try {
      // Store credentials first
      await storeCredentials({
        blz: state.bankForm.blz,
        username: state.bankForm.username,
        pin: state.bankForm.pin,
        tan_method: state.bankForm.tan_method,
        tan_medium: state.bankForm.tan_medium || null,
      })

      // Discover accounts
      const result = await discoverBankAccounts(state.bankForm.blz)

      // Initialize editable names with defaults
      const names: Record<string, string> = {}
      result.accounts.forEach(acc => {
        names[acc.iban] = acc.default_name
      })

      dispatch({
        type: 'ACCOUNT_DISCOVERY_SUCCESS',
        payload: { accounts: result.accounts, names },
      })
      queryClient.invalidateQueries({ queryKey: ['credentials'] })
    } catch (err) {
      dispatch({ type: 'ACCOUNT_DISCOVERY_ERROR', payload: err instanceof Error ? err.message : 'Failed to discover accounts' })
    }
  }, [state.bankForm, queryClient])

  const handleConnect = useCallback(async () => {
    dispatch({ type: 'CONNECT_START' })

    try {
      const result = await setupBankAccounts(
        state.bankForm.blz,
        state.discoveredAccounts,
        state.accountNames
      )
      dispatch({ type: 'CONNECT_SUCCESS', payload: result })
      queryClient.invalidateQueries({ queryKey: ['credentials'] })
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
      queryClient.invalidateQueries({ queryKey: ['reconciliation'] })
    } catch (err) {
      dispatch({ type: 'CONNECT_ERROR', payload: getUserMessage(err, 'Connection failed') })
    }
  }, [state.bankForm.blz, state.discoveredAccounts, state.accountNames, queryClient])

  const handleInitialSync = useCallback(async () => {
    dispatch({ type: 'SET_STEP', payload: 'syncing' })
    await startSync({
      days: state.syncDays,
      blz: state.bankForm.blz,
    })
  }, [state.syncDays, state.bankForm.blz, startSync])

  const handleSkipSync = useCallback(() => {
    dispatch({ type: 'SET_STEP', payload: 'success' })
    options.onSuccess?.()
  }, [options])

  // -------------------------------------------------------------------------
  // Return (Grouped + Legacy Flat)
  // -------------------------------------------------------------------------

  return {
    // Grouped access (new API)
    state: {
      step: state.step,
      bankLookup: state.bankLookup,
      discoveredTanMethods: state.discoveredTanMethods,
      discoveredAccounts: state.discoveredAccounts,
      connectionResult: state.connectionResult,
    },
    form: {
      bankForm: state.bankForm,
      setBankForm,
      updateBankForm,
      accountNames: state.accountNames,
      setAccountNames,
      updateAccountName,
      syncDays: state.syncDays,
      setSyncDays,
    },
    loading: {
      isLookingUp: state.isLookingUp,
      isDiscoveringTan: state.isDiscoveringTan,
      isDiscoveringAccounts: state.isDiscoveringAccounts,
    },
    errors: {
      bankLookupError: state.bankLookupError,
      tanDiscoveryError: state.tanDiscoveryError,
      accountDiscoveryError: state.accountDiscoveryError,
      bankError: state.bankError,
    },
    sync: {
      progress: syncProgress,
      result: syncResult,
      error: syncError,
    },
    actions: {
      setStep,
      handleBankLookup,
      handleDiscoverTanMethods,
      handleDiscoverAccounts,
      handleConnect,
      handleInitialSync,
      handleSkipSync,
      reset,
    },

    // Legacy flat access (backward compatibility)
    step: state.step,
    bankForm: state.bankForm,
    bankLookup: state.bankLookup,
    bankLookupError: state.bankLookupError,
    bankError: state.bankError,
    isLookingUp: state.isLookingUp,
    discoveredTanMethods: state.discoveredTanMethods,
    isDiscoveringTan: state.isDiscoveringTan,
    tanDiscoveryError: state.tanDiscoveryError,
    discoveredAccounts: state.discoveredAccounts,
    accountNames: state.accountNames,
    isDiscoveringAccounts: state.isDiscoveringAccounts,
    accountDiscoveryError: state.accountDiscoveryError,
    connectionResult: state.connectionResult,
    syncDays: state.syncDays,
    syncProgress,
    syncResult,
    syncError,
    setStep,
    setBankForm,
    setAccountNames,
    setSyncDays,
    handleBankLookup,
    handleDiscoverTanMethods,
    handleDiscoverAccounts,
    handleConnect,
    handleInitialSync,
    handleSkipSync,
    reset,
  }
}
