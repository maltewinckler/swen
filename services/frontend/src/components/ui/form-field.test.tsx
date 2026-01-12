import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { FormField } from './form-field'
import { Input } from './input'

describe('FormField', () => {
  describe('rendering', () => {
    it('renders label text', () => {
      render(
        <FormField label="Email">
          <Input />
        </FormField>
      )
      expect(screen.getByText('Email')).toBeInTheDocument()
    })

    it('renders children', () => {
      render(
        <FormField label="Name">
          <Input placeholder="Enter name" />
        </FormField>
      )
      expect(screen.getByPlaceholderText('Enter name')).toBeInTheDocument()
    })

    it('applies custom className to container', () => {
      render(
        <FormField label="Field" className="custom-class">
          <Input />
        </FormField>
      )
      // The container should have the custom class
      expect(document.querySelector('.custom-class')).toBeInTheDocument()
    })

    it('applies custom labelClassName to label', () => {
      render(
        <FormField label="Field" labelClassName="custom-label">
          <Input />
        </FormField>
      )
      expect(screen.getByText('Field')).toHaveClass('custom-label')
    })
  })

  describe('required indicator', () => {
    it('shows asterisk when required is true', () => {
      render(
        <FormField label="Email" required>
          <Input />
        </FormField>
      )
      expect(screen.getByText('*')).toBeInTheDocument()
    })

    it('does not show asterisk when required is false', () => {
      render(
        <FormField label="Email">
          <Input />
        </FormField>
      )
      expect(screen.queryByText('*')).not.toBeInTheDocument()
    })

    it('styles asterisk in danger color', () => {
      render(
        <FormField label="Email" required>
          <Input />
        </FormField>
      )
      expect(screen.getByText('*')).toHaveClass('text-accent-danger')
    })
  })

  describe('helper text', () => {
    it('renders helper text when provided', () => {
      render(
        <FormField label="Password" helperText="Must be at least 8 characters">
          <Input type="password" />
        </FormField>
      )
      expect(screen.getByText('Must be at least 8 characters')).toBeInTheDocument()
    })

    it('styles helper text as muted', () => {
      render(
        <FormField label="Field" helperText="Helper">
          <Input />
        </FormField>
      )
      expect(screen.getByText('Helper')).toHaveClass('text-text-muted')
    })

    it('uses xs text size for helper', () => {
      render(
        <FormField label="Field" helperText="Helper">
          <Input />
        </FormField>
      )
      expect(screen.getByText('Helper')).toHaveClass('text-xs')
    })
  })

  describe('error state', () => {
    it('renders error message when provided', () => {
      render(
        <FormField label="Email" error="Invalid email address">
          <Input />
        </FormField>
      )
      expect(screen.getByText('Invalid email address')).toBeInTheDocument()
    })

    it('styles error message in danger color', () => {
      render(
        <FormField label="Email" error="Error message">
          <Input />
        </FormField>
      )
      expect(screen.getByText('Error message')).toHaveClass('text-accent-danger')
    })

    it('error message overrides helper text', () => {
      render(
        <FormField label="Email" helperText="Enter your email" error="Invalid email">
          <Input />
        </FormField>
      )
      expect(screen.queryByText('Enter your email')).not.toBeInTheDocument()
      expect(screen.getByText('Invalid email')).toBeInTheDocument()
    })

    it('shows helper text when no error', () => {
      render(
        <FormField label="Email" helperText="Enter your email">
          <Input />
        </FormField>
      )
      expect(screen.getByText('Enter your email')).toBeInTheDocument()
    })
  })

  describe('label styling', () => {
    it('applies medium font weight to label', () => {
      render(
        <FormField label="Username">
          <Input />
        </FormField>
      )
      expect(screen.getByText('Username')).toHaveClass('font-medium')
    })

    it('applies primary text color to label', () => {
      render(
        <FormField label="Username">
          <Input />
        </FormField>
      )
      expect(screen.getByText('Username')).toHaveClass('text-text-primary')
    })

    it('uses sm text size for label', () => {
      render(
        <FormField label="Username">
          <Input />
        </FormField>
      )
      expect(screen.getByText('Username')).toHaveClass('text-sm')
    })
  })

  describe('accessibility', () => {
    it('renders label as a label element', () => {
      render(
        <FormField label="Email">
          <Input />
        </FormField>
      )
      const label = screen.getByText('Email')
      expect(label.tagName).toBe('LABEL')
    })

    it('associates the label with the form control', () => {
      render(
        <FormField label="Email">
          <Input />
        </FormField>
      )
      expect(screen.getByLabelText('Email')).toBeInTheDocument()
    })

    it('sets aria-describedby to helper text when provided', () => {
      render(
        <FormField label="Email" helperText="Enter your email">
          <Input />
        </FormField>
      )
      const input = screen.getByLabelText('Email')
      const describedBy = input.getAttribute('aria-describedby') ?? ''
      const ids = describedBy.split(/\s+/).filter(Boolean)
      expect(ids.length).toBeGreaterThan(0)
      expect(
        ids.some((id) => document.getElementById(id)?.textContent?.includes('Enter your email'))
      ).toBe(true)
    })

    it('sets aria-invalid and aria-describedby to error text when error is provided', () => {
      render(
        <FormField label="Email" error="Invalid email">
          <Input />
        </FormField>
      )
      const input = screen.getByLabelText('Email')
      expect(input).toHaveAttribute('aria-invalid', 'true')
      const describedBy = input.getAttribute('aria-describedby') ?? ''
      const ids = describedBy.split(/\s+/).filter(Boolean)
      expect(
        ids.some((id) => document.getElementById(id)?.textContent?.includes('Invalid email'))
      ).toBe(true)
    })

    it('sets aria-required when required is true', () => {
      render(
        <FormField label="Email" required>
          <Input />
        </FormField>
      )
      const input = screen.getByLabelText(/Email/i)
      expect(input).toHaveAttribute('aria-required', 'true')
    })
  })
})
