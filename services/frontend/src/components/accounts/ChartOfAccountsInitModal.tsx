import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Sparkles } from 'lucide-react'
import { Button, Modal, ModalBody, ModalHeader, useToast } from '@/components/ui'
import { initChartOfAccounts } from '@/api'
import { cn } from '@/lib/utils'

interface ChartOfAccountsInitModalProps {
  isOpen: boolean
  onClose: () => void
  onRequestManualSetup: () => void
}

export function ChartOfAccountsInitModal({ isOpen, onClose, onRequestManualSetup }: ChartOfAccountsInitModalProps) {
  const queryClient = useQueryClient()
  const toast = useToast()
  const [selectedOption, setSelectedOption] = useState<'template' | 'manual'>('template')

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
    <Modal isOpen={isOpen} onClose={onClose} size="lg">
      <ModalHeader onClose={onClose} description="Choose how to set up your chart of accounts">
        Initialize Accounts
      </ModalHeader>
      <ModalBody className="space-y-3">
        {/* Use Template Option */}
        <div
          className={cn(
            'p-4 rounded-lg border-2 cursor-pointer transition-all',
            selectedOption === 'template'
              ? 'border-accent-primary bg-accent-primary/5'
              : 'border-border-default hover:border-border-hover'
          )}
          onClick={() => setSelectedOption('template')}
        >
          <div className="flex items-start gap-3">
            <div
              className={cn(
                'w-5 h-5 rounded-full border-2 flex items-center justify-center mt-0.5 flex-shrink-0',
                selectedOption === 'template' ? 'border-accent-primary' : 'border-border-default'
              )}
            >
              {selectedOption === 'template' && <div className="w-2.5 h-2.5 rounded-full bg-accent-primary" />}
            </div>
            <div className="flex-1">
              <p className="font-medium text-text-primary">Use Default Template</p>
              <p className="text-sm text-text-muted mt-1">
                Simple expense and income accounts for everyday personal finance. ~15 accounts covering essentials.
              </p>
              <div className="mt-3 text-xs text-text-muted">
                <p className="font-medium text-text-secondary mb-1">Includes:</p>
                <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
                  <span>• Gehalt & Lohn</span>
                  <span>• Miete</span>
                  <span>• Lebensmittel</span>
                  <span>• Restaurants & Bars</span>
                  <span>• Transport</span>
                  <span>• Sport & Fitness</span>
                  <span>• Abonnements</span>
                  <span>• Sonstiges</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Manual Creation Option */}
        <div
          className={cn(
            'p-4 rounded-lg border-2 cursor-pointer transition-all',
            selectedOption === 'manual'
              ? 'border-accent-primary bg-accent-primary/5'
              : 'border-border-default hover:border-border-hover'
          )}
          onClick={() => setSelectedOption('manual')}
        >
          <div className="flex items-start gap-3">
            <div
              className={cn(
                'w-5 h-5 rounded-full border-2 flex items-center justify-center mt-0.5 flex-shrink-0',
                selectedOption === 'manual' ? 'border-accent-primary' : 'border-border-default'
              )}
            >
              {selectedOption === 'manual' && <div className="w-2.5 h-2.5 rounded-full bg-accent-primary" />}
            </div>
            <div className="flex-1">
              <p className="font-medium text-text-primary">Create Manually</p>
              <p className="text-sm text-text-muted mt-1">
                Build your own chart of accounts. We'll guide you through creating custom income and expense
                categories.
              </p>
            </div>
          </div>
        </div>

        <div className="flex gap-3 pt-2">
          <Button variant="secondary" className="flex-1" onClick={onClose}>
            Cancel
          </Button>
          <Button
            className="flex-1"
            onClick={() => {
              if (selectedOption === 'manual') {
                onClose()
                onRequestManualSetup()
              } else {
                initChartMutation.mutate()
              }
            }}
            isLoading={initChartMutation.isPending}
          >
            {selectedOption === 'manual' ? (
              <>
                <Plus className="h-4 w-4" />
                Start Creating
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                Create Accounts
              </>
            )}
          </Button>
        </div>
      </ModalBody>
    </Modal>
  )
}
