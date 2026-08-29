import { BookOpenText, ChartLineUp, MagnifyingGlass, Pulse } from '@phosphor-icons/react'
import { useState } from 'react'
import type { Instrument, LearningPage } from '../api/types'
import { instrumentDisplayName, instrumentSearchMeta } from '../utils/instrumentNames'

interface HeaderProps {
  onSearch: (query: string) => Promise<Instrument[]>
  onSelect: (instrument: Instrument) => void
  page: LearningPage
  onPageChange: (page: LearningPage) => void
}

export default function Header({ onSearch, onSelect, page, onPageChange }: HeaderProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Instrument[] | null>(null)
  const [searching, setSearching] = useState(false)

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    const normalized = query.trim()
    if (!normalized) return
    setSearching(true)
    try {
      setResults(await onSearch(normalized))
    } catch {
      setResults(null)
    } finally {
      setSearching(false)
    }
  }

  const choose = (instrument: Instrument) => {
    setQuery(`${instrumentDisplayName(instrument)} ${instrument.code}`)
    setResults(null)
    onSelect(instrument)
  }

  return (
    <header className="app-header">
      <a className="brand" href="#top" aria-label="量研手记首页">
        <span className="brand-mark"><BookOpenText size={22} weight="fill" /></span>
        <span className="brand-title">量研手记</span>
      </a>

      <div className="search-shell">
        <form className="search-form" onSubmit={handleSubmit} role="search">
          <MagnifyingGlass size={22} aria-hidden="true" />
          <label className="sr-only" htmlFor="instrument-search">证券代码或名称</label>
          <input
            id="instrument-search"
            value={query}
            onChange={(event) => { setQuery(event.target.value); setResults(null) }}
            placeholder="搜索 ETF / 股票（例：沪深300、600519）"
            autoComplete="off"
          />
          {searching ? <span className="searching-label">查询中…</span> : null}
        </form>
        {results ? (
          <div className="search-results" role="listbox" aria-label="证券搜索结果">
            {results.length ? results.map((instrument) => (
              <button key={instrument.code} type="button" role="option" onClick={() => choose(instrument)}>
                <span><strong>{instrumentDisplayName(instrument)}</strong><small>{instrumentSearchMeta(instrument)}</small></span>
                <code>{instrument.code}</code>
              </button>
            )) : <div className="search-empty">没有找到匹配证券，请检查代码或名称</div>}
          </div>
        ) : null}
      </div>

      <div className="header-controls">
        <nav className="lesson-navigation" aria-label="指标学习页面">
          <button type="button" className={page === 'performance' ? 'is-active' : ''} aria-pressed={page === 'performance'} onClick={() => onPageChange('performance')}>
            <ChartLineUp size={18} weight="duotone" />风险收益课
          </button>
          <button type="button" className={page === 'technical' ? 'is-active' : ''} aria-pressed={page === 'technical'} onClick={() => onPageChange('technical')}>
            <Pulse size={18} weight="duotone" />技术状态课
          </button>
        </nav>
      </div>
    </header>
  )
}
