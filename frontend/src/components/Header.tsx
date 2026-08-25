import { BookOpenText, CalendarBlank, CaretDown, MagnifyingGlass } from '@phosphor-icons/react'
import { useState } from 'react'
import type { DateRangeKey, Instrument } from '../api/types'

interface HeaderProps {
  onSearch: (query: string) => Promise<Instrument[]>
  onSelect: (instrument: Instrument) => void
  range: DateRangeKey
  onRangeChange: (range: DateRangeKey) => void
}

const rangeLabels: Record<DateRangeKey, string> = {
  '3m': '近3月',
  '6m': '近6月',
  '1y': '近1年',
  '3y': '近3年',
  all: '全部',
}

export default function Header({ onSearch, onSelect, range, onRangeChange }: HeaderProps) {
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
    setQuery(`${instrument.name} ${instrument.code}`)
    setResults(null)
    onSelect(instrument)
  }

  return (
    <header className="app-header">
      <a className="brand" href="#top" aria-label="量研手记首页">
        <span className="brand-mark"><BookOpenText size={22} weight="fill" /></span>
        <h1>量研手记</h1>
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
                <span><strong>{instrument.name}</strong><small>{instrument.asset_type === 'etf' ? 'ETF' : '股票'}</small></span>
                <code>{instrument.code}</code>
              </button>
            )) : <div className="search-empty">没有找到匹配证券，请检查代码或名称</div>}
          </div>
        ) : null}
      </div>

      <div className="header-controls">
        <label className="range-control">
          <CalendarBlank size={19} aria-hidden="true" />
          <span className="sr-only">观察区间</span>
          <select value={range} onChange={(event) => onRangeChange(event.target.value as DateRangeKey)}>
            {Object.entries(rangeLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
          </select>
          <CaretDown size={13} aria-hidden="true" />
        </label>
        <div className="benchmark-control" aria-label="对比基准"><span>沪深300</span><CaretDown size={13} aria-hidden="true" /></div>
        <a className="beginner-guide" href="#learning"><BookOpenText size={20} />新手指南</a>
      </div>
    </header>
  )
}
