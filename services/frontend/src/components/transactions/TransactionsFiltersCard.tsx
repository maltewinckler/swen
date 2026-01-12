import { ArrowLeftRight, Search } from 'lucide-react'
import { Button, Card, CardContent, Input } from '@/components/ui'

interface TransactionsFiltersCardProps {
  searchQuery: string
  onSearchQueryChange: (value: string) => void

  days: number
  onDaysChange: (days: 7 | 30 | 90) => void

  statusFilter: 'all' | 'posted' | 'draft'
  onStatusFilterChange: (value: 'all' | 'posted' | 'draft') => void

  showTransfers: boolean
  onToggleShowTransfers: () => void
}

export function TransactionsFiltersCard({
  searchQuery,
  onSearchQueryChange,
  days,
  onDaysChange,
  statusFilter,
  onStatusFilterChange,
  showTransfers,
  onToggleShowTransfers,
}: TransactionsFiltersCardProps) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <Input
              placeholder="Search transactions..."
              value={searchQuery}
              onChange={(e) => onSearchQueryChange(e.target.value)}
              leftIcon={<Search className="h-4 w-4" />}
            />
          </div>
          <div className="flex gap-2">
            <Button variant={days === 7 ? 'primary' : 'secondary'} size="sm" onClick={() => onDaysChange(7)}>
              7 days
            </Button>
            <Button variant={days === 30 ? 'primary' : 'secondary'} size="sm" onClick={() => onDaysChange(30)}>
              30 days
            </Button>
            <Button variant={days === 90 ? 'primary' : 'secondary'} size="sm" onClick={() => onDaysChange(90)}>
              90 days
            </Button>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-4 mt-3">
          <div className="flex gap-2">
            <Button variant={statusFilter === 'all' ? 'primary' : 'ghost'} size="sm" onClick={() => onStatusFilterChange('all')}>
              All
            </Button>
            <Button variant={statusFilter === 'posted' ? 'primary' : 'ghost'} size="sm" onClick={() => onStatusFilterChange('posted')}>
              Posted
            </Button>
            <Button variant={statusFilter === 'draft' ? 'primary' : 'ghost'} size="sm" onClick={() => onStatusFilterChange('draft')}>
              Draft
            </Button>
          </div>

          <div className="flex items-center gap-2 ml-auto">
            <Button
              variant={showTransfers ? 'secondary' : 'ghost'}
              size="sm"
              onClick={onToggleShowTransfers}
              className="flex items-center gap-1.5"
            >
              <ArrowLeftRight className="h-3.5 w-3.5" />
              {showTransfers ? 'Hide Transfers' : 'Show Transfers'}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
