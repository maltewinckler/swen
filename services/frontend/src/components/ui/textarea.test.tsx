import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Textarea } from './textarea'

describe('Textarea', () => {
  it('renders a textbox', () => {
    render(<Textarea />)
    expect(screen.getByRole('textbox')).toBeInTheDocument()
  })

  it('supports placeholder', () => {
    render(<Textarea placeholder="Enter text" />)
    expect(screen.getByPlaceholderText('Enter text')).toBeInTheDocument()
  })

  it('supports typing', async () => {
    const user = userEvent.setup()
    render(<Textarea />)
    const textarea = screen.getByRole('textbox')
    await user.type(textarea, 'Hello')
    expect(textarea).toHaveValue('Hello')
  })

  it('applies error styling when hasError is true', () => {
    render(<Textarea hasError />)
    expect(screen.getByRole('textbox')).toHaveClass('border-accent-danger')
  })
})
