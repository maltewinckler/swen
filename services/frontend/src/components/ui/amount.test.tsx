import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Amount } from './amount'

describe('Amount', () => {
  describe('rendering', () => {
    it('renders formatted currency value', () => {
      render(<Amount value={1234.56} />)
      // Default locale is de-DE (e.g., "1.234,56 €")
      expect(screen.getByText(/1\.234,56\s*€/)).toBeInTheDocument()
    })

    it('renders string value', () => {
      render(<Amount value="1234.56" />)
      expect(screen.getByText(/1\.234,56\s*€/)).toBeInTheDocument()
    })

    it('applies custom className', () => {
      render(<Amount value={100} className="custom-class" />)
      expect(screen.getByText(/100,00\s*€/)).toHaveClass('custom-class')
    })

    it('renders as a span element', () => {
      render(<Amount value={100} />)
      expect(screen.getByText(/100,00\s*€/).tagName).toBe('SPAN')
    })
  })

  describe('sign display', () => {
    it('does not show sign by default', () => {
      render(<Amount value={100} />)
      expect(screen.queryByText(/\+/)).not.toBeInTheDocument()
    })

    it('shows positive sign when showSign is true', () => {
      render(<Amount value={100} showSign />)
      expect(screen.getByText(/\+100,00\s*€/)).toBeInTheDocument()
    })

    it('shows negative sign when showSign is true and value is negative', () => {
      render(<Amount value={-100} showSign />)
      expect(screen.getByText(/-100,00\s*€/)).toBeInTheDocument()
    })

    it('shows no sign for zero with showSign', () => {
      render(<Amount value={0} showSign />)
      expect(screen.getByText(/0,00\s*€/)).toBeInTheDocument()
      // Should not have + or - before the amount
      expect(screen.queryByText(/[+-]0,00\s*€/)).not.toBeInTheDocument()
    })
  })

  describe('colorization', () => {
    it('applies success color for positive values by default', () => {
      render(<Amount value={100} />)
      expect(screen.getByText(/100,00\s*€/)).toHaveClass('text-accent-success')
    })

    it('applies danger color for negative values by default', () => {
      render(<Amount value={-100} />)
      expect(screen.getByText(/100,00\s*€/)).toHaveClass('text-accent-danger')
    })

    it('does not apply color when colorize is false', () => {
      render(<Amount value={100} colorize={false} />)
      const amount = screen.getByText(/100,00\s*€/)
      expect(amount).not.toHaveClass('text-accent-success')
      expect(amount).not.toHaveClass('text-accent-danger')
    })

    it('does not color zero values', () => {
      render(<Amount value={0} />)
      const amount = screen.getByText(/0,00\s*€/)
      expect(amount).not.toHaveClass('text-accent-success')
      expect(amount).not.toHaveClass('text-accent-danger')
    })
  })

  describe('currency', () => {
    it('uses EUR by default', () => {
      render(<Amount value={100} />)
      expect(screen.getByText(/€/)).toBeInTheDocument()
    })

    it('supports USD currency', () => {
      render(<Amount value={100} currency="USD" />)
      expect(screen.getByText(/\$/)).toBeInTheDocument()
    })

    it('supports GBP currency', () => {
      render(<Amount value={100} currency="GBP" />)
      expect(screen.getByText(/£/)).toBeInTheDocument()
    })
  })

  describe('formatting', () => {
    it('uses monospace font for numbers', () => {
      render(<Amount value={100} />)
      expect(screen.getByText(/100,00\s*€/)).toHaveClass('font-mono')
    })

    it('uses tabular numbers', () => {
      render(<Amount value={100} />)
      expect(screen.getByText(/100,00\s*€/)).toHaveClass('tabular-nums')
    })

    it('shows absolute value regardless of sign', () => {
      render(<Amount value={-500} />)
      // Should show 500.00, not -500.00 in the formatted part
      expect(screen.getByText(/500,00\s*€/)).toBeInTheDocument()
    })
  })

  describe('edge cases', () => {
    it('handles very large numbers', () => {
      render(<Amount value={1000000} />)
      expect(screen.getByText(/1\.000\.000,00\s*€/)).toBeInTheDocument()
    })

    it('handles very small numbers', () => {
      render(<Amount value={0.01} />)
      expect(screen.getByText(/0,01\s*€/)).toBeInTheDocument()
    })

    it('handles string numbers with decimals', () => {
      render(<Amount value="99.99" />)
      expect(screen.getByText(/99,99\s*€/)).toBeInTheDocument()
    })
  })
})
