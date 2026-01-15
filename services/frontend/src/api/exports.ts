/**
 * Export API functions for downloading financial reports.
 */

import { API_BASE, getAccessToken } from './client'

export interface ExcelExportOptions {
  /** Start date (YYYY-MM-DD) for custom date range */
  startDate?: string
  /** End date (YYYY-MM-DD) for custom date range */
  endDate?: string
  /** Number of days to look back (alternative to date range) */
  days?: number
  /** Specific month in YYYY-MM format */
  month?: string
  /** Include draft transactions (default: true) */
  includeDrafts?: boolean
}

/**
 * Downloads an Excel report file.
 *
 * Fetches the file with authentication and triggers browser download.
 *
 * @param options - Export configuration options
 */
export async function downloadExcelReport(options: ExcelExportOptions = {}): Promise<void> {
  const params = new URLSearchParams()

  if (options.startDate) {
    params.set('start_date', options.startDate)
  }
  if (options.endDate) {
    params.set('end_date', options.endDate)
  }
  if (options.days && options.days > 0) {
    params.set('days', options.days.toString())
  }
  if (options.month) {
    params.set('month', options.month)
  }
  if (options.includeDrafts !== undefined) {
    params.set('include_drafts', options.includeDrafts.toString())
  }

  const queryString = params.toString()
  const url = `${API_BASE}/exports/report.xlsx${queryString ? `?${queryString}` : ''}`

  // Fetch with authentication
  const token = getAccessToken()
  const response = await fetch(url, {
    method: 'GET',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    credentials: 'include',
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Download failed' }))
    throw new Error(error.detail || 'Download failed')
  }

  // Get filename from Content-Disposition header or use default
  const contentDisposition = response.headers.get('Content-Disposition')
  let filename = 'swen_report.xlsx'
  if (contentDisposition) {
    const match = contentDisposition.match(/filename="?([^"]+)"?/)
    if (match) {
      filename = match[1]
    }
  }

  // Create blob and trigger download
  const blob = await response.blob()
  const downloadUrl = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = downloadUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(downloadUrl)
}

/**
 * Quick export presets for common use cases.
 */
export const ExportPresets = {
  /** Export last 30 days */
  last30Days: () => downloadExcelReport({ days: 30 }),

  /** Export last 90 days */
  last90Days: () => downloadExcelReport({ days: 90 }),

  /** Export current month */
  currentMonth: () => {
    const now = new Date()
    const month = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
    return downloadExcelReport({ month })
  },

  /** Export previous month */
  previousMonth: () => {
    const now = new Date()
    now.setMonth(now.getMonth() - 1)
    const month = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
    return downloadExcelReport({ month })
  },

  /** Export all time */
  allTime: () => downloadExcelReport({}),

  /** Export year to date */
  yearToDate: () => {
    const now = new Date()
    const startDate = `${now.getFullYear()}-01-01`
    const endDate = now.toISOString().split('T')[0]
    return downloadExcelReport({ startDate, endDate })
  },
}
