import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SyncProgressDisplay } from './SyncProgressDisplay'
import type { SyncProgress } from '@/hooks/useSyncProgress'

describe('SyncProgressDisplay', () => {
  describe('initializing state', () => {
    it('shows initializing message when progress is null', () => {
      render(<SyncProgressDisplay progress={null} />)

      expect(screen.getByText('Initializing sync...')).toBeInTheDocument()
    })

    it('shows spinner when initializing', () => {
      render(<SyncProgressDisplay progress={null} />)

      const spinner = document.querySelector('.animate-spin')
      expect(spinner).toBeInTheDocument()
    })
  })

  describe('connecting phase', () => {
    it('shows active fetch step', () => {
      const progress: SyncProgress = {
        phase: 'connecting',
        currentAccount: 'DE123',
        currentAccountName: 'Girokonto',
        accountIndex: 1,
        totalAccounts: 2,
        transactionsCurrent: 0,
        transactionsTotal: 0,
        lastMessage: 'Connecting...',
      }

      render(<SyncProgressDisplay progress={progress} />)

      expect(screen.getByText('Fetching transactions from bank')).toBeInTheDocument()
    })

    it('shows account info', () => {
      const progress: SyncProgress = {
        phase: 'connecting',
        currentAccount: 'DE123',
        currentAccountName: 'Girokonto',
        accountIndex: 1,
        totalAccounts: 2,
        transactionsCurrent: 0,
        transactionsTotal: 0,
        lastMessage: 'Connecting...',
      }

      render(<SyncProgressDisplay progress={progress} />)

      expect(screen.getByText('Account 1 of 2')).toBeInTheDocument()
      expect(screen.getByText('Girokonto')).toBeInTheDocument()
    })

    it('shows TAN approval notice during connecting', () => {
      const progress: SyncProgress = {
        phase: 'connecting',
        currentAccount: 'DE123',
        currentAccountName: 'Girokonto',
        accountIndex: 1,
        totalAccounts: 1,
        transactionsCurrent: 0,
        transactionsTotal: 0,
        lastMessage: 'Connecting...',
      }

      render(<SyncProgressDisplay progress={progress} />)

      // TANApprovalNotice should be rendered - check for its warning background
      const tanNotice = document.querySelector('.bg-accent-warning\\/10')
      expect(tanNotice).toBeInTheDocument()
    })
  })

  describe('fetching phase', () => {
    it('shows fetching as active', () => {
      const progress: SyncProgress = {
        phase: 'fetching',
        currentAccount: 'DE123',
        currentAccountName: 'Girokonto',
        accountIndex: 1,
        totalAccounts: 1,
        transactionsCurrent: 0,
        transactionsTotal: 50,
        lastMessage: 'Fetching...',
      }

      render(<SyncProgressDisplay progress={progress} />)

      expect(screen.getByText('Fetched 50 transactions from bank')).toBeInTheDocument()
    })

    it('shows pending classify step', () => {
      const progress: SyncProgress = {
        phase: 'fetching',
        currentAccount: 'DE123',
        currentAccountName: 'Girokonto',
        accountIndex: 1,
        totalAccounts: 1,
        transactionsCurrent: 0,
        transactionsTotal: 50,
        lastMessage: 'Fetching...',
      }

      render(<SyncProgressDisplay progress={progress} />)

      expect(screen.getByText('Classifying transactions')).toBeInTheDocument()
    })
  })

  describe('classifying phase', () => {
    it('shows progress bar', () => {
      const progress: SyncProgress = {
        phase: 'classifying',
        currentAccount: 'DE123',
        currentAccountName: 'Girokonto',
        accountIndex: 1,
        totalAccounts: 1,
        transactionsCurrent: 25,
        transactionsTotal: 50,
        lastMessage: 'Classifying...',
      }

      render(<SyncProgressDisplay progress={progress} />)

      // Progress bar should be present
      const progressBar = document.querySelector('.bg-accent-primary')
      expect(progressBar).toBeInTheDocument()
      expect(progressBar).toHaveStyle({ width: '50%' })
    })

    it('shows progress count', () => {
      const progress: SyncProgress = {
        phase: 'classifying',
        currentAccount: 'DE123',
        currentAccountName: 'Girokonto',
        accountIndex: 1,
        totalAccounts: 1,
        transactionsCurrent: 25,
        transactionsTotal: 50,
        lastMessage: 'Classifying...',
      }

      render(<SyncProgressDisplay progress={progress} />)

      expect(screen.getByText('25 / 50')).toBeInTheDocument()
    })

    it('shows classifying label with progress', () => {
      const progress: SyncProgress = {
        phase: 'classifying',
        currentAccount: 'DE123',
        currentAccountName: 'Girokonto',
        accountIndex: 1,
        totalAccounts: 1,
        transactionsCurrent: 10,
        transactionsTotal: 50,
        lastMessage: 'Classifying...',
      }

      render(<SyncProgressDisplay progress={progress} />)

      expect(screen.getByText('Classifying transactions (10/50)')).toBeInTheDocument()
    })

    it('shows last classified transaction', () => {
      const progress: SyncProgress = {
        phase: 'classifying',
        currentAccount: 'DE123',
        currentAccountName: 'Girokonto',
        accountIndex: 1,
        totalAccounts: 1,
        transactionsCurrent: 10,
        transactionsTotal: 50,
        lastMessage: 'Classifying...',
        lastTransactionDescription: 'REWE Supermarket',
        lastCounterAccountName: 'Groceries',
      }

      render(<SyncProgressDisplay progress={progress} />)

      expect(screen.getByText('Last classified:')).toBeInTheDocument()
      expect(screen.getByText('"REWE Supermarket"')).toBeInTheDocument()
      expect(screen.getByText('→ Groceries')).toBeInTheDocument()
    })

    it('does not show TAN notice during classification', () => {
      const progress: SyncProgress = {
        phase: 'classifying',
        currentAccount: 'DE123',
        currentAccountName: 'Girokonto',
        accountIndex: 1,
        totalAccounts: 1,
        transactionsCurrent: 10,
        transactionsTotal: 50,
        lastMessage: 'Classifying...',
      }

      render(<SyncProgressDisplay progress={progress} />)

      expect(screen.queryByText(/approve/i)).not.toBeInTheDocument()
    })
  })

  describe('complete phase', () => {
    it('shows completed fetch step', () => {
      const progress: SyncProgress = {
        phase: 'complete',
        currentAccount: 'DE123',
        currentAccountName: 'Girokonto',
        accountIndex: 1,
        totalAccounts: 1,
        transactionsCurrent: 50,
        transactionsTotal: 50,
        lastMessage: 'Complete',
      }

      render(<SyncProgressDisplay progress={progress} />)

      expect(screen.getByText('Fetched 50 transactions from bank')).toBeInTheDocument()
    })

    it('shows classified count when complete with transactions', () => {
      const progress: SyncProgress = {
        phase: 'complete',
        currentAccount: 'DE123',
        currentAccountName: 'Girokonto',
        accountIndex: 1,
        totalAccounts: 1,
        transactionsCurrent: 50,
        transactionsTotal: 50,
        lastMessage: 'Complete',
      }

      render(<SyncProgressDisplay progress={progress} />)

      expect(screen.getByText('Classified 50 transactions')).toBeInTheDocument()
    })

    it('shows no transactions message when complete with 0 transactions', () => {
      const progress: SyncProgress = {
        phase: 'complete',
        currentAccount: 'DE123',
        currentAccountName: 'Girokonto',
        accountIndex: 1,
        totalAccounts: 1,
        transactionsCurrent: 0,
        transactionsTotal: 0,
        lastMessage: 'Complete',
      }

      render(<SyncProgressDisplay progress={progress} />)

      expect(screen.getByText('No new transactions to classify')).toBeInTheDocument()
    })

    it('shows checkmark icons for completed steps', () => {
      const progress: SyncProgress = {
        phase: 'complete',
        currentAccount: 'DE123',
        currentAccountName: 'Girokonto',
        accountIndex: 1,
        totalAccounts: 1,
        transactionsCurrent: 50,
        transactionsTotal: 50,
        lastMessage: 'Complete',
      }

      render(<SyncProgressDisplay progress={progress} />)

      // Both steps should have success checkmarks
      const successIcons = document.querySelectorAll('.text-accent-success')
      expect(successIcons.length).toBeGreaterThanOrEqual(2)
    })
  })

  describe('multiple accounts', () => {
    it('shows correct account index', () => {
      const progress: SyncProgress = {
        phase: 'fetching',
        currentAccount: 'DE456',
        currentAccountName: 'Sparkonto',
        accountIndex: 2,
        totalAccounts: 3,
        transactionsCurrent: 0,
        transactionsTotal: 20,
        lastMessage: 'Fetching...',
      }

      render(<SyncProgressDisplay progress={progress} />)

      expect(screen.getByText('Account 2 of 3')).toBeInTheDocument()
      expect(screen.getByText('Sparkonto')).toBeInTheDocument()
    })
  })

  describe('custom className', () => {
    it('applies custom className', () => {
      const progress: SyncProgress = {
        phase: 'complete',
        currentAccount: 'DE123',
        currentAccountName: 'Girokonto',
        accountIndex: 1,
        totalAccounts: 1,
        transactionsCurrent: 0,
        transactionsTotal: 0,
        lastMessage: 'Complete',
      }

      render(<SyncProgressDisplay progress={progress} className="custom-class" />)

      expect(document.querySelector('.custom-class')).toBeInTheDocument()
    })
  })
})
