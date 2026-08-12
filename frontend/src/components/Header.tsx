import { useState } from 'react'

interface HeaderProps {
  onSearch: (query: string) => void
}

export default function Header({ onSearch }: HeaderProps) {
  const [query, setQuery] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) {
      onSearch(query.trim())
    }
  }

  return (
    <header>
      <h1>量研手记</h1>
      <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '8px' }}>
        <input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="搜索 6 位代码/拼音"
          aria-label="证券代码或名称"
          style={{
            padding: '8px 16px',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--line)',
            background: 'var(--surface)',
            color: 'var(--ink)'
          }}
        />
        <button type="submit" style={{
          padding: '8px 16px',
          borderRadius: 'var(--radius-md)',
          background: 'var(--accent)',
          color: 'white',
          border: 'none',
          cursor: 'pointer'
        }}>
          搜索
        </button>
      </form>
    </header>
  )
}
