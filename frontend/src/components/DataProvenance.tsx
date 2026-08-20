import type { ResponseMeta } from '../api/types'
import { Clock, Database, WarningCircle } from '@phosphor-icons/react'

interface DataProvenanceProps {
  meta: ResponseMeta
}

export default function DataProvenance({ meta }: DataProvenanceProps) {
  const dateStr = new Date(meta.fetched_at).toLocaleString('zh-CN')
  
  return (
    <div className="data-provenance">
      <div><Database size={16} aria-hidden="true" /> 数据来源：<span>{meta.sources.join(', ')}</span></div>
      <div><Clock size={16} aria-hidden="true" /> 更新于：{dateStr}</div>
      {meta.is_demo && (
        <div className="provenance-demo">演示数据</div>
      )}
      {meta.warnings.length > 0 && (
        <div className="provenance-warning">
          <WarningCircle size={16} aria-hidden="true" /> 告警：{meta.warnings.join('; ')}
        </div>
      )}
    </div>
  )
}
