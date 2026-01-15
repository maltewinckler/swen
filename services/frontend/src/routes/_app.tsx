import { createFileRoute, redirect } from '@tanstack/react-router'
import { AppLayout } from '@/components/layout'
import { getAccessToken } from '@/api'

export const Route = createFileRoute('/_app')({
  beforeLoad: () => {
    // Redirect to login if not authenticated
    const token = getAccessToken()
    if (!token) {
      throw redirect({ to: '/login' })
    }
  },
  component: AppLayout,
})
