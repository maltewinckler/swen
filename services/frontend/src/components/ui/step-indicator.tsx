import * as React from 'react'
import { Check } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Step {
  /** Unique identifier for the step */
  id: string
  /** Label displayed below the step number */
  label: string
}

interface StepIndicatorProps {
  /** Array of steps to display */
  steps: Step[]
  /** ID of the current active step */
  currentStepId: string
  /** Optional className for the container */
  className?: string
  /** Whether to show labels (default: true on larger screens) */
  showLabels?: boolean
}

/**
 * StepIndicator - Visual progress indicator for multi-step flows
 *
 * Usage:
 * ```tsx
 * const steps = [
 *   { id: 'bank', label: 'Bank' },
 *   { id: 'login', label: 'Login' },
 *   { id: 'tan', label: 'TAN' },
 *   { id: 'review', label: 'Review' },
 *   { id: 'sync', label: 'Sync' },
 * ]
 *
 * <StepIndicator steps={steps} currentStepId="tan" />
 * ```
 */
export function StepIndicator({
  steps,
  currentStepId,
  className,
  showLabels = true,
}: StepIndicatorProps) {
  const currentIndex = steps.findIndex(s => s.id === currentStepId)

  return (
    <div className={cn('flex items-center gap-1', className)}>
      {steps.map((step, index) => {
        const isCompleted = index < currentIndex
        const isCurrent = index === currentIndex
        const isPending = index > currentIndex

        return (
          <React.Fragment key={step.id}>
            <div className={cn(
              'flex items-center gap-1.5',
              isCompleted && 'text-accent-success',
              isCurrent && 'text-accent-primary',
              isPending && 'text-text-muted'
            )}>
              <div className={cn(
                'w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium',
                isCompleted && 'bg-accent-success text-white',
                isCurrent && 'bg-accent-primary text-white',
                isPending && 'bg-bg-elevated text-text-muted border border-border-default'
              )}>
                {isCompleted ? <Check className="h-4 w-4" /> : index + 1}
              </div>
              {showLabels && (
                <span className="text-xs hidden sm:inline">{step.label}</span>
              )}
            </div>
            {index < steps.length - 1 && (
              <div className={cn(
                'flex-1 h-px',
                isCompleted ? 'bg-accent-success' : 'bg-border-default'
              )} />
            )}
          </React.Fragment>
        )
      })}
    </div>
  )
}

