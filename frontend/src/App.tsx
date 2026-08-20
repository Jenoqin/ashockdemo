import { useState } from 'react'
import { ChartBar, Flask, ListBullets } from '@phosphor-icons/react'
import { useResearch } from './hooks/useResearch'
import { api } from './api/client'
import Header from './components/Header'
import StatePanel from './components/StatePanel'
import MetricGrid from './components/MetricGrid'
import AssetProfile from './components/AssetProfile'
import BacktestLab from './components/BacktestLab'
import DataProvenance from './components/DataProvenance'
import ResearchNote from './components/ResearchNote'
import type { DateRangeKey } from './api/types'

const ranges: { label: string; key: DateRangeKey }[] = [
  { label: '3月', key: '3m' },
  { label: '6月', key: '6m' },
  { label: '1年', key: '1y' },
  { label: '3年', key: '3y' },
  { label: '全部', key: 'all' },
]

export default function App() {
  const { status, error, code, range, bundle, setCode, setRange, search, refresh } = useResearch()
  const [aiNoticeVisible, setAiNoticeVisible] = useState(false)

  const handleSearch = async (query: string) => {
    try {
      const res = await search(query)
      setCode(res.data[0]?.code ?? query)
    } catch {
      // useResearch owns the visible error state.
    }
  }

  return (
    <div className="app">
      <Header
        onSearch={handleSearch}
        instrument={bundle?.instrument.data}
        onRefresh={refresh}
        refreshing={status === 'refreshing'}
      />

      <main>
        <StatePanel status={status} error={error} />

        {bundle?.instrument ? (
          <>
            <ResearchNote
              analysis={bundle.analysis.data}
              bars={bundle.market.data}
              range={range}
              ranges={ranges}
              onRangeChange={setRange}
              aiNoticeVisible={aiNoticeVisible}
              onAiClick={() => setAiNoticeVisible((visible) => !visible)}
            />

            <DataProvenance meta={bundle.market.meta} />

            <details className="advanced-drawer" id="advanced">
              <summary>
                <span>
                  <strong>高级指标与实验</strong>
                  <small>已经看懂主图，再进入这里</small>
                </span>
                <span className="advanced-summary-hint">展开</span>
              </summary>

              <div className="advanced-content">
                <section id="advanced-metrics" className="advanced-section">
                  <div className="advanced-heading">
                    <ChartBar size={24} weight="duotone" aria-hidden="true" />
                    <div><p className="section-kicker">进阶学习</p><h2>量化评分明细</h2></div>
                  </div>
                  <MetricGrid analysis={bundle.analysis.data} days={bundle.market.data.length} />
                </section>

                <section id="holdings" className="advanced-section">
                  <div className="advanced-heading">
                    <ListBullets size={24} weight="duotone" aria-hidden="true" />
                    <div><p className="section-kicker">资产资料</p><h2>持仓与基本信息</h2></div>
                  </div>
                  <AssetProfile profile={bundle.profile.data} />
                </section>

                <section id="backtest" className="advanced-section">
                  <div className="advanced-heading">
                    <Flask size={24} weight="duotone" aria-hidden="true" />
                    <div><p className="section-kicker">进阶工具</p><h2>策略回测实验室</h2></div>
                  </div>
                  <BacktestLab
                    code={code}
                    start={bundle.market.data[0]?.trade_date}
                    end={bundle.market.data[bundle.market.data.length - 1]?.trade_date}
                    onRun={async (req) => (await api.runBacktest(req)).data}
                  />
                </section>
              </div>
            </details>
          </>
        ) : null}
      </main>

      <footer>
        <p>仅供个人研究学习，不构成投资建议</p>
      </footer>
    </div>
  )
}
