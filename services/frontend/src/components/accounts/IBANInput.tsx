/**
 * IBANInput - Formatted IBAN input component
 *
 * Automatically formats IBAN with spaces every 4 characters
 * and converts to uppercase.
 */

import { Input } from '@/components/ui'
import { cn } from '@/lib/utils'
import { formatIBAN } from './iban-utils'

export interface IBANInputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'value' | 'onChange'> {
  /** Current IBAN value (formatted with spaces) */
  value: string
  /** Called when IBAN value changes */
  onChange: (value: string) => void
}

export function IBANInput({
  value,
  onChange,
  placeholder = "e.g., DE89 3704 0044 0532 0130 00",
  className,
  disabled = false,
  ...props
}: IBANInputProps) {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const formatted = formatIBAN(e.target.value)
    onChange(formatted)
  }

  return (
    <Input
      className={cn("font-mono", className)}
      placeholder={placeholder}
      value={value}
      onChange={handleChange}
      disabled={disabled}
      {...props}
    />
  )
}
