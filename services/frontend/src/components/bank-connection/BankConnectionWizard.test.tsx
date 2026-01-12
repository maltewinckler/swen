import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BankConnectionWizard } from './BankConnectionWizard'
import type { UseBankConnectionReturn, BankConnectionStep } from '@/hooks/useBankConnection'

// Create a mock connection object for testing
function createMockConnection(
  overrides: Partial<UseBankConnectionReturn> = {}
): UseBankConnectionReturn {
  return {
    step: 'find_bank' as BankConnectionStep,
    bankForm: { blz: '', username: '', pin: '', tan_method: '', tan_medium: '' },
    bankLookup: null,
    bankLookupError: '',
    bankError: '',
    isLookingUp: false,
    discoveredTanMethods: [],
    isDiscoveringTan: false,
    tanDiscoveryError: '',
    discoveredAccounts: [],
    accountNames: {},
    isDiscoveringAccounts: false,
    accountDiscoveryError: '',
    connectionResult: null,
    syncDays: 90,
    syncProgress: null,
    syncResult: null,
    syncError: null,
    setStep: vi.fn(),
    setBankForm: vi.fn(),
    setAccountNames: vi.fn(),
    setSyncDays: vi.fn(),
    handleBankLookup: vi.fn(),
    handleDiscoverTanMethods: vi.fn(),
    handleDiscoverAccounts: vi.fn(),
    handleConnect: vi.fn(),
    handleInitialSync: vi.fn(),
    handleSkipSync: vi.fn(),
    reset: vi.fn(),
    ...overrides,
  }
}

describe('BankConnectionWizard', () => {
  describe('find_bank step', () => {
    it('renders bank code input', () => {
      const connection = createMockConnection({ step: 'find_bank' })
      render(<BankConnectionWizard connection={connection} />)

      expect(screen.getByText('Bank Code (BLZ)')).toBeInTheDocument()
      expect(screen.getByPlaceholderText('e.g., 12030000')).toBeInTheDocument()
    })

    it('shows search button', () => {
      const connection = createMockConnection({ step: 'find_bank' })
      render(<BankConnectionWizard connection={connection} />)

      expect(screen.getByRole('button', { name: /search bank/i })).toBeInTheDocument()
    })

    it('shows existing credentials count', () => {
      const connection = createMockConnection({ step: 'find_bank' })
      render(<BankConnectionWizard connection={connection} existingCredentialsCount={2} />)

      expect(screen.getByText(/you have 2 banks connected/i)).toBeInTheDocument()
    })

    it('shows back button when onBack is provided', () => {
      const connection = createMockConnection({ step: 'find_bank' })
      const onBack = vi.fn()
      render(<BankConnectionWizard connection={connection} onBack={onBack} />)

      expect(screen.getByRole('button', { name: /back/i })).toBeInTheDocument()
    })

    it('calls onBack when back button is clicked', async () => {
      const connection = createMockConnection({ step: 'find_bank' })
      const onBack = vi.fn()
      const user = userEvent.setup()

      render(<BankConnectionWizard connection={connection} onBack={onBack} />)
      await user.click(screen.getByRole('button', { name: /back/i }))

      expect(onBack).toHaveBeenCalled()
    })

    it('shows skip button when onSkip is provided', () => {
      const connection = createMockConnection({ step: 'find_bank' })
      const onSkip = vi.fn()
      render(<BankConnectionWizard connection={connection} onSkip={onSkip} />)

      expect(screen.getByRole('button', { name: /skip/i })).toBeInTheDocument()
    })

    it('shows bank lookup error', () => {
      const connection = createMockConnection({
        step: 'find_bank',
        bankLookupError: 'Bank not found',
      })
      render(<BankConnectionWizard connection={connection} />)

      expect(screen.getByText('Bank not found')).toBeInTheDocument()
    })

    it('disables search button when BLZ is not 8 digits', () => {
      const connection = createMockConnection({
        step: 'find_bank',
        bankForm: { blz: '1234', username: '', pin: '', tan_method: '', tan_medium: '' },
      })
      render(<BankConnectionWizard connection={connection} />)

      expect(screen.getByRole('button', { name: /search bank/i })).toBeDisabled()
    })

    it('enables search button when BLZ is 8 digits', () => {
      const connection = createMockConnection({
        step: 'find_bank',
        bankForm: { blz: '12345678', username: '', pin: '', tan_method: '', tan_medium: '' },
      })
      render(<BankConnectionWizard connection={connection} />)

      expect(screen.getByRole('button', { name: /search bank/i })).not.toBeDisabled()
    })

    it('shows loading state during lookup', () => {
      const connection = createMockConnection({
        step: 'find_bank',
        isLookingUp: true,
        bankForm: { blz: '12345678', username: '', pin: '', tan_method: '', tan_medium: '' },
      })
      render(<BankConnectionWizard connection={connection} />)

      expect(screen.getByRole('button', { name: /search bank/i })).toBeDisabled()
    })
  })

  describe('credentials step', () => {
    it('shows bank name', () => {
      const connection = createMockConnection({
        step: 'credentials',
        bankLookup: { name: 'Deutsche Bank', blz: '12345678', fints_url: 'https://test.de' },
      })
      render(<BankConnectionWizard connection={connection} />)

      expect(screen.getByText('Deutsche Bank')).toBeInTheDocument()
    })

    it('shows username and PIN inputs', () => {
      const connection = createMockConnection({
        step: 'credentials',
        bankLookup: { name: 'Test Bank', blz: '12345678', fints_url: 'https://test.de' },
      })
      render(<BankConnectionWizard connection={connection} />)

      expect(screen.getByText('Username / Login ID')).toBeInTheDocument()
      expect(screen.getByText('PIN / Password')).toBeInTheDocument()
    })

    it('shows back button', () => {
      const connection = createMockConnection({
        step: 'credentials',
        bankLookup: { name: 'Test Bank', blz: '12345678', fints_url: 'https://test.de' },
      })
      render(<BankConnectionWizard connection={connection} />)

      expect(screen.getByRole('button', { name: /back/i })).toBeInTheDocument()
    })

    it('calls setStep when back is clicked', async () => {
      const setStep = vi.fn()
      const connection = createMockConnection({
        step: 'credentials',
        bankLookup: { name: 'Test Bank', blz: '12345678', fints_url: 'https://test.de' },
        setStep,
      })
      const user = userEvent.setup()

      render(<BankConnectionWizard connection={connection} />)
      await user.click(screen.getByRole('button', { name: /back/i }))

      expect(setStep).toHaveBeenCalledWith('find_bank')
    })

    it('shows TAN discovery error', () => {
      const connection = createMockConnection({
        step: 'credentials',
        bankLookup: { name: 'Test Bank', blz: '12345678', fints_url: 'https://test.de' },
        tanDiscoveryError: 'Invalid credentials',
      })
      render(<BankConnectionWizard connection={connection} />)

      expect(screen.getByText('Invalid credentials')).toBeInTheDocument()
    })
  })

  describe('tan_discovery step', () => {
    it('shows TAN method options', () => {
      const connection = createMockConnection({
        step: 'tan_discovery',
        discoveredTanMethods: [
          { code: '920', name: 'Push TAN', is_decoupled: true },
          { code: '900', name: 'SMS TAN', is_decoupled: false },
        ],
      })
      render(<BankConnectionWizard connection={connection} />)

      expect(screen.getByText('Push TAN')).toBeInTheDocument()
      expect(screen.getByText('SMS TAN')).toBeInTheDocument()
    })

    it('shows loading state when discovering accounts', () => {
      const connection = createMockConnection({
        step: 'tan_discovery',
        isDiscoveringAccounts: true,
        bankLookup: { name: 'Test Bank', blz: '12345678', fints_url: 'https://test.de' },
      })
      render(<BankConnectionWizard connection={connection} />)

      expect(screen.getByText(/connecting to test bank/i)).toBeInTheDocument()
    })
  })

  describe('review_accounts step', () => {
    it('shows discovered accounts', () => {
      const connection = createMockConnection({
        step: 'review_accounts',
        bankLookup: { name: 'Test Bank', blz: '12345678', fints_url: 'https://test.de' },
        discoveredAccounts: [
          { iban: 'DE89370400440532013000', default_name: 'Girokonto', balance: '2500.00', currency: 'EUR' },
        ],
        accountNames: { 'DE89370400440532013000': 'Girokonto' },
      })
      render(<BankConnectionWizard connection={connection} />)

      expect(screen.getByText('DE89370400440532013000')).toBeInTheDocument()
      expect(screen.getByText('Found 1 account')).toBeInTheDocument()
    })

    it('shows balance for accounts', () => {
      const connection = createMockConnection({
        step: 'review_accounts',
        bankLookup: { name: 'Test Bank', blz: '12345678', fints_url: 'https://test.de' },
        discoveredAccounts: [
          { iban: 'DE89370400440532013000', default_name: 'Girokonto', balance: '2500.00', currency: 'EUR' },
        ],
        accountNames: { 'DE89370400440532013000': 'Girokonto' },
      })
      render(<BankConnectionWizard connection={connection} />)

      expect(screen.getByText(/2\.500,00/)).toBeInTheDocument()
    })

    it('shows import button', () => {
      const connection = createMockConnection({
        step: 'review_accounts',
        bankLookup: { name: 'Test Bank', blz: '12345678', fints_url: 'https://test.de' },
        discoveredAccounts: [],
        accountNames: {},
      })
      render(<BankConnectionWizard connection={connection} />)

      expect(screen.getByRole('button', { name: /import accounts/i })).toBeInTheDocument()
    })
  })

  describe('connecting step', () => {
    it('shows connecting message', () => {
      const connection = createMockConnection({
        step: 'connecting',
        bankLookup: { name: 'Test Bank', blz: '12345678', fints_url: 'https://test.de' },
      })
      render(<BankConnectionWizard connection={connection} />)

      expect(screen.getByText(/connecting to test bank/i)).toBeInTheDocument()
    })
  })

  describe('initial_sync step', () => {
    it('shows success message', () => {
      const connection = createMockConnection({
        step: 'initial_sync',
        bankLookup: { name: 'Test Bank', blz: '12345678', fints_url: 'https://test.de' },
        connectionResult: {
          message: 'Connected',
          accounts_imported: [{ iban: 'DE123', account_name: 'Girokonto' }],
        },
      })
      render(<BankConnectionWizard connection={connection} />)

      expect(screen.getByText('Test Bank')).toBeInTheDocument()
      expect(screen.getByText('1 account imported')).toBeInTheDocument()
    })

    it('shows sync days options', () => {
      const connection = createMockConnection({
        step: 'initial_sync',
        bankLookup: { name: 'Test Bank', blz: '12345678', fints_url: 'https://test.de' },
        connectionResult: {
          message: 'Connected',
          accounts_imported: [{ iban: 'DE123', account_name: 'Girokonto' }],
        },
      })
      render(<BankConnectionWizard connection={connection} />)

      expect(screen.getByText('30 days')).toBeInTheDocument()
      expect(screen.getByText('90 days')).toBeInTheDocument()
      expect(screen.getByText('1 year')).toBeInTheDocument()
      expect(screen.getByText('2 years')).toBeInTheDocument()
    })

    it('shows skip and sync buttons', () => {
      const connection = createMockConnection({
        step: 'initial_sync',
        bankLookup: { name: 'Test Bank', blz: '12345678', fints_url: 'https://test.de' },
        connectionResult: {
          message: 'Connected',
          accounts_imported: [],
        },
      })
      render(<BankConnectionWizard connection={connection} />)

      expect(screen.getByRole('button', { name: /skip/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /sync now/i })).toBeInTheDocument()
    })
  })

  describe('success step', () => {
    it('shows success message without sync result', () => {
      const connection = createMockConnection({
        step: 'success',
        bankLookup: { name: 'Test Bank', blz: '12345678', fints_url: 'https://test.de' },
        connectionResult: {
          message: 'Connection successful',
          accounts_imported: [{ iban: 'DE123', account_name: 'Girokonto' }],
        },
      })
      render(<BankConnectionWizard connection={connection} onDone={vi.fn()} />)

      expect(screen.getByText('Test Bank')).toBeInTheDocument()
      expect(screen.getByText('Connection successful')).toBeInTheDocument()
    })

    it('shows sync stats when sync result is available', () => {
      const connection = createMockConnection({
        step: 'success',
        bankLookup: { name: 'Test Bank', blz: '12345678', fints_url: 'https://test.de' },
        syncResult: {
          success: true,
          synced_at: '2024-01-01',
          start_date: '',
          end_date: '',
          auto_post: false,
          total_fetched: 0,
          total_imported: 50,
          total_skipped: 5,
          total_failed: 0,
          accounts_synced: 2,
          account_stats: [],
          opening_balances: [],
          errors: [],
          opening_balance_account_missing: false,
        },
      })
      render(<BankConnectionWizard connection={connection} onDone={vi.fn()} />)

      expect(screen.getByText('50')).toBeInTheDocument()
      expect(screen.getByText('Imported')).toBeInTheDocument()
    })

    it('shows done button when onDone is provided', () => {
      const connection = createMockConnection({
        step: 'success',
        bankLookup: { name: 'Test Bank', blz: '12345678', fints_url: 'https://test.de' },
      })
      render(<BankConnectionWizard connection={connection} onDone={vi.fn()} />)

      expect(screen.getByRole('button', { name: /done/i })).toBeInTheDocument()
    })

    it('shows add another button when showAddAnother is true', () => {
      const connection = createMockConnection({
        step: 'success',
        bankLookup: { name: 'Test Bank', blz: '12345678', fints_url: 'https://test.de' },
      })
      render(
        <BankConnectionWizard
          connection={connection}
          showAddAnother={true}
          onAddAnother={vi.fn()}
          onDone={vi.fn()}
        />
      )

      expect(screen.getByRole('button', { name: /add another bank/i })).toBeInTheDocument()
    })

    it('calls reset and onAddAnother when add another is clicked', async () => {
      const reset = vi.fn()
      const onAddAnother = vi.fn()
      const connection = createMockConnection({
        step: 'success',
        bankLookup: { name: 'Test Bank', blz: '12345678', fints_url: 'https://test.de' },
        reset,
      })
      const user = userEvent.setup()

      render(
        <BankConnectionWizard
          connection={connection}
          showAddAnother={true}
          onAddAnother={onAddAnother}
          onDone={vi.fn()}
        />
      )

      await user.click(screen.getByRole('button', { name: /add another bank/i }))

      expect(reset).toHaveBeenCalled()
      expect(onAddAnother).toHaveBeenCalled()
    })
  })

  describe('error step', () => {
    it('shows sync error', () => {
      const connection = createMockConnection({
        step: 'error',
        syncError: 'TAN verification failed',
      })
      render(<BankConnectionWizard connection={connection} />)

      expect(screen.getByText('Sync Failed')).toBeInTheDocument()
      expect(screen.getByText('TAN verification failed')).toBeInTheDocument()
    })

    it('shows bank error when no sync error', () => {
      const connection = createMockConnection({
        step: 'error',
        bankError: 'Connection timeout',
      })
      render(<BankConnectionWizard connection={connection} />)

      expect(screen.getByText('Connection Failed')).toBeInTheDocument()
      expect(screen.getByText('Connection timeout')).toBeInTheDocument()
    })

    it('shows try again button', () => {
      const connection = createMockConnection({
        step: 'error',
        bankError: 'Error occurred',
      })
      render(<BankConnectionWizard connection={connection} />)

      expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument()
    })

    it('calls reset when try again is clicked', async () => {
      const reset = vi.fn()
      const connection = createMockConnection({
        step: 'error',
        bankError: 'Error occurred',
        reset,
      })
      const user = userEvent.setup()

      render(<BankConnectionWizard connection={connection} />)
      await user.click(screen.getByRole('button', { name: /try again/i }))

      expect(reset).toHaveBeenCalled()
    })
  })

  describe('custom labels', () => {
    it('uses custom done button label', () => {
      const connection = createMockConnection({
        step: 'success',
        bankLookup: { name: 'Test Bank', blz: '12345678', fints_url: 'https://test.de' },
      })
      render(
        <BankConnectionWizard
          connection={connection}
          onDone={vi.fn()}
          labels={{ doneButton: 'Continue to Dashboard' }}
        />
      )

      expect(screen.getByRole('button', { name: /continue to dashboard/i })).toBeInTheDocument()
    })

    it('uses custom skip button label', () => {
      const connection = createMockConnection({ step: 'find_bank' })
      render(
        <BankConnectionWizard
          connection={connection}
          onSkip={vi.fn()}
          labels={{ skipButton: 'Skip for now' }}
        />
      )

      expect(screen.getByRole('button', { name: /skip for now/i })).toBeInTheDocument()
    })

    it('uses custom search button label', () => {
      const connection = createMockConnection({
        step: 'find_bank',
        bankForm: { blz: '12345678', username: '', pin: '', tan_method: '', tan_medium: '' },
      })
      render(
        <BankConnectionWizard
          connection={connection}
          labels={{ searchButton: 'Find Bank' }}
        />
      )

      expect(screen.getByRole('button', { name: /find bank/i })).toBeInTheDocument()
    })
  })
})
