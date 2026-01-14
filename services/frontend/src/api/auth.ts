import type { AuthResponse, LoginRequest, RegisterRequest, UserInfo } from '@/types/api'
import { api, setAccessToken, clearSession, tryRefreshToken } from './client'

// Re-export tryRefreshToken as tryRefresh for backward compatibility
export { tryRefreshToken as tryRefresh }

/**
 * Login user
 *
 * The refresh token is automatically set as an HttpOnly cookie by the server.
 * We only store the access token in memory.
 */
export async function login(credentials: LoginRequest): Promise<AuthResponse> {
  const response = await api.post<AuthResponse>('/auth/login', credentials)
  setAccessToken(response.access_token)
  return response
}

/**
 * Register new user
 *
 * The refresh token is automatically set as an HttpOnly cookie by the server.
 * We only store the access token in memory.
 */
export async function register(data: RegisterRequest): Promise<AuthResponse> {
  const response = await api.post<AuthResponse>('/auth/register', data)
  setAccessToken(response.access_token)
  return response
}

/**
 * Logout user
 *
 * Calls the logout API to clear the HttpOnly cookie and clears the in-memory access token.
 */
export async function logout(): Promise<void> {
  await clearSession()
}

/**
 * Get current user info
 */
export async function getCurrentUser(): Promise<UserInfo> {
  return api.get<UserInfo>('/auth/me')
}

/**
 * Change password
 */
export async function changePassword(
  currentPassword: string,
  newPassword: string
): Promise<void> {
  await api.post('/auth/change-password', {
    current_password: currentPassword,
    new_password: newPassword,
  })
}

/**
 * Request password reset email
 */
export async function forgotPassword(email: string): Promise<void> {
  await api.post('/auth/forgot-password', { email })
}

/**
 * Reset password with token from email
 */
export async function resetPassword(token: string, newPassword: string): Promise<void> {
  await api.post('/auth/reset-password', {
    token,
    new_password: newPassword,
  })
}
