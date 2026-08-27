import type { DateRangeKey } from '../api/types'
import DateRangeControl from './DateRangeControl'

interface AnalysisRangeToolbarProps {
  range: DateRangeKey
  onChange: (range: DateRangeKey) => void
}

export default function AnalysisRangeToolbar({ range, onChange }: AnalysisRangeToolbarProps) {
  return (
    <div className="analysis-toolbar">
      <div className="analysis-toolbar-copy">
        <strong>观察区间</strong>
        <span>影响本页全部指标与图表</span>
      </div>
      <DateRangeControl range={range} onChange={onChange} />
    </div>
  )
}
