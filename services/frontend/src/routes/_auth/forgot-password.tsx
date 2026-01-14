import { useState } from 'react'
import { createFileRoute, Link } from '@tanstack/react-router'
import { Mail, ArrowLeft, CheckCircle } from 'lucide-react'
import { Button, Input, Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter, FormField, InlineAlert, SwenLogo } from '@/components/ui'
import { forgotPassword } from '@/api'

export const Route = createFileRoute('/_auth/forgot-password')({
  component: ForgotPasswordPage,
})

function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [isSubmitted, setIsSubmitted] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      await forgotPassword(email)
      setIsSubmitted(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send reset email')
    } finally {
      setIsLoading(false)
    }
  }

  if (isSubmitted) {
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
            <h2 className="text-xl font-semibold text-text-primary mb-2">Check your email</h2>
            <p className="text-text-secondary text-sm">
              If an account exists for <span className="font-medium text-text-primary">{email}</span>,
              you will receive a password reset link shortly.
            </p>
          </div>
          <p className="text-text-tertiary text-xs">
            Didn't receive the email? Check your spam folder or try again.
          </p>
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

  return (
    <Card className="border-none bg-transparent shadow-none">
      <CardHeader className="text-center lg:hidden">
        <SwenLogo size="lg" className="text-accent-primary mx-auto mb-2" />
        <CardTitle className="text-2xl">Reset password</CardTitle>
        <CardDescription>Enter your email to receive a reset link</CardDescription>
      </CardHeader>

      <CardHeader className="hidden lg:flex lg:flex-col text-center">
        <CardTitle className="text-2xl">Reset password</CardTitle>
        <CardDescription>Enter your email to receive a reset link</CardDescription>
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
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              leftIcon={<Mail className="h-4 w-4" />}
              required
            />
          </FormField>

          <Button
            type="submit"
            className="w-full"
            size="lg"
            isLoading={isLoading}
          >
            Send reset link
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
