/**
 * Onboarding FinTS Configuration Step
 *
 * Allows the first admin user to configure FinTS Product ID and
 * upload the institute directory CSV during initial onboarding.
 * Uses the combined /initial endpoint for a single-step setup.
 */

import { useRef, useState } from 'react'
import { Settings, Upload, ArrowRight, ExternalLink, AlertTriangle } from 'lucide-react'
import {
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  FormField,
  Input,
  Button,
  InlineAlert,
  WizardInfoBanner,
} from '@/components/ui'

interface OnboardingFinTSConfigStepProps {
  /** Called when the step is completed successfully */
  onComplete: () => void
  /** Called when the user chooses to skip this step */
  onSkip: () => void
  /** Called when the save is initiated — parent handles the mutation */
  onSave: (productId: string, file: File) => void
  /** Whether the save mutation is currently pending */
  isSaving: boolean
  /** Error from the save mutation, if any */
  saveError: string | null
}

export function OnboardingFinTSConfigStep({
  onSkip,
  onSave,
  isSaving,
  saveError,
}: Omit<OnboardingFinTSConfigStepProps, 'onComplete'>) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [productId, setProductId] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [localError, setLocalError] = useState('')
  const [showSkipWarning, setShowSkipWarning] = useState(false)

  const error = saveError ?? localError

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setLocalError('')
    const file = e.target.files?.[0] ?? null
    if (file && !file.name.endsWith('.csv')) {
      setLocalError('Please select a CSV file')
      setSelectedFile(null)
      return
    }
    setSelectedFile(file)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setLocalError('')

    if (!productId.trim()) {
      setLocalError('Product ID is required')
      return
    }
    if (!selectedFile) {
      setLocalError('Institute CSV file is required')
      return
    }

    onSave(productId.trim(), selectedFile)
  }

  if (showSkipWarning) {
    return (
      <>
        <CardHeader className="text-center pb-2">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-accent-warning/10">
            <AlertTriangle className="h-8 w-8 text-accent-warning" />
          </div>
          <CardTitle>Skip FinTS Configuration?</CardTitle>
          <CardDescription className="text-base mt-2">
            Without FinTS configuration, bank connections will not work.
            You can configure this later in Settings → Administration.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-3">
            <Button
              variant="secondary"
              className="flex-1"
              onClick={() => setShowSkipWarning(false)}
            >
              Go Back
            </Button>
            <Button variant="primary" className="flex-1" onClick={onSkip}>
              Skip Anyway
              <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
          </div>
        </CardContent>
      </>
    )
  }

  return (
    <>
      <CardHeader className="text-center pb-2">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-accent-primary to-accent-info">
          <Settings className="h-8 w-8 text-white" />
        </div>
        <CardTitle className="text-2xl">FinTS Configuration</CardTitle>
        <CardDescription className="text-base mt-2">
          Configure your FinTS banking credentials to enable bank connections.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-5">
          {error && <InlineAlert variant="danger">{error}</InlineAlert>}

          <WizardInfoBanner>
            <p className="text-sm text-text-secondary">
              You need a{' '}
              <a
                href="https://www.hbci-zka.de/register/prod_register.htm"
                target="_blank"
                rel="noopener noreferrer"
                className="text-accent-primary hover:underline inline-flex items-center gap-1"
              >
                FinTS Product ID
                <ExternalLink className="h-3 w-3" />
              </a>{' '}
              and the institute directory CSV file from the Deutsche Kreditwirtschaft.
            </p>
          </WizardInfoBanner>

          <FormField
            label="FinTS Product ID"
            helperText="The product registration ID assigned by Deutsche Kreditwirtschaft"
            required
          >
            <Input
              value={productId}
              onChange={(e) => {
                setProductId(e.target.value)
                setLocalError('')
              }}
              placeholder="e.g. 1234567890AB"
              maxLength={100}
              required
            />
          </FormField>

          <FormField
            label="Institute Directory CSV"
            helperText="The fints_institute.csv file (CP1252 encoded)"
            required
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              onChange={handleFileChange}
              className="block w-full text-sm text-text-secondary
                file:mr-4 file:py-2 file:px-4
                file:rounded-md file:border-0
                file:text-sm file:font-medium
                file:bg-bg-hover file:text-text-primary
                hover:file:bg-bg-active
                file:cursor-pointer cursor-pointer"
            />
          </FormField>

          {selectedFile && (
            <div className="flex items-center gap-2 text-xs text-text-muted">
              <Upload className="h-3.5 w-3.5" />
              {selectedFile.name} ({Math.round(selectedFile.size / 1024)} KB)
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <Button
              type="button"
              variant="secondary"
              className="flex-1"
              onClick={() => setShowSkipWarning(true)}
            >
              Skip for Now
            </Button>
            <Button
              type="submit"
              className="flex-1"
              isLoading={isSaving}
              disabled={!productId.trim() || !selectedFile}
            >
              Save & Continue
              <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
          </div>
        </form>
      </CardContent>
    </>
  )
}
