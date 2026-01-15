/**
 * Reusable TAN Approval Notice component.
 *
 * Used to inform users that TAN (Transaction Authentication Number) approval
 * may be required during bank operations. Provides consistent visual styling
 * across all places where this notice is needed.
 *
 * Usage:
 *   <TANApprovalNotice />                    // Default: full box with title
 *   <TANApprovalNotice variant="compact" />  // Compact: single-line inline
 *   <TANApprovalNotice variant="inline" />   // Inline: minimal text style
 */

import { Smartphone } from 'lucide-react'
import { cn } from '@/lib/utils'

type TANApprovalVariant = 'default' | 'compact' | 'inline'

interface TANApprovalNoticeProps {
  /** Visual variant */
  variant?: TANApprovalVariant
  /** Additional CSS classes */
  className?: string
  /** Custom message (overrides default) */
  message?: string
  /** Show timing note (e.g., "This may take up to 5 minutes") */
  showTimingNote?: boolean
}

export function TANApprovalNotice({
  variant = 'default',
  className,
  message,
  showTimingNote = false,
}: TANApprovalNoticeProps) {
  if (variant === 'inline') {
    return (
      <p className={cn('text-xs text-text-muted', className)}>
        {message || 'Check your banking app if TAN approval is required.'}
      </p>
    )
  }

  if (variant === 'compact') {
    return (
      <div
        className={cn(
          'flex items-center gap-2 p-3 rounded-lg',
          'bg-accent-warning/10 border border-accent-warning/20',
          className
        )}
      >
        <Smartphone className="h-4 w-4 text-accent-warning flex-shrink-0" />
        <p className="text-sm text-text-secondary">
          {message || 'Check your banking app if TAN approval is required.'}
        </p>
      </div>
    )
  }

  // Default variant: full box with title and description
  return (
    <div
      className={cn(
        'p-3 rounded-lg',
        'bg-accent-warning/10 border border-accent-warning/20',
        className
      )}
    >
      <div className="flex items-start gap-3">
        <Smartphone className="h-5 w-5 text-accent-warning flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm text-accent-warning font-medium mb-1">
            TAN Approval May Be Required
          </p>
          <p className="text-xs text-text-secondary">
            {message || 'Check your banking app and approve the connection if prompted.'}
            {showTimingNote && ' This may take up to 5 minutes.'}
          </p>
        </div>
      </div>
    </div>
  )
}
