/**
 * AI API - Model management and settings
 */

import { api, API_BASE, getAccessToken } from './client'

// =============================================================================
// Types
// =============================================================================

export interface AIStatus {
  enabled: boolean
  provider: string
  current_model: string
  model_available: boolean
  service_healthy: boolean
}

export interface AIModel {
  name: string
  display_name: string
  description: string
  size_display: string
  status: 'available' | 'downloading' | 'not_installed'
  is_recommended: boolean
  download_progress: number | null
}

export interface AIModelsResponse {
  provider: string
  models: AIModel[]
}

export interface AISettings {
  enabled: boolean
  model_name: string
  min_confidence: number
}

export interface AISettingsUpdate {
  enabled?: boolean
  model_name?: string
  min_confidence?: number
}

export interface DownloadProgress {
  model_name: string
  status: string
  progress: number | null
  completed_bytes: number
  total_bytes: number
  is_complete: boolean
  error: string | null
}

export interface AITestRequest {
  counterparty_name: string
  purpose: string
  amount: number
  model_name?: string
}

export interface AITestSuggestion {
  account_id: string
  account_number: string
  account_name: string
  confidence: number
  reasoning: string | null
}

export interface AITestResponse {
  model_used: string
  suggestion: AITestSuggestion | null
  meets_confidence_threshold: boolean
  processing_time_ms: number
}

export interface AITestExample {
  id: string
  label: string
  counterparty_name: string
  purpose: string
  amount: number
  category_hint: string
}

// =============================================================================
// API Functions
// =============================================================================

/**
 * Get current AI service status
 */
export async function getAIStatus(): Promise<AIStatus> {
  return api.get<AIStatus>('/ai/status')
}

/**
 * List all available AI models
 */
export async function listAIModels(): Promise<AIModelsResponse> {
  return api.get<AIModelsResponse>('/ai/models')
}

/**
 * Get info for a specific model
 */
export async function getModelInfo(modelName: string): Promise<AIModel> {
  return api.get<AIModel>(`/ai/models/${encodeURIComponent(modelName)}`)
}

/**
 * Start downloading a model and receive progress updates via SSE
 *
 * Returns an EventSource that will receive progress events.
 * Caller is responsible for closing the EventSource when done.
 */
export function pullModel(
  modelName: string,
  onProgress: (progress: DownloadProgress) => void,
  onError: (error: string) => void,
  onComplete: () => void
): () => void {
  const token = getAccessToken()
  const url = `${API_BASE}/ai/models/${encodeURIComponent(modelName)}/pull`

  // Create EventSource with auth header workaround
  // EventSource doesn't support custom headers, so we need to use fetch with SSE parsing
  const controller = new AbortController()

  const fetchSSE = async () => {
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          Authorization: token ? `Bearer ${token}` : '',
          Accept: 'text/event-stream',
        },
        credentials: 'include',
        signal: controller.signal,
      })

      if (!response.ok) {
        const error = await response.text()
        onError(error || `HTTP ${response.status}`)
        return
      }

      const reader = response.body?.getReader()
      if (!reader) {
        onError('No response body')
        return
      }

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()

        if (done) {
          onComplete()
          break
        }

        buffer += decoder.decode(value, { stream: true })

        // Parse SSE events
        const lines = buffer.split('\n')
        buffer = lines.pop() || '' // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6)) as DownloadProgress
              onProgress(data)

              if (data.is_complete || data.error) {
                if (data.error) {
                  onError(data.error)
                } else {
                  onComplete()
                }
                return
              }
            } catch {
              // Ignore parse errors for partial data
            }
          }
        }
      }
    } catch (e) {
      if (e instanceof Error && e.name === 'AbortError') {
        // Cancelled by user
        return
      }
      onError(e instanceof Error ? e.message : 'Unknown error')
    }
  }

  fetchSSE()

  // Return cancel function
  return () => controller.abort()
}

/**
 * Get user's AI settings
 */
export async function getAISettings(): Promise<AISettings> {
  return api.get<AISettings>('/ai/settings')
}

/**
 * Update user's AI settings
 */
export async function updateAISettings(updates: AISettingsUpdate): Promise<AISettings> {
  return api.patch<AISettings>('/ai/settings', updates)
}

/**
 * Test AI classification with sample data
 */
export async function testAIClassification(request: AITestRequest): Promise<AITestResponse> {
  return api.post<AITestResponse>('/ai/test', request)
}

/**
 * Get example transactions for testing AI classification
 */
export async function getAITestExamples(): Promise<AITestExample[]> {
  return api.get<AITestExample[]>('/ai/test/examples')
}

