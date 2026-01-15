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
  tan_method: string
  tan_medium: string | null
}

export interface CredentialCreateResponse {
  credential_id: string
  blz: string
  label: string
  message: string
}


export interface AccountImportInfo {
  iban: string
  account_name: string
  balance: string | null
  currency: string
  accounting_account_id: string | null
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
  bank_name: string
  accounts: DiscoveredAccount[]
}

export interface SetupBankRequest {
  accounts?: DiscoveredAccount[]  // Pass accounts from discover to skip TAN
  account_names?: Record<string, string>  // IBAN -> custom account name
}

export interface SetupBankResponse {
  success: boolean
  bank_code: string
  accounts_imported: AccountImportInfo[]
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
  username: string
  pin: string
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
  return api.get<CredentialListResponse>('/credentials')
}

/**
 * Lookup bank information by BLZ
 */
export async function lookupBank(blz: string): Promise<BankLookupResponse> {
  return api.get<BankLookupResponse>(`/credentials/lookup/${blz}`)
}

/**
 * Store new bank credentials
 */
export async function storeCredentials(data: CredentialCreateRequest): Promise<CredentialCreateResponse> {
  return api.post<CredentialCreateResponse>('/credentials', data)
}

/**
 * Delete stored credentials by BLZ
 */
export async function deleteCredentials(blz: string): Promise<void> {
  await api.delete(`/credentials/${blz}`)
}

/**
 * Discover bank accounts without importing them
 * Returns accounts with default names for user review before import
 * Note: This can take up to 5 minutes if TAN approval is required
 */
export async function discoverBankAccounts(blz: string): Promise<DiscoverAccountsResponse> {
  return api.post<DiscoverAccountsResponse>(`/credentials/${blz}/discover-accounts`, undefined, { timeout: LONG_TIMEOUT })
}

/**
 * Setup bank connection and import accounts
 *
 * @param blz - Bank code (BLZ)
 * @param accounts - Accounts from discoverBankAccounts() - if provided, skips TAN
 * @param accountNames - Optional IBAN -> custom name mapping
 */
export async function setupBankAccounts(
  blz: string,
  accounts?: DiscoveredAccount[],
  accountNames?: Record<string, string>
): Promise<SetupBankResponse> {
  const body: SetupBankRequest = {}
  if (accounts) {
    body.accounts = accounts
  }
  if (accountNames) {
    body.account_names = accountNames
  }
  // If accounts provided, no TAN needed - use normal timeout
  const timeout = accounts ? undefined : LONG_TIMEOUT
  return api.post<SetupBankResponse>(`/credentials/${blz}/setup`, Object.keys(body).length > 0 ? body : undefined, { timeout: timeout ?? LONG_TIMEOUT })
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
  return api.post<TANMethodsResponse>('/credentials/tan-methods', data)
}

/**
 * Get bank connection details with all accounts and reconciliation status
 */
export async function getBankConnectionDetails(blz: string): Promise<BankConnectionDetails> {
  return api.get<BankConnectionDetails>(`/credentials/${blz}/accounts`)
}
