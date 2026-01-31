import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Sparkles, TrendingDown, TrendingUp } from 'lucide-react'
import { Button, Modal, ModalBody, ModalHeader, useToast } from '@/components/ui'
import { initChartOfAccounts } from '@/api'

interface ChartOfAccountsInitModalProps {
  isOpen: boolean
  onClose: () => void
}

const TEMPLATE_ACCOUNTS = [
  { name: 'Gehalt & Lohn', type: 'Income' },
  { name: 'Miete', type: 'Expense' },
  { name: 'Lebensmittel', type: 'Expense' },
  { name: 'Restaurants & Bars', type: 'Expense' },
  { name: 'Transport', type: 'Expense' },
  { name: 'Sport & Fitness', type: 'Expense' },
  { name: 'Abonnements', type: 'Expense' },
  { name: 'Sonstiges', type: 'Expense' },
]

export function ChartOfAccountsInitModal({ isOpen, onClose }: ChartOfAccountsInitModalProps) {
  const queryClient = useQueryClient()
  const toast = useToast()

  const initChartMutation = useMutation({
    mutationFn: () => initChartOfAccounts('minimal'),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
      onClose()
      if (result.skipped) {
        toast.info({ title: 'Accounts', description: 'Chart of accounts already initialized.' })
      } else {
        toast.success({
          title: 'Accounts created',
          description: `Created ${result.accounts_created} account${result.accounts_created === 1 ? '' : 's'}.`,
        })
      }
    },
    onError: (err) => {
      toast.danger({
        title: 'Failed to initialize accounts',
        description: err instanceof Error ? err.message : 'Unknown error',
      })
    },
  })

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="md">
      <ModalHeader onClose={onClose} description="Create common expense and income categories">
        Initialize Accounts
      </ModalHeader>
      <ModalBody className="space-y-4">
        <div className="p-4 rounded-lg bg-bg-subtle border border-border-default max-h-48 overflow-y-auto">
          <div className="grid grid-cols-2 gap-2">
            {TEMPLATE_ACCOUNTS.map((acc, i) => (
              <div key={i} className="flex items-center gap-2 text-sm">
                {acc.type === 'Income' ? (
                  <TrendingUp className="h-3.5 w-3.5 text-accent-success flex-shrink-0" />
                ) : (
                  <TrendingDown className="h-3.5 w-3.5 text-accent-danger flex-shrink-0" />
                )}
                <span className="text-text-primary">{acc.name}</span>
              </div>
            ))}
          </div>
        </div>

        <p className="text-xs text-text-muted text-center">
          You can add, rename, or remove accounts later using the "Add Account" button.
        </p>

        <div className="flex gap-3">
          <Button variant="secondary" className="flex-1" onClick={onClose}>
            Cancel
          </Button>
          <Button
            className="flex-1"
            onClick={() => initChartMutation.mutate()}
            isLoading={initChartMutation.isPending}
          >
            <Sparkles className="h-4 w-4" />
            Create Accounts
          </Button>
        </div>
      </ModalBody>
    </Modal>
  )
}
