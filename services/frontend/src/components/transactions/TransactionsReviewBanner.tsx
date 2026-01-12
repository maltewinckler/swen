import { ClipboardCheck } from 'lucide-react'
import { Button } from '@/components/ui'

interface TransactionsReviewBannerProps {
  isReviewMode: boolean
  onExit: () => void
}

export function TransactionsReviewBanner({ isReviewMode, onExit }: TransactionsReviewBannerProps) {
  if (!isReviewMode) return null

  return (
    <div className="flex items-center gap-3 p-3 bg-accent-primary/10 border border-accent-primary/20 rounded-xl">
      <ClipboardCheck className="h-5 w-5 text-accent-primary" />
      <div className="flex-1">
        <p className="text-sm font-medium text-text-primary">Review Mode Active — Draft Transactions Only</p>
        <p className="text-xs text-text-muted">
          Click any draft to edit it. Use arrow keys to navigate, Ctrl+Enter to save & next.
        </p>
      </div>
      <Button variant="ghost" size="sm" onClick={onExit}>
        Exit
      </Button>
    </div>
  )
}
