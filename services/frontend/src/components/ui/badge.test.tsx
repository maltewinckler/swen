import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Badge } from './badge'

describe('Badge', () => {
  describe('rendering', () => {
    it('renders children', () => {
      render(<Badge>Active</Badge>)
      expect(screen.getByText('Active')).toBeInTheDocument()
    })

    it('renders as a span element', () => {
      render(<Badge>Status</Badge>)
      expect(screen.getByText('Status').tagName).toBe('SPAN')
    })

    it('applies custom className', () => {
      render(<Badge className="custom-class">Badge</Badge>)
      expect(screen.getByText('Badge')).toHaveClass('custom-class')
    })
  })

  describe('variants', () => {
    it('applies default variant styles', () => {
      render(<Badge>Default</Badge>)
      const badge = screen.getByText('Default')
      expect(badge).toHaveClass('bg-bg-elevated', 'text-text-secondary')
    })

    it('applies success variant styles', () => {
      render(<Badge variant="success">Success</Badge>)
      const badge = screen.getByText('Success')
      expect(badge).toHaveClass('text-accent-success')
    })

    it('applies danger variant styles', () => {
      render(<Badge variant="danger">Danger</Badge>)
      const badge = screen.getByText('Danger')
      expect(badge).toHaveClass('text-accent-danger')
    })

    it('applies warning variant styles', () => {
      render(<Badge variant="warning">Warning</Badge>)
      const badge = screen.getByText('Warning')
      expect(badge).toHaveClass('text-accent-warning')
    })

    it('applies info variant styles', () => {
      render(<Badge variant="info">Info</Badge>)
      const badge = screen.getByText('Info')
      expect(badge).toHaveClass('text-accent-info')
    })
  })

  describe('styling', () => {
    it('has rounded-full corners', () => {
      render(<Badge>Rounded</Badge>)
      expect(screen.getByText('Rounded')).toHaveClass('rounded-full')
    })

    it('has small text size', () => {
      render(<Badge>Small</Badge>)
      expect(screen.getByText('Small')).toHaveClass('text-xs')
    })

    it('has medium font weight', () => {
      render(<Badge>Medium</Badge>)
      expect(screen.getByText('Medium')).toHaveClass('font-medium')
    })

    it('uses inline-flex for layout', () => {
      render(<Badge>Flex</Badge>)
      expect(screen.getByText('Flex')).toHaveClass('inline-flex')
    })
  })

  describe('accessibility', () => {
    it('forwards additional HTML attributes', () => {
      render(<Badge data-testid="test-badge" role="status">Status</Badge>)
      expect(screen.getByTestId('test-badge')).toBeInTheDocument()
      expect(screen.getByRole('status')).toBeInTheDocument()
    })
  })
})
