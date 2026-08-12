import React from 'react'
import { useResearch } from './hooks/useResearch'
import Header from './components/Header'
import InstrumentHero from './components/InstrumentHero'
import StatePanel from './components/StatePanel'
import MarketChart from './components/MarketChart'
import MetricGrid from './components/MetricGrid'
import AssetProfile from './components/AssetProfile'
import DataProvenance from './components/DataProvenance'
import type { DateRangeKey } from './api/types'

export default function App() {
  const { status, error, code, range, bundle, setCode, setRange, search, refresh } = useResearch()

  const handleSearch = async (query: string) => {
    // In a real app we might show a list of results. Here we just take the first match.
    // However, if the query is already a code, we can just set it.
    try {
      const res = await search(query)
      if (res.data.length > 0) {
        setCode(res.data[0].code)
      } else {
        setCode(query) // fallback to let loadResearch handle exact match or failure
      }
    } catch (err: any) {
      // Do nothing, useResearch sets error state
    }
  }

  const ranges: { label: string, key: DateRangeKey }[] = [
    { label: '3月', key: '3m' },
    { label: '6月', key: '6m' },
    { label: '1年', key: '1y' },
    { label: '3年', key: '3y' },
    { label: '全部', key: 'all' },
  ]

  return (
    <div className="app">
      <Header onSearch={handleSearch} />
      
      <main>
        <StatePanel status={status} error={error} />

        {bundle && bundle.instrument && (
          <>
            <InstrumentHero instrument={bundle.instrument.data} />
            
            <div style={{ marginBottom: '24px', display: 'flex', gap: '8px', alignItems: 'center' }}>
              <span style={{ color: 'var(--muted)', marginRight: '8px' }}>区间:</span>
              {ranges.map(r => (
                <button
                  key={r.key}
                  onClick={() => setRange(r.key)}
                  style={{
                    padding: '6px 12px',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--line)',
                    background: range === r.key ? 'var(--ink)' : 'var(--surface)',
                    color: range === r.key ? 'var(--surface)' : 'var(--ink)',
                    cursor: 'pointer'
                  }}
                >
                  {r.label}
                </button>
              ))}
              <button 
                onClick={refresh}
                style={{
                  marginLeft: 'auto',
                  padding: '6px 12px',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--line)',
                  background: 'var(--surface)',
                  color: 'var(--ink)',
                  cursor: 'pointer'
                }}
              >
                刷新数据
              </button>
            </div>

            {bundle && (
              <>
                <MarketChart bars={bundle.market.data} analysis={bundle.analysis.data} />
                <div style={{ marginTop: '24px' }}>
                  <MetricGrid analysis={bundle.analysis.data} days={bundle.market.data.length} />
                </div>
                <div style={{ marginTop: '24px' }}>
                  <AssetProfile profile={bundle.profile.data} />
                </div>
              </>
            )}

            {bundle.market && <DataProvenance meta={bundle.market.meta} />}
          </>
        )}
      </main>

      <footer>
        <p style={{ margin: 0 }}>仅供个人研究学习，不构成投资建议</p>
      </footer>
    </div>
  )
}
