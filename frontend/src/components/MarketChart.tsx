import { useEffect, useRef } from 'react'
import * as echarts from 'echarts'
import type { AnalysisResult, MetricKey, PriceBar } from '../api/types'

interface MarketChartProps {
  bars: PriceBar[]
  analysis: AnalysisResult
  metric: MetricKey
  instrumentName: string
}

const percent = (value: number) => `${(value * 100).toFixed(0)}%`

export default function MarketChart({ bars, analysis, metric, instrumentName }: MarketChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<echarts.ECharts | null>(null)

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
    const chart = chartRef.current
    const dates = analysis.series.dates
    if (!chart || !dates.length) return

    const common = {
      type: 'line',
      showSymbol: false,
      smooth: false,
      connectNulls: false,
      emphasis: { focus: 'series' },
    }
    const axisLabel = { color: '#777872', fontSize: 11, hideOverlap: true }
    const splitLine = { lineStyle: { color: '#e9e8e2', type: 'dashed' as const } }
    const tooltip = {
      trigger: 'axis' as const,
      backgroundColor: 'rgba(255,255,252,.98)',
      borderColor: '#d9d8d1',
      textStyle: { color: '#20241f' },
      valueFormatter: (value: number) => metric === 'sharpe' ? value.toFixed(2) : `${(value * 100).toFixed(2)}%`,
    }

    if (metric === 'drawdown') {
      const closes = bars.map((bar) => bar.close)
      const normalized = closes.map((close) => close / closes[0])
      const numericDrawdowns = analysis.series.drawdown.filter((value): value is number => value !== null)
      const maxDrawdown = numericDrawdowns.length ? Math.min(...numericDrawdowns) : 0
      const troughIndex = Math.max(0, analysis.series.drawdown.findIndex((value) => value === maxDrawdown))
      let peakIndex = 0
      for (let index = 1; index <= troughIndex; index += 1) {
        if (closes[index] >= closes[peakIndex]) peakIndex = index
      }

      chart.setOption({
        animationDuration: 450,
        textStyle: { fontFamily: 'WenQuanYi Micro Hei, Inter, sans-serif' },
        tooltip,
        axisPointer: { link: [{ xAxisIndex: 'all' }] },
        grid: [
          { left: 48, right: 22, top: 34, height: '28%' },
          { left: 48, right: 22, top: '47%', height: '42%' },
        ],
        xAxis: [
          { type: 'category', data: dates, gridIndex: 0, boundaryGap: false, axisLabel: { show: false }, axisTick: { show: false }, axisLine: { show: false } },
          { type: 'category', data: dates, gridIndex: 1, boundaryGap: false, axisLabel, axisTick: { show: false }, axisLine: { lineStyle: { color: '#c9c9c3' } } },
        ],
        yAxis: [
          { type: 'value', gridIndex: 0, scale: true, axisLabel: { ...axisLabel, formatter: (value: number) => value.toFixed(2) }, splitLine },
          { type: 'value', gridIndex: 1, max: 0, axisLabel: { ...axisLabel, formatter: percent }, splitLine },
        ],
        dataZoom: [{ type: 'inside', xAxisIndex: [0, 1], start: 0, end: 100 }],
        series: [
          { ...common, name: `${instrumentName} 净值`, data: normalized, xAxisIndex: 0, yAxisIndex: 0, lineStyle: { color: '#174d32', width: 2 } },
          {
            ...common,
            name: '回撤',
            data: analysis.series.drawdown,
            xAxisIndex: 1,
            yAxisIndex: 1,
            lineStyle: { color: '#ef634c', width: 2 },
            areaStyle: { color: 'rgba(239,99,76,.16)' },
            markPoint: {
              symbol: 'circle',
              symbolSize: 10,
              label: { show: true, color: '#6e2f26', fontSize: 12, lineHeight: 18, formatter: `最大回撤\n${(maxDrawdown * 100).toFixed(1)}%`, position: 'bottom' },
              itemStyle: { color: '#fff', borderColor: '#ef634c', borderWidth: 2 },
              data: [{ coord: [dates[troughIndex], maxDrawdown] }],
            },
            markLine: {
              symbol: 'none',
              lineStyle: { color: '#ef634c', type: 'dashed', width: 1 },
              label: { show: false },
              data: [[{ coord: [dates[peakIndex], 0] }, { coord: [dates[troughIndex], maxDrawdown] }]],
            },
          },
        ],
      }, true)
      return
    }

    const config = {
      return: {
        title: '累计收益',
        asset: analysis.series.cumulative_return,
        benchmark: analysis.series.benchmark_return,
        formatter: percent,
        areaColor: 'rgba(23,77,50,.08)',
        referenceLines: [{ yAxis: 0, name: '盈亏平衡' }],
      },
      volatility: {
        title: '年化波动（滚动20日）',
        asset: analysis.series.rolling_volatility,
        benchmark: [],
        formatter: percent,
        areaColor: 'rgba(194,138,49,.10)',
        referenceLines: [{ yAxis: 0.15, name: '较低' }, { yAxis: 0.3, name: '偏高' }],
      },
      sharpe: {
        title: '夏普比率（滚动60日）',
        asset: analysis.series.rolling_sharpe,
        benchmark: [],
        formatter: (value: number) => value.toFixed(1),
        areaColor: 'rgba(23,77,50,.07)',
        referenceLines: [{ yAxis: 0, name: '无超额回报' }, { yAxis: 1, name: '较好' }],
      },
    }[metric]

    chart.setOption({
      animationDuration: 450,
      textStyle: { fontFamily: 'WenQuanYi Micro Hei, Inter, sans-serif' },
      title: { text: config.title, left: 46, top: 5, textStyle: { color: '#242722', fontSize: 15, fontWeight: 650 } },
      tooltip,
      legend: { top: 6, right: 22, textStyle: { color: '#656760' } },
      grid: { left: 48, right: 22, top: 54, bottom: 42 },
      xAxis: { type: 'category', data: dates, boundaryGap: false, axisLabel, axisTick: { show: false }, axisLine: { lineStyle: { color: '#c9c9c3' } } },
      yAxis: { type: 'value', scale: metric === 'sharpe', axisLabel: { ...axisLabel, formatter: config.formatter }, splitLine },
      dataZoom: [{ type: 'inside', start: 0, end: 100 }],
      series: [
        {
          ...common,
          name: instrumentName,
          data: config.asset,
          lineStyle: { color: '#174d32', width: 2.4 },
          areaStyle: { color: config.areaColor },
          markLine: { symbol: 'none', label: { color: '#8a6e3c', fontSize: 10 }, lineStyle: { color: '#c7b48d', type: 'dashed' }, data: config.referenceLines },
        },
        ...(config.benchmark.some((value) => value !== null)
          ? [{ ...common, name: '跟踪基准', data: config.benchmark, lineStyle: { color: '#a4a6a1', width: 1.8 } }]
          : []),
      ],
    }, true)
  }, [analysis, bars, instrumentName, metric])

  return <div ref={containerRef} className="metric-chart" data-testid="market-chart" aria-label="指标联动图表" />
}
