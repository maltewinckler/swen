/**
 * Create User Modal
 *
 * Modal for administrators to create new user accounts.
 */

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import {
  Modal,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  Input,
  FormField,
  Select,
  InlineAlert,
  useToast,
} from '@/components/ui'
import { createUser, ApiRequestError } from '@/api'

interface CreateUserModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

export function CreateUserModal({ isOpen, onClose, onSuccess }: CreateUserModalProps) {
  const toast = useToast()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [role, setRole] = useState<'user' | 'admin'>('user')
  const [error, setError] = useState('')

  const resetForm = () => {
    setEmail('')
    setPassword('')
    setConfirmPassword('')
    setRole('user')
    setError('')
  }

  const handleClose = () => {
    resetForm()
    onClose()
  }

  const mutation = useMutation({
    mutationFn: () =>
      createUser({
        email,
        password,
        role,
      }),
    onSuccess: (user) => {
      toast.success({ description: `User ${user.email} created successfully` })
      resetForm()
      onSuccess()
    },
    onError: (err) => {
      if (err instanceof ApiRequestError) {
        setError(err.detail)
      } else {
        setError(err instanceof Error ? err.message : 'Failed to create user')
      }
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    // Validation
    if (!email.trim()) {
      setError('Email is required')
      return
    }

    if (!password) {
      setError('Password is required')
      return
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    mutation.mutate()
  }

  const roleOptions = [
    { value: 'user', label: 'User' },
    { value: 'admin', label: 'Admin' },
  ]

  return (
    <Modal isOpen={isOpen} onClose={handleClose} size="md">
      <form onSubmit={handleSubmit}>
        <ModalHeader onClose={handleClose}>Create New User</ModalHeader>

        <ModalBody className="space-y-4">
          {error && <InlineAlert variant="danger">{error}</InlineAlert>}

          <FormField label="Email">
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="user@example.com"
              autoFocus
            />
          </FormField>

          <FormField label="Password">
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Minimum 8 characters"
            />
          </FormField>

          <FormField label="Confirm Password">
            <Input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Repeat password"
            />
          </FormField>

          <FormField label="Role">
            <Select
              options={roleOptions}
              value={role}
              onChange={(value) => setRole(value as 'user' | 'admin')}
            />
          </FormField>
        </ModalBody>

        <ModalFooter>
          <Button variant="ghost" type="button" onClick={handleClose}>
            Cancel
          </Button>
          <Button type="submit" isLoading={mutation.isPending}>
            Create User
          </Button>
        </ModalFooter>
      </form>
    </Modal>
  )
}
