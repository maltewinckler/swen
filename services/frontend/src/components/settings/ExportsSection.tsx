/**
 * Exports Section
 *
 * Data export functionality with preset and custom date ranges.
 */

import { useState } from 'react'
import { Download, FileSpreadsheet, Calendar, Clock } from 'lucide-react'
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  FormField,
  Input,
  Button,
  Spinner,
  InlineAlert,
} from '@/components/ui'
import { downloadExcelReport, ExportPresets } from '@/api'

export function ExportsSection() {
  const [isExporting, setIsExporting] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)

  const handleExport = async (exportFn: () => Promise<void>, label: string) => {
    setIsExporting(true)
    setExportError(null)
    try {
      await exportFn()
    } catch (err) {
      setExportError(err instanceof Error ? err.message : `Failed to export ${label}`)
    } finally {
      setIsExporting(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Excel Report Card */}
      <Card className="animate-slide-up">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center h-10 w-10 rounded-lg bg-accent-success/10">
              <FileSpreadsheet className="h-5 w-5 text-accent-success" />
            </div>
            <div>
              <CardTitle>Excel Report</CardTitle>
              <CardDescription>
                Comprehensive report with dashboard overview, transactions, and accounts
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {exportError && <InlineAlert variant="danger">{exportError}</InlineAlert>}

          {/* Quick Export Options */}
          <div>
            <p className="text-sm font-medium text-text-primary mb-3">Quick Export</p>
            <div className="grid grid-cols-2 gap-3">
              <Button
                variant="secondary"
                className="justify-start"
                onClick={() => handleExport(ExportPresets.last30Days, 'Last 30 Days')}
                disabled={isExporting}
              >
                {isExporting ? (
                  <Spinner size="sm" className="mr-2" />
                ) : (
                  <Clock className="h-4 w-4 mr-2" />
                )}
                Last 30 Days
              </Button>
              <Button
                variant="secondary"
                className="justify-start"
                onClick={() => handleExport(ExportPresets.last90Days, 'Last 90 Days')}
                disabled={isExporting}
              >
                {isExporting ? (
                  <Spinner size="sm" className="mr-2" />
                ) : (
                  <Clock className="h-4 w-4 mr-2" />
                )}
                Last 90 Days
              </Button>
              <Button
                variant="secondary"
                className="justify-start"
                onClick={() => handleExport(ExportPresets.currentMonth, 'Current Month')}
                disabled={isExporting}
              >
                {isExporting ? (
                  <Spinner size="sm" className="mr-2" />
                ) : (
                  <Calendar className="h-4 w-4 mr-2" />
                )}
                Current Month
              </Button>
              <Button
                variant="secondary"
                className="justify-start"
                onClick={() => handleExport(ExportPresets.previousMonth, 'Previous Month')}
                disabled={isExporting}
              >
                {isExporting ? (
                  <Spinner size="sm" className="mr-2" />
                ) : (
                  <Calendar className="h-4 w-4 mr-2" />
                )}
                Previous Month
              </Button>
              <Button
                variant="secondary"
                className="justify-start"
                onClick={() => handleExport(ExportPresets.yearToDate, 'Year to Date')}
                disabled={isExporting}
              >
                {isExporting ? (
                  <Spinner size="sm" className="mr-2" />
                ) : (
                  <Calendar className="h-4 w-4 mr-2" />
                )}
                Year to Date
              </Button>
              <Button
                variant="secondary"
                className="justify-start"
                onClick={() => handleExport(ExportPresets.allTime, 'All Time')}
                disabled={isExporting}
              >
                {isExporting ? (
                  <Spinner size="sm" className="mr-2" />
                ) : (
                  <Download className="h-4 w-4 mr-2" />
                )}
                All Time
              </Button>
            </div>
          </div>

          {/* Custom Date Range */}
          <div className="border-t border-border-subtle pt-4">
            <p className="text-sm font-medium text-text-primary mb-3">Custom Date Range</p>
            <ExportCustomRange isExporting={isExporting} onExport={handleExport} />
          </div>
        </CardContent>
      </Card>

      {/* Other Export Formats (Coming Soon) */}
      <Card className="animate-slide-up opacity-60">
        <CardHeader>
          <CardTitle className="text-text-muted">Other Formats</CardTitle>
          <CardDescription>Additional export formats coming soon</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 text-sm text-text-muted">
            <p>• CSV Export</p>
            <p>• JSON Export</p>
            <p>• DATEV Export (for tax advisors)</p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

/**
 * Custom date range export sub-component.
 */
function ExportCustomRange({
  isExporting,
  onExport,
}: {
  isExporting: boolean
  onExport: (fn: () => Promise<void>, label: string) => void
}) {
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')

  const handleExport = () => {
    if (startDate && endDate) {
      onExport(() => downloadExcelReport({ startDate, endDate }), 'Custom Range')
    }
  }

  const isValid = startDate && endDate && new Date(startDate) <= new Date(endDate)

  return (
    <div className="flex items-end gap-3">
      <FormField label="Start Date" className="flex-1">
        <Input
          type="date"
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
          disabled={isExporting}
        />
      </FormField>
      <FormField label="End Date" className="flex-1">
        <Input
          type="date"
          value={endDate}
          onChange={(e) => setEndDate(e.target.value)}
          disabled={isExporting}
        />
      </FormField>
      <Button onClick={handleExport} disabled={!isValid || isExporting} className="mb-0.5">
        {isExporting ? (
          <Spinner size="sm" className="mr-2" />
        ) : (
          <Download className="h-4 w-4 mr-2" />
        )}
        Export
      </Button>
    </div>
  )
}

