import * as React from 'react'
import { cn } from '@/lib/utils'

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'success' | 'danger' | 'warning' | 'info'
}

export function Badge({
  className,
  variant = 'default',
  ...props
}: BadgeProps) {
  const variants = {
    default: 'bg-bg-elevated text-text-secondary',
    success: 'bg-accent-success/15 text-accent-success',
    danger: 'bg-accent-danger/15 text-accent-danger',
    warning: 'bg-accent-warning/15 text-accent-warning',
    info: 'bg-accent-info/15 text-accent-info',
  }

  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full',
        variants[variant],
        className
      )}
      {...props}
    />
  )
}

