import type {
  Instrument,
  PriceBar,
  AnalysisResult,
  AssetProfile,
  BacktestRequest,
  BacktestResult,
  Envelope,
  DateRange,
  ApiError
} from './types'

export interface ResearchBundle {
  instrument: Envelope<Instrument>
  market: Envelope<PriceBar[]>
  analysis: Envelope<AnalysisResult>
  profile: Envelope<AssetProfile>
}

const BASE_URL = ''

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, options)
  const json = await response.json()
  
  if (!response.ok) {
    if (json.error) {
      const apiError: ApiError = json.error
      throw new Error(apiError.message || apiError.code)
    }
    throw new Error(`HTTP error! status: ${response.status}`)
  }
  
  return json as T
}

export const api = {
  searchInstruments: (query: string) =>
    fetchApi<Envelope<Instrument[]>>(`/api/instruments/search?q=${encodeURIComponent(query)}`),
    
  loadResearch: async (code: string, range: DateRange): Promise<ResearchBundle> => {
    const encCode = encodeURIComponent(code)
    const [instrument, market, analysis, profileResult] = await Promise.all([
      fetchApi<Envelope<Instrument>>(`/api/instruments/${encCode}`),
      fetchApi<Envelope<PriceBar[]>>(`/api/market/${encCode}/daily?start=${range.start}&end=${range.end}`),
      fetchApi<Envelope<AnalysisResult>>(`/api/analysis/${encCode}?start=${range.start}&end=${range.end}`),
      fetchApi<Envelope<Instrument>>(`/api/instruments/${encCode}`).then(res => {
        const type = res.data.asset_type
        return fetchApi<Envelope<AssetProfile>>(`/api/${type}/${encCode}`)
      })
    ])
    
    return {
      instrument,
      market,
      analysis,
      profile: profileResult
    }
  },
  
  refresh: (code: string) =>
    fetchApi<Envelope<{ refreshed: boolean }>>(`/api/data/${encodeURIComponent(code)}/refresh`, { method: 'POST' }),
    
  runBacktest: (request: BacktestRequest) =>
    fetchApi<Envelope<BacktestResult>>('/api/backtests/ma-cross', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    }),
}
