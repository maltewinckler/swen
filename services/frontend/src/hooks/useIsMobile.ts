/**
 * Hook to detect mobile viewport
 *
 * Uses CSS media query to match Tailwind's md breakpoint (768px).
 * Returns true when viewport is smaller than md.
 */

import { useState, useEffect } from 'react'

const MOBILE_BREAKPOINT = 768 // Tailwind md breakpoint

export function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(() => {
    // SSR-safe: default to false if window not available
    if (typeof window === 'undefined') return false
    return window.innerWidth < MOBILE_BREAKPOINT
  })

  useEffect(() => {
    const mediaQuery = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`)

    const handleChange = (e: MediaQueryListEvent) => {
      setIsMobile(e.matches)
    }

    // Set initial value
    setIsMobile(mediaQuery.matches)

    // Listen for changes
    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [])

  return isMobile
}
