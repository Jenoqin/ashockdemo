import '@testing-library/jest-dom/vitest'
import { render, screen, cleanup, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import { api } from '../api/client'
import { researchBundle } from './fixtures'

vi.mock('../api/client', () => ({
  api: {
    searchInstruments: vi.fn(),
    loadResearch: vi.fn(),
    refresh: vi.fn(),
    runBacktest: vi.fn(),
  },
}))

vi.mock('echarts', () => ({
  init: () => ({ setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn() }),
}))

vi.stubGlobal('ResizeObserver', class {
  observe() {}
  unobserve() {}
  disconnect() {}
})

describe('App', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  beforeEach(() => {
    vi.mocked(api.loadResearch).mockResolvedValue(researchBundle)
    vi.mocked(api.searchInstruments).mockResolvedValue({ data: [], meta: researchBundle.instrument.meta })
  })

  it('renders the research product identity and disclaimer', () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: '量研手记' })).toBeInTheDocument()
    expect(screen.getByText('仅供个人研究学习，不构成投资建议')).toBeInTheDocument()
  })

  it('loads the default ETF and shows provenance', async () => {
    render(<App />)
    expect(await screen.findByRole('heading', { name: /半导体 ETF/ })).toBeInTheDocument()
    expect(screen.getByText('AkShare')).toBeInTheDocument()
    expect(screen.getAllByText(/更新于/).length).toBeGreaterThan(0)
    expect(screen.getByText('基础资料')).toBeInTheDocument()
  })

  it('requires choosing a search result before changing the instrument', async () => {
    vi.mocked(api.searchInstruments).mockResolvedValueOnce({
      data: [{ code: '600519.SH', name: '贵州茅台', asset_type: 'equity', exchange: 'SH' }],
      meta: researchBundle.instrument.meta,
    })
    render(<App />)
    await screen.findByRole('heading', { name: /半导体 ETF/ })

    const input = screen.getByLabelText('证券代码或名称')
    await userEvent.type(input, '贵州茅台{enter}')
    expect(await screen.findByRole('option', { name: /贵州茅台/ })).toBeInTheDocument()
    expect(api.loadResearch).toHaveBeenCalledTimes(1)

    await userEvent.click(screen.getByRole('option', { name: /贵州茅台/ }))
    await waitFor(() => expect(api.loadResearch).toHaveBeenLastCalledWith('600519.SH', expect.any(Object), expect.any(AbortSignal)))
  })

  it('keeps current research visible when a new code is invalid', async () => {
    vi.mocked(api.searchInstruments).mockRejectedValueOnce(new Error('请输入 6 位证券代码'))
    render(<App />)
    await screen.findByRole('heading', { name: /半导体 ETF/ })
    
    const input = screen.getByLabelText('证券代码或名称')
    await userEvent.clear(input)
    await userEvent.type(input, 'bad-code{enter}')
    
    expect(screen.getByRole('heading', { name: /半导体 ETF/ })).toBeInTheDocument()
    expect(await screen.findByText(/请输入 6 位证券代码/)).toBeInTheDocument()
  })

  it('hides stale metrics and cancels an obsolete range request', async () => {
    const pending: Array<{
      signal?: AbortSignal
      resolve: (value: typeof researchBundle) => void
    }> = []
    vi.mocked(api.loadResearch)
      .mockResolvedValueOnce(researchBundle)
      .mockImplementation((_code, _range, signal) => new Promise((resolve, reject) => {
        signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
        pending.push({ signal, resolve })
      }))

    render(<App />)
    await screen.findByRole('heading', { name: /半导体 ETF/ })

    const range = screen.getByLabelText('观察区间')
    await userEvent.selectOptions(range, '3m')
    await screen.findByText('正在更新观察区间…')
    expect(screen.queryByText('+8.4%')).not.toBeInTheDocument()

    await userEvent.selectOptions(range, '6m')
    await waitFor(() => expect(pending).toHaveLength(2))
    expect(pending[0].signal?.aborted).toBe(true)

    const sixMonthBundle = {
      ...researchBundle,
      analysis: {
        ...researchBundle.analysis,
        data: {
          ...researchBundle.analysis.data,
          metrics: { ...researchBundle.analysis.data.metrics, period_return: 0.123 },
        },
      },
    }
    pending[1].resolve(sixMonthBundle)
    expect(await screen.findAllByText('+12.3%')).not.toHaveLength(0)
  })
})
