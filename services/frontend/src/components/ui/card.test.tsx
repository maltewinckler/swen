import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from './card'

describe('Card', () => {
  describe('rendering', () => {
    it('renders children', () => {
      render(<Card>Card content</Card>)
      expect(screen.getByText('Card content')).toBeInTheDocument()
    })

    it('renders with custom className', () => {
      render(<Card className="custom-class">Content</Card>)
      expect(screen.getByText('Content')).toHaveClass('custom-class')
    })
  })

  describe('variants', () => {
    it('applies default variant styles', () => {
      render(<Card>Default</Card>)
      const card = screen.getByText('Default')
      expect(card).toHaveClass('bg-bg-surface')
      expect(card).toHaveClass('rounded-xl')
    })

    it('applies interactive variant styles', () => {
      render(<Card variant="interactive">Interactive</Card>)
      const card = screen.getByText('Interactive')
      expect(card).toHaveClass('cursor-pointer')
      expect(card).toHaveClass('hover:shadow-lg')
    })
  })

  describe('ref forwarding', () => {
    it('forwards ref to the card element', () => {
      const ref = { current: null }
      render(<Card ref={ref}>Content</Card>)
      expect(ref.current).toBeInstanceOf(HTMLDivElement)
    })
  })
})

describe('CardHeader', () => {
  it('renders children', () => {
    render(<CardHeader>Header content</CardHeader>)
    expect(screen.getByText('Header content')).toBeInTheDocument()
  })

  it('applies padding and spacing', () => {
    render(<CardHeader><span data-testid="child">Child</span></CardHeader>)
    expect(screen.getByTestId('child').parentElement).toHaveClass('p-6')
  })

  it('applies custom className', () => {
    render(<CardHeader className="custom-class">Header</CardHeader>)
    expect(screen.getByText('Header')).toHaveClass('custom-class')
  })
})

describe('CardTitle', () => {
  it('renders as h3 heading', () => {
    render(<CardTitle>Title</CardTitle>)
    expect(screen.getByRole('heading', { level: 3, name: /title/i })).toBeInTheDocument()
  })

  it('applies title styles', () => {
    render(<CardTitle>Title</CardTitle>)
    const title = screen.getByRole('heading')
    expect(title).toHaveClass('text-lg', 'font-semibold')
  })

  it('applies custom className', () => {
    render(<CardTitle className="custom-class">Title</CardTitle>)
    expect(screen.getByRole('heading')).toHaveClass('custom-class')
  })
})

describe('CardDescription', () => {
  it('renders description text', () => {
    render(<CardDescription>Description text</CardDescription>)
    expect(screen.getByText('Description text')).toBeInTheDocument()
  })

  it('applies secondary text styles', () => {
    render(<CardDescription>Description</CardDescription>)
    expect(screen.getByText('Description')).toHaveClass('text-text-secondary')
  })
})

describe('CardContent', () => {
  it('renders children', () => {
    render(<CardContent>Content area</CardContent>)
    expect(screen.getByText('Content area')).toBeInTheDocument()
  })

  it('applies padding with reduced top', () => {
    render(<CardContent><span data-testid="child">Child</span></CardContent>)
    expect(screen.getByTestId('child').parentElement).toHaveClass('p-6', 'pt-0')
  })
})

describe('CardFooter', () => {
  it('renders children', () => {
    render(<CardFooter>Footer content</CardFooter>)
    expect(screen.getByText('Footer content')).toBeInTheDocument()
  })

  it('applies flex layout', () => {
    render(<CardFooter><span data-testid="child">Child</span></CardFooter>)
    expect(screen.getByTestId('child').parentElement).toHaveClass('flex', 'items-center')
  })
})

describe('Card composition', () => {
  it('renders full card with all subcomponents', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Card Title</CardTitle>
          <CardDescription>Card description</CardDescription>
        </CardHeader>
        <CardContent>
          <p>Main content here</p>
        </CardContent>
        <CardFooter>
          <button>Action</button>
        </CardFooter>
      </Card>
    )

    expect(screen.getByRole('heading', { name: /card title/i })).toBeInTheDocument()
    expect(screen.getByText('Card description')).toBeInTheDocument()
    expect(screen.getByText('Main content here')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /action/i })).toBeInTheDocument()
  })
})
