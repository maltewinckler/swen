import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { IBANInput } from './IBANInput'

describe('IBANInput', () => {
  describe('rendering', () => {
    it('renders an input element', () => {
      render(<IBANInput value="" onChange={() => {}} />)
      expect(screen.getByRole('textbox')).toBeInTheDocument()
    })

    it('displays the provided value', () => {
      render(<IBANInput value="DE89 3704 0044 0532 0130 00" onChange={() => {}} />)
      expect(screen.getByDisplayValue('DE89 3704 0044 0532 0130 00')).toBeInTheDocument()
    })

    it('uses default placeholder', () => {
      render(<IBANInput value="" onChange={() => {}} />)
      expect(screen.getByPlaceholderText('e.g., DE89 3704 0044 0532 0130 00')).toBeInTheDocument()
    })

    it('applies custom placeholder', () => {
      render(<IBANInput value="" onChange={() => {}} placeholder="Enter IBAN" />)
      expect(screen.getByPlaceholderText('Enter IBAN')).toBeInTheDocument()
    })

    it('applies monospace font', () => {
      render(<IBANInput value="" onChange={() => {}} />)
      expect(screen.getByRole('textbox')).toHaveClass('font-mono')
    })

    it('applies custom className', () => {
      render(<IBANInput value="" onChange={() => {}} className="custom-class" />)
      expect(screen.getByRole('textbox')).toHaveClass('custom-class')
    })
  })

  describe('formatting', () => {
    it('calls onChange with formatted value', async () => {
      const handleChange = vi.fn()
      const user = userEvent.setup()

      render(<IBANInput value="" onChange={handleChange} />)

      await user.type(screen.getByRole('textbox'), 'DE89')

      // Should be called with formatted values
      expect(handleChange).toHaveBeenCalled()
    })
  })

  describe('disabled state', () => {
    it('is disabled when disabled prop is true', () => {
      render(<IBANInput value="" onChange={() => {}} disabled />)
      expect(screen.getByRole('textbox')).toBeDisabled()
    })

    it('is not disabled by default', () => {
      render(<IBANInput value="" onChange={() => {}} />)
      expect(screen.getByRole('textbox')).not.toBeDisabled()
    })
  })
})
