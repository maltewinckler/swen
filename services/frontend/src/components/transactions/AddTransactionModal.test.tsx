import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { render, setupUser } from '../../../tests/test-utils'
import { AddTransactionModal } from './AddTransactionModal'

// Mock the API module
vi.mock('@/api', () => ({
  listAccounts: vi.fn(),
  createSimpleTransaction: vi.fn(),
}))

import { listAccounts, createSimpleTransaction } from '@/api'

const mockListAccounts = listAccounts as ReturnType<typeof vi.fn>
const mockCreateSimpleTransaction = createSimpleTransaction as ReturnType<typeof vi.fn>

// Mock account data
const mockAssetAccounts = {
  items: [
    { id: '1', account_number: '1000', name: 'Checking Account', account_type: 'ASSET' },
    { id: '2', account_number: '1100', name: 'Savings Account', account_type: 'ASSET' },
  ],
  total: 2,
}

const mockExpenseAccounts = {
  items: [
    { id: '3', account_number: '4000', name: 'Groceries', account_type: 'EXPENSE' },
    { id: '4', account_number: '4100', name: 'Restaurant', account_type: 'EXPENSE' },
  ],
  total: 2,
}

const mockIncomeAccounts = {
  items: [
    { id: '5', account_number: '3000', name: 'Salary', account_type: 'INCOME' },
  ],
  total: 1,
}

describe('AddTransactionModal', () => {
  const mockOnClose = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    mockListAccounts.mockImplementation(async (params) => {
      if (params?.account_type === 'ASSET') return mockAssetAccounts
      if (params?.account_type === 'EXPENSE') return mockExpenseAccounts
      if (params?.account_type === 'INCOME') return mockIncomeAccounts
      return { items: [], total: 0 }
    })
  })

  describe('rendering', () => {
    it('renders when isOpen is true', () => {
      render(<AddTransactionModal isOpen onClose={mockOnClose} />)
      expect(screen.getByText('Add Transaction')).toBeInTheDocument()
    })

    it('does not render when isOpen is false', () => {
      render(<AddTransactionModal isOpen={false} onClose={mockOnClose} />)
      expect(screen.queryByText('Add Transaction')).not.toBeInTheDocument()
    })

    it('shows expense/income toggle', () => {
      render(<AddTransactionModal isOpen onClose={mockOnClose} />)
      // Single toggle button that shows current type
      expect(screen.getByTestId('type-toggle')).toBeInTheDocument()
    })

    it('shows required form fields', () => {
      render(<AddTransactionModal isOpen onClose={mockOnClose} />)
      expect(screen.getByText('Amount')).toBeInTheDocument()
      expect(screen.getByText('Description')).toBeInTheDocument()
      expect(screen.getByText('Date')).toBeInTheDocument()
    })
  })

  describe('expense/income toggle', () => {
    it('defaults to expense selected', () => {
      render(<AddTransactionModal isOpen onClose={mockOnClose} />)
      // Toggle button shows "Expense" and has expense styling
      const toggleButton = screen.getByTestId('type-toggle')
      expect(toggleButton).toHaveClass('bg-accent-danger/10')
      expect(toggleButton).toHaveTextContent(/expense/i)
    })

    it('switches to income when toggle is clicked', async () => {
      const user = setupUser()
      render(<AddTransactionModal isOpen onClose={mockOnClose} />)

      // Click toggle to switch from expense to income
      const toggleButton = screen.getByTestId('type-toggle')
      await user.click(toggleButton)

      // Now shows Income with success styling
      expect(toggleButton).toHaveClass('bg-accent-success/10')
      expect(toggleButton).toHaveTextContent(/income/i)
    })

    it('changes account label when toggling', async () => {
      const user = setupUser()
      render(<AddTransactionModal isOpen onClose={mockOnClose} />)

      // Initially shows Expense Account
      expect(screen.getByText('Expense Account')).toBeInTheDocument()

      // Toggle to income
      await user.click(screen.getByTestId('type-toggle'))

      // Now shows Income Account
      expect(screen.getByText('Income Account')).toBeInTheDocument()
    })

    it('auto-switches to expense when negative sign is typed', async () => {
      const user = setupUser()
      render(<AddTransactionModal isOpen onClose={mockOnClose} />)

      // First switch to income
      const toggleButton = screen.getByTestId('type-toggle')
      await user.click(toggleButton)
      expect(toggleButton).toHaveTextContent(/income/i)

      // Type negative amount - should auto-switch to expense
      await user.type(screen.getByPlaceholderText('0.00'), '-25')

      expect(toggleButton).toHaveTextContent(/expense/i)
    })
  })

  describe('form validation', () => {
    it('shows error when amount is empty', async () => {
      const user = setupUser()
      render(<AddTransactionModal isOpen onClose={mockOnClose} />)

      // Fill in other required fields
      await user.type(screen.getByPlaceholderText(/coffee at starbucks/i), 'Test')

      // Try to submit
      await user.click(screen.getByRole('button', { name: /add expense/i }))

      expect(screen.getByText('Please enter a valid amount')).toBeInTheDocument()
    })

    it('shows error when description is empty', async () => {
      const user = setupUser()
      render(<AddTransactionModal isOpen onClose={mockOnClose} />)

      // Fill amount but not description
      await user.type(screen.getByPlaceholderText('0.00'), '25.00')

      // Try to submit
      await user.click(screen.getByRole('button', { name: /add expense/i }))

      expect(screen.getByText('Description is required')).toBeInTheDocument()
    })
  })

  describe('negative amount handling', () => {
    it('auto-switches to expense when negative amount is entered', async () => {
      const user = setupUser()
      render(<AddTransactionModal isOpen onClose={mockOnClose} />)

      // Switch to income first
      const toggleButton = screen.getByTestId('type-toggle')
      await user.click(toggleButton)

      // Type negative amount
      await user.type(screen.getByPlaceholderText('0.00'), '-25.50')

      // Should have switched back to expense
      expect(toggleButton).toHaveTextContent(/expense/i)
    })
  })

  describe('form submission', () => {
    it('calls createSimpleTransaction with negative amount for expense', async () => {
      const user = setupUser()
      mockCreateSimpleTransaction.mockResolvedValueOnce({ id: '123' })

      render(<AddTransactionModal isOpen onClose={mockOnClose} />)

      // Wait for accounts to load
      await waitFor(() => {
        expect(mockListAccounts).toHaveBeenCalled()
      })

      // Fill in form
      await user.type(screen.getByPlaceholderText('0.00'), '25.50')

      // Select asset account
      const assetSelect = screen.getAllByRole('combobox')[0]
      await user.selectOptions(assetSelect, '1000')

      // Select expense account
      const expenseSelect = screen.getAllByRole('combobox')[1]
      await user.selectOptions(expenseSelect, '4000')

      // Fill description
      await user.type(screen.getByPlaceholderText(/coffee at starbucks/i), 'Test purchase')

      // Submit
      await user.click(screen.getByRole('button', { name: /add expense/i }))

      await waitFor(() => {
        expect(mockCreateSimpleTransaction).toHaveBeenCalled()
      })

      // Verify the amount is negative (expense)
      const callArg = mockCreateSimpleTransaction.mock.calls[0][0]
      expect(callArg.amount).toBe('-25.50')
      expect(callArg.description).toBe('Test purchase')
    })

    it('calls createSimpleTransaction with positive amount for income', async () => {
      const user = setupUser()
      mockCreateSimpleTransaction.mockResolvedValueOnce({ id: '123' })

      render(<AddTransactionModal isOpen onClose={mockOnClose} />)

      // Wait for accounts to load
      await waitFor(() => {
        expect(mockListAccounts).toHaveBeenCalled()
      })

      // Switch to income (click the toggle button)
      await user.click(screen.getByTestId('type-toggle'))

      // Fill in form
      await user.type(screen.getByPlaceholderText('0.00'), '100.00')

      // Select asset account
      const assetSelect = screen.getAllByRole('combobox')[0]
      await user.selectOptions(assetSelect, '1000')

      // Select income account
      const incomeSelect = screen.getAllByRole('combobox')[1]
      await user.selectOptions(incomeSelect, '3000')

      // Fill description
      await user.type(screen.getByPlaceholderText(/salary december/i), 'Monthly salary')

      // Submit
      await user.click(screen.getByRole('button', { name: /add income/i }))

      await waitFor(() => {
        expect(mockCreateSimpleTransaction).toHaveBeenCalled()
      })

      // Verify the amount is positive (income)
      const callArg = mockCreateSimpleTransaction.mock.calls[0][0]
      expect(callArg.amount).toBe('100.00')
      expect(callArg.description).toBe('Monthly salary')
    })

    it('calls onClose after successful submission', async () => {
      const user = setupUser()
      mockCreateSimpleTransaction.mockResolvedValueOnce({ id: '123' })

      render(<AddTransactionModal isOpen onClose={mockOnClose} />)

      await waitFor(() => {
        expect(mockListAccounts).toHaveBeenCalled()
      })

      // Fill in minimal form
      await user.type(screen.getByPlaceholderText('0.00'), '25.00')
      const assetSelect = screen.getAllByRole('combobox')[0]
      await user.selectOptions(assetSelect, '1000')
      const expenseSelect = screen.getAllByRole('combobox')[1]
      await user.selectOptions(expenseSelect, '4000')
      await user.type(screen.getByPlaceholderText(/coffee at starbucks/i), 'Test')

      await user.click(screen.getByRole('button', { name: /add expense/i }))

      await waitFor(() => {
        expect(mockOnClose).toHaveBeenCalled()
      })
    })

    it('passes selected accounts with correct API parameter names', async () => {
      const user = setupUser()
      mockCreateSimpleTransaction.mockResolvedValueOnce({ id: '123' })

      render(<AddTransactionModal isOpen onClose={mockOnClose} />)

      await waitFor(() => {
        expect(mockListAccounts).toHaveBeenCalled()
      })

      // Fill in form with specific account selections
      await user.type(screen.getByPlaceholderText('0.00'), '42.00')

      // Select specific asset account (Savings - 1100)
      const assetSelect = screen.getAllByRole('combobox')[0]
      await user.selectOptions(assetSelect, '1100')

      // Select specific expense account (Restaurant - 4100)
      const expenseSelect = screen.getAllByRole('combobox')[1]
      await user.selectOptions(expenseSelect, '4100')

      await user.type(screen.getByPlaceholderText(/coffee at starbucks/i), 'Dinner')

      await user.click(screen.getByRole('button', { name: /add expense/i }))

      await waitFor(() => {
        expect(mockCreateSimpleTransaction).toHaveBeenCalled()
      })

      // Verify the correct API parameter names are used (not _hint suffix)
      // This prevents regression where accounts are ignored due to wrong field names
      const callArg = mockCreateSimpleTransaction.mock.calls[0][0]
      expect(callArg).toHaveProperty('asset_account', '1100')
      expect(callArg).toHaveProperty('category_account', '4100')
      // Ensure old incorrect names are NOT used
      expect(callArg).not.toHaveProperty('asset_account_hint')
      expect(callArg).not.toHaveProperty('category_account_hint')
    })
  })

  describe('cancel button', () => {
    it('calls onClose when cancel is clicked', async () => {
      const user = setupUser()
      render(<AddTransactionModal isOpen onClose={mockOnClose} />)

      await user.click(screen.getByRole('button', { name: /cancel/i }))

      expect(mockOnClose).toHaveBeenCalled()
    })

    it('resets form when reopened', async () => {
      const user = setupUser()
      const { rerender } = render(<AddTransactionModal isOpen onClose={mockOnClose} />)

      // Type something
      await user.type(screen.getByPlaceholderText('0.00'), '25.00')

      // Close
      await user.click(screen.getByRole('button', { name: /cancel/i }))

      // Reopen
      rerender(<AddTransactionModal isOpen onClose={mockOnClose} />)

      // Amount should be reset
      expect(screen.getByPlaceholderText('0.00')).toHaveValue(null)
    })
  })
})
