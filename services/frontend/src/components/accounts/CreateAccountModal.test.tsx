import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { render, setupUser } from '../../../tests/test-utils'
import { CreateAccountModal } from './CreateAccountModal'

vi.mock('@/api', () => ({
  createAccount: vi.fn(),
  createExternalAccount: vi.fn(),
  listAccounts: vi.fn(),
}))

import { createAccount, listAccounts } from '@/api'

const mockCreateAccount = createAccount as ReturnType<typeof vi.fn>
const mockListAccounts = listAccounts as ReturnType<typeof vi.fn>

const existingExpenseAccounts = [
  {
    id: 'parent-1',
    name: 'Food & Drink',
    account_number: '4000',
    account_type: 'EXPENSE',
    is_active: true,
    parent_id: null,
    currency: 'EUR',
    created_at: '2024-01-01T00:00:00Z',
  },
]

describe('CreateAccountModal', () => {
  const mockOnClose = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    mockListAccounts.mockResolvedValue({ items: existingExpenseAccounts, total: 1 })
  })

  it('shows a Parent Account selector listing same-type accounts', async () => {
    render(<CreateAccountModal isOpen onClose={mockOnClose} />)

    await waitFor(() => {
      expect(screen.getByText('Parent Account')).toBeInTheDocument()
    })

    const parentSelect = screen.getByRole('combobox')
    await waitFor(() => {
      expect(parentSelect).toHaveTextContent('Food & Drink')
    })
  })

  it('sends parent_id through to createAccount when a parent is selected', async () => {
    const user = setupUser()
    mockCreateAccount.mockResolvedValueOnce({ id: 'new-account' })

    render(<CreateAccountModal isOpen onClose={mockOnClose} />)

    await user.type(screen.getByPlaceholderText('e.g., Groceries'), 'Groceries')

    const parentSelect = await screen.findByRole('combobox')
    await waitFor(() => expect(parentSelect).toHaveTextContent('Food & Drink'))
    await user.selectOptions(parentSelect, 'parent-1')

    await user.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => {
      expect(mockCreateAccount).toHaveBeenCalledWith(
        expect.objectContaining({ parent_id: 'parent-1' })
      )
    })
  })

  it('hides the Parent Account field once an IBAN is entered for an asset account', async () => {
    const user = setupUser()

    render(<CreateAccountModal isOpen onClose={mockOnClose} />)

    await user.click(screen.getByRole('button', { name: /bank \/ savings/i }))

    await waitFor(() => {
      expect(screen.getByText('Parent Account')).toBeInTheDocument()
    })

    await user.type(screen.getByPlaceholderText(/DE89/), 'DE89370400440532013000')

    await waitFor(() => {
      expect(screen.queryByText('Parent Account')).not.toBeInTheDocument()
    })
  })

  it('clears a selected parent when the account type changes', async () => {
    const user = setupUser()

    render(<CreateAccountModal isOpen onClose={mockOnClose} />)

    const parentSelect = await screen.findByRole('combobox')
    await waitFor(() => expect(parentSelect).toHaveTextContent('Food & Drink'))
    await user.selectOptions(parentSelect, 'parent-1')
    expect(parentSelect).toHaveValue('parent-1')

    await user.click(screen.getByRole('button', { name: /income source/i }))
    await user.click(screen.getByRole('button', { name: /expense category/i }))

    const resetSelect = await screen.findByRole('combobox')
    expect(resetSelect).toHaveValue('')
  })
})
