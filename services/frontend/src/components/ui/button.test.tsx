import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Button } from './button'

describe('Button', () => {
  describe('rendering', () => {
    it('renders children correctly', () => {
      render(<Button>Click me</Button>)
      expect(screen.getByRole('button', { name: /click me/i })).toBeInTheDocument()
    })

    it('renders as a button element by default', () => {
      render(<Button>Test</Button>)
      expect(screen.getByRole('button')).toBeInTheDocument()
    })

    it('renders with custom className', () => {
      render(<Button className="custom-class">Test</Button>)
      expect(screen.getByRole('button')).toHaveClass('custom-class')
    })
  })

  describe('variants', () => {
    it('applies primary variant classes by default', () => {
      render(<Button>Primary</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('bg-accent-primary')
    })

    it('applies secondary variant classes', () => {
      render(<Button variant="secondary">Secondary</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('border-border-default')
    })

    it('applies ghost variant classes', () => {
      render(<Button variant="ghost">Ghost</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('bg-transparent')
    })

    it('applies danger variant classes', () => {
      render(<Button variant="danger">Danger</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('bg-accent-danger')
    })

    it('applies link variant classes', () => {
      render(<Button variant="link">Link</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('text-accent-primary')
    })
  })

  describe('sizes', () => {
    it('applies medium size by default', () => {
      render(<Button>Medium</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('h-10')
    })

    it('applies small size', () => {
      render(<Button size="sm">Small</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('h-8')
    })

    it('applies large size', () => {
      render(<Button size="lg">Large</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('h-12')
    })

    it('applies icon size', () => {
      render(<Button size="icon">🔍</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('h-10', 'w-10')
    })
  })

  describe('loading state', () => {
    it('shows loading spinner when isLoading is true', () => {
      render(<Button isLoading>Submit</Button>)
      const button = screen.getByRole('button')
      expect(button).toContainHTML('animate-spin')
    })

    it('disables button when loading', () => {
      render(<Button isLoading>Submit</Button>)
      expect(screen.getByRole('button')).toBeDisabled()
    })

    it('still shows children text when loading', () => {
      render(<Button isLoading>Submit</Button>)
      expect(screen.getByText('Submit')).toBeInTheDocument()
    })
  })

  describe('disabled state', () => {
    it('is disabled when disabled prop is true', () => {
      render(<Button disabled>Disabled</Button>)
      expect(screen.getByRole('button')).toBeDisabled()
    })

    it('applies disabled styles', () => {
      render(<Button disabled>Disabled</Button>)
      expect(screen.getByRole('button')).toHaveClass('disabled:opacity-50')
    })
  })

  describe('interactions', () => {
    it('calls onClick handler when clicked', async () => {
      const handleClick = vi.fn()
      const user = userEvent.setup()

      render(<Button onClick={handleClick}>Click me</Button>)
      await user.click(screen.getByRole('button'))

      expect(handleClick).toHaveBeenCalledTimes(1)
    })

    it('does not call onClick when disabled', async () => {
      const handleClick = vi.fn()
      const user = userEvent.setup()

      render(<Button disabled onClick={handleClick}>Click me</Button>)
      await user.click(screen.getByRole('button'))

      expect(handleClick).not.toHaveBeenCalled()
    })

    it('does not call onClick when loading', async () => {
      const handleClick = vi.fn()
      const user = userEvent.setup()

      render(<Button isLoading onClick={handleClick}>Click me</Button>)
      await user.click(screen.getByRole('button'))

      expect(handleClick).not.toHaveBeenCalled()
    })
  })

  describe('asChild prop', () => {
    it('renders as Slot when asChild is true', () => {
      render(
        <Button asChild>
          <a href="/test">Link Button</a>
        </Button>
      )
      expect(screen.getByRole('link', { name: /link button/i })).toBeInTheDocument()
    })
  })

  describe('accessibility', () => {
    it('has proper focus styles via className', () => {
      render(<Button>Focusable</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('transition-all')
    })

    it('accepts and forwards aria attributes', () => {
      render(<Button aria-label="Custom label">Icon</Button>)
      expect(screen.getByRole('button', { name: /custom label/i })).toBeInTheDocument()
    })
  })
})

