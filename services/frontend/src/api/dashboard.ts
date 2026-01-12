import type { DashboardSummary, AccountBalance } from '@/types/api'
import { api } from './client'
import { buildQueryString } from '@/lib/utils'

interface GetSummaryParams {
  days?: number
  start_date?: string
  end_date?: string
}

/**
 * Get dashboard summary
 */
export async function getDashboardSummary(params?: GetSummaryParams): Promise<DashboardSummary> {
  const query = buildQueryString(params ?? {})
  return api.get<DashboardSummary>(`/dashboard/summary${query}`)
}

interface DashboardBalancesResponse {
  balances: AccountBalance[]
  total_assets: string
}

/**
 * Get dashboard account balances
 */
export async function getDashboardBalances(): Promise<AccountBalance[]> {
  const response = await api.get<DashboardBalancesResponse>('/dashboard/balances')
  return response.balances
}
