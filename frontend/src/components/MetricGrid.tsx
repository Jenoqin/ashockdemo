import { useState } from 'react'
import type { AnalysisResult } from '../api/types'

export default function MetricGrid({ analysis, days }: { analysis: AnalysisResult; days: number }) {
  const { metrics, diagnostics } = analysis
  const [expanded, setExpanded] = useState<string | null>(null)

  const isShort = days < 252

  const formatPct = (v: number | null | undefined) => {
    if (v === null || v === undefined) return '--'
    return `${(v * 100).toFixed(2)}%`
  }

  const formatNum = (v: number | null | undefined) => {
    if (v === null || v === undefined) return '--'
    return v.toFixed(2)
  }

  const toggle = (key: string) => setExpanded(p => p === key ? null : key)

  const ScoreCard = ({ title, scoreKey, score }: { title: string, scoreKey: string, score: any }) => (
    <div className="card" style={{ cursor: 'pointer' }} onClick={() => toggle(scoreKey)}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ color: 'var(--muted)', fontSize: '14px' }}>{title}</div>
        <div style={{ fontSize: '24px', fontWeight: 'bold', color: score.score >= 60 ? 'var(--positive)' : 'var(--negative)' }}>
          {score.score}
        </div>
      </div>
      {expanded === scoreKey && (
        <div style={{ marginTop: '16px', borderTop: '1px solid var(--line)', paddingTop: '16px' }}>
          {score.rules.map((r: any, i: number) => (
            <div key={i} style={{ marginBottom: '8px', fontSize: '14px', color: r.triggered ? 'var(--ink)' : 'var(--muted)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>{r.label}</span>
                <span>{r.triggered ? `+${r.points}` : '0'}</span>
              </div>
              <div style={{ fontSize: '12px', marginTop: '4px' }}>{r.explanation}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )

  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '16px', marginBottom: '24px' }}>
        <div className="card">
          <div style={{ color: 'var(--muted)', fontSize: '14px', marginBottom: '8px' }}>
            年化收益 {isShort && <span style={{ fontSize: '12px', background: 'var(--line)', padding: '2px 4px', borderRadius: '4px' }}>短样本</span>}
          </div>
          <div style={{ fontSize: '20px', fontWeight: 'bold', color: (metrics.annualized_return || 0) >= 0 ? 'var(--positive)' : 'var(--negative)' }}>
            {formatPct(metrics.annualized_return)}
          </div>
        </div>
        <div className="card">
          <div style={{ color: 'var(--muted)', fontSize: '14px', marginBottom: '8px' }}>
            年化波动 {isShort && <span style={{ fontSize: '12px', background: 'var(--line)', padding: '2px 4px', borderRadius: '4px' }}>短样本</span>}
          </div>
          <div style={{ fontSize: '20px', fontWeight: 'bold' }}>{formatPct(metrics.annualized_volatility)}</div>
        </div>
        <div className="card">
          <div style={{ color: 'var(--muted)', fontSize: '14px', marginBottom: '8px' }}>夏普比率</div>
          <div style={{ fontSize: '20px', fontWeight: 'bold' }}>{formatNum(metrics.sharpe_ratio)}</div>
        </div>
        <div className="card">
          <div style={{ color: 'var(--muted)', fontSize: '14px', marginBottom: '8px' }}>索提诺比率</div>
          <div style={{ fontSize: '20px', fontWeight: 'bold' }}>{formatNum(metrics.sortino_ratio)}</div>
        </div>
        <div className="card">
          <div style={{ color: 'var(--muted)', fontSize: '14px', marginBottom: '8px' }}>最大回撤</div>
          <div style={{ fontSize: '20px', fontWeight: 'bold', color: 'var(--negative)' }}>{formatPct(metrics.max_drawdown)}</div>
          <div style={{ fontSize: '12px', color: 'var(--muted)' }}>{metrics.max_drawdown_duration ?? '--'} 天</div>
        </div>
      </div>
      
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '16px' }}>
        <ScoreCard title="趋势得分" scoreKey="trend" score={diagnostics.trend} />
        <ScoreCard title="动能得分" scoreKey="momentum" score={diagnostics.momentum} />
        <ScoreCard title="波动得分" scoreKey="volatility" score={diagnostics.volatility} />
        <ScoreCard title="抗回撤得分" scoreKey="drawdown" score={diagnostics.drawdown} />
      </div>
    </div>
  )
}
