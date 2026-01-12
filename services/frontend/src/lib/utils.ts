import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

/**
 * Combine and merge Tailwind CSS classes
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Default locale for formatting (German for banking context)
 */
export const DEFAULT_LOCALE = 'de-DE'

/**
 * Format a number as currency
 */
export function formatCurrency(
  amount: number | string,
  currency: string = 'EUR',
  locale: string = DEFAULT_LOCALE
): string {
  const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount

  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(numAmount)
}

/**
 * Format a number with sign prefix
 */
export function formatSignedCurrency(
  amount: number | string,
  currency: string = 'EUR',
  locale: string = DEFAULT_LOCALE
): string {
  const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount
  const formatted = formatCurrency(Math.abs(numAmount), currency, locale)

  if (numAmount > 0) return `+${formatted}`
  if (numAmount < 0) return `-${formatted}`
  return formatted
}

/**
 * Format a date
 */
export function formatDate(
  date: string | Date,
  options: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  },
  locale: string = DEFAULT_LOCALE
): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return new Intl.DateTimeFormat(locale, options).format(d)
}

/**
 * Format a relative date
 */
export function formatRelativeDate(date: string | Date, locale: string = DEFAULT_LOCALE): string {
  const d = typeof date === 'string' ? new Date(date) : date
  const now = new Date()
  const diffInMs = now.getTime() - d.getTime()
  const diffInDays = Math.floor(diffInMs / (1000 * 60 * 60 * 24))

  if (diffInDays === 0) return 'Heute'
  if (diffInDays === 1) return 'Gestern'
  if (diffInDays < 7) return `vor ${diffInDays} Tagen`
  if (diffInDays < 30) return `vor ${Math.floor(diffInDays / 7)} Wochen`

  return formatDate(d, { month: 'short', day: 'numeric' }, locale)
}

/**
 * Truncate text with ellipsis
 */
export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength - 1) + '…'
}

/**
 * Get initials from a name
 */
export function getInitials(name: string): string {
  return name
    .split(' ')
    .map((part) => part.charAt(0).toUpperCase())
    .slice(0, 2)
    .join('')
}

/**
 * Delay execution
 */
export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/**
 * Check if a value is defined (not null or undefined)
 */
export function isDefined<T>(value: T | null | undefined): value is T {
  return value !== null && value !== undefined
}

/**
 * Check if two arrays are equal (shallow comparison)
 *
 * More performant than JSON.stringify for simple arrays.
 * Uses strict equality (===) for element comparison.
 *
 * @example
 * arraysEqual(['a', 'b'], ['a', 'b']) // true
 * arraysEqual(['a', 'b'], ['b', 'a']) // false (order matters)
 * arraysEqual([1, 2, 3], [1, 2]) // false
 */
export function arraysEqual<T>(a: T[], b: T[]): boolean {
  if (a.length !== b.length) return false
  return a.every((val, idx) => val === b[idx])
}

/**
 * Build a query string from an object of parameters.
 * Filters out null and undefined values.
 *
 * @example
 * buildQueryString({ days: 30, page: 1, filter: undefined })
 * // Returns: "?days=30&page=1"
 */
export function buildQueryString<T extends object>(params: T): string {
  const searchParams = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) {
      searchParams.set(key, String(value))
    }
  }
  const query = searchParams.toString()
  return query ? `?${query}` : ''
}

/**
 * Format an IBAN with spaces after every 4 characters for readability.
 * Optionally truncate long IBANs to show first and last parts.
 *
 * @example
 * formatIban('DE89370400440532013000')
 * // Returns: "DE89 3704 0044 0532 0130 00"
 *
 * formatIban('DE89370400440532013000', true)
 * // Returns: "DE89 …3000"
 */
export function formatIban(
  iban: string | null | undefined,
  truncate: boolean = false
): string {
  if (!iban) return ''
  // Remove any existing spaces and uppercase
  const clean = iban.replace(/\s/g, '').toUpperCase()

  if (truncate && clean.length > 12) {
    // Show first 4 (country + check) and last 4 (account end)
    return `${clean.slice(0, 4)} …${clean.slice(-4)}`
  }

  // Insert a space after every 4 characters
  return clean.replace(/(.{4})/g, '$1 ').trim()
}
