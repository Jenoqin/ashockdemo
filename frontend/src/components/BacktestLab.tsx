import { useState, useRef, useEffect } from 'react'
import * as echarts from 'echarts'
import type { BacktestRequest, BacktestResult } from '../api/types'

interface BacktestLabProps {
  code: string
  start?: string
  end?: string
  onRun: (req: BacktestRequest) => Promise<BacktestResult>
}

export default function BacktestLab({ code, start, end, onRun }: BacktestLabProps) {
  const [fast, setFast] = useState(20)
  const [slow, setSlow] = useState(60)
  const [fee, setFee] = useState(0.0003)
  const [slippage, setSlippage] = useState(0.0002)
  const [cash] = useState(100000)

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<BacktestResult | null>(null)

  const chartRef = useRef<echarts.ECharts | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    
    if (fast < 2 || fast > 120) return setError('快线周期必须在 2 到 120 之间')
    if (slow < 3 || slow > 250) return setError('慢线周期必须在 3 到 250 之间')
    if (fast >= slow) return setError('快线周期必须小于慢线周期')
    if (fee < 0 || fee > 0.02) return setError('费率超出范围')
    if (slippage < 0 || slippage > 0.02) return setError('滑点超出范围')
    
    setLoading(true)
    try {
      const res = await onRun({
        code,
        start: start ?? null,
        end: end ?? null,
        fast_window: fast,
        slow_window: slow,
        fee_rate: fee,
        slippage_rate: slippage,
        initial_cash: cash
      })
      setResult(res)
    } catch (err: any) {
      setError(err.message || '回测失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!containerRef.current || !result) return
    if (!chartRef.current) {
      chartRef.current = echarts.init(containerRef.current)
      const observer = new ResizeObserver(() => chartRef.current?.resize())
      observer.observe(containerRef.current)
      // we can't easily clean observer up here without losing it, 
      // but React unmount will handle it if we store it on a ref, 
      // or we can just ignore it for this simple component since it's unmounted rarely
    }

    const chart = chartRef.current
    const dates = result.equity_curve.map(c => c.date)
    const strategy = result.equity_curve.map(c => c.strategy)
    const benchmark = result.equity_curve.map(c => c.benchmark)
    
    // calculate drawdown
    let maxSoFar = -Infinity
    const drawdown = strategy.map(s => {
      if (s > maxSoFar) maxSoFar = s
      return ((s / maxSoFar) - 1) * 100
    })

    chart.setOption({
      tooltip: { trigger: 'axis' },
      axisPointer: { link: [{ xAxisIndex: 'all' }] },
      dataZoom: [
        { type: 'inside', xAxisIndex: [0, 1], start: 0, end: 100 },
        { type: 'slider', xAxisIndex: [0, 1], start: 0, end: 100, bottom: '2%' }
      ],
      grid: [
        { left: '60px', right: '20px', top: '10%', height: '50%' },
        { left: '60px', right: '20px', top: '65%', height: '20%' }
      ],
      xAxis: [
        { type: 'category', data: dates, boundaryGap: false, gridIndex: 0, show: false },
        { type: 'category', data: dates, boundaryGap: false, gridIndex: 1 }
      ],
      yAxis: [
        { type: 'value', scale: true, gridIndex: 0 },
        { type: 'value', gridIndex: 1, axisLabel: { formatter: '{value}%' } }
      ],
      series: [
        { type: 'line', name: '策略净值', data: strategy, smooth: true, showSymbol: false, xAxisIndex: 0, yAxisIndex: 0, itemStyle: { color: 'var(--accent)' } },
        { type: 'line', name: '买入并持有', data: benchmark, smooth: true, showSymbol: false, xAxisIndex: 0, yAxisIndex: 0, itemStyle: { color: 'var(--muted)' } },
        { type: 'line', name: '回撤', data: drawdown, smooth: true, showSymbol: false, xAxisIndex: 1, yAxisIndex: 1, areaStyle: {}, itemStyle: { color: 'var(--negative)' } }
      ]
    }, true)

  }, [result])

  const formatPct = (v: number | null | undefined) => {
    if (v === null || v === undefined) return '--'
    return `${(v * 100).toFixed(2)}%`
  }

  const formatNum = (v: number | null | undefined) => {
    if (v === null || v === undefined) return '--'
    return v.toFixed(2)
  }

  return (
    <div className="card">
      <h2 style={{ fontSize: '20px', marginBottom: '16px' }}>双均线策略实验室</h2>
      <form onSubmit={handleRun} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '16px', marginBottom: '24px' }}>
        <div>
          <label style={{ display: 'block', fontSize: '12px', color: 'var(--muted)', marginBottom: '4px' }}>快线周期</label>
          <input type="number" aria-label="快线周期" value={fast} onChange={e => setFast(Number(e.target.value))} style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid var(--line)' }} />
        </div>
        <div>
          <label style={{ display: 'block', fontSize: '12px', color: 'var(--muted)', marginBottom: '4px' }}>慢线周期</label>
          <input type="number" aria-label="慢线周期" value={slow} onChange={e => setSlow(Number(e.target.value))} style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid var(--line)' }} />
        </div>
        <div>
          <label style={{ display: 'block', fontSize: '12px', color: 'var(--muted)', marginBottom: '4px' }}>费率</label>
          <input type="number" step="0.0001" aria-label="费率" value={fee} onChange={e => setFee(Number(e.target.value))} style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid var(--line)' }} />
        </div>
        <div>
          <label style={{ display: 'block', fontSize: '12px', color: 'var(--muted)', marginBottom: '4px' }}>滑点</label>
          <input type="number" step="0.0001" aria-label="滑点" value={slippage} onChange={e => setSlippage(Number(e.target.value))} style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid var(--line)' }} />
        </div>
        <div style={{ display: 'flex', alignItems: 'flex-end' }}>
          <button type="submit" disabled={loading} style={{ width: '100%', padding: '8px', background: 'var(--ink)', color: 'white', border: 'none', borderRadius: '4px', cursor: loading ? 'not-allowed' : 'pointer' }}>
            {loading ? '运行中...' : '运行回测'}
          </button>
        </div>
      </form>
      
      {error && <div style={{ color: 'var(--negative)', marginBottom: '16px' }}>{error}</div>}

      {result && (
        <div>
          <div style={{ color: 'var(--muted)', fontSize: '14px', marginBottom: '16px' }}>历史回测不代表未来表现；参数越多，过拟合风险越高。</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '16px', marginBottom: '24px' }}>
            <div style={{ background: 'var(--surface)', padding: '12px', borderRadius: '8px' }}>
              <div style={{ fontSize: '12px', color: 'var(--muted)' }}>策略年化</div>
              <div style={{ fontSize: '20px', fontWeight: 'bold' }}>{formatPct(result.metrics.annualized_return)}</div>
            </div>
            <div style={{ background: 'var(--surface)', padding: '12px', borderRadius: '8px' }}>
              <div style={{ fontSize: '12px', color: 'var(--muted)' }}>夏普比率</div>
              <div style={{ fontSize: '20px', fontWeight: 'bold' }}>{formatNum(result.metrics.sharpe)}</div>
            </div>
            <div style={{ background: 'var(--surface)', padding: '12px', borderRadius: '8px' }}>
              <div style={{ fontSize: '12px', color: 'var(--muted)' }}>最大回撤</div>
              <div style={{ fontSize: '20px', fontWeight: 'bold', color: 'var(--negative)' }}>{formatPct(result.metrics.max_drawdown)}</div>
            </div>
            <div style={{ background: 'var(--surface)', padding: '12px', borderRadius: '8px' }}>
              <div style={{ fontSize: '12px', color: 'var(--muted)' }}>胜率</div>
              <div style={{ fontSize: '20px', fontWeight: 'bold' }}>{formatPct(result.metrics.win_rate)}</div>
            </div>
          </div>
          
          <div ref={containerRef} style={{ width: '100%', height: '400px', marginBottom: '24px' }} />

          <h3 style={{ fontSize: '16px', marginBottom: '16px' }}>交易记录 ({result.trades.length})</h3>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--line)' }}>
                  <th style={{ padding: '8px' }}>信号日</th>
                  <th style={{ padding: '8px' }}>执行日</th>
                  <th style={{ padding: '8px' }}>方向</th>
                  <th style={{ padding: '8px' }}>价格</th>
                  <th style={{ padding: '8px' }}>数量</th>
                  <th style={{ padding: '8px' }}>手续费</th>
                </tr>
              </thead>
              <tbody>
                {result.trades.map((t, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid var(--line)' }}>
                    <td style={{ padding: '8px' }}>{t.signal_date}</td>
                    <td style={{ padding: '8px' }}>{t.execution_date}</td>
                    <td style={{ padding: '8px', color: t.direction === 'long' ? 'var(--positive)' : 'var(--negative)' }}>{t.direction === 'long' ? '买入' : '卖出'}</td>
                    <td style={{ padding: '8px' }}>{t.execution_price.toFixed(3)}</td>
                    <td style={{ padding: '8px' }}>{t.volume.toFixed(2)}</td>
                    <td style={{ padding: '8px' }}>{t.fee.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
