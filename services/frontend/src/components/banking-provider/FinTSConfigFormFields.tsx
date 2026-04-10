/**
 * Shared FinTS Configuration Form Fields
 *
 * Presentational component (no mutations) for Product ID + CSV file inputs.
 * Used by both the onboarding banking provider step and the settings FinTS panel.
 */

import { useRef } from 'react'
import { Upload, ExternalLink } from 'lucide-react'
import {
  FormField,
  Input,
  WizardInfoBanner,
} from '@/components/ui'

interface FinTSConfigFormFieldsProps {
  productId: string
  onProductIdChange: (value: string) => void
  selectedFile: File | null
  onFileChange: (file: File | null) => void
  error?: string
}

export function FinTSConfigFormFields({
  productId,
  onProductIdChange,
  selectedFile,
  onFileChange,
}: FinTSConfigFormFieldsProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null
    if (file && !file.name.endsWith('.csv')) {
      onFileChange(null)
      return
    }
    onFileChange(file)
  }

  return (
    <div className="space-y-5">
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
          onChange={(e) => onProductIdChange(e.target.value)}
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
    </div>
  )
}
