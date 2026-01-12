import type {
  TimeSeriesResponse,
  CategoryTimeSeriesResponse,
  SpendingBreakdownResponse,
  IncomeBreakdownResponse,
  TopExpensesResponse,
  MonthComparisonResponse,
  SankeyResponse,
} from '@/types/api'
import { api } from './client'
import { buildQueryString } from '@/lib/utils'

interface AnalyticsParams {
  months?: number
  end_month?: string
  include_drafts?: boolean
}

interface BreakdownParams {
  month?: string
  days?: number
  include_drafts?: boolean
}

// =============================================================================
// Spending Endpoints
// =============================================================================

/**
 * Get spending over time by category
 */
export async function getSpendingOverTime(params?: AnalyticsParams): Promise<CategoryTimeSeriesResponse> {
  const query = buildQueryString({
    months: params?.months,
    end_month: params?.end_month,
    include_drafts: params?.include_drafts,
  })
  return api.get<CategoryTimeSeriesResponse>(`/analytics/spending/over-time${query}`)
}

/**
 * Get spending breakdown by category
 */
export async function getSpendingBreakdown(params?: BreakdownParams): Promise<SpendingBreakdownResponse> {
  const query = buildQueryString({
    month: params?.month,
    days: params?.days,
    include_drafts: params?.include_drafts,
  })
  return api.get<SpendingBreakdownResponse>(`/analytics/spending/breakdown${query}`)
}

/**
 * Get top expense categories
 */
export async function getTopExpenses(params?: {
  months?: number
  top_n?: number
  end_month?: string
  include_drafts?: boolean
}): Promise<TopExpensesResponse> {
  const query = buildQueryString({
    months: params?.months,
    top_n: params?.top_n,
    end_month: params?.end_month,
    include_drafts: params?.include_drafts,
  })
  return api.get<TopExpensesResponse>(`/analytics/spending/top${query}`)
}

/**
 * Get spending for a single expense account over time
 */
export async function getSingleAccountSpending(
  accountId: string,
  params?: AnalyticsParams
): Promise<TimeSeriesResponse> {
  const query = buildQueryString({
    months: params?.months,
    end_month: params?.end_month,
    include_drafts: params?.include_drafts,
  })
  return api.get<TimeSeriesResponse>(`/analytics/spending/account/${accountId}/over-time${query}`)
}

// =============================================================================
// Income Endpoints
// =============================================================================

/**
 * Get income over time
 */
export async function getIncomeOverTime(params?: AnalyticsParams): Promise<TimeSeriesResponse> {
  const query = buildQueryString({
    months: params?.months,
    end_month: params?.end_month,
    include_drafts: params?.include_drafts,
  })
  return api.get<TimeSeriesResponse>(`/analytics/income/over-time${query}`)
}

/**
 * Get income breakdown by source
 */
export async function getIncomeBreakdown(params?: BreakdownParams): Promise<IncomeBreakdownResponse> {
  const query = buildQueryString({
    month: params?.month,
    days: params?.days,
    include_drafts: params?.include_drafts,
  })
  return api.get<IncomeBreakdownResponse>(`/analytics/income/breakdown${query}`)
}

// =============================================================================
// Financial Health Endpoints
// =============================================================================

/**
 * Get net income over time (income - expenses)
 */
export async function getNetIncomeOverTime(params?: AnalyticsParams): Promise<TimeSeriesResponse> {
  const query = buildQueryString({
    months: params?.months,
    end_month: params?.end_month,
    include_drafts: params?.include_drafts,
  })
  return api.get<TimeSeriesResponse>(`/analytics/net-income/over-time${query}`)
}

/**
 * Get savings rate over time (percentage of income saved)
 */
export async function getSavingsRate(params?: AnalyticsParams): Promise<TimeSeriesResponse> {
  const query = buildQueryString({
    months: params?.months,
    end_month: params?.end_month,
    include_drafts: params?.include_drafts,
  })
  return api.get<TimeSeriesResponse>(`/analytics/savings-rate/over-time${query}`)
}

/**
 * Get net worth over time (assets - liabilities)
 */
export async function getNetWorth(params?: AnalyticsParams): Promise<TimeSeriesResponse> {
  const query = buildQueryString({
    months: params?.months,
    end_month: params?.end_month,
    include_drafts: params?.include_drafts,
  })
  return api.get<TimeSeriesResponse>(`/analytics/net-worth/over-time${query}`)
}

// =============================================================================
// Balance Endpoints
// =============================================================================

/**
 * Get balance history over time
 */
export async function getBalanceHistory(params?: AnalyticsParams): Promise<CategoryTimeSeriesResponse> {
  const query = buildQueryString({
    months: params?.months,
    end_month: params?.end_month,
    include_drafts: params?.include_drafts,
  })
  return api.get<CategoryTimeSeriesResponse>(`/analytics/balances/over-time${query}`)
}

// =============================================================================
// Comparison Endpoints
// =============================================================================

/**
 * Get month-over-month comparison
 */
export async function getMonthComparison(params?: {
  month?: string
  include_drafts?: boolean
}): Promise<MonthComparisonResponse> {
  const query = buildQueryString({
    month: params?.month,
    include_drafts: params?.include_drafts,
  })
  return api.get<MonthComparisonResponse>(`/analytics/comparison/month-over-month${query}`)
}

// =============================================================================
// Cash Flow Visualization Endpoints
// =============================================================================

/**
 * Get Sankey diagram data for cash flow visualization
 */
export async function getSankeyData(params?: BreakdownParams): Promise<SankeyResponse> {
  const query = buildQueryString({
    month: params?.month,
    days: params?.days,
    include_drafts: params?.include_drafts,
  })
  return api.get<SankeyResponse>(`/analytics/sankey${query}`)
}
