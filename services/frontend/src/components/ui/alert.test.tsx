import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Alert, InlineAlert } from './alert'

describe('Alert', () => {
  describe('rendering', () => {
    it('renders children content', () => {
      render(<Alert>Alert message</Alert>)
      expect(screen.getByText('Alert message')).toBeInTheDocument()
    })

    it('renders with title', () => {
      render(<Alert title="Important">Alert content</Alert>)
      expect(screen.getByText('Important')).toBeInTheDocument()
      expect(screen.getByText('Alert content')).toBeInTheDocument()
    })

    it('applies custom className', () => {
      render(<Alert className="custom-class">Alert</Alert>)
      expect(document.querySelector('.custom-class')).toBeInTheDocument()
    })
  })

  describe('variants', () => {
    it('applies info variant by default', () => {
      render(<Alert>Info alert</Alert>)
      const container = screen.getByText('Info alert').closest('.p-3')
      expect(container).toHaveClass('text-accent-info')
    })

    it('applies success variant', () => {
      render(<Alert variant="success">Success alert</Alert>)
      const container = screen.getByText('Success alert').closest('.p-3')
      expect(container).toHaveClass('text-accent-success')
    })

    it('applies warning variant', () => {
      render(<Alert variant="warning">Warning alert</Alert>)
      const container = screen.getByText('Warning alert').closest('.p-3')
      expect(container).toHaveClass('text-accent-warning')
    })

    it('applies danger variant', () => {
      render(<Alert variant="danger">Danger alert</Alert>)
      const container = screen.getByText('Danger alert').closest('.p-3')
      expect(container).toHaveClass('text-accent-danger')
    })
  })

  describe('icon', () => {
    it('shows icon by default', () => {
      render(<Alert>With icon</Alert>)
      const svg = document.querySelector('svg')
      expect(svg).toBeInTheDocument()
    })

    it('hides icon when showIcon is false', () => {
      render(<Alert showIcon={false}>No icon</Alert>)
      // When showIcon is false, there should be no SVG in the alert
      const container = screen.getByText('No icon').closest('.p-3')
      const svg = container?.querySelector('svg')
      expect(svg).not.toBeInTheDocument()
    })

    it('shows correct icon for each variant', () => {
      const { rerender } = render(<Alert variant="info">Info</Alert>)
      expect(document.querySelector('svg')).toBeInTheDocument()

      rerender(<Alert variant="success">Success</Alert>)
      expect(document.querySelector('svg')).toBeInTheDocument()

      rerender(<Alert variant="warning">Warning</Alert>)
      expect(document.querySelector('svg')).toBeInTheDocument()

      rerender(<Alert variant="danger">Danger</Alert>)
      expect(document.querySelector('svg')).toBeInTheDocument()
    })
  })

  describe('title and content', () => {
    it('styles title as font-medium', () => {
      render(<Alert title="Title">Content</Alert>)
      expect(screen.getByText('Title')).toHaveClass('font-medium')
    })

    it('styles title as primary text', () => {
      render(<Alert title="Title">Content</Alert>)
      expect(screen.getByText('Title')).toHaveClass('text-text-primary')
    })

    it('renders content correctly when title is present', () => {
      render(<Alert title="Title">Content</Alert>)
      // Both title and content should be present
      expect(screen.getByText('Title')).toBeInTheDocument()
      expect(screen.getByText('Content')).toBeInTheDocument()
    })
  })

  describe('styling', () => {
    it('has rounded corners', () => {
      render(<Alert>Rounded</Alert>)
      const container = screen.getByText('Rounded').closest('.p-3')
      expect(container).toHaveClass('rounded-lg')
    })

    it('has border', () => {
      render(<Alert>Bordered</Alert>)
      const container = screen.getByText('Bordered').closest('.p-3')
      expect(container).toHaveClass('border')
    })
  })
})

describe('InlineAlert', () => {
  describe('rendering', () => {
    it('renders children content', () => {
      render(<InlineAlert>Inline message</InlineAlert>)
      expect(screen.getByText('Inline message')).toBeInTheDocument()
    })

    it('applies custom className', () => {
      render(<InlineAlert className="custom-class">Alert</InlineAlert>)
      expect(document.querySelector('.custom-class')).toBeInTheDocument()
    })
  })

  describe('variants', () => {
    it('applies info variant by default', () => {
      render(<InlineAlert>Info</InlineAlert>)
      const container = screen.getByText('Info')
      expect(container).toHaveClass('text-accent-info')
    })

    it('applies success variant', () => {
      render(<InlineAlert variant="success">Success</InlineAlert>)
      expect(screen.getByText('Success')).toHaveClass('text-accent-success')
    })

    it('applies warning variant', () => {
      render(<InlineAlert variant="warning">Warning</InlineAlert>)
      expect(screen.getByText('Warning')).toHaveClass('text-accent-warning')
    })

    it('applies danger variant', () => {
      render(<InlineAlert variant="danger">Danger</InlineAlert>)
      expect(screen.getByText('Danger')).toHaveClass('text-accent-danger')
    })
  })

  describe('styling', () => {
    it('has no icon (simpler than Alert)', () => {
      render(<InlineAlert>No icon</InlineAlert>)
      const svg = screen.getByText('No icon').closest('.p-3')?.querySelector('svg')
      expect(svg).not.toBeInTheDocument()
    })

    it('has padding', () => {
      render(<InlineAlert>Padded</InlineAlert>)
      expect(screen.getByText('Padded')).toHaveClass('p-3')
    })

    it('has rounded corners', () => {
      render(<InlineAlert>Rounded</InlineAlert>)
      expect(screen.getByText('Rounded')).toHaveClass('rounded-lg')
    })
  })
})

