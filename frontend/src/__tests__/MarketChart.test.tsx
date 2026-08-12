import '@testing-library/jest-dom/vitest'
import { render, screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import MarketChart from '../components/MarketChart'
import AssetProfile from '../components/AssetProfile'
import { analysis, bars, equityProfile, etfProfile } from './fixtures'

const { mockedSetOption } = vi.hoisted(() => ({ mockedSetOption: vi.fn() }))
vi.mock('echarts', () => ({
  init: () => ({ setOption: mockedSetOption, resize: vi.fn(), dispose: vi.fn() }),
}))

vi.stubGlobal('ResizeObserver', class {
  observe() {}
  unobserve() {}
  disconnect() {}
})

it('links candlestick and volume to the same zoom range', () => {
  render(<MarketChart bars={bars} analysis={analysis} overlays={['ma20', 'macd']} />)
  const option = mockedSetOption.mock.calls.at(-1)?.[0]
  expect(option.series.some((item: { type: string }) => item.type === 'candlestick')).toBe(true)
  expect(option.dataZoom).toHaveLength(2)
  expect(option.axisPointer.link).toEqual([{ xAxisIndex: 'all' }])
})

it('shows ETF holdings and hides equity financials', () => {
  render(<AssetProfile profile={etfProfile} />)
  expect(screen.getByText('前十大持仓')).toBeInTheDocument()
  expect(screen.queryByText('营业收入')).not.toBeInTheDocument()
})

it('shows report dates for equity financials', () => {
  render(<AssetProfile profile={equityProfile} />)
  expect(screen.getByText('营业收入')).toBeInTheDocument()
  expect(screen.getByText('报告期 2026-03-31')).toBeInTheDocument()
})
