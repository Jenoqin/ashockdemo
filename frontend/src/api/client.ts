import type {
  Instrument,
  PriceBar,
  AnalysisResult,
  BacktestRequest,
  BacktestResult,
  Envelope,
  DateRange,
  ApiError,
  RefreshResult,
} from './types'

export interface ResearchBundle {
  instrument: Envelope<Instrument>
  market: Envelope<PriceBar[]>
  analysis: Envelope<AnalysisResult>
}

interface ResearchPayload {
  instrument: Instrument
  market: PriceBar[]
  analysis: AnalysisResult
}

const BASE_URL = ''

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, options)
  const body = await response.text()
  let json: unknown

  try {
    json = body ? JSON.parse(body) : null
  } catch {
    throw new Error(
      response.ok
        ? '服务器返回了无法识别的响应'
        : `服务器请求失败（${response.status}）`,
    )
  }
  
  if (!response.ok) {
    if (json && typeof json === 'object' && 'error' in json && json.error) {
      const apiError = json.error as ApiError
      throw new Error(apiError.message || apiError.code)
    }
    if (json && typeof json === 'object' && 'detail' in json) {
      const detail = json.detail
      if (typeof detail === 'string') throw new Error(detail)
      if (detail && typeof detail === 'object' && 'message' in detail) {
        throw new Error(String(detail.message))
      }
    }
    throw new Error(`HTTP error! status: ${response.status}`)
  }
  
  return json as T
}

export const api = {
  searchInstruments: (query: string) =>
    fetchApi<Envelope<Instrument[]>>(`/api/instruments/search?q=${encodeURIComponent(query)}`),
    
  loadResearch: async (code: string, range: DateRange, signal?: AbortSignal): Promise<ResearchBundle> => {
    const encCode = encodeURIComponent(code)
    const requestOptions = { signal }
    const result = await fetchApi<Envelope<ResearchPayload>>(
      `/api/research/${encCode}?start=${range.start}&end=${range.end}`,
      requestOptions,
    )
    
    return {
      instrument: { data: result.data.instrument, meta: result.meta },
      market: { data: result.data.market, meta: result.meta },
      analysis: { data: result.data.analysis, meta: result.meta },
    }
  },
  
  refresh: (code: string, signal?: AbortSignal) =>
    fetchApi<Envelope<RefreshResult>>(
      `/api/data/${encodeURIComponent(code)}/refresh`,
      { method: 'POST', signal },
    ),
    
  runBacktest: (request: BacktestRequest) =>
    fetchApi<Envelope<BacktestResult>>('/api/backtests/ma-cross', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    }),
}
