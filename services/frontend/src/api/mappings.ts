import { api } from './client'

/**
 * Account mapping response
 */
export interface AccountMapping {
  id: string
  iban: string
  account_name: string
  accounting_account_id: string
  accounting_account_name: string | null
  accounting_account_number: string | null
  created_at: string | null
}

export interface MappingListResponse {
  mappings: AccountMapping[]
  count: number
}

/**
 * List all account mappings
 */
export async function listMappings(): Promise<MappingListResponse> {
  return api.get<MappingListResponse>('/mappings')
}

/**
 * Get mapping by IBAN
 */
export async function getMappingByIban(iban: string): Promise<AccountMapping> {
  return api.get<AccountMapping>(`/mappings/${encodeURIComponent(iban)}`)
}

/**
 * Account type for external accounts
 */
export type ExternalAccountType = 'asset' | 'liability'

/**
 * Request to create an external account mapping
 */
export interface CreateExternalAccountRequest {
  iban: string
  name: string
  currency?: string
  /** 'asset' for bank accounts/portfolios, 'liability' for credit cards/loans */
  account_type?: ExternalAccountType
  reconcile?: boolean
}

/**
 * Response after creating external account
 */
export interface CreateExternalAccountResponse {
  mapping: AccountMapping
  transactions_reconciled: number
  already_existed: boolean
}

/**
 * Create a mapping for an external bank account.
 *
 * Use this for accounts at banks that don't offer FinTS access.
 *
 * For ASSET accounts (default): Bank accounts, portfolios
 * - Transfers are tracked as internal transfers (Asset ↔ Asset)
 *
 * For LIABILITY accounts: Credit cards, loans
 * - Payments are tracked as liability payments (reduces what you owe)
 *
 * @param data - The external account details
 * @returns The created mapping and reconciliation info
 */
export async function createExternalAccount(
  data: CreateExternalAccountRequest
): Promise<CreateExternalAccountResponse> {
  return api.post<CreateExternalAccountResponse>('/mappings/external', {
    iban: data.iban,
    name: data.name,
    currency: data.currency ?? 'EUR',
    account_type: data.account_type ?? 'asset',
    reconcile: data.reconcile ?? true,
  })
}
