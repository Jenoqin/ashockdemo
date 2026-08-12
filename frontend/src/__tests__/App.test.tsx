import '@testing-library/jest-dom/vitest'
import { render, screen, cleanup } from '@testing-library/react'
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
    expect(screen.getByText(/更新于/)).toBeInTheDocument()
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
})
