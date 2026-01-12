import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export function Spinner({ size = 'md', className }: SpinnerProps) {
  const sizes = {
    sm: 'h-4 w-4',
    md: 'h-6 w-6',
    lg: 'h-8 w-8',
  }

  return (
    <Loader2 className={cn('animate-spin text-text-muted', sizes[size], className)} />
  )
}

export function LoadingScreen() {
  return (
    <div className="flex h-screen w-full items-center justify-center bg-bg-base">
      <div className="flex flex-col items-center gap-4">
        <Spinner size="lg" />
        <p className="text-text-secondary text-sm">Loading...</p>
      </div>
    </div>
  )
}

