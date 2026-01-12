import * as React from 'react'
import { cn } from '@/lib/utils'

interface FormFieldProps {
  /** The label text for the field */
  label: string
  /** Optional helper text below the input */
  helperText?: string
  /** Error message to display (overrides helperText) */
  error?: string
  /** Whether the field is required */
  required?: boolean
  /** The form input element(s) */
  children: React.ReactNode
  /** Additional className for the container */
  className?: string
  /** Additional className for the label */
  labelClassName?: string
  /**
   * Optional explicit id for the form control.
   *
   * If omitted, an id is generated and passed to the child control when possible.
   */
  id?: string
}

function isFormControlElement(element: React.ReactElement): boolean {
  if (typeof element.type === 'string') {
    return element.type === 'input' || element.type === 'select' || element.type === 'textarea'
  }
  // Assume custom components forward id/aria props to an underlying form control.
  return true
}

function mergeAriaDescribedBy(existing: unknown, next?: string) {
  const parts = [typeof existing === 'string' ? existing : '', next ?? ''].join(' ').trim()
  return parts || undefined
}

type FormControlLikeProps = {
  id?: string
  'aria-describedby'?: string
  'aria-invalid'?: React.AriaAttributes['aria-invalid']
  'aria-required'?: React.AriaAttributes['aria-required']
}

/**
 * FormField - Consistent form field wrapper with label and optional helper/error text
 *
 * Usage:
 * ```tsx
 * <FormField label="Email" required>
 *   <Input type="email" ... />
 * </FormField>
 *
 * <FormField label="Password" error={errors.password}>
 *   <Input type="password" ... />
 * </FormField>
 * ```
 */
export function FormField({
  label,
  helperText,
  error,
  required = false,
  children,
  className,
  labelClassName,
  id,
}: FormFieldProps) {
  const reactId = React.useId()

  const childElement = React.isValidElement(children)
    ? (children as React.ReactElement<FormControlLikeProps>)
    : null
  const childIsControl = childElement ? isFormControlElement(childElement) : false
  const existingChildId = childElement?.props.id

  const controlId = existingChildId ?? id ?? `field-${reactId}`

  const helperId = helperText && !error ? `${controlId}-help` : undefined
  const errorId = error ? `${controlId}-error` : undefined
  const describedBy = error ? errorId : helperId

  const enhancedChildren =
    childElement && childIsControl
      ? React.cloneElement(childElement, {
          id: childElement.props.id ?? controlId,
          'aria-describedby': mergeAriaDescribedBy(
            childElement.props['aria-describedby'],
            describedBy
          ),
          'aria-invalid': error ? true : childElement.props['aria-invalid'],
          'aria-required': required ? true : childElement.props['aria-required'],
        })
      : children

  return (
    <div className={cn('space-y-1.5', className)}>
      <label
        className={cn('text-sm font-medium text-text-primary', labelClassName)}
        {...(childIsControl ? { htmlFor: controlId } : {})}
      >
        {label}
        {required && <span className="text-accent-danger ml-1">*</span>}
      </label>
      {enhancedChildren}
      {error ? (
        <p id={errorId} className="text-xs text-accent-danger">
          {error}
        </p>
      ) : helperText ? (
        <p id={helperId} className="text-xs text-text-muted">
          {helperText}
        </p>
      ) : null}
    </div>
  )
}
