import '@testing-library/jest-dom/vitest'
import { render, screen, cleanup } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import BacktestLab from '../components/BacktestLab'
import { backtestResult } from './fixtures'

vi.mock('echarts', () => ({
  init: () => ({ setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn() }),
}))

vi.stubGlobal('ResizeObserver', class {
  observe() {}
  unobserve() {}
  disconnect() {}
})

afterEach(() => {
  cleanup()
})

it('blocks an invalid moving-average pair before requesting', async () => {
  const onRun = vi.fn()
  render(<BacktestLab code="512480.SH" start="2025-08-08" end="2026-08-08" onRun={onRun} />)
  
  const fast = screen.getByLabelText('快线周期')
  const slow = screen.getByLabelText('慢线周期')
  
  await userEvent.clear(fast)
  await userEvent.type(fast, '60')
  await userEvent.clear(slow)
  await userEvent.type(slow, '20')
  
  await userEvent.click(screen.getByRole('button', { name: '运行回测' }))
  
  expect(screen.getByText('快线周期必须小于慢线周期')).toBeInTheDocument()
  expect(onRun).not.toHaveBeenCalled()
})

it('renders strategy and buy-hold metrics with trade dates', async () => {
  render(<BacktestLab code="512480.SH" start="2025-08-08" end="2026-08-08" onRun={async () => backtestResult} />)
  await userEvent.click(screen.getByRole('button', { name: '运行回测' }))
  expect(await screen.findByText('策略年化')).toBeInTheDocument()
  expect(screen.getByText('夏普比率')).toBeInTheDocument()
  expect(screen.getByText(/信号日/)).toBeInTheDocument()
  expect(screen.getByText(/执行日/)).toBeInTheDocument()
})
