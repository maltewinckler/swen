/**
 * Admin FinTS Configuration API
 *
 * Functions for managing FinTS banking configuration (admin only).
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

export interface FinTSMessageResponse {
  message: string
}

export interface UploadCSVResponse {
  message: string
  institute_count: number
  file_size_kb: number
}

export interface SaveInitialConfigResponse {
  message: string
  institute_count: number
  file_size_kb: number
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
 * Get current FinTS configuration (admin only)
 */
export async function getFinTSConfiguration(): Promise<FinTSConfigResponse> {
  return api.get<FinTSConfigResponse>('/admin/fints_config/configuration')
}

/**
 * Update FinTS Product ID (admin only)
 */
export async function updateFinTSProductId(productId: string): Promise<FinTSMessageResponse> {
  return api.put<FinTSMessageResponse>('/admin/fints_config/product-id', {
    product_id: productId,
  })
}

/**
 * Upload FinTS institute directory CSV (admin only)
 */
export async function uploadFinTSCSV(file: File): Promise<UploadCSVResponse> {
  const formData = new FormData()
  formData.append('file', file)
  return postFormData<UploadCSVResponse>('/admin/fints_config/csv', formData)
}

/**
 * Check FinTS configuration status (admin only)
 */
export async function getFinTSConfigStatus(): Promise<ConfigStatusResponse> {
  return api.get<ConfigStatusResponse>('/admin/fints_config/status')
}

/**
 * Save initial FinTS configuration during onboarding (admin only).
 * Combines product ID + CSV upload in a single request.
 */
export async function saveInitialFinTSConfig(
  productId: string,
  file: File,
): Promise<SaveInitialConfigResponse> {
  const formData = new FormData()
  formData.append('product_id', productId)
  formData.append('file', file)
  return postFormData<SaveInitialConfigResponse>('/admin/fints_config/initial', formData)
}
