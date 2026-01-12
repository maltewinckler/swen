/**
 * Sankey Cash Flow Widget
 *
 * Displays a Sankey diagram showing the flow of money from income sources
 * through to expense categories and savings. Includes export functionality
 * for sharing on social media.
 *
 * Uses Apache ECharts for React 19 compatibility and excellent Sankey support.
 */

import { useRef, useState, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import ReactEChartsCore from 'echarts-for-react/lib/core'
import echarts from '@/lib/echarts'
import type { EChartsCoreOption } from 'echarts/core'
import type { ECharts } from 'echarts'
import { Download, Share2, Loader2, AlertCircle, Check } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent, Button, Spinner, Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui'
import { getSankeyData } from '@/api'
import { formatCurrency } from '@/lib/utils'
import type { WidgetProps } from './index'
import type { SankeyResponse } from '@/types/api'

// Transform API response to ECharts Sankey format
function transformToEChartsFormat(data: SankeyResponse): EChartsCoreOption {
  // ECharts expects nodes as { name: string } and links with source/target as names
  const nodes = data.nodes.map((node) => ({
    name: node.id,
    itemStyle: {
      color: node.color || getDefaultColor(node.category),
    },
  }))

  const links = data.links.map((link) => ({
    source: link.source,
    target: link.target,
    value: parseFloat(link.value),
  }))

  // Create a label map for display
  const labelMap: Record<string, string> = {}
  data.nodes.forEach((node) => {
    labelMap[node.id] = node.label
  })

  return {
    backgroundColor: '#1a1a2e',
    // Add watermark
    graphic: [
      {
        type: 'text',
        right: 12,
        bottom: 8,
        style: {
          text: 'Made with SWEN',
          font: '11px sans-serif',
          fill: 'rgba(160, 160, 160, 0.4)',
        },
      },
    ],
    tooltip: {
      trigger: 'item',
      triggerOn: 'mousemove',
      backgroundColor: 'rgba(30, 30, 46, 0.95)',
      borderColor: 'rgba(255, 255, 255, 0.1)',
      borderWidth: 1,
      textStyle: {
        color: '#e0e0e0',
        fontSize: 13,
      },
      formatter: (params: unknown) => {
        const p = params as { dataType: string; data: { source?: string; target?: string; value?: number }; name?: string; value?: number }
        if (p.dataType === 'edge') {
          const sourceName = labelMap[p.data.source || ''] || p.data.source
          const targetName = labelMap[p.data.target || ''] || p.data.target
          const edgeValue = typeof p.data.value === 'number' ? formatCurrency(p.data.value) : '—'
          return `<div style="font-weight: 600; margin-bottom: 4px;">${sourceName} → ${targetName}</div>
                  <div style="font-family: monospace; font-size: 14px;">${edgeValue}</div>`
        }
        const nodeName = labelMap[p.name || ''] || p.name
        const nodeValue = typeof p.value === 'number' ? formatCurrency(p.value) : '—'
        return `<div style="font-weight: 600; margin-bottom: 4px;">${nodeName}</div>
                <div style="font-family: monospace; font-size: 14px;">${nodeValue}</div>`
      },
    },
    series: [
      {
        type: 'sankey',
        emphasis: {
          focus: 'adjacency',
        },
        nodeAlign: 'justify',
        orient: 'horizontal',
        nodeGap: 12,
        nodeWidth: 20,
        layoutIterations: 32,
        data: nodes,
        links: links,
        label: {
          show: true,
          position: 'right',
          color: '#a0a0a0',
          fontSize: 12,
          formatter: (params: { name: string }) => labelMap[params.name] || params.name,
        },
        lineStyle: {
          color: 'gradient',
          curveness: 0.5,
          opacity: 0.4,
        },
        itemStyle: {
          borderWidth: 0,
          borderRadius: 3,
        },
      },
    ],
  }
}

// Default colors for node categories
function getDefaultColor(category: string): string {
  switch (category) {
    case 'income':
      return '#22c55e' // green-500
    case 'total':
      return '#6b7280' // gray-500
    case 'expense':
      return '#f97316' // orange-500
    case 'savings':
      return '#22c55e' // green-500
    default:
      return '#6b7280'
  }
}

export default function SankeyWidget({ settings }: WidgetProps) {
  const echartsRef = useRef<ReactEChartsCore>(null)
  const [isExporting, setIsExporting] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)
  const [exportSuccess, setExportSuccess] = useState(false)

  const days = settings.days ?? 30

  const { data, isLoading, error } = useQuery({
    queryKey: ['analytics', 'sankey', { days }],
    queryFn: () => getSankeyData({ days, include_drafts: true }),
  })

  // Use ECharts native export (more reliable than html-to-image)
  const getChartDataUrl = useCallback((): string | null => {
    const echartsInstance = echartsRef.current?.getEchartsInstance() as ECharts | undefined
    if (!echartsInstance) return null

    return echartsInstance.getDataURL({
      type: 'png',
      pixelRatio: 2,
      backgroundColor: '#1a1a2e',
    })
  }, [])

  const handleExport = useCallback(async () => {
    setIsExporting(true)
    setExportError(null)
    setExportSuccess(false)

    try {
      const dataUrl = getChartDataUrl()
      if (!dataUrl) {
        throw new Error('Chart not ready')
      }

      // Create download link
      const link = document.createElement('a')
      const timestamp = new Date().toISOString().split('T')[0]
      link.download = `swen_cashflow_${timestamp}.png`
      link.href = dataUrl
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)

      setExportSuccess(true)
      setTimeout(() => setExportSuccess(false), 2000)
    } catch (err) {
      console.error('Export failed:', err)
      setExportError('Failed to export image')
    } finally {
      setIsExporting(false)
    }
  }, [getChartDataUrl])

  const handleCopyToClipboard = useCallback(async () => {
    setIsExporting(true)
    setExportError(null)
    setExportSuccess(false)

    try {
      const dataUrl = getChartDataUrl()
      if (!dataUrl) {
        throw new Error('Chart not ready')
      }

      // Convert data URL to blob
      const response = await fetch(dataUrl)
      const blob = await response.blob()

      await navigator.clipboard.write([
        new ClipboardItem({ 'image/png': blob }),
      ])

      setExportSuccess(true)
      setTimeout(() => setExportSuccess(false), 2000)
    } catch (err) {
      console.error('Copy failed:', err)
      setExportError('Failed to copy to clipboard')
    } finally {
      setIsExporting(false)
    }
  }, [getChartDataUrl])

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Cash Flow</CardTitle>
        </CardHeader>
        <CardContent className="h-96 flex items-center justify-center">
          <Spinner size="lg" />
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Cash Flow</CardTitle>
        </CardHeader>
        <CardContent className="h-96 flex flex-col items-center justify-center text-text-muted">
          <AlertCircle className="h-8 w-8 mb-2" />
          <p>Failed to load cash flow data</p>
        </CardContent>
      </Card>
    )
  }

  if (!data || data.nodes.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Cash Flow</CardTitle>
        </CardHeader>
        <CardContent className="h-96 flex items-center justify-center text-text-muted">
          No data available for this period
        </CardContent>
      </Card>
    )
  }

  const chartOptions = transformToEChartsFormat(data)

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between">
        <div>
          <CardTitle>Cash Flow</CardTitle>
          <p className="text-sm text-text-muted mt-1">
            {data.period_label} • {formatCurrency(parseFloat(data.total_income))} income
          </p>
        </div>
        <div className="flex gap-2 items-center">
          {exportSuccess && (
            <Check className="h-4 w-4 text-green-500" />
          )}
          {exportError && (
            <span className="text-xs text-red-500">{exportError}</span>
          )}
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="inline-flex">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleCopyToClipboard}
                  disabled={isExporting}
                  aria-label="Copy to clipboard"
                >
                  {isExporting ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Share2 className="h-4 w-4" aria-hidden="true" />
                  )}
                </Button>
              </span>
            </TooltipTrigger>
            <TooltipContent>Copy to clipboard</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <span className="inline-flex">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleExport}
                  disabled={isExporting}
                  aria-label="Download as PNG"
                >
                  {isExporting ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Download className="h-4 w-4" aria-hidden="true" />
                  )}
                </Button>
              </span>
            </TooltipTrigger>
            <TooltipContent>Download as PNG</TooltipContent>
          </Tooltip>
        </div>
      </CardHeader>
      <CardContent>
        <div className="rounded-lg overflow-hidden">
          <ReactEChartsCore
            ref={echartsRef}
            echarts={echarts}
            option={chartOptions}
            style={{ height: '350px', width: '100%' }}
            opts={{ renderer: 'canvas' }}
            notMerge={true}
          />
        </div>
        {/* Summary stats below chart */}
        <div className="grid grid-cols-3 gap-4 mt-4 text-center">
          <div>
            <p className="text-xs text-text-muted uppercase tracking-wide">Income</p>
            <p className="text-lg font-semibold text-green-500">
              {formatCurrency(parseFloat(data.total_income))}
            </p>
          </div>
          <div>
            <p className="text-xs text-text-muted uppercase tracking-wide">Expenses</p>
            <p className="text-lg font-semibold text-orange-500">
              {formatCurrency(parseFloat(data.total_expenses))}
            </p>
          </div>
          <div>
            <p className="text-xs text-text-muted uppercase tracking-wide">Savings</p>
            <p
              className={`text-lg font-semibold ${
                parseFloat(data.net_savings) >= 0 ? 'text-green-500' : 'text-red-500'
              }`}
            >
              {formatCurrency(parseFloat(data.net_savings))}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
