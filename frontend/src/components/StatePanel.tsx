interface StatePanelProps {
  status: 'idle' | 'loading' | 'ready' | 'refreshing' | 'error'
  error?: string | null
}

export default function StatePanel({ status, error }: StatePanelProps) {
  if (status === 'ready' || status === 'idle') return null
  
  return (
    <div className={`state-panel state-${status}`} role={status === 'error' ? 'alert' : 'status'}>
      {status === 'loading' && <div>正在加载研究数据…</div>}
      {status === 'refreshing' && <div>正在更新观察区间…</div>}
      {status === 'error' && (
        <div>{error || '发生未知错误'}</div>
      )}
    </div>
  )
}
