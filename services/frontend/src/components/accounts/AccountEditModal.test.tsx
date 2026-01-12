import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { render, setupUser } from '../../../tests/test-utils'
import { AccountEditModal } from './AccountEditModal'

// Mock the API module
vi.mock('@/api', () => ({
  updateAccount: vi.fn(),
  listAccounts: vi.fn(),
}))

import { updateAccount, listAccounts } from '@/api'

const mockUpdateAccount = updateAccount as ReturnType<typeof vi.fn>
const mockListAccounts = listAccounts as ReturnType<typeof vi.fn>

// Mock account data
const mockAccount = {
  id: '123',
  name: 'Groceries',
  account_number: '4000',
  account_type: 'EXPENSE',
  description: 'Food and household items',
  is_active: true,
  parent_id: null,
  default_currency: 'EUR',
  created_at: '2024-01-01T00:00:00Z',
}

describe('AccountEditModal', () => {
  const mockOnClose = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    // Mock listAccounts for ParentAccountSelect
    mockListAccounts.mockResolvedValue({ items: [], total: 0 })
  })

  describe('rendering', () => {
    it('renders when isOpen is true', () => {
      render(
        <AccountEditModal
          account={mockAccount}
          isOpen
          onClose={mockOnClose}
        />
      )
      expect(screen.getByText('Edit Account')).toBeInTheDocument()
    })

    it('does not render when isOpen is false', () => {
      render(
        <AccountEditModal
          account={mockAccount}
          isOpen={false}
          onClose={mockOnClose}
        />
      )
      expect(screen.queryByText('Edit Account')).not.toBeInTheDocument()
    })

    it('shows account name in input', () => {
      render(
        <AccountEditModal
          account={mockAccount}
          isOpen
          onClose={mockOnClose}
        />
      )
      const nameInput = screen.getByDisplayValue('Groceries')
      expect(nameInput).toBeInTheDocument()
    })
  })

  describe('cache invalidation on update', () => {
    it('invalidates transactions cache when account is updated', async () => {
      const user = setupUser()
      mockUpdateAccount.mockResolvedValueOnce({ ...mockAccount, name: 'Supermarkets' })

      const { queryClient } = render(
        <AccountEditModal
          account={mockAccount}
          isOpen
          onClose={mockOnClose}
        />
      )

      // Spy on invalidateQueries
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      // Change the name
      const nameInput = screen.getByDisplayValue('Groceries')
      await user.clear(nameInput)
      await user.type(nameInput, 'Supermarkets')

      // Submit the form
      await user.click(screen.getByRole('button', { name: /save changes/i }))

      await waitFor(() => {
        expect(mockUpdateAccount).toHaveBeenCalled()
      })

      // Verify that transactions cache is invalidated
      // This prevents the bug where updated account names don't appear in transaction list
      await waitFor(() => {
        expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['transactions'] })
        expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['transaction'] })
      })
    })

    it('invalidates accounts and accountStats cache when account is updated', async () => {
      const user = setupUser()
      mockUpdateAccount.mockResolvedValueOnce({ ...mockAccount, name: 'Supermarkets' })

      const { queryClient } = render(
        <AccountEditModal
          account={mockAccount}
          isOpen
          onClose={mockOnClose}
        />
      )

      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      // Change the name
      const nameInput = screen.getByDisplayValue('Groceries')
      await user.clear(nameInput)
      await user.type(nameInput, 'Supermarkets')

      // Submit
      await user.click(screen.getByRole('button', { name: /save changes/i }))

      await waitFor(() => {
        expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['accounts'] })
        expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['account', '123'] })
        expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['accountStats', '123'] })
      })
    })
  })

  describe('form validation', () => {
    it('disables save button when name is unchanged', () => {
      render(
        <AccountEditModal
          account={mockAccount}
          isOpen
          onClose={mockOnClose}
        />
      )

      const saveButton = screen.getByRole('button', { name: /save changes/i })
      expect(saveButton).toBeDisabled()
    })

    it('enables save button when name is changed', async () => {
      const user = setupUser()
      render(
        <AccountEditModal
          account={mockAccount}
          isOpen
          onClose={mockOnClose}
        />
      )

      const nameInput = screen.getByDisplayValue('Groceries')
      await user.clear(nameInput)
      await user.type(nameInput, 'New Name')

      const saveButton = screen.getByRole('button', { name: /save changes/i })
      expect(saveButton).not.toBeDisabled()
    })
  })
})
