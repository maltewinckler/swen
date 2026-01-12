import { create } from 'zustand'
import type { UserInfo } from '@/types/api'
import {
  getCurrentUser,
  logout as apiLogout,
  tryRefresh,
  getAccessToken,
  clearAccessToken,
  clearLegacyTokens,
} from '@/api'

interface AuthState {
  user: UserInfo | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null

  // Actions
  initialize: () => Promise<void>
  setUser: (user: UserInfo) => void
  logout: () => Promise<void>
  clearError: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  error: null,

  initialize: async () => {
    // Clear any legacy localStorage tokens (migration)
    clearLegacyTokens()

    // First, check if we have an access token in memory
    const token = getAccessToken()

    if (token) {
      // We have a token, try to get user info
      try {
        const user = await getCurrentUser()
        set({ user, isAuthenticated: true, isLoading: false })
        return
      } catch {
        // Token might be expired, try to refresh
        clearAccessToken()
      }
    }

    // No token or expired - try to refresh using HttpOnly cookie
    const refreshed = await tryRefresh()

    if (refreshed) {
      try {
        const user = await getCurrentUser()
        set({ user, isAuthenticated: true, isLoading: false })
        return
      } catch {
        // Refresh worked but can't get user - clear everything
        clearAccessToken()
      }
    }

    // Not authenticated
    set({ user: null, isAuthenticated: false, isLoading: false })
  },

  setUser: (user) => {
    set({ user, isAuthenticated: true, error: null })
  },

  logout: async () => {
    await apiLogout()
    set({ user: null, isAuthenticated: false, error: null })
  },

  clearError: () => {
    set({ error: null })
  },
}))
