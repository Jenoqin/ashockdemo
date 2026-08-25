import { useResearch } from './hooks/useResearch'
import Header from './components/Header'
import ResearchWorkspace from './components/ResearchWorkspace'
import StatePanel from './components/StatePanel'

export default function App() {
  const { status, error, bundle, range, setCode, setRange, search } = useResearch()

  const meta = bundle?.market.meta

  return (
    <div className="app" id="top">
      <Header
        onSearch={async (query) => (await search(query)).data}
        onSelect={(instrument) => setCode(instrument.code)}
        range={range}
        onRangeChange={setRange}
      />
      <main>
        <StatePanel status={status} error={error} />
        {bundle && status !== 'refreshing' ? (
          <ResearchWorkspace
            instrument={bundle.instrument.data}
            analysis={bundle.analysis.data}
            bars={bundle.market.data}
            profile={bundle.profile.data}
            profileMeta={bundle.profile.meta}
          />
        ) : null}
      </main>
      <footer>
        <span>数据来源：<strong>{meta?.sources.join('、') || '—'}</strong></span>
        <span>更新于 {meta?.fetched_at ? new Date(meta.fetched_at).toLocaleDateString('zh-CN') : '—'}</span>
        <span>历史表现不代表未来</span>
        <span>仅供个人研究学习，不构成投资建议</span>
      </footer>
    </div>
  )
}
