/**
 * Admin API
 *
 * Functions for admin user management.
 */

import type { UserSummary, CreateUserRequest } from '@/types/api'
import { api } from './client'

/**
 * List all users (admin only)
 */
export async function listUsers(): Promise<UserSummary[]> {
  return api.get<UserSummary[]>('/admin/users')
}

/**
 * Create a new user (admin only)
 */
export async function createUser(data: CreateUserRequest): Promise<UserSummary> {
  return api.post<UserSummary>('/admin/users', data)
}

/**
 * Delete a user (admin only)
 */
export async function deleteUser(userId: string): Promise<void> {
  await api.delete(`/admin/users/${userId}`)
}

/**
 * Update a user's role (admin only)
 */
export async function updateUserRole(
  userId: string,
  role: 'user' | 'admin'
): Promise<UserSummary> {
  return api.patch<UserSummary>(`/admin/users/${userId}/role`, { role })
}
