import type { DateRangeKey } from '../api/types'
import DateRangeControl from './DateRangeControl'

interface AnalysisRangeToolbarProps {
  range: DateRangeKey
  onChange: (range: DateRangeKey) => void
}

export default function AnalysisRangeToolbar({ range, onChange }: AnalysisRangeToolbarProps) {
  return (
    <div className="analysis-toolbar">
      <DateRangeControl range={range} onChange={onChange} />
    </div>
  )
}
