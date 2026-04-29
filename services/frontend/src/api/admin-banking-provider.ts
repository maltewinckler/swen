/**
 * Admin Banking Provider API
 *
 * Client for the /admin/fints_provider endpoints.
 * Abstracts FinTS provider management behind a "banking provider" concept.
 */
import { api } from './client'

export type BankingProviderMode = 'local' | 'api'

export interface BankingProviderStatus {
  local_configured: boolean
  local_active: boolean
  api_configured: boolean
  api_active: boolean
  active_provider: BankingProviderMode | null
}

export interface GeldstromApiConfigResponse {
  api_key_masked: string
  endpoint_url: string
  is_active: boolean
  last_updated: string | null
  last_updated_by: string | null
}

export async function getBankingProviderStatus(): Promise<BankingProviderStatus> {
  return api.get<BankingProviderStatus>('/admin/fints_provider/status')
}

export async function getGeldstromApiConfig(): Promise<GeldstromApiConfigResponse> {
  return api.get<GeldstromApiConfigResponse>('/admin/fints_provider/geldstrom-api')
}

export async function saveGeldstromApiConfig(
  apiKey: string,
  endpointUrl: string,
): Promise<{ message: string }> {
  return api.put<{ message: string }>('/admin/fints_provider/geldstrom-api', {
    api_key: apiKey,
    endpoint_url: endpointUrl,
  }, { timeout: 90_000 })
}

export async function activateProvider(
  mode: BankingProviderMode,
): Promise<{ message: string }> {
  return api.post<{ message: string }>('/admin/fints_provider/activate', { mode })
}
