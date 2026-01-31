import { createFileRoute, redirect } from '@tanstack/react-router'
import { getAccessToken } from '@/api'

const MOBILE_BREAKPOINT = 768

function isMobileViewport(): boolean {
  if (typeof window === 'undefined') return false
  return window.innerWidth < MOBILE_BREAKPOINT
}

export const Route = createFileRoute('/')({
  beforeLoad: () => {
    const token = getAccessToken()
    if (token) {
      // Redirect mobile users to quick actions, desktop to dashboard
      const destination = isMobileViewport() ? '/quick' : '/dashboard'
      throw redirect({ to: destination })
    } else {
      throw redirect({ to: '/login' })
    }
  },
})
