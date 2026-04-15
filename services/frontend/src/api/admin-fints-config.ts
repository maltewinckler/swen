/**
 * Admin Local FinTS Configuration API
 *
 * Functions for managing local FinTS banking configuration (admin only).
 */

import { api, API_BASE, getAccessToken, ApiRequestError } from './client'

// --- Types ---

export interface FinTSConfigResponse {
  product_id_masked: string
  csv_institute_count: number
  csv_file_size_kb: number
  last_updated: string
  last_updated_by: string
}

export interface ConfigStatusResponse {
  is_configured: boolean
  message: string
}

export interface UpdateLocalFinTSConfigResponse {
  message: string
  institute_count: number | null
  file_size_kb: number | null
}

// --- Helpers ---

/**
 * POST with FormData (multipart/form-data).
 * The standard `api.post` forces Content-Type: application/json and
 * JSON.stringifies the body, which doesn't work for file uploads.
 */
async function postFormData<T>(endpoint: string, formData: FormData): Promise<T> {
  const token = getAccessToken()
  const headers: Record<string, string> = {}
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  // Do NOT set Content-Type — the browser adds the multipart boundary automatically.

  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    headers,
    credentials: 'include',
    body: formData,
  })

  if (!response.ok) {
    let detail = response.statusText
    let code: string | undefined
    try {
      const data = await response.json()
      detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
      code = data.code
    } catch {
      // fall back to statusText
    }
    throw new ApiRequestError(response.status, response.statusText, detail, code)
  }

  return response.json() as Promise<T>
}

// --- API Functions ---

/**
 * Get current local FinTS configuration (admin only).
 */
export async function getFinTSConfiguration(): Promise<FinTSConfigResponse> {
  return api.get<FinTSConfigResponse>('/admin/local_fints_configuration')
}

/**
 * Check local FinTS configuration status (admin only).
 */
export async function getFinTSConfigStatus(): Promise<ConfigStatusResponse> {
  return api.get<ConfigStatusResponse>('/admin/local_fints_configuration/status')
}

/**
 * Create or update local FinTS configuration (admin only).
 *
 * On first-time setup both product_id and file are required.
 * On subsequent calls each field is optional — only provided fields are updated.
 */
export async function saveLocalFinTSConfig(
  productId?: string,
  file?: File,
): Promise<UpdateLocalFinTSConfigResponse> {
  const formData = new FormData()
  if (productId !== undefined) {
    formData.append('product_id', productId)
  }
  if (file !== undefined) {
    formData.append('file', file)
  }
  return postFormData<UpdateLocalFinTSConfigResponse>('/admin/local_fints_configuration', formData)
}
