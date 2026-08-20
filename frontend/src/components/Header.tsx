import { ArrowsClockwise, BookOpenText, MagnifyingGlass } from '@phosphor-icons/react'
import { useState } from 'react'
import type { Instrument } from '../api/types'

interface HeaderProps {
  onSearch: (query: string) => void
  instrument?: Instrument | null
  onRefresh?: () => void
  refreshing?: boolean
}

export default function Header({ onSearch, instrument, onRefresh, refreshing = false }: HeaderProps) {
  const [query, setQuery] = useState('')
  const today = new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit', weekday: 'short',
  }).format(new Date())

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    const normalized = query.trim()
    if (normalized) onSearch(normalized)
  }

  return (
    <header className="app-header">
      <div className="instrument-lockup">
        <BookOpenText size={22} weight="duotone" aria-hidden="true" />
        <h1 className={instrument ? 'sr-only' : undefined}>量研手记</h1>
        {instrument ? <h2>{instrument.name}</h2> : null}
        {instrument ? <span>{instrument.code}</span> : null}
        {instrument ? <small>{instrument.asset_type === 'etf' ? 'ETF' : '股票'}</small> : null}
      </div>

      <div className="header-tools">
        <span className="note-date">研究手记&nbsp;&nbsp;|&nbsp;&nbsp;{today}</span>
        <form className="search-form" onSubmit={handleSubmit}>
          <label className="sr-only" htmlFor="instrument-search">证券代码或名称</label>
          <input id="instrument-search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索证券" />
          <button type="submit" className="icon-button" aria-label="搜索"><MagnifyingGlass size={18} /></button>
        </form>
        {instrument && onRefresh ? (
          <button type="button" className="icon-button" aria-label={refreshing ? '刷新中' : '刷新数据'} onClick={onRefresh} disabled={refreshing}>
            <ArrowsClockwise size={19} className={refreshing ? 'is-spinning' : ''} />
          </button>
        ) : null}
      </div>
    </header>
  )
}
