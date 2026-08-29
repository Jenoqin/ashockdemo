import { useState } from 'react'

export interface ChartDataColumn {
  label: string
  values: Array<number | null>
  format?: 'number' | 'percent'
  digits?: number
}

interface ChartDataTableProps {
  label: string
  dates: string[]
  columns: ChartDataColumn[]
}

const formatValue = (value: number | null, column: ChartDataColumn) => {
  if (value === null || Number.isNaN(value)) return '—'
  const digits = column.digits ?? 2
  return column.format === 'percent'
    ? `${(value * 100).toFixed(digits)}%`
    : value.toFixed(digits)
}

export default function ChartDataTable({ label, dates, columns }: ChartDataTableProps) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <details className="chart-data-disclosure" onToggle={(event) => setIsOpen(event.currentTarget.open)}>
      <summary>{label}</summary>
      {isOpen ? <div className="chart-data-scroll">
        <table>
          <thead>
            <tr>
              <th scope="col">日期</th>
              {columns.map((column) => <th key={column.label} scope="col">{column.label}</th>)}
            </tr>
          </thead>
          <tbody>
            {dates.map((date, index) => (
              <tr key={date}>
                <th scope="row">{date}</th>
                {columns.map((column) => (
                  <td key={column.label}>{formatValue(column.values[index] ?? null, column)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div> : null}
    </details>
  )
}
