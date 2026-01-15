import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Input } from './input'
import { Search, Eye } from 'lucide-react'

describe('Input', () => {
  describe('rendering', () => {
    it('renders an input element', () => {
      render(<Input />)
      expect(screen.getByRole('textbox')).toBeInTheDocument()
    })

    it('renders with placeholder', () => {
      render(<Input placeholder="Enter text..." />)
      expect(screen.getByPlaceholderText('Enter text...')).toBeInTheDocument()
    })

    it('renders with custom className', () => {
      render(<Input className="custom-class" />)
      expect(screen.getByRole('textbox')).toHaveClass('custom-class')
    })

    it('renders different input types', () => {
      const { rerender } = render(<Input type="email" />)
      expect(screen.getByRole('textbox')).toHaveAttribute('type', 'email')

      rerender(<Input type="password" />)
      // Password inputs don't have the textbox role
      expect(document.querySelector('input[type="password"]')).toBeInTheDocument()
    })
  })

  describe('value and onChange', () => {
    it('renders with initial value', () => {
      render(<Input value="Initial value" readOnly />)
      expect(screen.getByDisplayValue('Initial value')).toBeInTheDocument()
    })

    it('calls onChange when user types', async () => {
      const handleChange = vi.fn()
      const user = userEvent.setup()

      render(<Input onChange={handleChange} />)
      await user.type(screen.getByRole('textbox'), 'Hello')

      expect(handleChange).toHaveBeenCalledTimes(5)
    })

    it('updates value on user input', async () => {
      const user = userEvent.setup()
      render(<Input />)

      const input = screen.getByRole('textbox')
      await user.type(input, 'Hello World')

      expect(input).toHaveValue('Hello World')
    })
  })

  describe('error state', () => {
    it('applies error styles when hasError is true', () => {
      render(<Input hasError />)
      expect(screen.getByRole('textbox')).toHaveClass('border-accent-danger')
    })

    it('does not apply error styles when hasError is false', () => {
      render(<Input hasError={false} />)
      expect(screen.getByRole('textbox')).not.toHaveClass('border-accent-danger')
    })

    it('applies normal border styles when no hasError prop', () => {
      render(<Input placeholder="Normal input" />)
      expect(screen.getByRole('textbox')).toHaveClass('border-border-default')
    })
  })

  describe('icons', () => {
    it('renders left icon', () => {
      render(<Input leftIcon={<Search data-testid="left-icon" />} />)
      expect(screen.getByTestId('left-icon')).toBeInTheDocument()
    })

    it('renders right icon', () => {
      render(<Input rightIcon={<Eye data-testid="right-icon" />} />)
      expect(screen.getByTestId('right-icon')).toBeInTheDocument()
    })

    it('applies padding for left icon', () => {
      render(<Input leftIcon={<Search />} />)
      expect(screen.getByRole('textbox')).toHaveClass('pl-10')
    })

    it('applies padding for right icon', () => {
      render(<Input rightIcon={<Eye />} />)
      expect(screen.getByRole('textbox')).toHaveClass('pr-10')
    })
  })

  describe('disabled state', () => {
    it('is disabled when disabled prop is true', () => {
      render(<Input disabled />)
      expect(screen.getByRole('textbox')).toBeDisabled()
    })

    it('applies disabled styles', () => {
      render(<Input disabled />)
      expect(screen.getByRole('textbox')).toHaveClass('disabled:opacity-50')
    })

    it('does not accept input when disabled', async () => {
      const user = userEvent.setup()
      render(<Input disabled />)

      const input = screen.getByRole('textbox')
      await user.type(input, 'Test')

      expect(input).toHaveValue('')
    })
  })

  describe('accessibility', () => {
    it('supports aria-label', () => {
      render(<Input aria-label="Email address" />)
      expect(screen.getByLabelText('Email address')).toBeInTheDocument()
    })

    it('supports aria-describedby', () => {
      render(
        <>
          <Input aria-describedby="helper" />
          <span id="helper">Enter your email</span>
        </>
      )
      expect(screen.getByRole('textbox')).toHaveAttribute('aria-describedby', 'helper')
    })
  })

  describe('ref forwarding', () => {
    it('forwards ref to the input element', () => {
      const ref = vi.fn()
      render(<Input ref={ref} />)
      expect(ref).toHaveBeenCalled()
    })
  })
})
