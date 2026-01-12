/**
 * IBAN formatting utilities
 */

/**
 * Format an IBAN with spaces every 4 characters
 */
export function formatIBAN(raw: string): string {
  // Remove all non-alphanumeric characters and uppercase
  const cleaned = raw.replace(/[^a-zA-Z0-9]/g, '').toUpperCase()
  // Add space every 4 characters
  return cleaned.match(/.{1,4}/g)?.join(' ') || cleaned
}

/**
 * Remove formatting from IBAN (strip spaces)
 */
export function unformatIBAN(formatted: string): string {
  return formatted.replace(/\s/g, '')
}

