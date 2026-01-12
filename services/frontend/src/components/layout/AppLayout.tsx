import { useEffect } from 'react'
import { Outlet, useNavigate, useLocation } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { Navbar } from './Navbar'
import { getOnboardingStatus } from '@/api/onboarding'

export function AppLayout() {
  const navigate = useNavigate()
  const location = useLocation()

  // Check onboarding status
  const { data: onboardingStatus, isLoading } = useQuery({
    queryKey: ['onboarding', 'status'],
    queryFn: getOnboardingStatus,
    staleTime: 1000 * 60 * 5, // 5 minutes
    retry: false, // Don't retry on error
  })

  // Redirect to onboarding if needed (but not if already there)
  useEffect(() => {
    if (!isLoading && onboardingStatus?.needs_onboarding) {
      const isOnboardingPage = location.pathname === '/onboarding'
      if (!isOnboardingPage) {
        navigate({ to: '/onboarding' })
      }
    }
  }, [isLoading, onboardingStatus, location.pathname, navigate])

  return (
    <div className="min-h-screen bg-bg-base">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-[80] focus:rounded-lg focus:bg-bg-surface focus:px-4 focus:py-2 focus:text-sm focus:text-text-primary focus:ring-2 focus:ring-accent-primary/50"
      >
        Skip to content
      </a>
      <Navbar />
      {/* pb-20 on mobile for bottom nav, pb-8 on desktop */}
      <main
        id="main-content"
        tabIndex={-1}
        className="mx-auto max-w-7xl px-4 py-6 pb-20 md:pb-8 sm:px-6 lg:px-8 focus:outline-none"
      >
        <Outlet />
      </main>
    </div>
  )
}
