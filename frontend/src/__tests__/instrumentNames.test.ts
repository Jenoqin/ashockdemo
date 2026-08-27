import { describe, expect, it } from 'vitest'
import type { Instrument } from '../api/types'
import { instrumentDisplayName, instrumentSearchMeta } from '../utils/instrumentNames'

describe('instrument names', () => {
  it('prefers the formal company name and keeps the short name as search context', () => {
    const instrument: Instrument = {
      code: '600519.SH',
      name: '贵州茅台',
      full_name: '贵州茅台酒股份有限公司',
      asset_type: 'equity',
      exchange: 'SH',
    }

    expect(instrumentDisplayName(instrument)).toBe('贵州茅台酒股份有限公司')
    expect(instrumentSearchMeta(instrument)).toBe('贵州茅台 · 股票')
  })

  it('falls back to the security short name when no formal name is available', () => {
    const instrument: Instrument = {
      code: '512480.SH',
      name: '半导体ETF',
      full_name: null,
      asset_type: 'etf',
      exchange: 'SH',
    }

    expect(instrumentDisplayName(instrument)).toBe('半导体ETF')
    expect(instrumentSearchMeta(instrument)).toBe('ETF')
  })
})
