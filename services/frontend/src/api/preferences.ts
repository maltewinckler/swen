import { api } from './client'

// =============================================================================
// Types
// =============================================================================

export interface SyncSettings {
  auto_post_transactions: boolean
  default_currency: string
}

export interface DisplaySettings {
  show_draft_transactions: boolean
  default_date_range_days: number
}

export interface UserPreferences {
  sync_settings: SyncSettings
  display_settings: DisplaySettings
}

export interface PreferencesUpdateRequest {
  auto_post_transactions?: boolean
  default_currency?: string
  show_draft_transactions?: boolean
  default_date_range_days?: number
}

// Dashboard settings types
export interface DashboardSettings {
  enabled_widgets: string[]
  widget_settings: Record<string, Record<string, unknown>>
}

export interface DashboardSettingsUpdateRequest {
  enabled_widgets?: string[]
  widget_settings?: Record<string, Record<string, unknown>>
}

export interface WidgetInfo {
  id: string
  title: string
  description: string
  category: 'overview' | 'spending' | 'income'
  enabled: boolean
  settings: Record<string, unknown>
}

export interface AvailableWidgetsResponse {
  widgets: WidgetInfo[]
  default_widgets: string[]
}

// =============================================================================
// User Preferences API
// =============================================================================

/**
 * Get user preferences
 */
export async function getPreferences(): Promise<UserPreferences> {
  return api.get<UserPreferences>('/preferences')
}

/**
 * Update user preferences (partial update)
 */
export async function updatePreferences(request: PreferencesUpdateRequest): Promise<UserPreferences> {
  return api.patch<UserPreferences>('/preferences', request)
}

/**
 * Reset preferences to defaults
 */
export async function resetPreferences(): Promise<UserPreferences> {
  return api.post<UserPreferences>('/preferences/reset')
}

// =============================================================================
// Dashboard Settings API
// =============================================================================

/**
 * Get dashboard widget configuration
 */
export async function getDashboardSettings(): Promise<DashboardSettings> {
  return api.get<DashboardSettings>('/preferences/dashboard')
}

/**
 * Update dashboard widget configuration
 */
export async function updateDashboardSettings(
  request: DashboardSettingsUpdateRequest
): Promise<DashboardSettings> {
  return api.patch<DashboardSettings>('/preferences/dashboard', request)
}

/**
 * Reset dashboard to default widgets
 */
export async function resetDashboardSettings(): Promise<DashboardSettings> {
  return api.post<DashboardSettings>('/preferences/dashboard/reset')
}

/**
 * Get all available widgets with metadata
 */
export async function getAvailableWidgets(): Promise<AvailableWidgetsResponse> {
  return api.get<AvailableWidgetsResponse>('/preferences/dashboard/widgets')
}

// =============================================================================
// Convenience helpers
// =============================================================================

/**
 * Enable a single widget (adds to end of list)
 */
export async function enableWidget(widgetId: string): Promise<DashboardSettings> {
  const current = await getDashboardSettings()
  if (current.enabled_widgets.includes(widgetId)) {
    return current // Already enabled
  }
  return updateDashboardSettings({
    enabled_widgets: [...current.enabled_widgets, widgetId],
  })
}

/**
 * Disable a single widget
 */
export async function disableWidget(widgetId: string): Promise<DashboardSettings> {
  const current = await getDashboardSettings()
  return updateDashboardSettings({
    enabled_widgets: current.enabled_widgets.filter((id) => id !== widgetId),
  })
}

/**
 * Reorder widgets
 */
export async function reorderWidgets(newOrder: string[]): Promise<DashboardSettings> {
  return updateDashboardSettings({
    enabled_widgets: newOrder,
  })
}

/**
 * Update settings for a specific widget
 */
export async function updateWidgetSettings(
  widgetId: string,
  settings: Record<string, unknown>
): Promise<DashboardSettings> {
  const current = await getDashboardSettings()
  return updateDashboardSettings({
    widget_settings: {
      ...current.widget_settings,
      [widgetId]: settings,
    },
  })
}

