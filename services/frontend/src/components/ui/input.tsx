import * as React from 'react'
import { cn } from '@/lib/utils'

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  /**
   * Whether the input is in an error state.
   * When true, applies error styling (red border).
   * Note: Error messages should be displayed by the parent FormField component.
   */
  hasError?: boolean
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, hasError, leftIcon, rightIcon, ...props }, ref) => {
    return (
      <div className="relative w-full">
        {leftIcon && (
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted">
            {leftIcon}
          </div>
        )}
        <input
          type={type}
          className={cn(
            'flex h-10 w-full rounded-lg border bg-bg-elevated px-3 text-sm',
            'text-text-primary placeholder:text-text-muted',
            'transition-colors duration-fast',
            'focus:outline-none focus:ring-1',
            hasError
              ? 'border-accent-danger focus:border-accent-danger focus:ring-accent-danger'
              : 'border-border-default focus:border-accent-primary focus:ring-accent-primary',
            leftIcon && 'pl-10',
            rightIcon && 'pr-10',
            'disabled:cursor-not-allowed disabled:opacity-50',
            className
          )}
          ref={ref}
          {...props}
        />
        {rightIcon && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted">
            {rightIcon}
          </div>
        )}
      </div>
    )
  }
)
Input.displayName = 'Input'

export { Input }

