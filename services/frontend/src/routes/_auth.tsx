import { createFileRoute, redirect } from '@tanstack/react-router'
import { AuthLayout } from '@/components/layout'
import { getAccessToken } from '@/api'

export const Route = createFileRoute('/_auth')({
  beforeLoad: () => {
    // Redirect to dashboard if already logged in
    const token = getAccessToken()
    if (token) {
      throw redirect({ to: '/dashboard' })
    }
  },
  component: AuthLayout,
})
