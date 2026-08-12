import '@testing-library/jest-dom/vitest'
import { render, screen, cleanup } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
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

describe('Debug', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('debugs test', async () => {
    vi.mocked(api.loadResearch).mockResolvedValue(researchBundle)
    render(<App />)
    
    // Wait a bit
    await new Promise(r => setTimeout(r, 100))
    
    console.log("DOM AFTER 100ms:")
    screen.debug()
    
    const h2 = await screen.findByRole('heading', { name: /半导体 ETF/ })
    console.log("FOUND H2:", h2.outerHTML)
  })
})
