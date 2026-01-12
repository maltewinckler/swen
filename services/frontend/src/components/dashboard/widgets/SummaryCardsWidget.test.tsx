import { describe, it, expect, vi, type ReactNode } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import SummaryCardsWidget from './SummaryCardsWidget'

// Mock the API
vi.mock('@/api', () => ({
  getDashboardSummary: vi.fn().mockResolvedValue({
    total_income: '5000.00',
    total_expenses: '3000.00',
    net_income: '2000.00',
  }),
  getDashboardBalances: vi.fn().mockResolvedValue([
    { account_id: '1', account_name: 'Checking', balance: '2500.00', currency: 'EUR' },
    { account_id: '2', account_name: 'Savings', balance: '10000.00', currency: 'EUR' },
  ]),
}))

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
      },
    },
  })
}

function renderWithProviders(ui: ReactNode) {
  const queryClient = createTestQueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>
  )
}

describe('SummaryCardsWidget', () => {
  const defaultSettings = { days: 30 }

  describe('rendering', () => {
    it('renders loading state initially', () => {
      renderWithProviders(<SummaryCardsWidget settings={defaultSettings} />)
      // Loading state shows animated pulse cards
      const pulseCards = document.querySelectorAll('.animate-pulse')
      expect(pulseCards.length).toBeGreaterThan(0)
    })

    it('renders all four summary cards after loading', async () => {
      renderWithProviders(<SummaryCardsWidget settings={defaultSettings} />)

      await waitFor(() => {
        expect(screen.getByText('Total Assets')).toBeInTheDocument()
        expect(screen.getByText('Income')).toBeInTheDocument()
        expect(screen.getByText('Expenses')).toBeInTheDocument()
        expect(screen.getByText('Net Income')).toBeInTheDocument()
      })
    })
  })

  describe('data display', () => {
    it('displays formatted total assets', async () => {
      renderWithProviders(<SummaryCardsWidget settings={defaultSettings} />)

      await waitFor(() => {
        // Total assets = 2500 + 10000 = 12500
        expect(screen.getByText(/12\.500,00\s*€/)).toBeInTheDocument()
      })
    })

    it('displays formatted income', async () => {
      renderWithProviders(<SummaryCardsWidget settings={defaultSettings} />)

      await waitFor(() => {
        expect(screen.getByText(/5\.000,00\s*€/)).toBeInTheDocument()
      })
    })

    it('displays formatted expenses', async () => {
      renderWithProviders(<SummaryCardsWidget settings={defaultSettings} />)

      await waitFor(() => {
        expect(screen.getByText(/3\.000,00\s*€/)).toBeInTheDocument()
      })
    })

    it('displays formatted net income', async () => {
      renderWithProviders(<SummaryCardsWidget settings={defaultSettings} />)

      await waitFor(() => {
        // Net income should be displayed with sign
        expect(screen.getByText(/\+2\.000,00\s*€/)).toBeInTheDocument()
      })
    })

    it('displays time period label', async () => {
      renderWithProviders(<SummaryCardsWidget settings={{ days: 30 }} />)

      await waitFor(() => {
        // Should show "Last 30 days" multiple times (for income, expenses, net income)
        const periodLabels = screen.getAllByText('Last 30 days')
        expect(periodLabels.length).toBeGreaterThanOrEqual(1)
      })
    })
  })

  describe('settings', () => {
    it('uses days from settings', async () => {
      renderWithProviders(<SummaryCardsWidget settings={{ days: 90 }} />)

      await waitFor(() => {
        const periodLabels = screen.getAllByText('Last 90 days')
        expect(periodLabels.length).toBeGreaterThanOrEqual(1)
      })
    })

    it('defaults to 30 days if not specified', async () => {
      renderWithProviders(<SummaryCardsWidget settings={{}} />)

      await waitFor(() => {
        const periodLabels = screen.getAllByText('Last 30 days')
        expect(periodLabels.length).toBeGreaterThanOrEqual(1)
      })
    })
  })

  describe('icons', () => {
    it('displays wallet icon for total assets', async () => {
      renderWithProviders(<SummaryCardsWidget settings={defaultSettings} />)

      await waitFor(() => {
        expect(screen.getByText('Total Assets')).toBeInTheDocument()
      })

      // Check that SVG icons are rendered (we can't easily check which one)
      const svgIcons = document.querySelectorAll('svg')
      expect(svgIcons.length).toBeGreaterThan(0)
    })
  })

  describe('layout', () => {
    it('uses responsive grid layout', async () => {
      renderWithProviders(<SummaryCardsWidget settings={defaultSettings} />)

      await waitFor(() => {
        const grid = document.querySelector('.grid')
        expect(grid).toHaveClass('md:grid-cols-2', 'lg:grid-cols-4')
      })
    })

    it('applies staggered animations', async () => {
      renderWithProviders(<SummaryCardsWidget settings={defaultSettings} />)

      await waitFor(() => {
        expect(document.querySelector('.animate-stagger-1')).toBeInTheDocument()
        expect(document.querySelector('.animate-stagger-2')).toBeInTheDocument()
        expect(document.querySelector('.animate-stagger-3')).toBeInTheDocument()
        expect(document.querySelector('.animate-stagger-4')).toBeInTheDocument()
      })
    })
  })
})
