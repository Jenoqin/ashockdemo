import { useEffect, useRef, useState } from 'react'
import * as echarts from 'echarts'
import type { AnalysisResult, PriceBar } from '../api/types'

type LessonKey = 'trend' | 'levels' | 'volume'

interface MarketChartProps {
  bars: PriceBar[]
  analysis: AnalysisResult | null
  overlays?: string[]
  lesson?: LessonKey
}

const overlayKeys = ['ma5', 'ma10', 'ma20', 'ma60', 'boll', 'macd', 'rsi']

export default function MarketChart({ bars, analysis, overlays = [], lesson = 'trend' }: MarketChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<echarts.ECharts | null>(null)
  const [activeOverlays, setActiveOverlays] = useState<string[]>(overlays)

  const toggleOverlay = (overlay: string) => {
    setActiveOverlays((previous) => {
      const lowerPane = ['macd', 'rsi']
      if (lowerPane.includes(overlay)) {
        const withoutLower = previous.filter((item) => !lowerPane.includes(item))
        return previous.includes(overlay) ? withoutLower : [...withoutLower, overlay]
      }
      return previous.includes(overlay) ? previous.filter((item) => item !== overlay) : [...previous, overlay]
    })
  }

  useEffect(() => {
    if (!containerRef.current) return
    const chart = echarts.init(containerRef.current)
    chartRef.current = chart
    const observer = new ResizeObserver(() => chart.resize())
    observer.observe(containerRef.current)
    return () => {
      observer.disconnect()
      chart.dispose()
    }
  }, [])

  useEffect(() => {
    if (!chartRef.current || !bars.length || !containerRef.current) return

    const dates = bars.map((bar) => bar.trade_date)
    const ohlc = bars.map((bar) => [bar.open, bar.close, bar.low, bar.high])
    const compact = containerRef.current.clientWidth < 720
    const showLowerPane = activeOverlays.includes('macd') || activeOverlays.includes('rsi')
    const downEnd = Math.max(1, Math.floor((bars.length - 1) * 0.22))
    const flatStart = Math.max(downEnd + 1, Math.floor((bars.length - 1) * 0.28))
    const flatEnd = Math.max(flatStart + 1, Math.floor((bars.length - 1) * 0.66))
    const riseStart = Math.max(flatEnd + 1, Math.floor((bars.length - 1) * 0.78))

    const grids = showLowerPane
      ? [
          { left: compact ? 46 : 54, right: 18, top: 22, height: '51%' },
          { left: compact ? 46 : 54, right: 18, top: '58%', height: '12%' },
          { left: compact ? 46 : 54, right: 18, top: '76%', height: '17%' },
        ]
      : [
          { left: compact ? 46 : 54, right: 18, top: 22, height: '66%' },
          { left: compact ? 46 : 54, right: 18, top: '76%', height: '16%' },
        ]

    const series: Record<string, unknown>[] = [
      {
        type: 'candlestick',
        name: 'K线',
        data: ohlc,
        itemStyle: {
          color: '#d95842',
          color0: '#15906b',
          borderColor: '#d95842',
          borderColor0: '#15906b',
        },
        xAxisIndex: 0,
        yAxisIndex: 0,
        markArea: {
          silent: true,
          label: { show: lesson === 'trend' && !compact, position: 'insideTopLeft', fontSize: 12, lineHeight: 18, fontWeight: 650 },
          data: [
            [
              { name: `下跌阶段  ${dates[0]} ～ ${dates[downEnd]}\n高位快速回落，市场情绪走弱`, xAxis: dates[0], itemStyle: { color: lesson === 'trend' ? 'rgba(198, 66, 54, .10)' : 'rgba(198, 66, 54, .035)' }, label: { color: '#ad3c35' } },
              { xAxis: dates[downEnd] },
            ],
            [
              { name: `震荡整理  ${dates[flatStart]} ～ ${dates[flatEnd]}\n低位反复，方向尚不清晰`, xAxis: dates[flatStart], itemStyle: { color: lesson === 'trend' ? 'rgba(209, 130, 19, .10)' : 'rgba(209, 130, 19, .035)' }, label: { color: '#b56f13' } },
              { xAxis: dates[flatEnd] },
            ],
            [
              { name: `回升阶段  ${dates[riseStart]} ～ ${dates[dates.length - 1]}\n高点和低点逐步抬高`, xAxis: dates[riseStart], itemStyle: { color: lesson === 'trend' ? 'rgba(20, 122, 91, .11)' : 'rgba(20, 122, 91, .04)' }, label: { color: '#147a5b' } },
              { xAxis: dates[dates.length - 1] },
            ],
          ],
        },
        markPoint: lesson === 'levels' ? {
          symbolSize: 42,
          label: { color: '#fff', fontSize: 10, formatter: '{b}' },
          data: [
            { type: 'max', name: '高点', itemStyle: { color: '#c64236' } },
            { type: 'min', name: '低点', itemStyle: { color: '#147a5b' } },
          ],
        } : undefined,
        markLine: lesson === 'levels' ? {
          symbol: 'none',
          label: { formatter: '区间均价', color: '#746f67' },
          lineStyle: { color: '#9f988f', type: 'dashed' },
          data: [{ type: 'average' }],
        } : undefined,
      },
      {
        type: 'bar',
        name: '成交量',
        data: bars.map((bar) => ({
          value: bar.volume,
          itemStyle: {
            color: bar.close >= bar.open ? '#d95842' : '#15906b',
            opacity: lesson === 'volume' ? 1 : 0.62,
          },
        })),
        xAxisIndex: 1,
        yAxisIndex: 1,
      },
    ]

    if (analysis) {
      const diagnostics = analysis.diagnostics
      const maColors: Record<string, string> = { ma5: '#c64236', ma10: '#375a7f', ma20: '#8b6e43', ma60: '#76558f' }

      for (const overlay of activeOverlays) {
        if (['ma5', 'ma10', 'ma20', 'ma60'].includes(overlay) && diagnostics[overlay]) {
          series.push({ type: 'line', name: overlay.toUpperCase(), data: Object.values(diagnostics[overlay]), smooth: true, showSymbol: false, lineStyle: { width: 1.25, color: maColors[overlay] }, xAxisIndex: 0, yAxisIndex: 0 })
        }
        if (overlay === 'boll' && diagnostics.boll_upper && diagnostics.boll_lower && diagnostics.boll_mid) {
          series.push(
            { type: 'line', name: 'BOLL UPPER', data: Object.values(diagnostics.boll_upper), showSymbol: false, lineStyle: { width: 1, type: 'dashed', color: '#a9a198' }, xAxisIndex: 0, yAxisIndex: 0 },
            { type: 'line', name: 'BOLL MID', data: Object.values(diagnostics.boll_mid), showSymbol: false, lineStyle: { width: 1, color: '#6f6a64' }, xAxisIndex: 0, yAxisIndex: 0 },
            { type: 'line', name: 'BOLL LOWER', data: Object.values(diagnostics.boll_lower), showSymbol: false, lineStyle: { width: 1, type: 'dashed', color: '#a9a198' }, xAxisIndex: 0, yAxisIndex: 0 },
          )
        }
        if (overlay === 'macd' && diagnostics.macd && diagnostics.macd_signal && diagnostics.macd_hist) {
          series.push(
            { type: 'line', name: 'MACD', data: Object.values(diagnostics.macd), showSymbol: false, xAxisIndex: 2, yAxisIndex: 2 },
            { type: 'line', name: 'SIGNAL', data: Object.values(diagnostics.macd_signal), showSymbol: false, xAxisIndex: 2, yAxisIndex: 2 },
            { type: 'bar', name: 'HIST', data: Object.values(diagnostics.macd_hist), xAxisIndex: 2, yAxisIndex: 2 },
          )
        }
        if (overlay === 'rsi' && diagnostics.rsi14) {
          series.push({ type: 'line', name: 'RSI(14)', data: Object.values(diagnostics.rsi14), showSymbol: false, xAxisIndex: 2, yAxisIndex: 2 })
        }
      }
    }

    chartRef.current.setOption({
      animation: bars.length <= 1000,
      textStyle: { fontFamily: 'Inter, PingFang SC, Microsoft YaHei, sans-serif', color: '#59544d' },
      tooltip: { trigger: 'axis', axisPointer: { type: 'cross' }, borderColor: '#d8d2c8', backgroundColor: 'rgba(255, 254, 250, .96)' },
      axisPointer: { link: [{ xAxisIndex: 'all' }] },
      dataZoom: [
        { type: 'inside', xAxisIndex: showLowerPane ? [0, 1, 2] : [0, 1], start: 0, end: 100 },
        { type: 'slider', show: false, xAxisIndex: showLowerPane ? [0, 1, 2] : [0, 1], start: 0, end: 100 },
      ],
      grid: grids,
      xAxis: grids.map((_, index) => ({
        type: 'category', data: dates, gridIndex: index, scale: true, boundaryGap: false,
        axisLine: { lineStyle: { color: '#cfc9bf' } },
        axisTick: { show: false },
        axisLabel: { color: '#746f67', fontSize: 11, hideOverlap: true },
        splitLine: { show: false },
        show: index === grids.length - 1,
      })),
      yAxis: grids.map((_, index) => ({
        type: 'value', scale: true, gridIndex: index,
        axisLine: { show: false }, axisTick: { show: false },
        axisLabel: { color: '#746f67', fontSize: 11 },
        splitLine: { show: index === 0, lineStyle: { color: '#e9e5de' } },
      })),
      series,
    }, true)
  }, [bars, analysis, activeOverlays, lesson])

  return (
    <div className="market-chart" data-testid="market-chart">
      <div ref={containerRef} className="chart-canvas" />
      <details className="indicator-controls">
        <summary>高级指标（可展开）</summary>
        <div className="overlay-controls" aria-label="技术指标叠加">
          {overlayKeys.map((overlay) => (
            <button key={overlay} type="button" onClick={() => toggleOverlay(overlay)} className={activeOverlays.includes(overlay) ? 'is-active' : ''} aria-pressed={activeOverlays.includes(overlay)}>{overlay.toUpperCase()}</button>
          ))}
        </div>
      </details>
    </div>
  )
}
