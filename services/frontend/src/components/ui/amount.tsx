import * as React from 'react'
import { cn, formatCurrency } from '@/lib/utils'

interface AmountProps extends React.HTMLAttributes<HTMLSpanElement> {
  value: number | string
  currency?: string
  showSign?: boolean
  colorize?: boolean
}

export function Amount({
  value,
  currency = 'EUR',
  showSign = false,
  colorize = true,
  className,
  ...props
}: AmountProps) {
  const numValue = typeof value === 'string' ? parseFloat(value) : value
  const isPositive = numValue > 0
  const isNegative = numValue < 0

  const formatted = formatCurrency(Math.abs(numValue), currency)
  const sign = isPositive ? '+' : isNegative ? '-' : ''

  return (
    <span
      className={cn(
        'font-mono tabular-nums',
        colorize && isPositive && 'text-accent-success',
        colorize && isNegative && 'text-accent-danger',
        className
      )}
      {...props}
    >
      {showSign && sign}
      {formatted}
    </span>
  )
}
