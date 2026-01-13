/**
 * Admin Section
 *
 * User management panel for administrators.
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2, ShieldCheck, User as UserIcon, MoreVertical } from 'lucide-react'
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Button,
  Badge,
  Spinner,
  InlineAlert,
  ConfirmDialog,
  useToast,
} from '@/components/ui'
import { listUsers, deleteUser, updateUserRole } from '@/api'
import type { UserSummary } from '@/types/api'
import { formatDate } from '@/lib/utils'
import { useAuthStore } from '@/stores'
import { CreateUserModal } from './CreateUserModal'

export function AdminSection() {
  const queryClient = useQueryClient()
  const toast = useToast()
  const { user: currentUser } = useAuthStore()

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [userToDelete, setUserToDelete] = useState<UserSummary | null>(null)
  const [expandedUserId, setExpandedUserId] = useState<string | null>(null)

  // Fetch users
  const {
    data: users,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['admin', 'users'],
    queryFn: listUsers,
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (userId: string) => deleteUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
      toast.success({ description: 'User deleted successfully' })
      setUserToDelete(null)
    },
    onError: (err) => {
      toast.danger({ description: err instanceof Error ? err.message : 'Failed to delete user' })
    },
  })

  // Role update mutation
  const roleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: 'user' | 'admin' }) =>
      updateUserRole(userId, role),
    onSuccess: (updatedUser) => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
      toast.success({
        description: `${updatedUser.email} is now ${updatedUser.role === 'admin' ? 'an admin' : 'a user'}`,
      })
      setExpandedUserId(null)
    },
    onError: (err) => {
      toast.danger({ description: err instanceof Error ? err.message : 'Failed to update role' })
    },
  })

  const handleRoleChange = (user: UserSummary, newRole: 'user' | 'admin') => {
    if (user.role === newRole) return
    roleMutation.mutate({ userId: user.id, role: newRole })
  }

  const isCurrentUser = (user: UserSummary) => user.id === currentUser?.id

  return (
    <>
      <Card className="animate-slide-up">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>User Management</CardTitle>
            <CardDescription>Manage user accounts and permissions</CardDescription>
          </div>
          <Button onClick={() => setShowCreateModal(true)} size="sm">
            <Plus className="h-4 w-4 mr-2" />
            Add User
          </Button>
        </CardHeader>
        <CardContent>
          {isLoading && (
            <div className="flex justify-center py-8">
              <Spinner />
            </div>
          )}

          {error && (
            <InlineAlert variant="danger">
              {error instanceof Error ? error.message : 'Failed to load users'}
            </InlineAlert>
          )}

          {users && users.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border-subtle">
                    <th className="text-left py-3 px-4 text-sm font-medium text-text-secondary">
                      Email
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-text-secondary">
                      Role
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-text-secondary">
                      Created
                    </th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-text-secondary">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((user) => (
                    <tr
                      key={user.id}
                      className="border-b border-border-subtle last:border-0 hover:bg-bg-hover transition-colors"
                    >
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <span className="text-sm text-text-primary">{user.email}</span>
                          {isCurrentUser(user) && (
                            <Badge variant="info">You</Badge>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        {user.role === 'admin' ? (
                          <Badge variant="warning">
                            <ShieldCheck className="h-3 w-3 mr-1" />
                            Admin
                          </Badge>
                        ) : (
                          <Badge variant="default">
                            <UserIcon className="h-3 w-3 mr-1" />
                            User
                          </Badge>
                        )}
                      </td>
                      <td className="py-3 px-4 text-sm text-text-secondary">
                        {formatDate(user.created_at)}
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center justify-end gap-2 relative">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() =>
                              setExpandedUserId(expandedUserId === user.id ? null : user.id)
                            }
                            disabled={isCurrentUser(user)}
                            title={isCurrentUser(user) ? "Can't modify your own account" : 'Actions'}
                          >
                            <MoreVertical className="h-4 w-4" />
                          </Button>

                          {/* Dropdown menu */}
                          {expandedUserId === user.id && !isCurrentUser(user) && (
                            <div className="absolute right-0 top-full mt-1 z-10 bg-bg-surface border border-border-subtle rounded-lg shadow-lg py-1 min-w-[160px]">
                              {user.role === 'user' ? (
                                <button
                                  className="w-full text-left px-4 py-2 text-sm hover:bg-bg-hover transition-colors flex items-center gap-2"
                                  onClick={() => handleRoleChange(user, 'admin')}
                                  disabled={roleMutation.isPending}
                                >
                                  <ShieldCheck className="h-4 w-4" />
                                  Make Admin
                                </button>
                              ) : (
                                <button
                                  className="w-full text-left px-4 py-2 text-sm hover:bg-bg-hover transition-colors flex items-center gap-2"
                                  onClick={() => handleRoleChange(user, 'user')}
                                  disabled={roleMutation.isPending}
                                >
                                  <UserIcon className="h-4 w-4" />
                                  Remove Admin
                                </button>
                              )}
                              <button
                                className="w-full text-left px-4 py-2 text-sm hover:bg-bg-hover transition-colors flex items-center gap-2 text-accent-danger"
                                onClick={() => {
                                  setExpandedUserId(null)
                                  setUserToDelete(user)
                                }}
                              >
                                <Trash2 className="h-4 w-4" />
                                Delete User
                              </button>
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {users && users.length === 0 && (
            <p className="text-center text-text-muted py-8">No users found</p>
          )}
        </CardContent>
      </Card>

      {/* Create User Modal */}
      <CreateUserModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSuccess={() => {
          queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
          setShowCreateModal(false)
        }}
      />

      {/* Delete Confirmation */}
      <ConfirmDialog
        isOpen={!!userToDelete}
        onCancel={() => setUserToDelete(null)}
        onConfirm={() => {
          if (userToDelete) {
            deleteMutation.mutate(userToDelete.id)
          }
        }}
        title="Delete User"
        description={`Are you sure you want to delete ${userToDelete?.email}? This will permanently remove their account and all associated data.`}
        confirmLabel="Delete"
        variant="danger"
        isLoading={deleteMutation.isPending}
      />
    </>
  )
}
