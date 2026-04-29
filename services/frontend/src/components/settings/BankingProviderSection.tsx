/**
 * Banking Provider Section
 *
 * Admin panel for managing the active banking provider (Geldstrom API or local FinTS).
 * Replaces the former FinTSConfigSection with a unified provider management view.
 */

import { useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Upload, CheckCircle, XCircle, Zap, Settings, AlertTriangle } from 'lucide-react'
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  FormField,
  Input,
  Button,
  Badge,
  Spinner,
  InlineAlert,
  useToast,
} from '@/components/ui'
import {
  getBankingProviderStatus,
  getGeldstromApiConfig,
  saveGeldstromApiConfig,
  activateProvider,
  getFinTSConfiguration,
  saveLocalFinTSConfig,
} from '@/api'
import type { BankingProviderMode, GeldstromApiConfigResponse } from '@/api/admin-banking-provider'
import type { FinTSConfigResponse } from '@/api/admin-fints-config'
import { FinTSConfigFormFields } from '@/components/banking-provider'
import { formatDate } from '@/lib/utils'

export function BankingProviderSection() {
  const queryClient = useQueryClient()

  const {
    data: providerStatus,
    isLoading: statusLoading,
  } = useQuery({
    queryKey: ['admin', 'fints-provider', 'status'],
    queryFn: getBankingProviderStatus,
  })

  const {
    data: geldstromConfig,
    isLoading: geldstromLoading,
  } = useQuery({
    queryKey: ['admin', 'fints-provider', 'geldstrom'],
    queryFn: getGeldstromApiConfig,
    enabled: providerStatus?.api_configured === true,
    retry: false,
  })

  const {
    data: fintsConfig,
    isLoading: fintsLoading,
  } = useQuery({
    queryKey: ['admin', 'fints-config'],
    queryFn: getFinTSConfiguration,
    enabled: providerStatus?.local_configured === true,
    retry: false,
  })

  const activeProvider = providerStatus?.active_provider ?? null
  const isLoading = statusLoading

  return (
    <Card className="animate-slide-up">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Banking Provider</CardTitle>
            <CardDescription>
              Configure how SWEN connects to banks (centralized Geldstrom API or local FinTS).
            </CardDescription>
          </div>
          <ConfigStatusBadge activeProvider={activeProvider} isLoading={statusLoading} />
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {isLoading && (
          <div className="flex justify-center py-8">
            <Spinner />
          </div>
        )}

        {!isLoading && (
          <>
            {/* Geldstrom API Panel */}
            <GeldstromApiPanel
              isActive={activeProvider === 'api'}
              isConfigured={providerStatus?.api_configured ?? false}
              config={geldstromConfig ?? null}
              isLoadingConfig={geldstromLoading}
              otherProvider={activeProvider}
              onInvalidate={() => {
                queryClient.invalidateQueries({ queryKey: ['admin', 'fints-provider'] })
              }}
            />

            {/* Local FinTS Panel */}
            <FinTSPanel
              isActive={activeProvider === 'local'}
              isConfigured={providerStatus?.local_configured ?? false}
              config={fintsConfig ?? null}
              isLoadingConfig={fintsLoading}
              otherProvider={activeProvider}
              onInvalidate={() => {
                queryClient.invalidateQueries({ queryKey: ['admin', 'fints-provider'] })
                queryClient.invalidateQueries({ queryKey: ['admin', 'fints-config'] })
              }}
            />
          </>
        )}
      </CardContent>
    </Card>
  )
}

// --- Sub-components ---

function ConfigStatusBadge({
  activeProvider,
  isLoading,
}: {
  activeProvider: BankingProviderMode | null
  isLoading: boolean
}) {
  if (isLoading) return null

  if (activeProvider === 'api') {
    return (
      <Badge variant="success">
        <Zap className="h-3 w-3 mr-1" />
        Geldstrom API
      </Badge>
    )
  }
  if (activeProvider === 'local') {
    return (
      <Badge variant="success">
        <Settings className="h-3 w-3 mr-1" />
        Local FinTS
      </Badge>
    )
  }
  return (
    <Badge variant="danger">
      <XCircle className="h-3 w-3 mr-1" />
      Not Configured
    </Badge>
  )
}

function GeldstromApiPanel({
  isActive,
  isConfigured,
  config,
  isLoadingConfig,
  otherProvider,
  onInvalidate,
}: {
  isActive: boolean
  isConfigured: boolean
  config: GeldstromApiConfigResponse | null
  isLoadingConfig: boolean
  otherProvider: BankingProviderMode | null
  onInvalidate: () => void
}) {
  const toast = useToast()
  const [showForm, setShowForm] = useState(false)
  const [showSwitchWarning, setShowSwitchWarning] = useState(false)
  const [apiKey, setApiKey] = useState('')
  const [endpointUrl, setEndpointUrl] = useState('https://geldstrom-api.de')
  const [formError, setFormError] = useState('')
  const [isSavingAndActivating, setIsSavingAndActivating] = useState(false)

  const saveMutation = useMutation({
    mutationFn: () => saveGeldstromApiConfig(apiKey.trim(), endpointUrl.trim()),
    onSuccess: () => {
      toast.success({ description: 'Geldstrom API configuration saved' })
      setApiKey('')
      setShowForm(false)
      setFormError('')
      onInvalidate()
    },
    onError: (err) => {
      setFormError(err instanceof Error ? err.message : 'Failed to save configuration')
    },
  })

  const activateMutation = useMutation({
    mutationFn: () => activateProvider('api'),
    onSuccess: () => {
      toast.success({ description: 'Geldstrom API activated' })
      setShowSwitchWarning(false)
      onInvalidate()
    },
    onError: (err) => {
      toast.danger({
        description: err instanceof Error ? err.message : 'Unknown error',
      })
      setShowSwitchWarning(false)
    },
  })

  const handleSaveAndActivate = async () => {
    if (!apiKey.trim() || !endpointUrl.trim()) {
      setFormError('API Key and Endpoint URL are required')
      return
    }
    setIsSavingAndActivating(true)
    try {
      await saveGeldstromApiConfig(apiKey.trim(), endpointUrl.trim())
      await activateProvider('api')
      toast.success({ description: 'Geldstrom API configured and activated' })
      setApiKey('')
      setShowForm(false)
      setShowSwitchWarning(false)
      setFormError('')
      onInvalidate()
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Failed to configure')
    } finally {
      setIsSavingAndActivating(false)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setFormError('')
    if (!apiKey.trim()) { setFormError('API Key is required'); return }
    if (!endpointUrl.trim()) { setFormError('Endpoint URL is required'); return }
    saveMutation.mutate()
  }

  return (
    <div className="rounded-lg border border-border-subtle p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Zap className="h-5 w-5 text-accent-primary" />
          <h4 className="text-sm font-medium text-text-primary">Geldstrom API</h4>
          {isActive && (
            <Badge variant="success">
              <CheckCircle className="h-3 w-3 mr-1" />
              Active
            </Badge>
          )}
        </div>
        {!isActive && otherProvider !== null && (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              if (isConfigured) {
                setShowSwitchWarning(true)
              } else {
                setShowForm(true)
                setShowSwitchWarning(true)
              }
            }}
          >
            Switch to Geldstrom API
          </Button>
        )}
        {!isActive && otherProvider === null && (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setShowForm(true)}
          >
            Configure
          </Button>
        )}
      </div>

      {showSwitchWarning && !showForm && (
        <ProviderSwitchWarning
          targetLabel="Geldstrom API"
          isLoading={activateMutation.isPending}
          onCancel={() => setShowSwitchWarning(false)}
          onConfirm={() => activateMutation.mutate()}
        />
      )}

      {showSwitchWarning && showForm && (
        <div className="space-y-3">
          <InlineAlert variant="warning">
            <AlertTriangle className="h-4 w-4 mr-1 inline" />
            Configure Geldstrom API to switch from Local FinTS. Switching may interrupt active bank syncs.
          </InlineAlert>
          {formError && <InlineAlert variant="danger">{formError}</InlineAlert>}
          <FormField label="API Key" required>
            <Input
              type="password"
              value={apiKey}
              onChange={(e) => { setApiKey(e.target.value); setFormError('') }}
              placeholder="Enter API key"
              maxLength={500}
            />
          </FormField>
          <FormField label="Endpoint URL" required>
            <Input
              value={endpointUrl}
              onChange={(e) => { setEndpointUrl(e.target.value); setFormError('') }}
              placeholder="https://geldstrom-api.de"
              maxLength={500}
            />
          </FormField>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => { setShowSwitchWarning(false); setShowForm(false); setFormError('') }}>
              Cancel
            </Button>
            <Button onClick={handleSaveAndActivate} isLoading={isSavingAndActivating} disabled={isSavingAndActivating || !apiKey.trim() || !endpointUrl.trim()}>
              Save & Activate
            </Button>
          </div>
        </div>
      )}

      {isConfigured && config && !showSwitchWarning && (
        <div className="grid gap-3 sm:grid-cols-3">
          <div>
            <p className="text-xs text-text-muted">API Key</p>
            <code className="text-sm text-text-primary mt-0.5">{config.api_key_masked}</code>
          </div>
          <div>
            <p className="text-xs text-text-muted">Endpoint</p>
            <p className="text-sm text-text-primary mt-0.5">{config.endpoint_url}</p>
          </div>
          <div>
            <p className="text-xs text-text-muted">Last Updated</p>
            <p className="text-sm text-text-primary mt-0.5">
              {config.last_updated ? formatDate(config.last_updated) : '—'}
            </p>
          </div>
        </div>
      )}

      {isLoadingConfig && <Spinner />}

      {/* Update form when already active */}
      {isActive && !showForm && (
        <Button variant="secondary" size="sm" onClick={() => setShowForm(true)}>
          Update Configuration
        </Button>
      )}

      {isActive && showForm && (
        <form onSubmit={handleSubmit} className="space-y-3">
          {formError && <InlineAlert variant="danger">{formError}</InlineAlert>}
          <FormField label="API Key" helperText="Enter a new API key to update">
            <Input
              type="password"
              value={apiKey}
              onChange={(e) => { setApiKey(e.target.value); setFormError('') }}
              placeholder="Enter new API key"
              maxLength={500}
              required
            />
          </FormField>
          <FormField label="Endpoint URL">
            <Input
              value={endpointUrl}
              onChange={(e) => { setEndpointUrl(e.target.value); setFormError('') }}
              placeholder="https://geldstrom-api.de"
              maxLength={500}
              required
            />
          </FormField>
          <div className="flex gap-2">
            <Button variant="secondary" type="button" onClick={() => { setShowForm(false); setFormError('') }}>
              Cancel
            </Button>
            <Button type="submit" isLoading={saveMutation.isPending} disabled={!apiKey.trim() || !endpointUrl.trim()}>
              <Upload className="h-4 w-4 mr-2" />
              Save
            </Button>
          </div>
        </form>
      )}
    </div>
  )
}

function FinTSPanel({
  isActive,
  isConfigured,
  config,
  isLoadingConfig,
  otherProvider,
  onInvalidate,
}: {
  isActive: boolean
  isConfigured: boolean
  config: FinTSConfigResponse | null
  isLoadingConfig: boolean
  otherProvider: BankingProviderMode | null
  onInvalidate: () => void
}) {
  const toast = useToast()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [showForm, setShowForm] = useState(false)
  const [showSwitchWarning, setShowSwitchWarning] = useState(false)
  const [productId, setProductId] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [formError, setFormError] = useState('')

  const saveMutation = useMutation({
    mutationFn: ({ productId, file }: { productId?: string; file?: File }) =>
      saveLocalFinTSConfig(productId, file),
    onSuccess: (data) => {
      const msg = data.institute_count != null
        ? `${data.institute_count} institutes loaded`
        : 'Configuration updated'
      toast.success({ description: msg })
      setProductId('')
      setSelectedFile(null)
      setShowForm(false)
      setFormError('')
      if (fileInputRef.current) fileInputRef.current.value = ''
      onInvalidate()
    },
    onError: (err) => {
      setFormError(err instanceof Error ? err.message : 'Failed to save FinTS configuration')
    },
  })

  const activateMutation = useMutation({
    mutationFn: () => activateProvider('local'),
    onSuccess: () => {
      toast.success({ description: 'Local FinTS activated' })
      setShowSwitchWarning(false)
      onInvalidate()
    },
    onError: (err) => {
      toast.danger({
        description: err instanceof Error ? err.message : 'Unknown error',
      })
      setShowSwitchWarning(false)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setFormError('')
    if (isConfigured) {
      // Partial update: at least one field must be provided
      if (!productId.trim() && !selectedFile) {
        setFormError('Provide a new Product ID, a new CSV file, or both')
        return
      }
      saveMutation.mutate({
        productId: productId.trim() || undefined,
        file: selectedFile ?? undefined,
      })
    } else {
      // Initial setup: both fields required
      if (!productId.trim()) { setFormError('Product ID is required'); return }
      if (!selectedFile) { setFormError('Institute CSV file is required'); return }
      saveMutation.mutate({ productId: productId.trim(), file: selectedFile })
    }
  }

  const handleSaveAndActivate = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError('')
    if (!productId.trim()) { setFormError('Product ID is required'); return }
    if (!selectedFile) { setFormError('Institute CSV file is required'); return }
    try {
      await saveLocalFinTSConfig(productId.trim(), selectedFile)
      await activateProvider('local')
      toast.success({ description: 'Local FinTS configured and activated' })
      setProductId('')
      setSelectedFile(null)
      setShowForm(false)
      setShowSwitchWarning(false)
      setFormError('')
      if (fileInputRef.current) fileInputRef.current.value = ''
      onInvalidate()
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Failed to configure')
    }
  }

  return (
    <div className="rounded-lg border border-border-subtle p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Settings className="h-5 w-5 text-accent-primary" />
          <h4 className="text-sm font-medium text-text-primary">Local FinTS</h4>
          {isActive && (
            <Badge variant="success">
              <CheckCircle className="h-3 w-3 mr-1" />
              Active
            </Badge>
          )}
        </div>
        {!isActive && otherProvider !== null && (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              if (isConfigured) {
                setShowSwitchWarning(true)
              } else {
                setShowForm(true)
                setShowSwitchWarning(true)
              }
            }}
          >
            Switch to Local FinTS
          </Button>
        )}
        {!isActive && otherProvider === null && (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setShowForm(true)}
          >
            Configure
          </Button>
        )}
      </div>

      {showSwitchWarning && (
        <ProviderSwitchWarning
          targetLabel="Local FinTS"
          isLoading={activateMutation.isPending}
          onCancel={() => setShowSwitchWarning(false)}
          onConfirm={() => activateMutation.mutate()}
        />
      )}

      {isConfigured && config && !showSwitchWarning && (
        <div className="grid gap-3 sm:grid-cols-3">
          <div>
            <p className="text-xs text-text-muted">Product ID</p>
            <code className="text-sm text-text-primary mt-0.5">{config.product_id_masked}</code>
          </div>
          <div>
            <p className="text-xs text-text-muted">Institute Directory</p>
            <p className="text-sm text-text-primary mt-0.5">
              {config.csv_institute_count.toLocaleString()} institutes ({config.csv_file_size_kb} KB)
            </p>
          </div>
          <div>
            <p className="text-xs text-text-muted">Last Updated</p>
            <p className="text-sm text-text-primary mt-0.5">{formatDate(config.last_updated)}</p>
          </div>
        </div>
      )}

      {isLoadingConfig && <Spinner />}

      {/* Update form when active or first-time setup */}
      {(isActive || (!isConfigured && otherProvider === null)) && !showForm && (
        <Button variant="secondary" size="sm" onClick={() => setShowForm(true)}>
          {isConfigured ? 'Update Configuration' : 'Configure'}
        </Button>
      )}

      {showForm && (
        <form onSubmit={showSwitchWarning ? handleSaveAndActivate : handleSubmit} className="space-y-4">
          {showSwitchWarning && (
            <InlineAlert variant="warning">
              <AlertTriangle className="h-4 w-4 mr-1 inline" />
              Configure Local FinTS to switch from Geldstrom API. Switching may interrupt active bank syncs.
            </InlineAlert>
          )}
          {formError && <InlineAlert variant="danger">{formError}</InlineAlert>}
          <FinTSConfigFormFields
            productId={productId}
            onProductIdChange={(v) => { setProductId(v); setFormError('') }}
            selectedFile={selectedFile}
            onFileChange={(f) => { setSelectedFile(f); setFormError('') }}
            required={!isConfigured}
          />
          <div className="flex gap-2">
            <Button variant="secondary" type="button" onClick={() => { setShowForm(false); setShowSwitchWarning(false); setFormError('') }}>
              Cancel
            </Button>
            <Button type="submit" isLoading={saveMutation.isPending} disabled={isConfigured ? (!productId.trim() && !selectedFile) : (!productId.trim() || !selectedFile)}>
              <Upload className="h-4 w-4 mr-2" />
              {showSwitchWarning ? 'Save & Activate' : (isConfigured ? 'Update Configuration' : 'Save Configuration')}
            </Button>
          </div>
        </form>
      )}
    </div>
  )
}

function ProviderSwitchWarning({
  targetLabel,
  isLoading,
  onCancel,
  onConfirm,
}: {
  targetLabel: string
  isLoading: boolean
  onCancel: () => void
  onConfirm: () => void
}) {
  return (
    <div className="rounded-md border border-accent-warning/30 bg-accent-warning/5 p-4 space-y-3">
      <div className="flex items-start gap-2">
        <AlertTriangle className="h-5 w-5 text-accent-warning shrink-0 mt-0.5" />
        <p className="text-sm text-text-primary">
          Switching to <strong>{targetLabel}</strong> may interrupt active bank syncs. Are you sure?
        </p>
      </div>
      <div className="flex gap-2">
        <Button variant="secondary" size="sm" onClick={onCancel} disabled={isLoading}>
          Cancel
        </Button>
        <Button size="sm" isLoading={isLoading} onClick={onConfirm}>
          Switch Provider
        </Button>
      </div>
    </div>
  )
}
