import { CaretDown } from '@phosphor-icons/react'
import type { DateRangeKey } from '../api/types'

interface DateRangeControlProps {
  range: DateRangeKey
  onChange: (range: DateRangeKey) => void
}

const ranges: Array<{ key: DateRangeKey; shortLabel: string; fullLabel: string }> = [
  { key: '1w', shortLabel: '1周', fullLabel: '近1周' },
  { key: '1m', shortLabel: '1月', fullLabel: '近1月' },
  { key: '3m', shortLabel: '3月', fullLabel: '近3月' },
  { key: '6m', shortLabel: '6月', fullLabel: '近6月' },
  { key: '1y', shortLabel: '1年', fullLabel: '近1年' },
  { key: '3y', shortLabel: '3年', fullLabel: '近3年' },
  { key: 'all', shortLabel: '全部', fullLabel: '全部' },
]

export default function DateRangeControl({ range, onChange }: DateRangeControlProps) {
  return (
    <div className="date-range-control">
      <div className="date-range-segments" role="group" aria-label="观察区间">
        {ranges.map((item) => (
          <button
            key={item.key}
            type="button"
            className={range === item.key ? 'is-active' : ''}
            aria-label={item.fullLabel}
            aria-pressed={range === item.key}
            onClick={() => onChange(item.key)}
          >
            {item.shortLabel}
          </button>
        ))}
      </div>
      <label className="date-range-select">
        <span className="sr-only">观察区间</span>
        <select value={range} onChange={(event) => onChange(event.target.value as DateRangeKey)}>
          {ranges.map((item) => <option key={item.key} value={item.key}>{item.fullLabel}</option>)}
        </select>
        <CaretDown size={13} aria-hidden="true" />
      </label>
    </div>
  )
}
