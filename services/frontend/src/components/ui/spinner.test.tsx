import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Spinner, LoadingScreen } from './spinner'

describe('Spinner', () => {
  describe('rendering', () => {
    it('renders a spinner element', () => {
      render(<Spinner />)
      // Spinner uses Loader2 icon which renders as an SVG
      const spinner = document.querySelector('svg')
      expect(spinner).toBeInTheDocument()
    })

    it('applies animation class', () => {
      render(<Spinner />)
      const spinner = document.querySelector('svg')
      expect(spinner).toHaveClass('animate-spin')
    })
  })

  describe('sizes', () => {
    it('applies medium size by default', () => {
      render(<Spinner />)
      const spinner = document.querySelector('svg')
      expect(spinner).toHaveClass('h-6', 'w-6')
    })

    it('applies small size', () => {
      render(<Spinner size="sm" />)
      const spinner = document.querySelector('svg')
      expect(spinner).toHaveClass('h-4', 'w-4')
    })

    it('applies large size', () => {
      render(<Spinner size="lg" />)
      const spinner = document.querySelector('svg')
      expect(spinner).toHaveClass('h-8', 'w-8')
    })
  })

  describe('custom className', () => {
    it('applies custom className', () => {
      render(<Spinner className="text-accent-primary" />)
      const spinner = document.querySelector('svg')
      expect(spinner).toHaveClass('text-accent-primary')
    })

    it('merges with default classes', () => {
      render(<Spinner className="custom-class" />)
      const spinner = document.querySelector('svg')
      expect(spinner).toHaveClass('animate-spin', 'custom-class')
    })
  })
})

describe('LoadingScreen', () => {
  it('renders a full-screen loading container', () => {
    render(<LoadingScreen />)
    const container = document.querySelector('.h-screen')
    expect(container).toBeInTheDocument()
  })

  it('displays a large spinner', () => {
    render(<LoadingScreen />)
    const spinner = document.querySelector('svg')
    expect(spinner).toHaveClass('h-8', 'w-8')
  })

  it('shows loading text', () => {
    render(<LoadingScreen />)
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('centers content', () => {
    render(<LoadingScreen />)
    const container = document.querySelector('.flex')
    expect(container).toHaveClass('items-center', 'justify-center')
  })
})
