import { StrictMode, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider, createRouter } from '@tanstack/react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { routeTree } from './routeTree.gen'
import { useAuthStore } from './stores'
import { LoadingScreen, AppErrorFallback, ToastProvider, TooltipProvider } from './components/ui'
import './index.css'

// Create a new router instance
const router = createRouter({ routeTree })

// Register the router instance for type safety
declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}

// Create a query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      gcTime: 1000 * 60 * 30, // 30 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

function App() {
  const { isLoading, initialize } = useAuthStore()
  const [initialized, setInitialized] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Initialize auth on mount
  useEffect(() => {
    initialize()
      .then(() => {
        setInitialized(true)
      })
      .catch((err) => {
        setError(err?.message || 'Unknown error')
        setInitialized(true) // Allow app to continue
      })
  }, [initialize])

  if (error) {
    return <AppErrorFallback error={error} />
  }

  if (isLoading || !initialized) {
    return <LoadingScreen />
  }

  return <RouterProvider router={router} />
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <TooltipProvider>
          <App />
        </TooltipProvider>
      </ToastProvider>
    </QueryClientProvider>
  </StrictMode>,
)
