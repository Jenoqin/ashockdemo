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

  it('renders the research product identity and disclaimer', async () => {
    render(<App />)
    expect(screen.getByRole('link', { name: '量研手记首页' })).toHaveTextContent('量研手记')
    expect(screen.getByText('仅供个人研究学习，不构成投资建议')).toBeInTheDocument()
    await screen.findByRole('heading', { name: /半导体 ETF/ })
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1)
    expect(screen.getByRole('button', { name: '近1周' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '近1月' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '全部' })).toBeInTheDocument()
    expect(screen.queryByRole('combobox', { name: '观察区间' })).not.toBeInTheDocument()
  })

  it('loads the default ETF and shows provenance', async () => {
    render(<App />)
    expect(await screen.findByRole('heading', { name: /半导体 ETF/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /区间收益/ })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: '近1年' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('group', { name: '观察区间' }).closest('.instrument-summary')).not.toBeNull()
    expect(screen.getByRole('group', { name: '观察区间' }).closest('.analysis-toolbar')).toBeNull()
    expect(screen.getByRole('group', { name: '观察区间' }).closest('.chart-panel')).toBeNull()
    expect(screen.queryByRole('button', { name: '图表' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '指标解释' })).not.toBeInTheDocument()
    expect(screen.getByLabelText('区间收益解释')).toBeInTheDocument()
    expect(screen.getByText('查看区间收益图表数据')).toBeInTheDocument()
    await userEvent.click(screen.getByText('查看区间收益图表数据'))
    expect(screen.getByRole('table')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /年化波动/ })).toHaveTextContent('15.0%')
    expect(screen.getByRole('button', { name: /年化波动/ })).not.toHaveTextContent('+15.0%')
    expect(screen.getByRole('heading', { name: '怎么看这四项指标？' })).toBeInTheDocument()
    const guideButton = screen.getByRole('button', { name: '展开指南' })
    expect(guideButton).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByText(/区间收益为正时，还要结合最大回撤和波动/)).not.toBeInTheDocument()
    await userEvent.click(guideButton)
    expect(screen.getByRole('button', { name: '收起指南' })).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText(/区间收益为正时，还要结合最大回撤和波动/)).toBeInTheDocument()
    expect(screen.getByText('Tushare Pro')).toBeInTheDocument()
    expect(screen.getAllByText(/更新于/).length).toBeGreaterThan(0)
    expect(screen.getByText('基础资料')).toBeInTheDocument()
  })

  it('keeps technical-state and performance scoring on separate learning pages', async () => {
    render(<App />)
    await screen.findByRole('heading', { name: /半导体 ETF/ })

    expect(screen.queryByText('本页只评历史风险收益。')).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: '展开指南' }))
    expect(screen.getByText('本页只评历史风险收益。')).toBeInTheDocument()
    expect(screen.getAllByText('学习分 60 / 100')).toHaveLength(4)

    await userEvent.click(screen.getByRole('button', { name: /技术状态课/ }))

    expect(screen.queryByText('技术状态课 · 当前体征')).not.toBeInTheDocument()
    expect(screen.queryByText('本页只评当前技术状态。')).not.toBeInTheDocument()
    expect(screen.getByRole('group', { name: '观察区间' }).closest('.instrument-summary')).not.toBeNull()
    expect(screen.getByText(/趋势 80 分、动量 60 分、波动状态 90 分/)).toBeInTheDocument()
    expect(screen.getByTestId('technical-chart')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /动量状态/ }))
    expect(screen.getAllByText('RSI 14').length).toBeGreaterThan(0)
    expect(screen.getByText(/“超买”不等于马上下跌/)).toBeInTheDocument()
  })

  it('requires choosing a search result before changing the instrument', async () => {
    vi.mocked(api.searchInstruments).mockResolvedValueOnce({
      data: [{ code: '600519.SH', name: '贵州茅台', full_name: '贵州茅台酒股份有限公司', asset_type: 'equity', exchange: 'SH' }],
      meta: researchBundle.instrument.meta,
    })
    render(<App />)
    await screen.findByRole('heading', { name: /半导体 ETF/ })

    const input = screen.getByLabelText('证券代码或名称')
    await userEvent.type(input, '贵州茅台{enter}')
    expect(await screen.findByRole('option', { name: /贵州茅台/ })).toBeInTheDocument()
    expect(api.loadResearch).toHaveBeenCalledTimes(1)

    await userEvent.click(screen.getByRole('option', { name: /贵州茅台/ }))
    expect(input).toHaveValue('贵州茅台酒股份有限公司 600519.SH')
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

    await userEvent.click(screen.getByRole('button', { name: '近3月' }))
    await screen.findByText('正在更新观察区间…')
    expect(screen.queryByText('+8.4%')).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: '近6月' }))
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
