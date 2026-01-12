/**
 * Token Service
 *
 * Centralized management of access tokens and legacy token migration.
 * Access tokens are stored in memory only for security (not in localStorage).
 *
 * This protects against XSS attacks that could steal tokens from localStorage.
 * On page refresh, tokens are cleared, but the HttpOnly refresh cookie allows
 * silent re-authentication.
 */

/**
 * In-memory access token storage
 */
let accessToken: string | null = null

/**
 * Get the current access token
 */
export function getAccessToken(): string | null {
  return accessToken
}

/**
 * Set the access token (called after login or token refresh)
 */
export function setAccessToken(token: string): void {
  accessToken = token
}

/**
 * Clear the access token (called on logout or auth failure)
 */
export function clearAccessToken(): void {
  accessToken = null
}

/**
 * Legacy localStorage keys for migration
 * These were used in older versions of the app
 */
const LEGACY_TOKEN_KEY = 'swen_access_token'
const LEGACY_REFRESH_TOKEN_KEY = 'swen_refresh_token'

/**
 * Clear legacy localStorage tokens (migration from old storage)
 * Call this on app initialization to migrate existing users
 */
export function clearLegacyTokens(): void {
  localStorage.removeItem(LEGACY_TOKEN_KEY)
  localStorage.removeItem(LEGACY_REFRESH_TOKEN_KEY)
}

