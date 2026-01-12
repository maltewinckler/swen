import { useState } from 'react'
import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import { useQueryClient } from '@tanstack/react-query'
import { Mail, Lock, Eye, EyeOff } from 'lucide-react'
import { Button, Input, Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter, FormField, InlineAlert, SwenLogo } from '@/components/ui'
import { register, getCurrentUser } from '@/api'
import { useAuthStore } from '@/stores'

export const Route = createFileRoute('/_auth/register')({
  component: RegisterPage,
})

function RegisterPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { setUser } = useAuthStore()
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  const [form, setForm] = useState({
    email: '',
    password: '',
    confirmPassword: '',
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (form.password !== form.confirmPassword) {
      setError('Passwords do not match')
      return
    }

    if (form.password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }

    setIsLoading(true)

    try {
      await register({
        email: form.email,
        password: form.password,
      })
      // Fetch user info after registration
      const user = await getCurrentUser()
      setUser(user)
      // Invalidate all queries to refetch with new auth token
      await queryClient.invalidateQueries()
      navigate({ to: '/dashboard' })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Card className="border-none bg-transparent shadow-none">
      <CardHeader className="text-center lg:hidden">
        <SwenLogo size="lg" className="text-accent-primary mx-auto mb-2" />
        <CardTitle className="text-2xl">Create account</CardTitle>
        <CardDescription>Get started with SWEN</CardDescription>
      </CardHeader>

      <CardHeader className="hidden lg:flex lg:flex-col text-center">
        <CardTitle className="text-2xl">Create account</CardTitle>
        <CardDescription>Start tracking your finances today</CardDescription>
      </CardHeader>

      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <InlineAlert variant="danger">{error}</InlineAlert>
          )}

          <FormField label="Email">
            <Input
              id="email"
              type="email"
              placeholder="you@example.com"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              leftIcon={<Mail className="h-4 w-4" />}
              required
            />
          </FormField>

          <FormField label="Password">
            <Input
              id="password"
              type={showPassword ? 'text' : 'password'}
              placeholder="At least 8 characters"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              leftIcon={<Lock className="h-4 w-4" />}
              rightIcon={
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="hover:text-text-primary transition-colors"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              }
              required
            />
          </FormField>

          <FormField label="Confirm Password">
            <Input
              id="confirmPassword"
              type={showPassword ? 'text' : 'password'}
              placeholder="Repeat your password"
              value={form.confirmPassword}
              onChange={(e) => setForm({ ...form, confirmPassword: e.target.value })}
              leftIcon={<Lock className="h-4 w-4" />}
              required
            />
          </FormField>

          <Button
            type="submit"
            className="w-full"
            size="lg"
            isLoading={isLoading}
          >
            Create account
          </Button>
        </form>
      </CardContent>

      <CardFooter className="justify-center">
        <p className="text-sm text-text-secondary">
          Already have an account?{' '}
          <Link to="/login" className="text-accent-primary hover:underline font-medium">
            Sign in
          </Link>
        </p>
      </CardFooter>
    </Card>
  )
}
