import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor, within } from '@testing-library/react'
import { render, setupUser } from '../../../tests/test-utils'
import { TransactionDetailModal } from './TransactionDetailModal'

// Mock the API module
vi.mock('@/api', () => ({
  getTransaction: vi.fn(),
  updateTransaction: vi.fn(),
  postTransaction: vi.fn(),
  deleteTransaction: vi.fn(),
  listAccounts: vi.fn(),
}))

import {
  getTransaction,
  updateTransaction,
  deleteTransaction,
  listAccounts,
} from '@/api'

const mockGetTransaction = getTransaction as ReturnType<typeof vi.fn>
const mockUpdateTransaction = updateTransaction as ReturnType<typeof vi.fn>
const mockDeleteTransaction = deleteTransaction as ReturnType<typeof vi.fn>
const mockListAccounts = listAccounts as ReturnType<typeof vi.fn>

// Mock transaction data
const mockDraftTransaction = {
  id: 'txn-draft-123',
  transaction_date: '2024-01-15',
  booking_date: '2024-01-15',
  description: 'Test Draft Transaction',
  amount: '50.00',
  is_posted: false,
  entries: [
    { account_id: 'acc-1', account_name: 'Checking', account_type: 'asset', debit: null, credit: '50.00', currency: 'EUR' },
    { account_id: 'acc-2', account_name: 'Groceries', account_type: 'expense', debit: '50.00', credit: null, currency: 'EUR' },
  ],
  metadata: null,
}

const mockPostedTransaction = {
  id: 'txn-posted-123',
  transaction_date: '2024-01-15',
  booking_date: '2024-01-15',
  description: 'Test Posted Transaction',
  amount: '75.50',
  is_posted: true,
  entries: [
    { account_id: 'acc-1', account_name: 'Checking', account_type: 'asset', debit: null, credit: '75.50', currency: 'EUR' },
    { account_id: 'acc-2', account_name: 'Groceries', account_type: 'expense', debit: '75.50', credit: null, currency: 'EUR' },
  ],
  metadata: null,
}

describe('TransactionDetailModal', () => {
  const mockOnClose = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    mockListAccounts.mockResolvedValue({ items: [], total: 0 })
  })

  describe('rendering', () => {
    it('renders when transactionId is provided', async () => {
      mockGetTransaction.mockResolvedValueOnce(mockDraftTransaction)

      render(
        <TransactionDetailModal
          transactionId="txn-draft-123"
          onClose={mockOnClose}
        />
      )

      await waitFor(() => {
        expect(screen.getByText('Transaction Details')).toBeInTheDocument()
      })
    })

    it('shows loading spinner while fetching', () => {
      mockGetTransaction.mockReturnValue(new Promise(() => {})) // Never resolves

      render(
        <TransactionDetailModal
          transactionId="txn-draft-123"
          onClose={mockOnClose}
        />
      )

      // Spinner uses Loader2 icon which renders as an SVG with animate-spin
      const spinner = document.querySelector('svg.animate-spin')
      expect(spinner).toBeInTheDocument()
    })
  })

  describe('Danger Zone', () => {
    // Helper to enter edit mode first (Danger Zone is now inside edit mode)
    const enterEditMode = async (user: ReturnType<typeof setupUser>) => {
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /edit/i })).toBeInTheDocument()
      })
      await user.click(screen.getByRole('button', { name: /edit/i }))
    }

    describe('collapsed by default', () => {
      it('shows Danger Zone summary in edit mode', async () => {
        const user = setupUser()
        mockGetTransaction.mockResolvedValueOnce(mockDraftTransaction)

        render(
          <TransactionDetailModal
            transactionId="txn-draft-123"
            onClose={mockOnClose}
          />
        )

        await enterEditMode(user)

        await waitFor(() => {
          expect(screen.getByText('Danger Zone')).toBeInTheDocument()
        })

        // Verify the details element is present
        const details = document.querySelector('details')
        expect(details).toBeInTheDocument()
        // Should be collapsed by default (no 'open' attribute)
        expect(details).not.toHaveAttribute('open')
      })

      it('can be expanded by clicking', async () => {
        const user = setupUser()
        mockGetTransaction.mockResolvedValueOnce(mockDraftTransaction)

        render(
          <TransactionDetailModal
            transactionId="txn-draft-123"
            onClose={mockOnClose}
          />
        )

        await enterEditMode(user)

        await waitFor(() => {
          expect(screen.getByText('Danger Zone')).toBeInTheDocument()
        })

        // Click to expand
        await user.click(screen.getByText('Danger Zone'))

        // Details should now be open
        const details = document.querySelector('details')
        expect(details).toHaveAttribute('open')
      })
    })

    describe('draft transaction deletion', () => {
      it('shows simple delete button for draft transactions', async () => {
        const user = setupUser()
        mockGetTransaction.mockResolvedValueOnce(mockDraftTransaction)

        render(
          <TransactionDetailModal
            transactionId="txn-draft-123"
            onClose={mockOnClose}
          />
        )

        await enterEditMode(user)

        await waitFor(() => {
          expect(screen.getByText('Danger Zone')).toBeInTheDocument()
        })

        await user.click(screen.getByText('Danger Zone'))

        await waitFor(() => {
          expect(screen.getByRole('button', { name: /delete draft/i })).toBeInTheDocument()
        })

        // Should NOT show amount confirmation input for draft transactions
        expect(screen.queryByText(/To confirm, type the amount/)).not.toBeInTheDocument()
      })

      it('shows confirmation dialog when deleting draft', async () => {
        const user = setupUser()
        mockGetTransaction.mockResolvedValueOnce(mockDraftTransaction)

        render(
          <TransactionDetailModal
            transactionId="txn-draft-123"
            onClose={mockOnClose}
          />
        )

        await enterEditMode(user)

        await waitFor(() => {
          expect(screen.getByText('Danger Zone')).toBeInTheDocument()
        })

        await user.click(screen.getByText('Danger Zone'))

        await waitFor(() => {
          expect(screen.getByRole('button', { name: /delete draft/i })).toBeInTheDocument()
        })

        await user.click(screen.getByRole('button', { name: /delete draft/i }))

        const confirmDialog = screen.getByRole('dialog', { name: /delete draft transaction/i })
        expect(within(confirmDialog).getByRole('button', { name: /^delete$/i })).toBeInTheDocument()
        expect(within(confirmDialog).getByRole('button', { name: /cancel/i })).toBeInTheDocument()
      })

      it('calls deleteTransaction when confirmed', async () => {
        const user = setupUser()
        mockGetTransaction.mockResolvedValueOnce(mockDraftTransaction)
        mockDeleteTransaction.mockResolvedValueOnce({})

        render(
          <TransactionDetailModal
            transactionId="txn-draft-123"
            onClose={mockOnClose}
          />
        )

        await enterEditMode(user)

        await waitFor(() => {
          expect(screen.getByText('Danger Zone')).toBeInTheDocument()
        })

        await user.click(screen.getByText('Danger Zone'))

        await waitFor(() => {
          expect(screen.getByRole('button', { name: /delete draft/i })).toBeInTheDocument()
        })

        await user.click(screen.getByRole('button', { name: /delete draft/i }))

        await user.click(screen.getByRole('button', { name: /^delete$/i }))

        await waitFor(() => {
          expect(mockDeleteTransaction).toHaveBeenCalledWith('txn-draft-123', false)
        })
      })
    })

    describe('posted transaction deletion', () => {
      it('shows amount confirmation input for posted transactions', async () => {
        const user = setupUser()
        mockGetTransaction.mockResolvedValueOnce(mockPostedTransaction)

        render(
          <TransactionDetailModal
            transactionId="txn-posted-123"
            onClose={mockOnClose}
          />
        )

        await enterEditMode(user)

        await waitFor(() => {
          expect(screen.getByText('Danger Zone')).toBeInTheDocument()
        })

        await user.click(screen.getByText('Danger Zone'))

        await waitFor(() => {
          // Should show the confirmation hint with amount
          expect(screen.getByText(/To confirm, type the amount/)).toBeInTheDocument()
        })
      })

      it('disables delete button until amount is matched', async () => {
        const user = setupUser()
        mockGetTransaction.mockResolvedValueOnce(mockPostedTransaction)

        render(
          <TransactionDetailModal
            transactionId="txn-posted-123"
            onClose={mockOnClose}
          />
        )

        await enterEditMode(user)

        await waitFor(() => {
          expect(screen.getByText('Danger Zone')).toBeInTheDocument()
        })

        await user.click(screen.getByText('Danger Zone'))

        await waitFor(() => {
          // The button says just "Delete" for posted transactions
          const deleteButton = screen.getByRole('button', { name: 'Delete' })
          expect(deleteButton).toBeDisabled()
        })
      })

      it('enables delete button when amount matches (European format)', async () => {
        const user = setupUser()
        mockGetTransaction.mockResolvedValueOnce(mockPostedTransaction)

        render(
          <TransactionDetailModal
            transactionId="txn-posted-123"
            onClose={mockOnClose}
          />
        )

        await enterEditMode(user)

        await waitFor(() => {
          expect(screen.getByText('Danger Zone')).toBeInTheDocument()
        })

        await user.click(screen.getByText('Danger Zone'))

        await waitFor(() => {
          expect(screen.getByTestId('delete-confirm-amount')).toBeInTheDocument()
        })

        // Type the amount in European format (with comma)
        await user.type(screen.getByTestId('delete-confirm-amount'), '75,50')

        expect(screen.getByRole('button', { name: 'Delete' })).toBeEnabled()
      })

      it('enables delete button when amount matches (US format)', async () => {
        const user = setupUser()
        mockGetTransaction.mockResolvedValueOnce(mockPostedTransaction)

        render(
          <TransactionDetailModal
            transactionId="txn-posted-123"
            onClose={mockOnClose}
          />
        )

        await enterEditMode(user)

        await waitFor(() => {
          expect(screen.getByText('Danger Zone')).toBeInTheDocument()
        })

        await user.click(screen.getByText('Danger Zone'))

        await waitFor(() => {
          expect(screen.getByTestId('delete-confirm-amount')).toBeInTheDocument()
        })

        // Type the amount in US format (with period)
        await user.type(screen.getByTestId('delete-confirm-amount'), '75.50')

        expect(screen.getByRole('button', { name: 'Delete' })).toBeEnabled()
      })

      it('calls deleteTransaction with force=true when amount matches', async () => {
        const user = setupUser()
        mockGetTransaction.mockResolvedValueOnce(mockPostedTransaction)
        mockDeleteTransaction.mockResolvedValueOnce({})

        render(
          <TransactionDetailModal
            transactionId="txn-posted-123"
            onClose={mockOnClose}
          />
        )

        await enterEditMode(user)

        await waitFor(() => {
          expect(screen.getByText('Danger Zone')).toBeInTheDocument()
        })

        await user.click(screen.getByText('Danger Zone'))

        await waitFor(() => {
          expect(screen.getByTestId('delete-confirm-amount')).toBeInTheDocument()
        })

        await user.type(screen.getByTestId('delete-confirm-amount'), '75.50')
        await user.click(screen.getByRole('button', { name: 'Delete' }))

        await waitFor(() => {
          expect(mockDeleteTransaction).toHaveBeenCalledWith('txn-posted-123', true)
        })
      })
    })
  })

  describe('close button', () => {
    it('calls onClose when close button is clicked', async () => {
      const user = setupUser()
      mockGetTransaction.mockResolvedValueOnce(mockDraftTransaction)

      render(
        <TransactionDetailModal
          transactionId="txn-draft-123"
          onClose={mockOnClose}
        />
      )

      await waitFor(() => {
        expect(screen.getByText('Transaction Details')).toBeInTheDocument()
      })

      // Find close button in header
      const header = screen.getByText('Transaction Details').closest('div')
      const closeButton = header?.parentElement?.querySelector('button')
      if (closeButton) {
        await user.click(closeButton)
        expect(mockOnClose).toHaveBeenCalled()
      }
    })
  })

  describe('Review Mode', () => {
    it('shows Edit Transaction header when isReviewMode is true', async () => {
      mockGetTransaction.mockResolvedValueOnce(mockDraftTransaction)

      render(
        <TransactionDetailModal
          transactionId="txn-draft-123"
          onClose={mockOnClose}
          isReviewMode={true}
        />
      )

      await waitFor(() => {
        expect(screen.getByText('Edit Transaction')).toBeInTheDocument()
      })
    })

    it('shows Review Mode badge when isReviewMode is true', async () => {
      mockGetTransaction.mockResolvedValueOnce(mockDraftTransaction)

      render(
        <TransactionDetailModal
          transactionId="txn-draft-123"
          onClose={mockOnClose}
          isReviewMode={true}
        />
      )

      await waitFor(() => {
        expect(screen.getByText('Review Mode')).toBeInTheDocument()
      })
    })

    it('shows editable description field in review mode', async () => {
      mockGetTransaction.mockResolvedValueOnce(mockDraftTransaction)

      render(
        <TransactionDetailModal
          transactionId="txn-draft-123"
          onClose={mockOnClose}
          isReviewMode={true}
        />
      )

      await waitFor(() => {
        // Find the description input (should have the transaction description as value)
        const descriptionInput = screen.getByDisplayValue('Test Draft Transaction')
        expect(descriptionInput).toBeInTheDocument()
        expect(descriptionInput.tagName).toBe('INPUT')
      })
    })

    it('shows Save & Next button when there is a next transaction', async () => {
      mockGetTransaction.mockResolvedValueOnce(mockDraftTransaction)

      render(
        <TransactionDetailModal
          transactionId="txn-draft-123"
          transactionIds={['txn-draft-123', 'txn-next-456']}
          onClose={mockOnClose}
          isReviewMode={true}
        />
      )

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /save & next/i })).toBeInTheDocument()
      })
    })

    it('does not show Save & Next when at last transaction', async () => {
      mockGetTransaction.mockResolvedValueOnce(mockDraftTransaction)

      render(
        <TransactionDetailModal
          transactionId="txn-draft-123"
          transactionIds={['txn-draft-123']} // Only one transaction
          onClose={mockOnClose}
          isReviewMode={true}
        />
      )

      await waitFor(() => {
        expect(screen.getByText('Edit Transaction')).toBeInTheDocument()
      })

      expect(screen.queryByRole('button', { name: /save & next/i })).not.toBeInTheDocument()
    })

    it('shows unsaved changes indicator when description is modified', async () => {
      const user = setupUser()
      mockGetTransaction.mockResolvedValueOnce(mockDraftTransaction)

      render(
        <TransactionDetailModal
          transactionId="txn-draft-123"
          onClose={mockOnClose}
          isReviewMode={true}
        />
      )

      await waitFor(() => {
        expect(screen.getByDisplayValue('Test Draft Transaction')).toBeInTheDocument()
      })

      // Initially no "Unsaved" indicator shown
      expect(screen.queryByText('Unsaved')).not.toBeInTheDocument()

      // Modify the description
      const descriptionInput = screen.getByDisplayValue('Test Draft Transaction')
      await user.clear(descriptionInput)
      await user.type(descriptionInput, 'Modified Description')

      // Should show unsaved indicator
      expect(screen.getByText('Unsaved')).toBeInTheDocument()
    })

    it('calls updateTransaction when Save is clicked', async () => {
      const user = setupUser()
      mockGetTransaction.mockResolvedValueOnce(mockDraftTransaction)
      mockUpdateTransaction.mockResolvedValueOnce(mockDraftTransaction)

      render(
        <TransactionDetailModal
          transactionId="txn-draft-123"
          onClose={mockOnClose}
          isReviewMode={true}
        />
      )

      await waitFor(() => {
        expect(screen.getByDisplayValue('Test Draft Transaction')).toBeInTheDocument()
      })

      // Modify the description
      const descriptionInput = screen.getByDisplayValue('Test Draft Transaction')
      await user.clear(descriptionInput)
      await user.type(descriptionInput, 'Modified Description')

      // Click Save
      await user.click(screen.getByRole('button', { name: /^save$/i }))

      await waitFor(() => {
        expect(mockUpdateTransaction).toHaveBeenCalledWith('txn-draft-123', {
          description: 'Modified Description',
        })
      })
    })
  })

  describe('Edit Mode (manual toggle)', () => {
    it('shows Edit button in view mode', async () => {
      mockGetTransaction.mockResolvedValueOnce(mockDraftTransaction)

      render(
        <TransactionDetailModal
          transactionId="txn-draft-123"
          onClose={mockOnClose}
        />
      )

      // Wait for transaction data to load (description appears)
      await waitFor(() => {
        expect(screen.getByText('Test Draft Transaction')).toBeInTheDocument()
      })

      // Now the Edit button should be visible
      expect(screen.getByRole('button', { name: /edit/i })).toBeInTheDocument()
    })

    it('switches to edit mode when Edit button is clicked', async () => {
      const user = setupUser()
      mockGetTransaction.mockResolvedValueOnce(mockDraftTransaction)

      render(
        <TransactionDetailModal
          transactionId="txn-draft-123"
          onClose={mockOnClose}
        />
      )

      // Wait for transaction data to load
      await waitFor(() => {
        expect(screen.getByText('Test Draft Transaction')).toBeInTheDocument()
      })

      // Click Edit button
      await user.click(screen.getByRole('button', { name: /edit/i }))

      // Should now show Edit Transaction header
      await waitFor(() => {
        expect(screen.getByText('Edit Transaction')).toBeInTheDocument()
      })
    })

    it('shows Cancel button in edit mode (non-review mode)', async () => {
      const user = setupUser()
      mockGetTransaction.mockResolvedValueOnce(mockDraftTransaction)

      render(
        <TransactionDetailModal
          transactionId="txn-draft-123"
          onClose={mockOnClose}
        />
      )

      // Wait for transaction data to load
      await waitFor(() => {
        expect(screen.getByText('Test Draft Transaction')).toBeInTheDocument()
      })

      // Click Edit button
      await user.click(screen.getByRole('button', { name: /edit/i }))

      // Should show Cancel button
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
      })
    })

    it('exits edit mode when Cancel is clicked', async () => {
      const user = setupUser()
      mockGetTransaction.mockResolvedValueOnce(mockDraftTransaction)

      render(
        <TransactionDetailModal
          transactionId="txn-draft-123"
          onClose={mockOnClose}
        />
      )

      // Wait for transaction data to load
      await waitFor(() => {
        expect(screen.getByText('Test Draft Transaction')).toBeInTheDocument()
      })

      // Click Edit button
      await user.click(screen.getByRole('button', { name: /edit/i }))

      await waitFor(() => {
        expect(screen.getByText('Edit Transaction')).toBeInTheDocument()
      })

      // Click Cancel
      await user.click(screen.getByRole('button', { name: /cancel/i }))

      // Should go back to view mode
      await waitFor(() => {
        expect(screen.getByText('Transaction Details')).toBeInTheDocument()
      })
    })
  })
})
