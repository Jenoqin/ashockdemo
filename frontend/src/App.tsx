import { useState } from 'react'
import { useResearch } from './hooks/useResearch'
import Header from './components/Header'
import ResearchWorkspace from './components/ResearchWorkspace'
import TechnicalWorkspace from './components/TechnicalWorkspace'
import AnalysisRangeToolbar from './components/AnalysisRangeToolbar'
import StatePanel from './components/StatePanel'
import type { LearningPage } from './api/types'

export default function App() {
  const { status, error, bundle, range, setCode, setRange, refresh, search } = useResearch()
  const [page, setPage] = useState<LearningPage>('performance')

  const meta = bundle?.market.meta
  const freshnessNotice = meta?.warnings.includes('LATEST_BAR_PENDING')
    ? '今日收盘数据待发布，当前展示最近已完成交易日'
    : meta?.warnings.includes('CURRENT_SESSION_EXCLUDED')
      ? '盘中仅使用已完成交易日数据'
      : meta?.warnings.includes('STALE_CACHE')
        ? '数据源暂不可用，当前展示已验证缓存'
        : null

  return (
    <div className="app" id="top">
      <Header
        onSearch={async (query) => (await search(query)).data}
        onSelect={(instrument) => setCode(instrument.code)}
        page={page}
        onPageChange={setPage}
      />
      <main>
        <StatePanel status={status} error={error} />
        {bundle && status === 'refreshing' ? (
          <div className="refreshing-range-shell"><AnalysisRangeToolbar range={range} onChange={setRange} /></div>
        ) : null}
        {bundle && status !== 'refreshing' ? (
          page === 'performance' ? (
            <ResearchWorkspace
              instrument={bundle.instrument.data}
              analysis={bundle.analysis.data}
              bars={bundle.market.data}
              range={range}
              onRangeChange={setRange}
            />
          ) : (
            <TechnicalWorkspace
              instrument={bundle.instrument.data}
              analysis={bundle.analysis.data}
              bars={bundle.market.data}
              range={range}
              onRangeChange={setRange}
            />
          )
        ) : null}
      </main>
      <footer>
        <span>数据来源：<strong>{meta?.sources.join('、') || '—'}</strong></span>
        {meta?.data_end_date ? <span>数据截至 {meta.data_end_date}</span> : null}
        <span>行情抓取于 {meta?.fetched_at ? new Date(meta.fetched_at).toLocaleString('zh-CN') : '—'}</span>
        {freshnessNotice ? <span className="freshness-notice">{freshnessNotice}</span> : null}
        {bundle ? (
          <button
            className="footer-refresh-button"
            type="button"
            onClick={() => void refresh()}
            disabled={status === 'loading' || status === 'refreshing'}
          >
            {status === 'refreshing' ? '刷新中…' : '刷新行情'}
          </button>
        ) : null}
        <span>历史表现不代表未来</span>
        <span>仅供个人研究学习，不构成投资建议</span>
      </footer>
    </div>
  )
}
