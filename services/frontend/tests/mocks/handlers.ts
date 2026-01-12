import { http, HttpResponse } from 'msw'

// Mock data
export const mockDashboardSummary = {
  total_income: '5000.00',
  total_expenses: '3000.00',
  net_income: '2000.00',
}

export const mockDashboardBalances = [
  { account_id: '1', account_name: 'Checking', balance: '2500.00', currency: 'EUR' },
  { account_id: '2', account_name: 'Savings', balance: '10000.00', currency: 'EUR' },
]

export const mockBankLookup = {
  name: 'Test Bank',
  blz: '12345678',
  fints_url: 'https://fints.test-bank.de',
}

export const mockTanMethods = {
  tan_methods: [
    { code: '920', name: 'Push TAN', is_decoupled: true },
    { code: '900', name: 'SMS TAN', is_decoupled: false },
  ],
  default_method: '920',
}

export const mockDiscoveredAccounts = {
  accounts: [
    {
      iban: 'DE89370400440532013000',
      default_name: 'Girokonto',
      balance: '2500.00',
      currency: 'EUR',
    },
    {
      iban: 'DE89370400440532013001',
      default_name: 'Sparkonto',
      balance: '10000.00',
      currency: 'EUR',
    },
  ],
}

export const mockSpendingBreakdown = {
  categories: [
    { category: 'Groceries', amount: '500.00', percentage: 25 },
    { category: 'Transport', amount: '300.00', percentage: 15 },
    { category: 'Entertainment', amount: '200.00', percentage: 10 },
  ],
  total: '2000.00',
}

export const mockIncomeBreakdown = {
  sources: [
    { source: 'Salary', amount: '4000.00', percentage: 80 },
    { source: 'Freelance', amount: '1000.00', percentage: 20 },
  ],
  total: '5000.00',
}

export const mockTimeSeriesData = {
  data: [
    { month: '2024-01', value: 1000 },
    { month: '2024-02', value: 1200 },
    { month: '2024-03', value: 950 },
  ],
}

export const mockCredentials = [
  { id: '1', blz: '12345678', bank_name: 'Test Bank', username: 'testuser' },
]

export const mockAccounts = [
  {
    id: '1',
    iban: 'DE89370400440532013000',
    account_name: 'Checking Account',
    balance: '2500.00',
    currency: 'EUR',
  },
]

export const handlers = [
  // Dashboard endpoints
  http.get('/api/dashboard/summary', () => {
    return HttpResponse.json(mockDashboardSummary)
  }),

  http.get('/api/dashboard/balances', () => {
    return HttpResponse.json(mockDashboardBalances)
  }),

  // Bank lookup
  http.get('/api/credentials/lookup/:blz', ({ params }) => {
    if (params.blz === '12345678') {
      return HttpResponse.json(mockBankLookup)
    }
    return new HttpResponse(null, { status: 404 })
  }),

  // TAN methods
  http.post('/api/credentials/tan-methods', () => {
    return HttpResponse.json(mockTanMethods)
  }),

  // Store credentials
  http.post('/api/credentials', () => {
    return HttpResponse.json({ message: 'Credentials stored successfully' })
  }),

  // Discover accounts
  http.get('/api/credentials/:blz/accounts', () => {
    return HttpResponse.json(mockDiscoveredAccounts)
  }),

  // Setup accounts
  http.post('/api/credentials/:blz/accounts', () => {
    return HttpResponse.json({
      message: 'Accounts imported successfully',
      accounts_imported: mockDiscoveredAccounts.accounts.map(a => ({
        iban: a.iban,
        account_name: a.default_name,
      })),
    })
  }),

  // Analytics endpoints
  http.get('/api/analytics/spending/breakdown', () => {
    return HttpResponse.json(mockSpendingBreakdown)
  }),

  http.get('/api/analytics/income/breakdown', () => {
    return HttpResponse.json(mockIncomeBreakdown)
  }),

  http.get('/api/analytics/spending/over-time', () => {
    return HttpResponse.json(mockTimeSeriesData)
  }),

  http.get('/api/analytics/income/over-time', () => {
    return HttpResponse.json(mockTimeSeriesData)
  }),

  http.get('/api/analytics/net-income/over-time', () => {
    return HttpResponse.json(mockTimeSeriesData)
  }),

  http.get('/api/analytics/savings-rate/over-time', () => {
    return HttpResponse.json(mockTimeSeriesData)
  }),

  http.get('/api/analytics/net-worth/over-time', () => {
    return HttpResponse.json(mockTimeSeriesData)
  }),

  // Credentials list
  http.get('/api/credentials', () => {
    return HttpResponse.json(mockCredentials)
  }),

  // Accounts list
  http.get('/api/accounts', () => {
    return HttpResponse.json(mockAccounts)
  }),

  // Sync endpoint
  http.post('/api/sync', () => {
    return HttpResponse.json({
      task_id: 'test-task-123',
      message: 'Sync started',
    })
  }),

  http.get('/api/sync/status/:taskId', () => {
    return HttpResponse.json({
      status: 'completed',
      progress: 100,
      total_imported: 50,
      total_skipped: 5,
      accounts_synced: 2,
    })
  }),

  // User settings
  http.get('/api/users/me', () => {
    return HttpResponse.json({
      id: '1',
      username: 'testuser',
      email: 'test@example.com',
    })
  }),
]

