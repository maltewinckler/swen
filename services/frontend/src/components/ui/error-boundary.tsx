import * as React from 'react'
import { AlertCircle, RefreshCw } from 'lucide-react'
import { Button } from './button'
import { Card, CardContent } from './card'

interface ErrorBoundaryProps {
  children: React.ReactNode
  /** Fallback UI to show on error. If not provided, uses default error card. */
  fallback?: React.ReactNode
  /** Called when an error is caught */
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void
  /** Called when user clicks retry */
  onRetry?: () => void
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

/**
 * Error Boundary component that catches JavaScript errors in child components.
 *
 * Usage:
 * ```tsx
 * <ErrorBoundary onError={(error) => logError(error)}>
 *   <MyComponent />
 * </ErrorBoundary>
 * ```
 */
export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    this.props.onError?.(error, errorInfo)
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: null })
    this.props.onRetry?.()
  }

  render(): React.ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <Card className="border-accent-danger/20 bg-accent-danger/5">
          <CardContent className="p-6">
            <div className="flex items-start gap-4">
              <div className="flex items-center justify-center h-10 w-10 rounded-full bg-accent-danger/10 flex-shrink-0">
                <AlertCircle className="h-5 w-5 text-accent-danger" />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-sm font-medium text-text-primary">
                  Something went wrong
                </h3>
                <p className="text-sm text-text-secondary mt-1">
                  {this.state.error?.message || 'An unexpected error occurred'}
                </p>
                <Button
                  variant="secondary"
                  size="sm"
                  className="mt-3"
                  onClick={this.handleRetry}
                >
                  <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
                  Try again
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )
    }

    return this.props.children
  }
}

/**
 * Widget-specific error boundary with compact styling
 */
interface WidgetErrorBoundaryProps {
  children: React.ReactNode
  widgetName?: string
}

export function WidgetErrorBoundary({ children, widgetName }: WidgetErrorBoundaryProps) {
  return (
    <ErrorBoundary
      fallback={
        <Card>
          <CardContent className="p-6">
            <div className="flex flex-col items-center justify-center h-48 text-center">
              <AlertCircle className="h-8 w-8 text-accent-danger mb-3" />
              <p className="text-sm font-medium text-text-primary">
                Failed to load {widgetName || 'widget'}
              </p>
              <p className="text-xs text-text-muted mt-1">
                Please refresh the page to try again
              </p>
            </div>
          </CardContent>
        </Card>
      }
    >
      {children}
    </ErrorBoundary>
  )
}

