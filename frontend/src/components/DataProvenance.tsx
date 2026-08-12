import type { ResponseMeta } from '../api/types'

interface DataProvenanceProps {
  meta: ResponseMeta
}

export default function DataProvenance({ meta }: DataProvenanceProps) {
  const dateStr = new Date(meta.fetched_at).toLocaleString('zh-CN')
  
  return (
    <div style={{ fontSize: '14px', color: 'var(--muted)', marginTop: '16px', display: 'flex', gap: '16px', alignItems: 'center' }}>
      <div>数据来源: <span>{meta.sources.join(', ')}</span></div>
      <div>更新于: {dateStr}</div>
      {meta.is_demo && (
        <div style={{ color: 'var(--accent)', fontWeight: 'bold' }}>演示数据</div>
      )}
      {meta.warnings.length > 0 && (
        <div style={{ color: 'var(--negative)' }}>
          告警: {meta.warnings.join('; ')}
        </div>
      )}
    </div>
  )
}
