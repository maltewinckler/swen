/**
 * API Types - matches backend schemas
 */

// Auth types
export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
}

export interface AuthResponse {
  user: UserInfo
  access_token: string
  refresh_token: string | null  // Now sent as HttpOnly cookie, may be null in response
  expires_in: number
}

export interface UserInfo {
  id: string
  email: string
  role: 'user' | 'admin'
  created_at: string
}

// Admin types
export interface UserSummary {
  id: string
  email: string
  role: 'user' | 'admin'
  created_at: string
}

export interface CreateUserRequest {
  email: string
  password: string
  role?: 'user' | 'admin'
}

export interface UpdateRoleRequest {
  role: 'user' | 'admin'
}

// Account types - uppercase for frontend display logic
export type AccountType = 'ASSET' | 'LIABILITY' | 'EQUITY' | 'INCOME' | 'EXPENSE'

// Parent action for account updates
export type ParentAction = 'keep' | 'set' | 'remove'

export interface Account {
  id: string
  account_number: string  // Backend uses account_number
  name: string
  account_type: string  // Backend may return lowercase, normalize in frontend
  description?: string | null  // Description with examples for AI classification
  iban?: string | null  // IBAN for bank accounts or external accounts with IBAN mapping
  currency: string
  parent_id?: string | null
  is_active: boolean
  is_placeholder?: boolean
  created_at: string
}

// Matches backend AccountBalanceResponse
export interface AccountBalance {
  id: string
  name: string
  balance: string
  currency: string
}

// Account statistics (from GET /accounts/{id}/stats)
export interface AccountStats {
  account_id: string
  account_name: string
  account_number: string
  account_type: string
  currency: string
  balance: string
  balance_includes_drafts: boolean
  transaction_count: number
  posted_count: number
  draft_count: number
  total_debits: string
  total_credits: string
  net_flow: string
  first_transaction_date: string | null
  last_transaction_date: string | null
  period_days: number | null
  period_start: string | null
  period_end: string | null
}

// Transaction types
export type TransactionStatus = 'DRAFT' | 'POSTED' | 'VOIDED'

export interface JournalEntry {
  account_id: string
  account_name: string
  account_type: string
  debit: string | null
  credit: string | null
  currency: string
}

export interface AIResolutionMetadata {
  suggested_counter_account_id?: string
  suggested_counter_account_name?: string
  confidence?: number
  reasoning?: string
  model?: string
  resolved_at?: string
}

export interface TransactionMetadata {
  ai_resolution?: AIResolutionMetadata
  [key: string]: unknown
}

export interface Transaction {
  id: string
  date: string
  description: string
  counterparty: string | null
  counterparty_iban: string | null
  bank_reference: string | null
  source: 'bank_import' | 'manual' | 'opening_balance' | 'reversal'
  source_iban: string | null
  is_posted: boolean
  is_internal_transfer: boolean
  entries: JournalEntry[]
  created_at: string
  metadata: TransactionMetadata
}

// Simplified transaction for list view (matches backend TransactionListItemResponse)
export interface TransactionListItem {
  id: string
  short_id: string
  date: string
  description: string
  counterparty: string | null
  counter_account: string | null
  debit_account: string | null  // Account being debited (money goes TO)
  credit_account: string | null  // Account being credited (money comes FROM)
  amount: string
  currency: string
  is_income: boolean
  is_posted: boolean
  is_internal_transfer: boolean
}

export interface TransactionListResponse {
  transactions: TransactionListItem[]
  total: number
  draft_count: number
  posted_count: number
}

// Dashboard types
export interface DashboardSummary {
  total_income: string
  total_expenses: string
  net_income: string
  period_start: string
  period_end: string
}

// Analytics types
export interface TimeSeriesDataPoint {
  period: string
  period_label: string
  value: string
}

// Legacy format (used by some older API calls)
export interface LegacyTimeSeriesDataPoint {
  date: string
  value: string
}

export interface CategoryDataPoint {
  period: string
  period_label: string
  categories: Record<string, string>
  total: string
}

// Legacy format
export interface LegacyCategoryDataPoint {
  date: string
  category: string
  value: string
}

export interface TimeSeriesResponse {
  data_points: TimeSeriesDataPoint[]
  currency: string
  total: string
  average: string
  min_value: string
  max_value: string
}

export interface CategoryTimeSeriesResponse {
  data_points: CategoryDataPoint[]
  categories: string[]
  currency: string
  totals_by_category: Record<string, string>
}

// Legacy response format (for backward compatibility)
export interface LegacyTimeSeriesResponse {
  data: LegacyTimeSeriesDataPoint[]
  total: string
  currency: string
  period: {
    start: string
    end: string
  }
}

export interface LegacyCategoryTimeSeriesResponse {
  data: LegacyCategoryDataPoint[]
  categories: string[]
  currency: string
  period: {
    start: string
    end: string
  }
}

export interface BreakdownItem {
  category: string
  account_id: string
  amount: string
  percentage: string
}

export interface SpendingBreakdownResponse {
  period_label: string
  items: BreakdownItem[]
  total: string
  currency: string
  category_count: number
}

// Income breakdown (same structure as spending breakdown)
export interface IncomeBreakdownResponse {
  period_label: string
  items: BreakdownItem[]
  total: string
  currency: string
}

// Top expenses response
export interface TopExpenseItem {
  rank: number
  category: string
  account_id: string
  total_amount: string
  monthly_average: string
  percentage_of_total: string
  transaction_count: number
}

export interface TopExpensesResponse {
  period_label: string
  items: TopExpenseItem[]
  total_spending: string
  currency: string
  months_analyzed: number
}

// Month comparison response
export interface CategoryComparison {
  category: string
  current_amount: string
  previous_amount: string
  change_amount: string
  change_percentage: string
}

export interface MonthComparisonResponse {
  current_month: string
  previous_month: string
  currency: string
  current_income: string
  previous_income: string
  income_change: string
  income_change_percentage: string
  current_spending: string
  previous_spending: string
  spending_change: string
  spending_change_percentage: string
  current_net: string
  previous_net: string
  net_change: string
  net_change_percentage: string
  category_comparisons: CategoryComparison[]
}

// Pagination
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
  pages: number
}

// Sankey diagram types
export interface SankeyNode {
  id: string
  label: string
  category: 'income' | 'total' | 'expense' | 'savings'
  color: string | null
}

export interface SankeyLink {
  source: string
  target: string
  value: string
}

export interface SankeyResponse {
  nodes: SankeyNode[]
  links: SankeyLink[]
  currency: string
  period_label: string
  total_income: string
  total_expenses: string
  net_savings: string
}

// Error response
export interface ApiError {
  detail: string
}
