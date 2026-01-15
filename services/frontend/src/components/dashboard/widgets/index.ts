/**
 * Dashboard Widget Registry
 *
 * Defines all available widgets and maps their IDs to components.
 */

import { lazy, type ComponentType } from 'react'

// Lazy load widget components for better code splitting
const SummaryCardsWidget = lazy(() => import('./SummaryCardsWidget'))
const SpendingPieWidget = lazy(() => import('./SpendingPieWidget'))
const AccountBalancesWidget = lazy(() => import('./AccountBalancesWidget'))
const NetWorthWidget = lazy(() => import('./NetWorthWidget'))
const IncomeOverTimeWidget = lazy(() => import('./IncomeOverTimeWidget'))
const SpendingOverTimeWidget = lazy(() => import('./SpendingOverTimeWidget'))
const NetIncomeWidget = lazy(() => import('./NetIncomeWidget'))
const SavingsRateWidget = lazy(() => import('./SavingsRateWidget'))
const IncomeBreakdownWidget = lazy(() => import('./IncomeBreakdownWidget'))
const TopExpensesWidget = lazy(() => import('./TopExpensesWidget'))
const MonthComparisonWidget = lazy(() => import('./MonthComparisonWidget'))
const SingleAccountSpendingWidget = lazy(() => import('./SingleAccountSpendingWidget'))
const SankeyWidget = lazy(() => import('./SankeyWidget'))

// Widget settings interface
export interface WidgetSettings {
  months?: number
  days?: number
  limit?: number
  account_id?: string
  [key: string]: unknown
}

// Widget component props
export interface WidgetProps {
  settings: WidgetSettings
  onSettingsChange?: (settings: WidgetSettings) => void
}

// Widget metadata (matches backend AVAILABLE_WIDGETS)
export interface WidgetMeta {
  id: string
  title: string
  description: string
  category: 'overview' | 'spending' | 'income'
  defaultSettings: WidgetSettings
  component: ComponentType<WidgetProps>
  // Grid sizing hints
  colSpan?: 1 | 2
  minHeight?: string
}

// Widget registry - maps widget IDs to their metadata and components
export const WIDGET_REGISTRY: Record<string, WidgetMeta> = {
  'summary-cards': {
    id: 'summary-cards',
    title: 'Summary Cards',
    description: 'Key financial metrics at a glance',
    category: 'overview',
    defaultSettings: { days: 30 },
    component: SummaryCardsWidget,
    colSpan: 2,
    minHeight: 'auto',
  },
  'spending-pie': {
    id: 'spending-pie',
    title: 'Spending Breakdown',
    description: 'Pie chart showing spending by category',
    category: 'spending',
    defaultSettings: { months: 1 },
    component: SpendingPieWidget,
    colSpan: 1,
    minHeight: '20rem',
  },
  'account-balances': {
    id: 'account-balances',
    title: 'Account Balances',
    description: 'Bar chart of current account balances',
    category: 'overview',
    defaultSettings: {},
    component: AccountBalancesWidget,
    colSpan: 1,
    minHeight: '20rem',
  },
  'net-worth': {
    id: 'net-worth',
    title: 'Net Worth Over Time',
    description: 'Track your net worth trend',
    category: 'overview',
    defaultSettings: { months: 12 },
    component: NetWorthWidget,
    colSpan: 2,
    minHeight: '20rem',
  },
  'income-over-time': {
    id: 'income-over-time',
    title: 'Income Over Time',
    description: 'Monthly income trend',
    category: 'income',
    defaultSettings: { months: 12 },
    component: IncomeOverTimeWidget,
    colSpan: 1,
    minHeight: '20rem',
  },
  'spending-over-time': {
    id: 'spending-over-time',
    title: 'Spending Over Time',
    description: 'Monthly spending trend',
    category: 'spending',
    defaultSettings: { months: 12 },
    component: SpendingOverTimeWidget,
    colSpan: 1,
    minHeight: '20rem',
  },
  'net-income': {
    id: 'net-income',
    title: 'Net Income Over Time',
    description: 'Income minus expenses over time',
    category: 'overview',
    defaultSettings: { months: 12 },
    component: NetIncomeWidget,
    colSpan: 2,
    minHeight: '20rem',
  },
  'savings-rate': {
    id: 'savings-rate',
    title: 'Savings Rate',
    description: 'Percentage of income saved each month',
    category: 'overview',
    defaultSettings: { months: 12 },
    component: SavingsRateWidget,
    colSpan: 1,
    minHeight: '20rem',
  },
  'income-breakdown': {
    id: 'income-breakdown',
    title: 'Income Sources',
    description: 'Pie chart showing income by source',
    category: 'income',
    defaultSettings: { months: 1 },
    component: IncomeBreakdownWidget,
    colSpan: 1,
    minHeight: '20rem',
  },
  'top-expenses': {
    id: 'top-expenses',
    title: 'Top Expenses',
    description: 'Highest spending categories',
    category: 'spending',
    defaultSettings: { months: 1, limit: 5 },
    component: TopExpensesWidget,
    colSpan: 1,
    minHeight: '20rem',
  },
  'month-comparison': {
    id: 'month-comparison',
    title: 'Month Comparison',
    description: 'Compare this month to previous',
    category: 'overview',
    defaultSettings: {},
    component: MonthComparisonWidget,
    colSpan: 1,
    minHeight: '20rem',
  },
  'single-account-spending': {
    id: 'single-account-spending',
    title: 'Category Spending',
    description: 'Spending trend for a specific category',
    category: 'spending',
    defaultSettings: { months: 12, account_id: undefined },
    component: SingleAccountSpendingWidget,
    colSpan: 1,
    minHeight: '20rem',
  },
  'sankey': {
    id: 'sankey',
    title: 'Cash Flow Sankey',
    description: 'Visual flow of income to expenses and savings',
    category: 'overview',
    defaultSettings: { days: 30 },
    component: SankeyWidget,
    colSpan: 2,
    minHeight: '28rem',
  },
}

// Get widget component by ID
export function getWidgetComponent(widgetId: string): ComponentType<WidgetProps> | null {
  return WIDGET_REGISTRY[widgetId]?.component ?? null
}

// Get widget metadata by ID
export function getWidgetMeta(widgetId: string): WidgetMeta | null {
  return WIDGET_REGISTRY[widgetId] ?? null
}

// Get all widgets grouped by category
export function getWidgetsByCategory(): Record<string, WidgetMeta[]> {
  const categories: Record<string, WidgetMeta[]> = {
    overview: [],
    spending: [],
    income: [],
  }

  for (const widget of Object.values(WIDGET_REGISTRY)) {
    categories[widget.category].push(widget)
  }

  return categories
}

// Export widget components for direct use
export {
  SummaryCardsWidget,
  SpendingPieWidget,
  AccountBalancesWidget,
  NetWorthWidget,
  IncomeOverTimeWidget,
  SpendingOverTimeWidget,
  NetIncomeWidget,
  SavingsRateWidget,
  IncomeBreakdownWidget,
  TopExpensesWidget,
  MonthComparisonWidget,
  SingleAccountSpendingWidget,
  SankeyWidget,
}
