interface StatePanelProps {
  status: 'idle' | 'loading' | 'ready' | 'refreshing' | 'error'
  error?: string | null
}

export default function StatePanel({ status, error }: StatePanelProps) {
  if (status === 'ready' || status === 'idle') return null
  
  return (
    <div className="card" style={{ marginBottom: '24px' }}>
      {status === 'loading' && <div style={{ color: 'var(--muted)' }}>加载中...</div>}
      {status === 'refreshing' && <div style={{ color: 'var(--muted)' }}>刷新中...</div>}
      {status === 'error' && (
        <div style={{ color: 'var(--negative)' }}>
          {error || '发生未知错误'}
        </div>
      )}
    </div>
  )
}
