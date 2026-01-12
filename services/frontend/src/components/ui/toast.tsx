import * as React from 'react'
import * as ToastPrimitives from '@radix-ui/react-toast'
import { X, CheckCircle2, AlertCircle, Info, AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from './button'

export type ToastVariant = 'info' | 'success' | 'warning' | 'danger'

interface ToastInput {
  title?: string
  description: React.ReactNode
  variant?: ToastVariant
  durationMs?: number
}

interface ToastItem extends Required<Omit<ToastInput, 'durationMs'>> {
  id: string
  open: boolean
  durationMs: number
}

interface ToastContextValue {
  push: (toast: ToastInput) => void
  info: (toast: Omit<ToastInput, 'variant'>) => void
  success: (toast: Omit<ToastInput, 'variant'>) => void
  warning: (toast: Omit<ToastInput, 'variant'>) => void
  danger: (toast: Omit<ToastInput, 'variant'>) => void
}

const ToastContext = React.createContext<ToastContextValue | null>(null)

function useToastContext(): ToastContextValue {
  const ctx = React.useContext(ToastContext)
  if (!ctx) {
    // Allow calling useToast() in tests without provider; no-op instead of crashing.
    const noop = () => undefined
    return {
      push: noop,
      info: noop,
      success: noop,
      warning: noop,
      danger: noop,
    }
  }
  return ctx
}

const variantIcon: Record<ToastVariant, React.ComponentType<{ className?: string }>> = {
  info: Info,
  success: CheckCircle2,
  warning: AlertTriangle,
  danger: AlertCircle,
}

const variantStyles: Record<ToastVariant, string> = {
  info: 'border-accent-info/30 bg-bg-surface',
  success: 'border-accent-success/30 bg-bg-surface',
  warning: 'border-accent-warning/30 bg-bg-surface',
  danger: 'border-accent-danger/30 bg-bg-surface',
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<ToastItem[]>([])

  const remove = React.useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const push = React.useCallback((input: ToastInput) => {
    const id = globalThis.crypto?.randomUUID?.() ?? `toast_${Date.now()}_${Math.random().toString(16).slice(2)}`
    const item: ToastItem = {
      id,
      open: true,
      title: input.title ?? '',
      description: input.description,
      variant: input.variant ?? 'info',
      durationMs: input.durationMs ?? 4500,
    }
    setToasts((prev) => [...prev, item])
  }, [])

  const ctx: ToastContextValue = React.useMemo(() => {
    const wrap = (variant: ToastVariant) => (toast: Omit<ToastInput, 'variant'>) =>
      push({ ...toast, variant })
    return {
      push,
      info: wrap('info'),
      success: wrap('success'),
      warning: wrap('warning'),
      danger: wrap('danger'),
    }
  }, [push])

  return (
    <ToastContext.Provider value={ctx}>
      <ToastPrimitives.Provider swipeDirection="right">
        {children}

        {toasts.map((t) => {
          const Icon = variantIcon[t.variant]
          return (
            <ToastPrimitives.Root
              key={t.id}
              open={t.open}
              duration={t.durationMs}
              onOpenChange={(open) => {
                if (!open) remove(t.id)
              }}
              className={cn(
                'relative w-full max-w-sm rounded-xl border shadow-lg',
                'p-4 pr-10',
                'data-[state=open]:animate-slide-up data-[state=closed]:animate-fade-out',
                variantStyles[t.variant]
              )}
            >
              <div className="flex items-start gap-3">
                <Icon className="h-5 w-5 text-text-muted flex-shrink-0 mt-0.5" />
                <div className="min-w-0 flex-1">
                  {t.title ? (
                    <ToastPrimitives.Title className="text-sm font-medium text-text-primary">
                      {t.title}
                    </ToastPrimitives.Title>
                  ) : null}
                  <ToastPrimitives.Description className="text-sm text-text-secondary">
                    {t.description}
                  </ToastPrimitives.Description>
                </div>
              </div>

              <ToastPrimitives.Close asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="absolute right-2 top-2 h-8 w-8"
                  aria-label="Dismiss notification"
                >
                  <X className="h-4 w-4" />
                </Button>
              </ToastPrimitives.Close>
            </ToastPrimitives.Root>
          )
        })}

        <ToastPrimitives.Viewport
          className={cn(
            'fixed z-[70] flex flex-col gap-2 p-4',
            'bottom-0 right-0 w-full sm:max-w-sm',
            'safe-area-bottom'
          )}
        />
      </ToastPrimitives.Provider>
    </ToastContext.Provider>
  )
}

export function useToast() {
  return useToastContext()
}
