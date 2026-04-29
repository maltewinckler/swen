/**
 * Onboarding Banking Provider Step
 *
 * Allows the first admin user to configure either Geldstrom API or
 * local FinTS during initial onboarding. Replaces the former
 * OnboardingFinTSConfigStep with a two-tab provider selection.
 */

import { useState } from 'react'
import { Zap, Settings, ArrowRight, AlertTriangle } from 'lucide-react'
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
import { FinTSConfigFormFields } from '@/components/banking-provider'
import type { BankingProviderMode } from '@/api/admin-banking-provider'

export type BankingProviderSaveParams =
  | { mode: 'api'; apiKey: string; endpointUrl: string }
  | { mode: 'local'; productId: string; file: File }

interface OnboardingBankingProviderStepProps {
  onSkip: () => void
  onSave: (params: BankingProviderSaveParams) => void
  isSaving: boolean
  saveError: string | null
}

const DEFAULT_ENDPOINT_URL = 'https://geldstrom-api.de'

export function OnboardingBankingProviderStep({
  onSkip,
  onSave,
  isSaving,
  saveError,
}: OnboardingBankingProviderStepProps) {
  const [activeTab, setActiveTab] = useState<BankingProviderMode>('api')
  const [showSkipWarning, setShowSkipWarning] = useState(false)

  // Geldstrom API state
  const [apiKey, setApiKey] = useState('')
  const [endpointUrl, setEndpointUrl] = useState(DEFAULT_ENDPOINT_URL)

  // Local FinTS state
  const [productId, setProductId] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  const [localError, setLocalError] = useState('')
  const error = saveError ?? localError

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setLocalError('')

    if (activeTab === 'api') {
      if (!apiKey.trim()) {
        setLocalError('API Key is required')
        return
      }
      if (!endpointUrl.trim()) {
        setLocalError('Endpoint URL is required')
        return
      }
      onSave({ mode: 'api', apiKey: apiKey.trim(), endpointUrl: endpointUrl.trim() })
    } else {
      if (!productId.trim()) {
        setLocalError('Product ID is required')
        return
      }
      if (!selectedFile) {
        setLocalError('Institute CSV file is required')
        return
      }
      onSave({ mode: 'local', productId: productId.trim(), file: selectedFile })
    }
  }

  if (showSkipWarning) {
    return (
      <>
        <CardHeader className="text-center pb-2">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-accent-warning/10">
            <AlertTriangle className="h-8 w-8 text-accent-warning" />
          </div>
          <CardTitle>Skip Banking Provider Configuration?</CardTitle>
          <CardDescription className="text-base mt-2">
            Without a banking provider configured, bank connections will not work.
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
          <Zap className="h-8 w-8 text-white" />
        </div>
        <CardTitle className="text-2xl">Banking Provider</CardTitle>
        <CardDescription className="text-base mt-2">
          Choose how SWEN connects to your bank (centralized Geldstrom API or local FinTS).
        </CardDescription>
      </CardHeader>
      <CardContent>
        {/* Tab Switcher */}
        <div className="flex gap-2 mb-6">
          <Button
            type="button"
            variant={activeTab === 'api' ? 'primary' : 'secondary'}
            className="flex-1"
            onClick={() => { setActiveTab('api'); setLocalError('') }}
          >
            <Zap className="h-4 w-4 mr-2" />
            Geldstrom API
          </Button>
          <Button
            type="button"
            variant={activeTab === 'local' ? 'primary' : 'secondary'}
            className="flex-1"
            onClick={() => { setActiveTab('local'); setLocalError('') }}
          >
            <Settings className="h-4 w-4 mr-2" />
            Local FinTS
          </Button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {error && <InlineAlert variant="danger">{error}</InlineAlert>}

          {activeTab === 'api' && (
            <>
              <WizardInfoBanner>
                <p className="text-sm text-text-secondary">
                  The Geldstrom API handles the institute directory and product key centrally.
                </p>
              </WizardInfoBanner>

              <FormField
                label="API Key"
                helperText="Your Geldstrom API bearer token"
                required
              >
                <Input
                  type="password"
                  value={apiKey}
                  onChange={(e) => { setApiKey(e.target.value); setLocalError('') }}
                  placeholder="Enter API key"
                  maxLength={500}
                  required
                />
              </FormField>

              <FormField
                label="Endpoint URL"
                helperText="Base URL of the Geldstrom API"
                required
              >
                <Input
                  value={endpointUrl}
                  onChange={(e) => { setEndpointUrl(e.target.value); setLocalError('') }}
                  placeholder={DEFAULT_ENDPOINT_URL}
                  maxLength={500}
                  required
                />
              </FormField>
            </>
          )}

          {activeTab === 'local' && (
            <FinTSConfigFormFields
              productId={productId}
              onProductIdChange={(v) => { setProductId(v); setLocalError('') }}
              selectedFile={selectedFile}
              onFileChange={(f) => { setSelectedFile(f); setLocalError('') }}
            />
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
              disabled={
                activeTab === 'api'
                  ? !apiKey.trim() || !endpointUrl.trim()
                  : !productId.trim() || !selectedFile
              }
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
