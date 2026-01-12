import * as React from 'react'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from './button'

type ModalSize = 'sm' | 'md' | 'lg' | 'xl' | '2xl'

const sizeClasses: Record<ModalSize, string> = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
  '2xl': 'max-w-2xl',
}

interface ModalProps {
  isOpen: boolean
  onClose: () => void
  children: React.ReactNode
  className?: string
  /** Modal size preset */
  size?: ModalSize
  /** Whether clicking the backdrop closes the modal */
  closeOnBackdropClick?: boolean
}

// ------------------------------
// Accessibility + scroll locking
// ------------------------------

interface ModalContextValue {
  titleId: string
}

const ModalContext = React.createContext<ModalContextValue | null>(null)

function useModalContext() {
  return React.useContext(ModalContext)
}

// Track open modals so we can:
// - lock body scroll only once (supports nested modals)
// - only trap focus / handle Escape for the top-most modal
const modalStack: string[] = []
let scrollLockCount = 0
let previousBodyOverflow: string | null = null

function pushModal(id: string) {
  modalStack.push(id)
}

function removeModal(id: string) {
  const idx = modalStack.lastIndexOf(id)
  if (idx >= 0) modalStack.splice(idx, 1)
}

function isTopModal(id: string) {
  return modalStack[modalStack.length - 1] === id
}

function lockBodyScroll() {
  if (scrollLockCount === 0) {
    previousBodyOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
  }
  scrollLockCount += 1
}

function unlockBodyScroll() {
  scrollLockCount = Math.max(0, scrollLockCount - 1)
  if (scrollLockCount === 0) {
    document.body.style.overflow = previousBodyOverflow ?? ''
    previousBodyOverflow = null
  }
}

function getFocusableElements(container: HTMLElement): HTMLElement[] {
  const focusableSelector =
    'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
  return Array.from(container.querySelectorAll<HTMLElement>(focusableSelector)).filter(
    (el) => !el.hasAttribute('disabled') && el.tabIndex !== -1
  )
}

function trapFocus(e: KeyboardEvent, container: HTMLElement) {
  if (e.key !== 'Tab') return

  const focusables = getFocusableElements(container)
  if (focusables.length === 0) {
    // Keep focus on the dialog container itself
    e.preventDefault()
    container.focus()
    return
  }

  const first = focusables[0]
  const last = focusables[focusables.length - 1]
  const active = document.activeElement as HTMLElement | null

  // If focus escaped the dialog (e.g., due to nested dialog close),
  // bring it back to the first/last focusable element.
  if (!active || !container.contains(active)) {
    e.preventDefault()
    ;(e.shiftKey ? last : first).focus()
    return
  }

  if (e.shiftKey) {
    if (!active || active === first) {
      e.preventDefault()
      last.focus()
    }
  } else {
    if (active === last) {
      e.preventDefault()
      first.focus()
    }
  }
}

export function Modal({
  isOpen,
  onClose,
  children,
  className,
  size = '2xl',
  closeOnBackdropClick = true,
}: ModalProps) {
  const modalId = React.useId()
  const titleId = `${modalId}-title`
  const contentRef = React.useRef<HTMLDivElement>(null)
  const previouslyFocusedRef = React.useRef<HTMLElement | null>(null)
  const onCloseRef = React.useRef(onClose)

  // Keep the latest onClose without re-running the open/close effect on each render
  React.useEffect(() => {
    onCloseRef.current = onClose
  }, [onClose])

  // Close on escape key + focus trap + scroll lock
  React.useEffect(() => {
    if (!isOpen) return

    pushModal(modalId)
    lockBodyScroll()

    // Remember focus and move it inside the dialog
    previouslyFocusedRef.current = document.activeElement as HTMLElement | null
    const container = contentRef.current
    if (container) {
      const focusables = getFocusableElements(container)
      if (focusables.length > 0) {
        focusables[0].focus()
      } else {
        container.focus()
      }
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isTopModal(modalId)) return

      if (e.key === 'Escape') {
        e.preventDefault()
        onCloseRef.current()
        return
      }

      if (e.key === 'Tab' && contentRef.current) {
        trapFocus(e, contentRef.current)
      }
    }
    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      removeModal(modalId)
      unlockBodyScroll()

      // If another modal is still open (nested dialogs), move focus back to the
      // top-most modal. Otherwise restore focus to what was active before opening.
      const nextTopId = modalStack[modalStack.length - 1]
      if (nextTopId) {
        const topEl = document.querySelector<HTMLElement>(`[data-swen-modal-id="${nextTopId}"]`)
        topEl?.focus()
        return
      }

      const previous = previouslyFocusedRef.current
      if (previous && document.contains(previous)) previous.focus()
    }
  }, [isOpen, modalId])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm animate-fade-in"
        onClick={closeOnBackdropClick ? () => onCloseRef.current() : undefined}
        aria-hidden="true"
      />
      {/* Centering wrapper - uses min-height to allow scrolling when content is tall */}
      <div className="flex min-h-full items-center justify-center p-4">
        {/* Modal content */}
        <div
          ref={contentRef}
          className={cn(
            'relative z-10 w-full max-h-[calc(100vh-2rem)] flex flex-col',
            'bg-bg-surface border border-border-subtle rounded-2xl shadow-2xl',
            'animate-scale-in',
            sizeClasses[size],
            className
          )}
          data-swen-modal="true"
          data-swen-modal-id={modalId}
          role="dialog"
          aria-modal="true"
          aria-labelledby={titleId}
          tabIndex={-1}
        >
          <ModalContext.Provider value={{ titleId }}>
            {children}
          </ModalContext.Provider>
        </div>
      </div>
    </div>
  )
}

interface ModalHeaderProps {
  children: React.ReactNode
  onClose?: () => void
  className?: string
  /** Optional description text below the title */
  description?: React.ReactNode
}

export function ModalHeader({ children, onClose, className, description }: ModalHeaderProps) {
  const ctx = useModalContext()

  return (
    <div className={cn('flex items-start justify-between p-6 border-b border-border-subtle flex-shrink-0', className)}>
      <div>
        <h2 id={ctx?.titleId} className="text-lg font-semibold text-text-primary">
          {children}
        </h2>
        {description && (
          <p className="text-sm text-text-muted mt-1">{description}</p>
        )}
      </div>
      {onClose && (
        <Button
          variant="ghost"
          size="icon"
          onClick={onClose}
          className="h-8 w-8 flex-shrink-0 ml-4"
          aria-label="Close dialog"
        >
          <X className="h-4 w-4" />
        </Button>
      )}
    </div>
  )
}

interface ModalBodyProps {
  children: React.ReactNode
  className?: string
}

export function ModalBody({ children, className }: ModalBodyProps) {
  return <div className={cn('p-6 flex-1 overflow-y-auto', className)}>{children}</div>
}

interface ModalFooterProps {
  children: React.ReactNode
  className?: string
}

export function ModalFooter({ children, className }: ModalFooterProps) {
  return (
    <div className={cn('flex items-center justify-end gap-3 p-6 border-t border-border-subtle flex-shrink-0', className)}>
      {children}
    </div>
  )
}
