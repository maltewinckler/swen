/**
 * Dashboard components
 */

import { lazy } from 'react'

export * from './widgets'

// Lazy-load DashboardCustomizer to defer dnd-kit (~30-40KB) until user clicks "Customize"
export const DashboardCustomizer = lazy(() => import('./DashboardCustomizer'))

export { default as WidgetContainer } from './WidgetContainer'
