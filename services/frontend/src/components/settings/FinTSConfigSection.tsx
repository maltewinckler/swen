/**
 * FinTS Configuration Section
 *
 * Admin panel for managing FinTS Product ID and institute directory CSV.
 * Shown within the Administration section of the Settings page.
 */

import { useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Upload, CheckCircle, XCircle, RefreshCw } from 'lucide-react'
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
  getFinTSConfiguration,
  updateFinTSProductId,
  uploadFinTSCSV,
  getFinTSConfigStatus,
} from '@/api'
import type { FinTSConfigResponse } from '@/api/admin-fints-config'
import { formatDate } from '@/lib/utils'

export function FinTSConfigSection() {
  const queryClient = useQueryClient()

  // --- Data fetching ---

  const {
    data: configStatus,
    isLoading: statusLoading,
  } = useQuery({
    queryKey: ['admin', 'fints-config', 'status'],
    queryFn: getFinTSConfigStatus,
  })

  const {
    data: config,
    isLoading: configLoading,
    error: configError,
  } = useQuery({
    queryKey: ['admin', 'fints-config'],
    queryFn: getFinTSConfiguration,
    enabled: configStatus?.is_configured === true,
    retry: false,
  })

  const isConfigured = configStatus?.is_configured ?? false
  const isLoading = statusLoading || (isConfigured && configLoading)

  return (
    <Card className="animate-slide-up">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>FinTS Configuration</CardTitle>
            <CardDescription>
              Manage FinTS Product ID and institute directory for banking connections
            </CardDescription>
          </div>
          <ConfigStatusBadge isConfigured={isConfigured} isLoading={statusLoading} />
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {isLoading && (
          <div className="flex justify-center py-8">
            <Spinner />
          </div>
        )}

        {configError && !isLoading && (
          <InlineAlert variant="danger">
            {configError instanceof Error ? configError.message : 'Failed to load configuration'}
          </InlineAlert>
        )}

        {!isLoading && (
          <>
            {/* Current configuration display */}
            {isConfigured && config && <ConfigDisplay config={config} />}

            {!isConfigured && (
              <InlineAlert variant="warning">
                FinTS is not configured. Banking connections will not work until both the Product ID
                and institute directory CSV are provided.
              </InlineAlert>
            )}

            {/* Product ID form */}
            <ProductIdForm
              isConfigured={isConfigured}
              onSuccess={() => {
                queryClient.invalidateQueries({ queryKey: ['admin', 'fints-config'] })
              }}
            />

            {/* CSV upload (only after initial config exists) */}
            {isConfigured && (
              <CsvUploadForm
                onSuccess={() => {
                  queryClient.invalidateQueries({ queryKey: ['admin', 'fints-config'] })
                }}
              />
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}

// --- Sub-components ---

function ConfigStatusBadge({
  isConfigured,
  isLoading,
}: {
  isConfigured: boolean
  isLoading: boolean
}) {
  if (isLoading) return null

  return isConfigured ? (
    <Badge variant="success">
      <CheckCircle className="h-3 w-3 mr-1" />
      Configured
    </Badge>
  ) : (
    <Badge variant="danger">
      <XCircle className="h-3 w-3 mr-1" />
      Not Configured
    </Badge>
  )
}

function ConfigDisplay({ config }: { config: FinTSConfigResponse }) {
  return (
    <div className="rounded-lg border border-border-subtle p-4 space-y-3">
      <h4 className="text-sm font-medium text-text-primary">Current Configuration</h4>
      <div className="grid gap-3 sm:grid-cols-3">
        <div>
          <p className="text-xs text-text-muted">Product ID</p>
          <code className="text-sm text-text-primary mt-0.5">
            {config.product_id_masked}
          </code>
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
    </div>
  )
}

function ProductIdForm({
  isConfigured,
  onSuccess,
}: {
  isConfigured: boolean
  onSuccess: () => void
}) {
  const toast = useToast()
  const [productId, setProductId] = useState('')
  const [error, setError] = useState('')

  const mutation = useMutation({
    mutationFn: (id: string) => updateFinTSProductId(id),
    onSuccess: () => {
      toast.success({ description: 'Product ID updated successfully' })
      setProductId('')
      setError('')
      onSuccess()
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Failed to update Product ID')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!productId.trim()) {
      setError('Product ID is required')
      return
    }

    mutation.mutate(productId.trim())
  }

  return (
    <div className="space-y-3">
      <form onSubmit={handleSubmit} className="space-y-3">
        {error && <InlineAlert variant="danger">{error}</InlineAlert>}
        <FormField
          label={isConfigured ? 'Update Product ID' : 'Set Product ID'}
          helperText="Obtain your Product ID from the Deutsche Kreditwirtschaft registration portal"
        >
          <div className="flex items-center gap-3">
            <Input
              value={productId}
              onChange={(e) => setProductId(e.target.value)}
              placeholder="Enter Product ID"
              maxLength={100}
              required
            />
            <Button type="submit" size="sm" isLoading={mutation.isPending} className="shrink-0">
              <RefreshCw className="h-4 w-4 mr-2" />
              {isConfigured ? 'Update Product ID' : 'Save Product ID'}
            </Button>
          </div>
        </FormField>
      </form>
    </div>
  )
}

function CsvUploadForm({ onSuccess }: { onSuccess: () => void }) {
  const toast = useToast()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [error, setError] = useState('')

  const mutation = useMutation({
    mutationFn: (file: File) => uploadFinTSCSV(file),
    onSuccess: (data) => {
      toast.success({
        description: `CSV uploaded: ${data.institute_count} institutes (${data.file_size_kb} KB)`,
      })
      setSelectedFile(null)
      setError('')
      if (fileInputRef.current) fileInputRef.current.value = ''
      onSuccess()
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Failed to upload CSV')
    },
  })

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError('')
    const file = e.target.files?.[0] ?? null
    if (file && !file.name.endsWith('.csv')) {
      setError('Please select a CSV file')
      setSelectedFile(null)
      return
    }
    setSelectedFile(file)
  }

  const handleUpload = () => {
    if (!selectedFile) return
    setError('')
    mutation.mutate(selectedFile)
  }

  return (
    <div className="space-y-3">
      {error && <InlineAlert variant="danger">{error}</InlineAlert>}
      <FormField
        label="Update Institute Directory"
        helperText="Upload the fints_institute.csv file (CP1252 encoded, max 10 MB)"
      >
        <div className="flex items-center gap-3">
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
          <Button
            size="sm"
            onClick={handleUpload}
            isLoading={mutation.isPending}
            disabled={!selectedFile}
            className="shrink-0"
          >
            <Upload className="h-4 w-4 mr-2" />
            Upload CSV
          </Button>
        </div>
      </FormField>
    </div>
  )
}
