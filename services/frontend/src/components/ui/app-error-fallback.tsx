import { Button } from './button'

interface AppErrorFallbackProps {
  /** The error message to display */
  error: string
  /** Title shown above the error message */
  title?: string
  /** Label for the retry/reload button */
  retryLabel?: string
  /** Custom action to run on retry (defaults to page reload) */
  onRetry?: () => void
}

/**
 * AppErrorFallback - Full-screen error display for critical app errors
 *
 * Used when the application fails to initialize or encounters
 * an unrecoverable error at the root level.
 *
 * @example
 * ```tsx
 * if (error) {
 *   return <AppErrorFallback error={error} onRetry={retryInit} />
 * }
 * ```
 */
export function AppErrorFallback({
  error,
  title = 'Initialization error',
  retryLabel = 'Reload',
  onRetry,
}: AppErrorFallbackProps) {
  const handleRetry = () => {
    if (onRetry) {
      onRetry()
    } else {
      window.location.reload()
    }
  }

  return (
    <div className="flex h-screen w-full items-center justify-center bg-bg-base">
      <div className="max-w-md text-center px-4">
        <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-full bg-accent-danger/10">
          <svg
            className="h-6 w-6 text-accent-danger"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
        </div>
        <h1 className="text-xl font-bold text-text-primary">{title}</h1>
        <p className="mt-2 text-text-secondary">{error}</p>
        <Button onClick={handleRetry} className="mt-6">
          {retryLabel}
        </Button>
      </div>
    </div>
  )
}
