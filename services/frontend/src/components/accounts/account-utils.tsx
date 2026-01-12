/**
 * Account Type Utilities
 *
 * Shared utilities for account type handling across the app.
 * Includes icon mapping, color schemes, and type normalization.
 */

import {
  Wallet,
  CreditCard,
  TrendingUp,
  TrendingDown,
  DollarSign,
} from 'lucide-react'

// =============================================================================
// Types
// =============================================================================

/** Normalized account type (always uppercase) */
export type NormalizedAccountType = 'ASSET' | 'LIABILITY' | 'INCOME' | 'EXPENSE' | 'EQUITY'

// =============================================================================
// Type Normalization
// =============================================================================

/**
 * Normalize account type string to uppercase.
 * Handles both API responses (lowercase) and internal usage (uppercase).
 */
export function normalizeAccountType(type: string): NormalizedAccountType {
  return type.toUpperCase() as NormalizedAccountType
}

// =============================================================================
// Icons
// =============================================================================

/**
 * Get the appropriate icon component for an account type.
 */
export function getAccountIcon(type: NormalizedAccountType) {
  switch (type) {
    case 'ASSET':
      return <Wallet className="h-5 w-5" />
    case 'LIABILITY':
      return <CreditCard className="h-5 w-5" />
    case 'INCOME':
      return <TrendingUp className="h-5 w-5" />
    case 'EXPENSE':
      return <TrendingDown className="h-5 w-5" />
    case 'EQUITY':
      return <DollarSign className="h-5 w-5" />
    default:
      return <Wallet className="h-5 w-5" />
  }
}

// =============================================================================
// Colors
// =============================================================================

/**
 * Get color classes for an account type (text + background).
 */
export function getAccountColor(type: NormalizedAccountType): string {
  switch (type) {
    case 'ASSET':
      return 'text-accent-primary bg-accent-primary/10'
    case 'LIABILITY':
      return 'text-accent-danger bg-accent-danger/10'
    case 'INCOME':
      return 'text-accent-success bg-accent-success/10'
    case 'EXPENSE':
      return 'text-chart-1 bg-chart-1/10'
    case 'EQUITY':
      return 'text-accent-info bg-accent-info/10'
    default:
      return 'text-text-muted bg-bg-elevated'
  }
}

// =============================================================================
// Labels
// =============================================================================

/** Human-readable labels for account types */
export const accountTypeLabels: Record<NormalizedAccountType, string> = {
  ASSET: 'Assets',
  LIABILITY: 'Liabilities',
  INCOME: 'Income',
  EXPENSE: 'Expenses',
  EQUITY: 'Equity',
}

/** Order for displaying account type groups */
export const accountTypeOrder: NormalizedAccountType[] = [
  'ASSET',
  'LIABILITY',
  'INCOME',
  'EXPENSE',
  'EQUITY',
]

