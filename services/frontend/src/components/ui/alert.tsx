import * as React from 'react'
import { AlertCircle, CheckCircle2, Info, AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'

type AlertVariant = 'info' | 'success' | 'warning' | 'danger'

const variantStyles: Record<AlertVariant, { container: string; icon: string }> = {
  info: {
    container: 'bg-accent-info/10 border-accent-info/20 text-accent-info',
    icon: 'text-accent-info',
  },
  success: {
    container: 'bg-accent-success/10 border-accent-success/20 text-accent-success',
    icon: 'text-accent-success',
  },
  warning: {
    container: 'bg-accent-warning/10 border-accent-warning/20 text-accent-warning',
    icon: 'text-accent-warning',
  },
  danger: {
    container: 'bg-accent-danger/10 border-accent-danger/20 text-accent-danger',
    icon: 'text-accent-danger',
  },
}

const variantIcons: Record<AlertVariant, React.ComponentType<{ className?: string }>> = {
  info: Info,
  success: CheckCircle2,
  warning: AlertTriangle,
  danger: AlertCircle,
}

interface AlertProps {
  /** The alert variant/style */
  variant?: AlertVariant
  /** The alert message or content */
  children: React.ReactNode
  /** Optional title for the alert */
  title?: string
  /** Whether to show the icon */
  showIcon?: boolean
  /** Additional className */
  className?: string
}

/**
 * Alert - Consistent alert/notification box with variants
 *
 * Usage:
 * ```tsx
 * <Alert variant="danger">Something went wrong</Alert>
 *
 * <Alert variant="success" title="Success!">
 *   Your changes have been saved.
 * </Alert>
 * ```
 */
export function Alert({
  variant = 'info',
  children,
  title,
  showIcon = true,
  className,
}: AlertProps) {
  const styles = variantStyles[variant]
  const Icon = variantIcons[variant]

  return (
    <div
      className={cn(
        'p-3 rounded-lg border text-sm',
        styles.container,
        className
      )}
    >
      <div className="flex items-start gap-3">
        {showIcon && (
          <Icon className={cn('h-5 w-5 flex-shrink-0 mt-0.5', styles.icon)} />
        )}
        <div className="flex-1 min-w-0">
          {title && (
            <p className="font-medium text-text-primary">{title}</p>
          )}
          <div className={cn(title && 'text-text-secondary mt-1')}>
            {children}
          </div>
        </div>
      </div>
    </div>
  )
}

/**
 * Inline Alert - Simpler version without icon, for compact spaces
 */
interface InlineAlertProps {
  variant?: AlertVariant
  children: React.ReactNode
  className?: string
}

export function InlineAlert({ variant = 'info', children, className }: InlineAlertProps) {
  const styles = variantStyles[variant]

  return (
    <div className={cn('p-3 rounded-lg border text-sm', styles.container, className)}>
      {children}
    </div>
  )
}
