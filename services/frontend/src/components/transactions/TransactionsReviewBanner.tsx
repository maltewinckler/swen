import { ClipboardCheck, CheckCheck, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui'

interface TransactionsReviewBannerProps {
  isReviewMode: boolean
  onExit: () => void
  onPostAll?: () => void
  onReclassify?: () => void
  isPostingAll?: boolean
  isReclassifying?: boolean
}

export function TransactionsReviewBanner({
  isReviewMode,
  onExit,
  onPostAll,
  onReclassify,
  isPostingAll = false,
  isReclassifying = false,
}: TransactionsReviewBannerProps) {
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
      {onReclassify && (
        <Button variant="ghost" size="sm" onClick={onReclassify} disabled={isReclassifying}>
          <Sparkles className="h-4 w-4" />
          Reclassify
        </Button>
      )}
      {onPostAll && (
        <Button variant="ghost" size="sm" onClick={onPostAll} disabled={isPostingAll}>
          <CheckCheck className="h-4 w-4" />
          Post All
        </Button>
      )}
    </div>
  )
}
