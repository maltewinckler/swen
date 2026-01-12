import * as React from 'react'
import { ArrowLeft } from 'lucide-react'
import { Button } from './button'
import { cn } from '@/lib/utils'

interface WizardStepFooterProps {
  /** Called when back button is clicked */
  onBack?: () => void
  /** Custom back button label */
  backLabel?: string
  /** Additional buttons or content for the footer */
  children?: React.ReactNode
  /** Additional className for the footer container */
  className?: string
}

/**
 * WizardStepFooter - Footer area for wizard step with back button and custom actions
 */
export function WizardStepFooter({
  onBack,
  backLabel = 'Back',
  children,
  className,
}: WizardStepFooterProps) {
  return (
    <div className={cn('flex gap-3 pt-2', className)}>
      {onBack && (
        <Button type="button" variant="secondary" onClick={onBack}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          {backLabel}
        </Button>
      )}
      {children}
    </div>
  )
}

interface WizardStepProps {
  /** Whether this step is wrapped in a form element */
  asForm?: boolean
  /** Called when form is submitted (only if asForm=true) */
  onSubmit?: () => void
  /** Content of the wizard step */
  children: React.ReactNode
  /** Additional className for the container */
  className?: string
}

/**
 * WizardStep - Container for a single step in a multi-step wizard
 *
 * Provides consistent spacing and optional form handling.
 *
 * @example
 * ```tsx
 * <WizardStep asForm onSubmit={handleSubmit}>
 *   <FormField label="Email">
 *     <Input value={email} onChange={...} />
 *   </FormField>
 *   <WizardStepFooter onBack={goBack}>
 *     <Button type="submit" className="flex-1">Continue</Button>
 *   </WizardStepFooter>
 * </WizardStep>
 * ```
 */
export function WizardStep({
  asForm = false,
  onSubmit,
  children,
  className,
}: WizardStepProps) {
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit?.()
  }

  if (asForm) {
    return (
      <form className={cn('space-y-4', className)} onSubmit={handleSubmit}>
        {children}
      </form>
    )
  }

  return <div className={cn('space-y-4', className)}>{children}</div>
}

interface WizardLoadingStateProps {
  /** Main loading message */
  message: string
  /** Optional subtext or additional content below the message */
  children?: React.ReactNode
  /** Additional className */
  className?: string
}

/**
 * WizardLoadingState - Centered loading spinner with message
 *
 * Used for intermediate loading states in wizards (connecting, syncing, etc.)
 */
export function WizardLoadingState({
  message,
  children,
  className,
}: WizardLoadingStateProps) {
  return (
    <div className={cn('py-8 text-center', className)}>
      <div className="h-12 w-12 mx-auto mb-4 rounded-full border-4 border-accent-primary/20 border-t-accent-primary animate-spin" />
      <p className="text-text-primary font-medium mb-2">{message}</p>
      {children}
    </div>
  )
}

interface WizardSuccessMessageProps {
  /** Title/heading of the success message */
  title: string
  /** Description text */
  description?: string
  /** Icon to display (defaults to checkmark) */
  icon?: React.ReactNode
  /** Additional className */
  className?: string
}

/**
 * WizardSuccessMessage - Success banner for completed wizard steps
 */
export function WizardSuccessMessage({
  title,
  description,
  icon,
  className,
}: WizardSuccessMessageProps) {
  return (
    <div className={cn('p-4 rounded-lg bg-accent-success/10 border border-accent-success/20', className)}>
      <div className="flex items-start gap-3">
        {icon || (
          <svg
            className="h-6 w-6 text-accent-success flex-shrink-0"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        )}
        <div>
          <p className="font-medium text-text-primary">{title}</p>
          {description && (
            <p className="text-sm text-text-secondary mt-1">{description}</p>
          )}
        </div>
      </div>
    </div>
  )
}

interface WizardErrorMessageProps {
  /** Title/heading of the error message */
  title: string
  /** Error description/details */
  description?: string
  /** Icon to display (defaults to alert circle) */
  icon?: React.ReactNode
  /** Additional className */
  className?: string
}

/**
 * WizardErrorMessage - Error banner for failed wizard steps
 */
export function WizardErrorMessage({
  title,
  description,
  icon,
  className,
}: WizardErrorMessageProps) {
  return (
    <div className={cn('p-4 rounded-lg bg-accent-danger/10 border border-accent-danger/20', className)}>
      <div className="flex items-start gap-3">
        {icon || (
          <svg
            className="h-6 w-6 text-accent-danger flex-shrink-0"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        )}
        <div>
          <p className="font-medium text-text-primary">{title}</p>
          {description && (
            <p className="text-sm text-text-secondary mt-1">{description}</p>
          )}
        </div>
      </div>
    </div>
  )
}

interface WizardInfoBannerProps {
  /** Icon to display */
  icon?: React.ReactNode
  /** Main text content */
  children: React.ReactNode
  /** Additional className */
  className?: string
}

/**
 * WizardInfoBanner - Informational banner for context in wizard steps
 */
export function WizardInfoBanner({
  icon,
  children,
  className,
}: WizardInfoBannerProps) {
  return (
    <div className={cn('p-3 rounded-lg bg-accent-primary/10 border border-accent-primary/20', className)}>
      <div className="flex items-center gap-2">
        {icon}
        {children}
      </div>
    </div>
  )
}
