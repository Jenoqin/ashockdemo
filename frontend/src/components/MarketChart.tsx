import { useEffect, useRef, useState } from 'react'
import * as echarts from 'echarts'
import type { PriceBar, AnalysisResult } from '../api/types'

interface MarketChartProps {
  bars: PriceBar[]
  analysis: AnalysisResult | null
  overlays?: string[]
}

export default function MarketChart({ bars, analysis, overlays = [] }: MarketChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<echarts.ECharts | null>(null)
  const [activeOverlays, setActiveOverlays] = useState<string[]>(overlays)

  const toggleOverlay = (o: string) => {
    setActiveOverlays(prev => {
      // lower pane can only have one of macd, rsi
      const lower = ['macd', 'rsi']
      if (lower.includes(o)) {
        const withoutLower = prev.filter(x => !lower.includes(x))
        if (prev.includes(o)) return withoutLower
        return [...withoutLower, o]
      }
      if (prev.includes(o)) return prev.filter(x => x !== o)
      return [...prev, o]
    })
  }

  useEffect(() => {
    if (!containerRef.current) return
    const chart = echarts.init(containerRef.current)
    chartRef.current = chart

    const observer = new ResizeObserver(() => {
      chart.resize()
    })
    observer.observe(containerRef.current)

    return () => {
      observer.disconnect()
      chart.dispose()
    }
  }, [])

  useEffect(() => {
    if (!chartRef.current || !bars.length) return

    const dates = bars.map(b => b.trade_date)
    const ohlc = bars.map(b => [b.open, b.close, b.low, b.high])
    const volumes = bars.map(b => [b.trade_date, b.volume, b.close > b.open ? 1 : -1])

    const showLowerPane = activeOverlays.includes('macd') || activeOverlays.includes('rsi')
    const gridLayout = showLowerPane
      ? [
          { left: '60px', right: '20px', top: '20px', height: '50%' }, // candlestick
          { left: '60px', right: '20px', top: '55%', height: '15%' }, // volume
          { left: '60px', right: '20px', top: '75%', height: '20%' }, // lower pane
        ]
      : [
          { left: '60px', right: '20px', top: '20px', height: '60%' }, // candlestick
          { left: '60px', right: '20px', top: '85%', height: '15%' }, // volume
        ]

    const series: any[] = [
      {
        type: 'candlestick',
        name: 'K线',
        data: ohlc,
        itemStyle: {
          color: '#D55331',
          color0: '#167A58',
          borderColor: '#D55331',
          borderColor0: '#167A58'
        },
        xAxisIndex: 0,
        yAxisIndex: 0
      },
      {
        type: 'bar',
        name: '成交量',
        data: volumes.map((v, i) => ({
          value: v[1],
          itemStyle: {
            color: v[2] === 1 ? '#D55331' : '#167A58'
          }
        })),
        xAxisIndex: 1,
        yAxisIndex: 1
      }
    ]

    if (analysis) {
      const { diagnostics } = analysis
      
      const maColors: Record<string, string> = { ma5: '#c23531', ma10: '#2f4554', ma20: '#61a0a8', ma60: '#d48265' }
      
      for (const overlay of activeOverlays) {
        if (['ma5', 'ma10', 'ma20', 'ma60'].includes(overlay)) {
          if (diagnostics[overlay]) {
            series.push({
              type: 'line',
              name: overlay.toUpperCase(),
              data: Object.values(diagnostics[overlay]),
              smooth: true,
              showSymbol: false,
              lineStyle: { width: 1 },
              itemStyle: { color: maColors[overlay] },
              xAxisIndex: 0,
              yAxisIndex: 0
            })
          }
        } else if (overlay === 'boll') {
          if (diagnostics.boll_upper && diagnostics.boll_lower && diagnostics.boll_mid) {
            series.push(
              { type: 'line', name: 'BOLL UPPER', data: Object.values(diagnostics.boll_upper), smooth: true, showSymbol: false, lineStyle: { width: 1, type: 'dashed' }, itemStyle: { color: '#ccc' }, xAxisIndex: 0, yAxisIndex: 0 },
              { type: 'line', name: 'BOLL MID', data: Object.values(diagnostics.boll_mid), smooth: true, showSymbol: false, lineStyle: { width: 1 }, itemStyle: { color: '#aaa' }, xAxisIndex: 0, yAxisIndex: 0 },
              { type: 'line', name: 'BOLL LOWER', data: Object.values(diagnostics.boll_lower), smooth: true, showSymbol: false, lineStyle: { width: 1, type: 'dashed' }, itemStyle: { color: '#ccc' }, xAxisIndex: 0, yAxisIndex: 0 }
            )
          }
        } else if (overlay === 'macd') {
          if (diagnostics.macd && diagnostics.macd_signal && diagnostics.macd_hist) {
            series.push(
              { type: 'line', name: 'MACD', data: Object.values(diagnostics.macd), smooth: true, showSymbol: false, xAxisIndex: 2, yAxisIndex: 2 },
              { type: 'line', name: 'SIGNAL', data: Object.values(diagnostics.macd_signal), smooth: true, showSymbol: false, xAxisIndex: 2, yAxisIndex: 2 },
              { type: 'bar', name: 'HIST', data: Object.values(diagnostics.macd_hist).map((v: any) => ({ value: v, itemStyle: { color: v > 0 ? '#D55331' : '#167A58' }})), xAxisIndex: 2, yAxisIndex: 2 }
            )
          }
        } else if (overlay === 'rsi') {
          if (diagnostics.rsi14) {
            series.push({ type: 'line', name: 'RSI(14)', data: Object.values(diagnostics.rsi14), smooth: true, showSymbol: false, xAxisIndex: 2, yAxisIndex: 2 })
          }
        }
      }
    }

    const option = {
      animation: bars.length <= 1000,
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' }
      },
      axisPointer: { link: [{ xAxisIndex: 'all' }] },
      dataZoom: [
        { type: 'inside', xAxisIndex: showLowerPane ? [0, 1, 2] : [0, 1], start: 0, end: 100 },
        { type: 'slider', xAxisIndex: showLowerPane ? [0, 1, 2] : [0, 1], start: 0, end: 100, bottom: '2%' }
      ],
      grid: gridLayout,
      xAxis: gridLayout.map((_, i) => ({
        type: 'category',
        data: dates,
        gridIndex: i,
        scale: true,
        boundaryGap: false,
        axisLine: { onZero: false },
        splitLine: { show: false },
        show: i === gridLayout.length - 1, // Only show label on the bottom-most axis
      })),
      yAxis: gridLayout.map((_, i) => ({
        type: 'value',
        scale: true,
        gridIndex: i,
        splitLine: { show: i === 0 }
      })),
      series
    }

    chartRef.current.setOption(option, true)
  }, [bars, analysis, activeOverlays])

  return (
    <div className="card" data-testid="market-chart">
      <div style={{ marginBottom: '16px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        {['ma5', 'ma10', 'ma20', 'ma60', 'boll', 'macd', 'rsi'].map(o => (
          <button
            key={o}
            onClick={() => toggleOverlay(o)}
            style={{
              padding: '4px 12px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--line)',
              background: activeOverlays.includes(o) ? 'var(--ink)' : 'var(--surface)',
              color: activeOverlays.includes(o) ? 'var(--surface)' : 'var(--ink)',
              cursor: 'pointer',
              fontSize: '12px',
              textTransform: 'uppercase'
            }}
          >
            {o}
          </button>
        ))}
      </div>
      <div ref={containerRef} style={{ width: '100%', height: '600px' }} />
    </div>
  )
}
