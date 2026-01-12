import * as React from 'react'
import { cn } from '@/lib/utils'

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  /**
   * Whether the textarea is in an error state.
   * When true, applies error styling (red border).
   */
  hasError?: boolean
}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, hasError, ...props }, ref) => {
    return (
      <textarea
        ref={ref}
        className={cn(
          'flex w-full rounded-lg border bg-bg-elevated px-3 py-2 text-sm',
          'text-text-primary placeholder:text-text-muted',
          'transition-colors duration-fast',
          'focus:outline-none focus:ring-1',
          hasError
            ? 'border-accent-danger focus:border-accent-danger focus:ring-accent-danger'
            : 'border-border-default focus:border-accent-primary focus:ring-accent-primary',
          'disabled:cursor-not-allowed disabled:opacity-50',
          'resize-none',
          className
        )}
        {...props}
      />
    )
  }
)
Textarea.displayName = 'Textarea'

export { Textarea }
