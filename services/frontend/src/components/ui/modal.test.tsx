import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Modal, ModalHeader, ModalBody, ModalFooter } from './modal'

describe('Modal', () => {
  beforeEach(() => {
    // Reset body overflow
    document.body.style.overflow = 'unset'
  })

  afterEach(() => {
    document.body.style.overflow = 'unset'
  })

  describe('rendering', () => {
    it('renders when isOpen is true', () => {
      render(
        <Modal isOpen onClose={() => {}}>
          <div>Modal content</div>
        </Modal>
      )
      expect(screen.getByText('Modal content')).toBeInTheDocument()
    })

    it('does not render when isOpen is false', () => {
      render(
        <Modal isOpen={false} onClose={() => {}}>
          <div>Modal content</div>
        </Modal>
      )
      expect(screen.queryByText('Modal content')).not.toBeInTheDocument()
    })

    it('renders with custom className', () => {
      render(
        <Modal isOpen onClose={() => {}} className="custom-class">
          <div data-testid="modal-content">Content</div>
        </Modal>
      )
      const modalContent = screen.getByTestId('modal-content').parentElement
      expect(modalContent).toHaveClass('custom-class')
    })
  })

  describe('sizes', () => {
    it('applies default 2xl size', () => {
      render(
        <Modal isOpen onClose={() => {}}>
          <div data-testid="content">Content</div>
        </Modal>
      )
      expect(screen.getByTestId('content').parentElement).toHaveClass('max-w-2xl')
    })

    it('applies sm size', () => {
      render(
        <Modal isOpen onClose={() => {}} size="sm">
          <div data-testid="content">Content</div>
        </Modal>
      )
      expect(screen.getByTestId('content').parentElement).toHaveClass('max-w-sm')
    })

    it('applies lg size', () => {
      render(
        <Modal isOpen onClose={() => {}} size="lg">
          <div data-testid="content">Content</div>
        </Modal>
      )
      expect(screen.getByTestId('content').parentElement).toHaveClass('max-w-lg')
    })
  })

  describe('closing behavior', () => {
    it('calls onClose when backdrop is clicked', async () => {
      const handleClose = vi.fn()
      const user = userEvent.setup()

      render(
        <Modal isOpen onClose={handleClose}>
          <div>Content</div>
        </Modal>
      )

      // Click the backdrop (first element with animate-fade-in class)
      const backdrop = document.querySelector('.animate-fade-in')
      await user.click(backdrop as Element)

      expect(handleClose).toHaveBeenCalledTimes(1)
    })

    it('does not close on backdrop click when closeOnBackdropClick is false', async () => {
      const handleClose = vi.fn()
      const user = userEvent.setup()

      render(
        <Modal isOpen onClose={handleClose} closeOnBackdropClick={false}>
          <div>Content</div>
        </Modal>
      )

      const backdrop = document.querySelector('.animate-fade-in')
      await user.click(backdrop as Element)

      expect(handleClose).not.toHaveBeenCalled()
    })

    it('calls onClose when Escape key is pressed', async () => {
      const handleClose = vi.fn()
      const user = userEvent.setup()

      render(
        <Modal isOpen onClose={handleClose}>
          <div>Content</div>
        </Modal>
      )

      await user.keyboard('{Escape}')

      expect(handleClose).toHaveBeenCalledTimes(1)
    })
  })

  describe('body scroll lock', () => {
    it('locks body scroll when modal opens', () => {
      render(
        <Modal isOpen onClose={() => {}}>
          <div>Content</div>
        </Modal>
      )
      expect(document.body.style.overflow).toBe('hidden')
    })

    it('unlocks body scroll when modal closes', () => {
      const { rerender } = render(
        <Modal isOpen onClose={() => {}}>
          <div>Content</div>
        </Modal>
      )

      rerender(
        <Modal isOpen={false} onClose={() => {}}>
          <div>Content</div>
        </Modal>
      )

      expect(document.body.style.overflow).toBe('unset')
    })
  })
})

describe('ModalHeader', () => {
  it('renders children as title', () => {
    render(<ModalHeader>My Title</ModalHeader>)
    expect(screen.getByRole('heading', { name: /my title/i })).toBeInTheDocument()
  })

  it('renders description when provided', () => {
    render(<ModalHeader description="Some description">Title</ModalHeader>)
    expect(screen.getByText('Some description')).toBeInTheDocument()
  })

  it('renders close button when onClose is provided', () => {
    const handleClose = vi.fn()
    render(<ModalHeader onClose={handleClose}>Title</ModalHeader>)
    expect(screen.getByRole('button')).toBeInTheDocument()
  })

  it('calls onClose when close button is clicked', async () => {
    const handleClose = vi.fn()
    const user = userEvent.setup()

    render(<ModalHeader onClose={handleClose}>Title</ModalHeader>)
    await user.click(screen.getByRole('button'))

    expect(handleClose).toHaveBeenCalledTimes(1)
  })

  it('does not render close button when onClose is not provided', () => {
    render(<ModalHeader>Title</ModalHeader>)
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})

describe('ModalBody', () => {
  it('renders children', () => {
    render(<ModalBody><p>Body content</p></ModalBody>)
    expect(screen.getByText('Body content')).toBeInTheDocument()
  })

  it('applies default padding', () => {
    render(<ModalBody><p data-testid="content">Content</p></ModalBody>)
    expect(screen.getByTestId('content').parentElement).toHaveClass('p-6')
  })

  it('applies custom className', () => {
    render(<ModalBody className="custom-class"><p>Content</p></ModalBody>)
    expect(screen.getByText('Content').parentElement).toHaveClass('custom-class')
  })
})

describe('ModalFooter', () => {
  it('renders children', () => {
    render(
      <ModalFooter>
        <button>Cancel</button>
        <button>Confirm</button>
      </ModalFooter>
    )
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /confirm/i })).toBeInTheDocument()
  })

  it('applies flex layout with gap', () => {
    render(
      <ModalFooter>
        <button data-testid="btn">Button</button>
      </ModalFooter>
    )
    expect(screen.getByTestId('btn').parentElement).toHaveClass('flex', 'gap-3')
  })
})
