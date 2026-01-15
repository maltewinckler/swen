import * as React from 'react'
import { ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface SelectOption {
  value: string
  label: string
  disabled?: boolean
}

export interface SelectProps extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, 'onChange'> {
  options: SelectOption[]
  placeholder?: string
  onChange?: (value: string) => void
  error?: boolean
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, options, placeholder, onChange, error, value, disabled, ...props }, ref) => {
    const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
      onChange?.(e.target.value)
    }

    return (
      <div className="relative">
        <select
          ref={ref}
          value={value}
          onChange={handleChange}
          disabled={disabled}
          className={cn(
            'flex h-10 w-full appearance-none rounded-lg border px-3 pr-10 py-2 text-sm',
            'bg-bg-base border-border-subtle text-text-primary',
            'focus:outline-none focus:ring-2 focus:ring-accent-primary/50 focus:border-accent-primary',
            'disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-bg-hover',
            'transition-colors cursor-pointer',
            error && 'border-accent-danger focus:ring-accent-danger/50 focus:border-accent-danger',
            className
          )}
          {...props}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((option) => (
            <option key={option.value} value={option.value} disabled={option.disabled}>
              {option.label}
            </option>
          ))}
        </select>
        <ChevronDown
          className={cn(
            'absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 pointer-events-none',
            'text-text-muted',
            disabled && 'opacity-50'
          )}
        />
      </div>
    )
  }
)

Select.displayName = 'Select'
