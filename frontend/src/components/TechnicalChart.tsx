import { useEffect, useRef } from 'react'
import * as echarts from 'echarts'
import type { AnalysisResult, PriceBar, TechnicalMetricKey } from '../api/types'
import { CHART_FONT_FAMILY } from '../styles/chartTheme'

interface TechnicalChartProps {
  bars: PriceBar[]
  analysis: AnalysisResult
  metric: TechnicalMetricKey
  instrumentName: string
}

const percent = (value: number) => `${(value * 100).toFixed(1)}%`

export default function TechnicalChart({ bars, analysis, metric, instrumentName }: TechnicalChartProps) {
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
    const { dates } = analysis.series
    if (!chart || !dates.length) return

    const closes = bars.map((bar) => bar.close)
    const axisLabel = { color: '#777872', fontSize: 11, hideOverlap: true }
    const splitLine = { lineStyle: { color: '#e9e8e2', type: 'dashed' as const } }
    const line = { type: 'line' as const, showSymbol: false, connectNulls: false, emphasis: { focus: 'series' as const } }
    const base = {
      animationDuration: 450,
      textStyle: { fontFamily: CHART_FONT_FAMILY },
      tooltip: {
        trigger: 'axis' as const,
        backgroundColor: 'rgba(255,255,252,.98)',
        borderColor: '#d9d8d1',
        textStyle: { color: '#20241f' },
      },
      axisPointer: { link: [{ xAxisIndex: 'all' }] },
      dataZoom: [{ type: 'inside' as const, xAxisIndex: [0, 1], start: 0, end: 100 }],
    }

    if (metric === 'trend') {
      chart.setOption({
        ...base,
        legend: { top: 5, right: 18, textStyle: { color: '#656760' } },
        grid: [
          { left: 52, right: 22, top: 52, height: '52%' },
          { left: 52, right: 22, top: '73%', height: '17%' },
        ],
        xAxis: [
          { type: 'category', data: dates, gridIndex: 0, boundaryGap: false, axisLabel: { show: false }, axisTick: { show: false }, axisLine: { show: false } },
          { type: 'category', data: dates, gridIndex: 1, boundaryGap: false, axisLabel, axisTick: { show: false }, axisLine: { lineStyle: { color: '#c9c9c3' } } },
        ],
        yAxis: [
          { type: 'value', gridIndex: 0, scale: true, axisLabel: { ...axisLabel, formatter: (value: number) => value.toFixed(2) }, splitLine },
          { type: 'value', gridIndex: 1, scale: true, axisLabel: { ...axisLabel, formatter: (value: number) => value.toFixed(3) }, splitLine },
        ],
        series: [
          { ...line, name: instrumentName, data: closes, xAxisIndex: 0, yAxisIndex: 0, lineStyle: { color: '#20241f', width: 2.2 } },
          { ...line, name: 'MA20', data: analysis.series.ma20, xAxisIndex: 0, yAxisIndex: 0, lineStyle: { color: '#174d32', width: 2 } },
          { ...line, name: 'MA60', data: analysis.series.ma60, xAxisIndex: 0, yAxisIndex: 0, lineStyle: { color: '#b47a22', width: 1.8 } },
          { type: 'bar', name: 'MACD 柱', data: analysis.series.macd_hist, xAxisIndex: 1, yAxisIndex: 1, itemStyle: { color: (params: { value: number }) => params.value >= 0 ? '#4f8a68' : '#df806f' } },
          { ...line, name: 'MACD', data: analysis.series.macd, xAxisIndex: 1, yAxisIndex: 1, lineStyle: { color: '#174d32', width: 1.5 } },
          { ...line, name: '信号线', data: analysis.series.macd_signal, xAxisIndex: 1, yAxisIndex: 1, lineStyle: { color: '#b47a22', width: 1.4 } },
        ],
      }, true)
      return
    }

    if (metric === 'momentum') {
      chart.setOption({
        ...base,
        legend: { top: 5, right: 18, textStyle: { color: '#656760' } },
        grid: [
          { left: 52, right: 22, top: 52, height: '45%' },
          { left: 52, right: 22, top: '68%', height: '22%' },
        ],
        xAxis: [
          { type: 'category', data: dates, gridIndex: 0, boundaryGap: false, axisLabel: { show: false }, axisTick: { show: false }, axisLine: { show: false } },
          { type: 'category', data: dates, gridIndex: 1, boundaryGap: false, axisLabel, axisTick: { show: false }, axisLine: { lineStyle: { color: '#c9c9c3' } } },
        ],
        yAxis: [
          { type: 'value', gridIndex: 0, min: 0, max: 100, axisLabel, splitLine },
          { type: 'value', gridIndex: 1, scale: true, axisLabel: { ...axisLabel, formatter: (value: number) => value.toFixed(3) }, splitLine },
        ],
        series: [
          {
            ...line,
            name: 'RSI 14',
            data: analysis.series.rsi14,
            xAxisIndex: 0,
            yAxisIndex: 0,
            lineStyle: { color: '#174d32', width: 2.2 },
            markArea: { silent: true, itemStyle: { color: 'rgba(180,122,34,.08)' }, data: [[{ yAxis: 70 }, { yAxis: 100 }]] },
            markLine: { symbol: 'none', label: { color: '#8a6e3c', fontSize: 10 }, lineStyle: { color: '#c7b48d', type: 'dashed' }, data: [{ yAxis: 70, name: '偏热参考' }, { yAxis: 30, name: '偏弱参考' }] },
          },
          { type: 'bar', name: 'MACD 柱', data: analysis.series.macd_hist, xAxisIndex: 1, yAxisIndex: 1, itemStyle: { color: (params: { value: number }) => params.value >= 0 ? '#4f8a68' : '#df806f' } },
          { ...line, name: 'MACD', data: analysis.series.macd, xAxisIndex: 1, yAxisIndex: 1, lineStyle: { color: '#174d32', width: 1.5 } },
          { ...line, name: '信号线', data: analysis.series.macd_signal, xAxisIndex: 1, yAxisIndex: 1, lineStyle: { color: '#b47a22', width: 1.4 } },
        ],
      }, true)
      return
    }

    chart.setOption({
      ...base,
      legend: { top: 5, right: 18, textStyle: { color: '#656760' } },
      grid: [
        { left: 52, right: 22, top: 52, height: '52%' },
        { left: 52, right: 22, top: '73%', height: '17%' },
      ],
      xAxis: [
        { type: 'category', data: dates, gridIndex: 0, boundaryGap: false, axisLabel: { show: false }, axisTick: { show: false }, axisLine: { show: false } },
        { type: 'category', data: dates, gridIndex: 1, boundaryGap: false, axisLabel, axisTick: { show: false }, axisLine: { lineStyle: { color: '#c9c9c3' } } },
      ],
      yAxis: [
        { type: 'value', gridIndex: 0, scale: true, axisLabel: { ...axisLabel, formatter: (value: number) => value.toFixed(2) }, splitLine },
        { type: 'value', gridIndex: 1, min: 0, axisLabel: { ...axisLabel, formatter: percent }, splitLine },
      ],
      series: [
        { ...line, name: instrumentName, data: closes, xAxisIndex: 0, yAxisIndex: 0, lineStyle: { color: '#20241f', width: 2.2 } },
        { ...line, name: '布林上轨', data: analysis.series.boll_upper, xAxisIndex: 0, yAxisIndex: 0, lineStyle: { color: '#b47a22', width: 1.2, type: 'dashed' } },
        { ...line, name: '布林中轨', data: analysis.series.boll_mid, xAxisIndex: 0, yAxisIndex: 0, lineStyle: { color: '#174d32', width: 1.7 } },
        { ...line, name: '布林下轨', data: analysis.series.boll_lower, xAxisIndex: 0, yAxisIndex: 0, lineStyle: { color: '#b47a22', width: 1.2, type: 'dashed' } },
        { ...line, name: 'ATR 14 / 价格', data: analysis.series.atr14_percent, xAxisIndex: 1, yAxisIndex: 1, lineStyle: { color: '#ef634c', width: 2 }, areaStyle: { color: 'rgba(239,99,76,.10)' } },
      ],
    }, true)
  }, [analysis, bars, instrumentName, metric])

  return <div ref={containerRef} className="metric-chart" data-testid="technical-chart" aria-label="技术状态联动图表" />
}
