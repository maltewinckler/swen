import type { ApiError } from '@/types/api'
import {
  getAccessToken,
  setAccessToken,
  clearAccessToken,
} from '@/services/token-service'

// Re-export token functions for backward compatibility
export { getAccessToken, setAccessToken, clearAccessToken, clearLegacyTokens } from '@/services/token-service'

export const API_BASE = '/api/v1'

// Default timeout: 30 seconds
const DEFAULT_TIMEOUT = 30000

// Long timeout for bank operations: configurable via env (default: 6 minutes)
// TAN approval can take 5+ minutes, large imports even longer
export const LONG_TIMEOUT = import.meta.env.VITE_LONG_TIMEOUT
  ? parseInt(import.meta.env.VITE_LONG_TIMEOUT as string, 10) * 1000  // Convert seconds to milliseconds
  : 360000  // Default: 6 minutes

// Minimum timeout for retry requests
const MIN_RETRY_TIMEOUT = 5000

/**
 * Custom API error with optional error code for field-level error handling
 */
export class ApiRequestError extends Error {
  status: number
  statusText: string
  detail: string
  /** Error code from backend (e.g., "DUPLICATE_ACCOUNT", "DUPLICATE_ACCOUNT_NUMBER") */
  code?: string

  constructor(status: number, statusText: string, detail: string, code?: string) {
    super(detail)
    this.name = 'ApiRequestError'
    this.status = status
    this.statusText = statusText
    this.detail = detail
    this.code = code
  }
}

interface FetchOptions extends RequestInit {
  timeout?: number
  /** Skip the automatic token refresh on 401 (for login/register endpoints) */
  skipAuthRefresh?: boolean
}

/**
 * Build headers object with proper typing
 */
function buildHeaders(
  baseHeaders: HeadersInit | undefined,
  token: string | null
): Record<string, string> {
  // Start with default headers
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }

  // Merge in any provided headers
  if (baseHeaders) {
    if (baseHeaders instanceof Headers) {
      baseHeaders.forEach((value, key) => {
        headers[key] = value
      })
    } else if (Array.isArray(baseHeaders)) {
      baseHeaders.forEach(([key, value]) => {
        headers[key] = value
      })
    } else {
      Object.assign(headers, baseHeaders)
    }
  }

  // Add authorization if token exists
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  return headers
}

/**
 * Base fetch wrapper with auth, timeout, and credentials
 */
async function fetchWithAuth<T>(
  endpoint: string,
  options: FetchOptions = {}
): Promise<T> {
  const { timeout = DEFAULT_TIMEOUT, skipAuthRefresh = false, ...fetchOptions } = options
  const startTime = Date.now()
  const token = getAccessToken()
  const headers = buildHeaders(fetchOptions.headers, token)

  // Create abort controller for timeout
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeout)

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...fetchOptions,
      headers,
      credentials: 'include', // Send cookies (for refresh token)
      signal: controller.signal,
    })

    clearTimeout(timeoutId)

    // Handle 401 - try to refresh token (unless skipAuthRefresh is set)
    if (response.status === 401 && !skipAuthRefresh) {
      const refreshed = await tryRefreshToken()
      if (refreshed) {
        // Calculate remaining timeout for retry
        const elapsed = Date.now() - startTime
        const remainingTimeout = Math.max(timeout - elapsed, MIN_RETRY_TIMEOUT)

        // Retry the request with new token
        const newToken = getAccessToken()
        const retryHeaders = buildHeaders(fetchOptions.headers, newToken)

        const retryController = new AbortController()
        const retryTimeoutId = setTimeout(() => retryController.abort(), remainingTimeout)

        try {
          const retryResponse = await fetch(`${API_BASE}${endpoint}`, {
            ...fetchOptions,
            headers: retryHeaders,
            credentials: 'include',
            signal: retryController.signal,
          })

          clearTimeout(retryTimeoutId)

          if (!retryResponse.ok) {
            const { detail, code } = await parseError(retryResponse)
            throw new ApiRequestError(retryResponse.status, retryResponse.statusText, detail, code)
          }

          // Handle 204 No Content
          if (retryResponse.status === 204) {
            return undefined as T
          }

          return retryResponse.json() as Promise<T>
        } catch (e) {
          clearTimeout(retryTimeoutId)
          if (e instanceof Error && e.name === 'AbortError') {
            throw new ApiRequestError(408, 'Request Timeout', 'The request timed out')
          }
          throw e
        }
      } else {
        // Clear access token and throw
        clearAccessToken()
        throw new ApiRequestError(401, 'Unauthorized', 'Session expired. Please log in again.')
      }
    }

    if (!response.ok) {
      const { detail, code } = await parseError(response)
      throw new ApiRequestError(response.status, response.statusText, detail, code)
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return undefined as T
    }

    return response.json() as Promise<T>
  } catch (e) {
    clearTimeout(timeoutId)
    if (e instanceof Error && e.name === 'AbortError') {
      throw new ApiRequestError(408, 'Request Timeout', 'The request timed out')
    }
    throw e
  }
}

interface ParsedError {
  detail: string
  code?: string
}

/**
 * Parse error response, extracting both detail and code
 */
async function parseError(response: Response): Promise<ParsedError> {
  try {
    const data = (await response.json()) as ApiError | { detail: unknown; code?: string }
    const detail = typeof data.detail === 'string'
      ? data.detail
      : JSON.stringify(data.detail)
    return {
      detail,
      code: 'code' in data ? data.code : undefined,
    }
  } catch {
    return {
      detail: response.statusText || 'An error occurred',
    }
  }
}

/**
 * Try to refresh the access token using HttpOnly cookie
 *
 * The refresh token is stored as an HttpOnly cookie, so we don't
 * need to send it in the request body - the browser sends it automatically.
 *
 * Returns true if successful, false otherwise.
 */
export async function tryRefreshToken(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include', // Send the HttpOnly cookie
      body: JSON.stringify({}), // Empty body - token is in cookie
    })

    if (!response.ok) return false

    const data = await response.json()
    setAccessToken(data.access_token)
    return true
  } catch {
    return false
  }
}

/**
 * Clear session - clears the refresh token cookie via API
 * (Internal function - use logout from auth.ts for the public API)
 */
export async function clearSession(): Promise<void> {
  try {
    await fetch(`${API_BASE}/auth/logout`, {
      method: 'POST',
      credentials: 'include',
    })
  } catch {
    // Ignore errors - we're logging out anyway
  }
  clearAccessToken()
}

/**
 * API methods
 */
export const api = {
  get: <T>(endpoint: string, options?: FetchOptions) =>
    fetchWithAuth<T>(endpoint, { ...options, method: 'GET' }),

  post: <T>(endpoint: string, body?: unknown, options?: FetchOptions) =>
    fetchWithAuth<T>(endpoint, {
      ...options,
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    }),

  put: <T>(endpoint: string, body?: unknown, options?: FetchOptions) =>
    fetchWithAuth<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: body ? JSON.stringify(body) : undefined,
    }),

  patch: <T>(endpoint: string, body?: unknown, options?: FetchOptions) =>
    fetchWithAuth<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body: body ? JSON.stringify(body) : undefined,
    }),

  delete: <T>(endpoint: string, options?: FetchOptions) =>
    fetchWithAuth<T>(endpoint, { ...options, method: 'DELETE' }),
}
