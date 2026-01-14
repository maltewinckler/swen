import { useState } from 'react'
import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import { useQueryClient } from '@tanstack/react-query'
import { Mail, Lock, Eye, EyeOff } from 'lucide-react'
import { Button, Input, Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter, FormField, InlineAlert, SwenLogo } from '@/components/ui'
import { login, getCurrentUser } from '@/api'
import { useAuthStore } from '@/stores'

export const Route = createFileRoute('/_auth/login')({
  component: LoginPage,
})

function LoginPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { setUser } = useAuthStore()
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  const [form, setForm] = useState({
    email: '',
    password: '',
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      await login(form)
      // Fetch user info after login
      const user = await getCurrentUser()
      setUser(user)
      // Invalidate all queries to refetch with new auth token
      await queryClient.invalidateQueries()
      navigate({ to: '/dashboard' })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Card className="border-none bg-transparent shadow-none">
      <CardHeader className="text-center lg:hidden">
        <SwenLogo size="lg" className="text-accent-primary mx-auto mb-2" />
        <CardTitle className="text-2xl">Welcome back</CardTitle>
        <CardDescription>Sign in to your SWEN account</CardDescription>
      </CardHeader>

      <CardHeader className="hidden lg:flex lg:flex-col text-center">
        <CardTitle className="text-2xl">Welcome back</CardTitle>
        <CardDescription>Sign in to your account</CardDescription>
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
              placeholder="Enter your password"
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

          <Button
            type="submit"
            className="w-full"
            size="lg"
            isLoading={isLoading}
          >
            Sign in
          </Button>
        </form>
      </CardContent>

      <CardFooter className="flex-col gap-2">
        <p className="text-sm text-text-secondary">
          Don't have an account?{' '}
          <Link to="/register" className="text-accent-primary hover:underline font-medium">
            Create one
          </Link>
        </p>
        <p className="text-sm text-text-secondary">
          Forgot password?{' '}
          <Link to="/forgot-password" className="text-accent-primary hover:underline font-medium">
            Reset it
          </Link>
        </p>
      </CardFooter>
    </Card>
  )
}
