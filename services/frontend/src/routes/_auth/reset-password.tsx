import { useState } from 'react'
import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import { Lock, Eye, EyeOff, ArrowLeft, CheckCircle, AlertCircle } from 'lucide-react'
import { Button, Input, Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter, FormField, InlineAlert, SwenLogo } from '@/components/ui'
import { resetPassword } from '@/api'

export const Route = createFileRoute('/_auth/reset-password')({
  component: ResetPasswordPage,
  validateSearch: (search: Record<string, unknown>) => {
    return {
      token: (search.token as string) || '',
    }
  },
})

function ResetPasswordPage() {
  const navigate = useNavigate()
  const { token } = Route.useSearch()
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [isSuccess, setIsSuccess] = useState(false)

  const [form, setForm] = useState({
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
      await resetPassword(token, form.password)
      setIsSuccess(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reset password')
    } finally {
      setIsLoading(false)
    }
  }

  if (!token) {
    return (
      <Card className="border-none bg-transparent shadow-none">
        <CardHeader className="text-center lg:hidden">
          <SwenLogo size="lg" className="text-accent-primary mx-auto mb-2" />
        </CardHeader>

        <CardContent className="text-center space-y-4">
          <div className="mx-auto w-12 h-12 rounded-full bg-status-danger/10 flex items-center justify-center">
            <AlertCircle className="w-6 h-6 text-status-danger" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-text-primary mb-2">Invalid link</h2>
            <p className="text-text-secondary text-sm">
              This password reset link is invalid or has expired.
            </p>
          </div>
        </CardContent>

        <CardFooter className="justify-center">
          <Link to="/forgot-password" className="text-accent-primary hover:underline font-medium text-sm">
            Request a new reset link
          </Link>
        </CardFooter>
      </Card>
    )
  }

  if (isSuccess) {
    return (
      <Card className="border-none bg-transparent shadow-none">
        <CardHeader className="text-center lg:hidden">
          <SwenLogo size="lg" className="text-accent-primary mx-auto mb-2" />
        </CardHeader>

        <CardContent className="text-center space-y-4">
          <div className="mx-auto w-12 h-12 rounded-full bg-status-success/10 flex items-center justify-center">
            <CheckCircle className="w-6 h-6 text-status-success" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-text-primary mb-2">Password reset successful</h2>
            <p className="text-text-secondary text-sm">
              Your password has been updated. You can now sign in with your new password.
            </p>
          </div>
          <Button
            className="w-full"
            size="lg"
            onClick={() => navigate({ to: '/login' })}
          >
            Sign in
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="border-none bg-transparent shadow-none">
      <CardHeader className="text-center lg:hidden">
        <SwenLogo size="lg" className="text-accent-primary mx-auto mb-2" />
        <CardTitle className="text-2xl">Set new password</CardTitle>
        <CardDescription>Enter your new password below</CardDescription>
      </CardHeader>

      <CardHeader className="hidden lg:flex lg:flex-col text-center">
        <CardTitle className="text-2xl">Set new password</CardTitle>
        <CardDescription>Enter your new password below</CardDescription>
      </CardHeader>

      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <InlineAlert variant="danger">{error}</InlineAlert>
          )}

          <FormField label="New password">
            <Input
              id="password"
              type={showPassword ? 'text' : 'password'}
              placeholder="Enter new password"
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

          <FormField label="Confirm password">
            <Input
              id="confirmPassword"
              type={showConfirmPassword ? 'text' : 'password'}
              placeholder="Confirm new password"
              value={form.confirmPassword}
              onChange={(e) => setForm({ ...form, confirmPassword: e.target.value })}
              leftIcon={<Lock className="h-4 w-4" />}
              rightIcon={
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="hover:text-text-primary transition-colors"
                >
                  {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
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
            Reset password
          </Button>
        </form>
      </CardContent>

      <CardFooter className="justify-center">
        <Link to="/login" className="text-accent-primary hover:underline font-medium text-sm inline-flex items-center gap-1">
          <ArrowLeft className="w-4 h-4" />
          Back to login
        </Link>
      </CardFooter>
    </Card>
  )
}
