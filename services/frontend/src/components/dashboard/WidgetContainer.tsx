/**
 * Widget Container
 *
 * Wraps widgets with Suspense for lazy loading and error boundary.
 */

import { Suspense, type ReactNode } from 'react'
import { Card, CardContent, Spinner, WidgetErrorBoundary } from '@/components/ui'
import { WIDGET_REGISTRY } from './widgets'

interface WidgetContainerProps {
  children: ReactNode
  widgetId: string
}

function WidgetLoadingFallback() {
  return (
    <Card>
      <CardContent className="h-80 flex items-center justify-center">
        <Spinner size="lg" />
      </CardContent>
    </Card>
  )
}

export default function WidgetContainer({ children, widgetId }: WidgetContainerProps) {
  const widgetName = WIDGET_REGISTRY[widgetId]?.title

  return (
    <WidgetErrorBoundary widgetName={widgetName}>
      <Suspense fallback={<WidgetLoadingFallback />}>
        {children}
      </Suspense>
    </WidgetErrorBoundary>
  )
}
