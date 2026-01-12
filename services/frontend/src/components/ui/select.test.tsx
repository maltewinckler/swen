import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Select, type SelectOption } from './select'

const defaultOptions: SelectOption[] = [
  { value: 'apple', label: 'Apple' },
  { value: 'banana', label: 'Banana' },
  { value: 'cherry', label: 'Cherry' },
]

describe('Select', () => {
  describe('rendering', () => {
    it('renders a select element', () => {
      render(<Select options={defaultOptions} />)
      expect(screen.getByRole('combobox')).toBeInTheDocument()
    })

    it('renders all options', () => {
      render(<Select options={defaultOptions} />)
      expect(screen.getByRole('option', { name: 'Apple' })).toBeInTheDocument()
      expect(screen.getByRole('option', { name: 'Banana' })).toBeInTheDocument()
      expect(screen.getByRole('option', { name: 'Cherry' })).toBeInTheDocument()
    })

    it('renders placeholder option', () => {
      render(<Select options={defaultOptions} placeholder="Select a fruit" />)
      expect(screen.getByRole('option', { name: 'Select a fruit' })).toBeInTheDocument()
    })

    it('applies custom className', () => {
      render(<Select options={defaultOptions} className="custom-class" />)
      expect(screen.getByRole('combobox')).toHaveClass('custom-class')
    })
  })

  describe('value and onChange', () => {
    it('renders with initial value', () => {
      render(<Select options={defaultOptions} value="banana" />)
      expect(screen.getByRole('combobox')).toHaveValue('banana')
    })

    it('calls onChange when selection changes', async () => {
      const handleChange = vi.fn()
      const user = userEvent.setup()

      render(<Select options={defaultOptions} onChange={handleChange} />)

      await user.selectOptions(screen.getByRole('combobox'), 'cherry')

      expect(handleChange).toHaveBeenCalledWith('cherry')
    })

    it('updates displayed value on change', async () => {
      const user = userEvent.setup()
      render(<Select options={defaultOptions} />)

      await user.selectOptions(screen.getByRole('combobox'), 'apple')

      expect(screen.getByRole('combobox')).toHaveValue('apple')
    })
  })

  describe('disabled state', () => {
    it('disables select when disabled prop is true', () => {
      render(<Select options={defaultOptions} disabled />)
      expect(screen.getByRole('combobox')).toBeDisabled()
    })

    it('applies disabled styles', () => {
      render(<Select options={defaultOptions} disabled />)
      expect(screen.getByRole('combobox')).toHaveClass('disabled:opacity-50')
    })
  })

  describe('disabled options', () => {
    it('disables individual options', () => {
      const optionsWithDisabled: SelectOption[] = [
        { value: 'apple', label: 'Apple' },
        { value: 'banana', label: 'Banana', disabled: true },
        { value: 'cherry', label: 'Cherry' },
      ]

      render(<Select options={optionsWithDisabled} />)
      expect(screen.getByRole('option', { name: 'Banana' })).toBeDisabled()
    })
  })

  describe('error state', () => {
    it('applies error styles when error is true', () => {
      render(<Select options={defaultOptions} error />)
      expect(screen.getByRole('combobox')).toHaveClass('border-accent-danger')
    })

    it('does not apply error styles when error is false', () => {
      render(<Select options={defaultOptions} error={false} />)
      expect(screen.getByRole('combobox')).not.toHaveClass('border-accent-danger')
    })
  })

  describe('placeholder behavior', () => {
    it('placeholder option is disabled', () => {
      render(<Select options={defaultOptions} placeholder="Select..." />)
      expect(screen.getByRole('option', { name: 'Select...' })).toBeDisabled()
    })

    it('placeholder has empty value', () => {
      render(<Select options={defaultOptions} placeholder="Select..." />)
      expect(screen.getByRole('option', { name: 'Select...' })).toHaveValue('')
    })
  })

  describe('styling', () => {
    it('has chevron icon', () => {
      render(<Select options={defaultOptions} />)
      const svg = document.querySelector('svg')
      expect(svg).toBeInTheDocument()
    })

    it('hides native appearance', () => {
      render(<Select options={defaultOptions} />)
      expect(screen.getByRole('combobox')).toHaveClass('appearance-none')
    })

    it('has consistent height', () => {
      render(<Select options={defaultOptions} />)
      expect(screen.getByRole('combobox')).toHaveClass('h-10')
    })
  })

  describe('ref forwarding', () => {
    it('forwards ref to select element', () => {
      const ref = vi.fn()
      render(<Select options={defaultOptions} ref={ref} />)
      expect(ref).toHaveBeenCalled()
    })
  })
})

