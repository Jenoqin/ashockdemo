import { useState, useEffect, useCallback, useRef } from 'react'
import { api, ResearchBundle } from '../api/client'
import type { DateRangeKey, DateRange, Envelope, Instrument } from '../api/types'

export type ResearchStatus = 'idle' | 'loading' | 'ready' | 'refreshing' | 'error'

export interface UseResearchReturn {
  status: ResearchStatus
  error: string | null
  code: string
  range: DateRangeKey
  bundle: ResearchBundle | null
  setCode: (code: string) => void
  setRange: (range: DateRangeKey) => void
  refresh: () => Promise<void>
  search: (query: string) => Promise<Envelope<Instrument[]>>
}

function getRangeDates(key: DateRangeKey): DateRange {
  const end = new Date()
  const start = new Date()
  
  if (key === '3m') {
    start.setMonth(start.getMonth() - 3)
  } else if (key === '6m') {
    start.setMonth(start.getMonth() - 6)
  } else if (key === '1y') {
    start.setFullYear(start.getFullYear() - 1)
  } else if (key === '3y') {
    start.setFullYear(start.getFullYear() - 3)
  } else if (key === 'all') {
    start.setFullYear(2000)
  }

  return {
    key,
    start: start.toISOString().split('T')[0],
    end: end.toISOString().split('T')[0]
  }
}

export function useResearch(): UseResearchReturn {
  const [code, setCode] = useState('512480.SH')
  const [range, setRange] = useState<DateRangeKey>('1y')
  const [status, setStatus] = useState<ResearchStatus>('idle')
  const [error, setError] = useState<string | null>(null)
  const [bundle, setBundle] = useState<ResearchBundle | null>(null)
  
  const abortControllerRef = useRef<AbortController | null>(null)

  useEffect(() => {
    let isMounted = true
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    const controller = new AbortController()
    abortControllerRef.current = controller

    const fetchData = async () => {
      setStatus(bundle ? 'refreshing' : 'loading')
      setError(null)
      try {
        const dates = getRangeDates(range)
        const result = await api.loadResearch(code, dates)
        if (isMounted) {
          setBundle(result)
          setStatus('ready')
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || '加载数据失败')
          setStatus('error')
        }
      }
    }

    fetchData()

    return () => {
      isMounted = false
      controller.abort()
    }
  }, [code, range])

  const refresh = useCallback(async () => {
    try {
      setStatus('refreshing')
      await api.refresh(code)
      const dates = getRangeDates(range)
      const result = await api.loadResearch(code, dates)
      setBundle(result)
      setStatus('ready')
    } catch (err: any) {
      setError(err.message || '刷新失败')
      setStatus('error')
    }
  }, [code, range])

  const search = useCallback(async (query: string) => {
    try {
      return await api.searchInstruments(query)
    } catch (err: any) {
      setError(err.message || '搜索失败')
      setStatus('error')
      throw err
    }
  }, [])

  return {
    status,
    error,
    code,
    range,
    bundle,
    setCode,
    setRange,
    refresh,
    search
  }
}
