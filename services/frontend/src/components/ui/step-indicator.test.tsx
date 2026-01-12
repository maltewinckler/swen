import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { StepIndicator } from './step-indicator'

const defaultSteps = [
  { id: 'bank', label: 'Bank' },
  { id: 'login', label: 'Login' },
  { id: 'tan', label: 'TAN' },
  { id: 'review', label: 'Review' },
  { id: 'sync', label: 'Sync' },
]

describe('StepIndicator', () => {
  describe('rendering', () => {
    it('renders all step numbers', () => {
      render(<StepIndicator steps={defaultSteps} currentStepId="bank" />)
      expect(screen.getByText('1')).toBeInTheDocument()
      expect(screen.getByText('2')).toBeInTheDocument()
      expect(screen.getByText('3')).toBeInTheDocument()
      expect(screen.getByText('4')).toBeInTheDocument()
      expect(screen.getByText('5')).toBeInTheDocument()
    })

    it('renders step labels by default', () => {
      render(<StepIndicator steps={defaultSteps} currentStepId="bank" />)
      expect(screen.getByText('Bank')).toBeInTheDocument()
      expect(screen.getByText('Login')).toBeInTheDocument()
      expect(screen.getByText('TAN')).toBeInTheDocument()
    })

    it('hides labels when showLabels is false', () => {
      render(<StepIndicator steps={defaultSteps} currentStepId="bank" showLabels={false} />)
      expect(screen.queryByText('Bank')).not.toBeInTheDocument()
      expect(screen.queryByText('Login')).not.toBeInTheDocument()
    })

    it('applies custom className', () => {
      render(<StepIndicator steps={defaultSteps} currentStepId="bank" className="custom-class" />)
      expect(document.querySelector('.custom-class')).toBeInTheDocument()
    })
  })

  describe('current step highlighting', () => {
    it('highlights current step with primary color', () => {
      render(<StepIndicator steps={defaultSteps} currentStepId="tan" />)
      // The number 3 should have the current step styling
      const stepNumber = screen.getByText('3')
      expect(stepNumber.closest('div')).toHaveClass('bg-accent-primary')
    })

    it('updates highlight when currentStepId changes', () => {
      const { rerender } = render(<StepIndicator steps={defaultSteps} currentStepId="bank" />)

      // Step 1 should be current
      expect(screen.getByText('1').closest('div')).toHaveClass('bg-accent-primary')

      rerender(<StepIndicator steps={defaultSteps} currentStepId="login" />)

      // Step 2 should now be current
      expect(screen.getByText('2').closest('div')).toHaveClass('bg-accent-primary')
    })
  })

  describe('completed steps', () => {
    it('shows checkmark for completed steps', () => {
      render(<StepIndicator steps={defaultSteps} currentStepId="tan" />)
      // Steps 1 and 2 should be completed (before step 3 "tan")
      // They should have check icons - verify SVG elements with success color
      const successElements = document.querySelectorAll('.text-accent-success')
      expect(successElements.length).toBeGreaterThanOrEqual(2)
    })

    it('applies success color to completed steps', () => {
      render(<StepIndicator steps={defaultSteps} currentStepId="review" />)
      // Steps 1, 2, 3 are completed - verify success colored elements
      const successElements = document.querySelectorAll('.text-accent-success')
      expect(successElements.length).toBeGreaterThanOrEqual(3)
    })
  })

  describe('pending steps', () => {
    it('shows numbers for pending steps', () => {
      render(<StepIndicator steps={defaultSteps} currentStepId="bank" />)
      // Steps 2, 3, 4, 5 should show numbers and be styled as pending
      expect(screen.getByText('2')).toBeInTheDocument()
      expect(screen.getByText('3')).toBeInTheDocument()
      expect(screen.getByText('4')).toBeInTheDocument()
      expect(screen.getByText('5')).toBeInTheDocument()
    })

    it('applies muted color to pending steps', () => {
      render(<StepIndicator steps={defaultSteps} currentStepId="bank" />)
      const step2 = screen.getByText('2').closest('.flex')
      expect(step2).toHaveClass('text-text-muted')
    })

    it('applies elevated background to pending step circles', () => {
      render(<StepIndicator steps={defaultSteps} currentStepId="bank" />)
      // Pending step numbers should have bg-bg-elevated
      const pendingNumber = screen.getByText('2').closest('div')
      expect(pendingNumber).toHaveClass('bg-bg-elevated')
    })
  })

  describe('connector lines', () => {
    it('renders connector lines between steps', () => {
      render(<StepIndicator steps={defaultSteps} currentStepId="tan" />)
      // There should be 4 connector lines for 5 steps
      const connectors = document.querySelectorAll('.h-px')
      expect(connectors.length).toBe(4)
    })

    it('applies success color to connectors after completed steps', () => {
      render(<StepIndicator steps={defaultSteps} currentStepId="tan" />)
      // First 2 connectors should be success colored
      const successConnectors = document.querySelectorAll('.h-px.bg-accent-success')
      expect(successConnectors.length).toBe(2)
    })

    it('applies default color to connectors after current/pending steps', () => {
      render(<StepIndicator steps={defaultSteps} currentStepId="tan" />)
      // Last 2 connectors should be default colored
      const defaultConnectors = document.querySelectorAll('.h-px.bg-border-default')
      expect(defaultConnectors.length).toBe(2)
    })
  })

  describe('edge cases', () => {
    it('handles first step as current', () => {
      render(<StepIndicator steps={defaultSteps} currentStepId="bank" />)
      const step1 = screen.getByText('1').closest('div')
      expect(step1).toHaveClass('bg-accent-primary')
      // No completed steps
      const completedSteps = document.querySelectorAll('.bg-accent-success')
      expect(completedSteps.length).toBe(0)
    })

    it('handles last step as current', () => {
      render(<StepIndicator steps={defaultSteps} currentStepId="sync" />)
      // All previous steps should be completed - verify success elements
      const successElements = document.querySelectorAll('.text-accent-success')
      expect(successElements.length).toBeGreaterThanOrEqual(4)
    })

    it('handles two steps', () => {
      const twoSteps = [
        { id: 'first', label: 'First' },
        { id: 'second', label: 'Second' },
      ]
      render(<StepIndicator steps={twoSteps} currentStepId="first" />)
      expect(screen.getByText('1')).toBeInTheDocument()
      expect(screen.getByText('2')).toBeInTheDocument()
    })
  })
})

