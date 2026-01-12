import { useState, Suspense } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { Settings2 } from 'lucide-react'
import { Button, Spinner } from '@/components/ui'
import { getDashboardSettings } from '@/api/preferences'
import {
  WIDGET_REGISTRY,
  DashboardCustomizer,
  WidgetContainer,
  type WidgetSettings,
} from '@/components/dashboard'

export const Route = createFileRoute('/_app/dashboard')({
  component: DashboardPage,
})

function DashboardPage() {
  const [showCustomizer, setShowCustomizer] = useState(false)

  // Fetch dashboard settings
  const {
    data: dashboardSettings,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['preferences', 'dashboard'],
    queryFn: getDashboardSettings,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Spinner size="lg" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-text-secondary">Failed to load dashboard settings</p>
        <p className="text-sm text-text-muted mt-1">{(error as Error).message}</p>
      </div>
    )
  }

  const enabledWidgets = dashboardSettings?.enabled_widgets ?? []
  const widgetSettings = dashboardSettings?.widget_settings ?? {}

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-display text-text-primary">Dashboard</h1>
          <p className="text-text-secondary mt-1">
            Your financial overview
          </p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => setShowCustomizer(true)}
        >
          <Settings2 className="h-4 w-4 mr-2" />
          Customize
        </Button>
      </div>

      {/* Widgets */}
      {enabledWidgets.length === 0 ? (
        <div className="text-center py-16 bg-bg-subtle rounded-xl border border-border-subtle">
          <Settings2 className="h-12 w-12 text-text-muted mx-auto mb-4" />
          <p className="text-text-secondary mb-2">No widgets enabled</p>
          <p className="text-sm text-text-muted mb-4">
            Click "Customize" to add widgets to your dashboard
          </p>
          <Button onClick={() => setShowCustomizer(true)}>
            Add Widgets
          </Button>
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          {enabledWidgets.map((widgetId) => {
            const widgetMeta = WIDGET_REGISTRY[widgetId]
            if (!widgetMeta) return null

            const Widget = widgetMeta.component
            const settings: WidgetSettings = {
              ...widgetMeta.defaultSettings,
              ...widgetSettings[widgetId],
            }

            // Full-width widgets span both columns
            const isFullWidth = widgetMeta.colSpan === 2

            return (
              <div
                key={widgetId}
                className={isFullWidth ? 'lg:col-span-2' : ''}
              >
                <WidgetContainer widgetId={widgetId}>
                  <Widget settings={settings} />
                </WidgetContainer>
              </div>
            )
          })}
        </div>
      )}

      {/* Customizer Modal - lazy loaded with dnd-kit */}
      {dashboardSettings && showCustomizer && (
        <Suspense fallback={null}>
          <DashboardCustomizer
            isOpen={showCustomizer}
            onClose={() => setShowCustomizer(false)}
            currentSettings={dashboardSettings}
          />
        </Suspense>
      )}
    </div>
  )
}
