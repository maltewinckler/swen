import { api, LONG_TIMEOUT } from './client'

// Types
export interface BankCredential {
  credential_id: string
  blz: string
  label: string
}

export interface CredentialListResponse {
  credentials: BankCredential[]
  total: number
}

export interface BankLookupResponse {
  blz: string
  name: string
  bic: string | null
  city: string | null
  endpoint_url: string
}

export interface CredentialCreateRequest {
  blz: string
  username: string
  pin: string
  tan_method?: string | null
  tan_medium: string | null
}


export interface DiscoveredAccount {
  // Display info
  iban: string
  default_name: string

  // Full bank account data (needed for import)
  account_number: string
  account_holder: string
  account_type: string
  blz: string
  bic: string | null
  bank_name: string | null
  currency: string
  balance: string | null
  balance_date: string | null
}

export interface DiscoverAccountsResponse {
  blz: string
  accounts: DiscoveredAccount[]
}

/** Discovered account with user-injected custom name for import */
export interface BankAccountToImport extends DiscoveredAccount {
  custom_name: string | null
}

/** Account that was successfully imported into the DB */
export interface ImportedBankAccount extends BankAccountToImport {
  accounting_account_id: string | null
}

export interface SetupBankRequest {
  accounts: BankAccountToImport[]
}

export interface SetupBankResponse {
  blz: string
  imported_accounts: ImportedBankAccount[]
  success: boolean
  message: string
  warning: string | null
}

// TAN Method Discovery Types
export type TANMethodType = 'decoupled' | 'push' | 'sms' | 'chiptan' | 'photo_tan' | 'manual' | 'unknown'

export interface TANMethod {
  code: string
  name: string
  method_type: TANMethodType
  is_decoupled: boolean
  technical_id: string | null
  zka_id: string | null
  zka_version: string | null
  max_tan_length: number | null
  decoupled_max_polls: number | null
  decoupled_first_poll_delay: number | null
  decoupled_poll_interval: number | null
  supports_cancel: boolean
  supports_multiple_tan: boolean
}

export interface TANMethodQueryRequest {
  blz: string
}

export interface TANMethodsResponse {
  blz: string
  bank_name: string
  tan_methods: TANMethod[]
  default_method: string | null
}

// Bank Connection Details Types
export interface BankAccountDetail {
  iban: string
  account_name: string
  account_type: string
  currency: string
  bank_balance: string
  bank_balance_date: string | null
  bookkeeping_balance: string
  discrepancy: string
  is_reconciled: boolean
}

export interface BankConnectionDetails {
  blz: string
  bank_name: string | null
  accounts: BankAccountDetail[]
  total_accounts: number
  reconciled_count: number
  discrepancy_count: number
}

/**
 * List all stored bank credentials
 */
export async function listCredentials(): Promise<CredentialListResponse> {
  return api.get<CredentialListResponse>('/bank-connections/credentials')
}

/**
 * Lookup bank information by BLZ
 */
export async function lookupBank(blz: string): Promise<BankLookupResponse> {
  return api.get<BankLookupResponse>(`/bank-connections/lookup/${blz}`)
}

/**
 * Store new bank credentials
 */
export async function storeCredentials(data: CredentialCreateRequest): Promise<void> {
  await api.post<void>('/bank-connections/credentials', data)
}

/**
 * Update TAN method and medium for already-stored credentials
 */
export async function updateCredentialsTan(
  blz: string,
  data: { tan_method: string | null; tan_medium: string | null },
): Promise<void> {
  await api.patch<void>(`/bank-connections/credentials/${blz}`, data)
}

/**
 * Delete stored credentials by BLZ
 */
export async function deleteCredentials(blz: string): Promise<void> {
  await api.delete(`/bank-connections/credentials/${blz}`)
}

/**
 * Discover bank accounts without importing them
 * Returns accounts with default names for user review before import
 * Note: This can take up to 5 minutes if TAN approval is required
 */
export async function discoverBankAccounts(blz: string, options?: { signal?: AbortSignal }): Promise<DiscoverAccountsResponse> {
  return api.post<DiscoverAccountsResponse>(`/bank-connections/discover/${blz}`, undefined, { timeout: LONG_TIMEOUT, signal: options?.signal })
}

/**
 * Import discovered bank accounts into swen.
 *
 * Requires accounts from discoverBankAccounts() with optional custom names
 * embedded per account. This endpoint does NOT contact the bank — it is a
 * pure DB write and completes quickly.
 *
 * @param blz - Bank code (BLZ)
 * @param accounts - Discovered accounts with optional custom_name per account
 */
export async function setupBankAccounts(
  blz: string,
  accounts: BankAccountToImport[]
): Promise<SetupBankResponse> {
  const body: SetupBankRequest = { accounts }
  return api.post<SetupBankResponse>(`/integration/setup/${blz}`, body)
}

/**
 * Query available TAN methods from the bank
 *
 * This performs a lightweight sync dialog to discover which TAN methods
 * are supported. Does NOT require TAN approval, making it safe to call
 * before choosing a TAN method.
 *
 * Use during credential setup to:
 * 1. Validate credentials work
 * 2. Discover available TAN methods
 * 3. Let user choose their preferred method
 */
export async function queryTANMethods(data: TANMethodQueryRequest): Promise<TANMethodsResponse> {
  return api.post<TANMethodsResponse>('/bank-connections/tan-methods', data)
}

/**
 * Get bank connection details with all accounts and reconciliation status
 */
export async function getBankConnectionDetails(blz: string): Promise<BankConnectionDetails> {
  return api.get<BankConnectionDetails>(`/integration/reconciliation/${blz}`)
}
