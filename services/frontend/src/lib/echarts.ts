/**
 * Modular ECharts setup
 *
 * Only imports the chart types and components we actually use,
 * dramatically reducing bundle size (~1MB -> ~200KB for Sankey-only usage).
 *
 * @see https://echarts.apache.org/handbook/en/basics/import
 */

import * as echarts from 'echarts/core'

// Chart type - only Sankey for now
import { SankeyChart } from 'echarts/charts'

// Components we use
import {
  TooltipComponent,
  GraphicComponent,
} from 'echarts/components'

// Renderer
import { CanvasRenderer } from 'echarts/renderers'

// Register required components
echarts.use([
  SankeyChart,
  TooltipComponent,
  GraphicComponent,
  CanvasRenderer,
])

export default echarts

