import { useState, useEffect, useCallback, useRef } from 'react'
import { api, type ResearchBundle } from '../api/client'
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
  
  if (key === '1w') {
    start.setDate(start.getDate() - 7)
  } else if (key === '1m') {
    start.setMonth(start.getMonth() - 1)
  } else if (key === '3m') {
    start.setMonth(start.getMonth() - 3)
  } else if (key === '6m') {
    start.setMonth(start.getMonth() - 6)
  } else if (key === '1y') {
    start.setFullYear(start.getFullYear() - 1)
  } else if (key === '3y') {
    start.setFullYear(start.getFullYear() - 3)
  } else if (key === 'all') {
    start.setFullYear(1990, 0, 1)
  }

  const formatLocalDate = (value: Date) => {
    const year = value.getFullYear()
    const month = String(value.getMonth() + 1).padStart(2, '0')
    const day = String(value.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }

  return {
    key,
    start: formatLocalDate(start),
    end: formatLocalDate(end)
  }
}

export function useResearch(): UseResearchReturn {
  const [code, setCode] = useState('512480.SH')
  const [range, setRange] = useState<DateRangeKey>('1y')
  const [status, setStatus] = useState<ResearchStatus>('idle')
  const [error, setError] = useState<string | null>(null)
  const [bundle, setBundle] = useState<ResearchBundle | null>(null)
  
  const abortControllerRef = useRef<AbortController | null>(null)
  const requestIdRef = useRef(0)
  const isMountedRef = useRef(false)

  const cancelCurrentRequest = useCallback(() => {
    abortControllerRef.current?.abort()
    abortControllerRef.current = null
    requestIdRef.current += 1
  }, [])

  const runResearchRequest = useCallback(async (
    requestCode: string,
    requestRange: DateRangeKey,
    refreshFirst: boolean,
  ) => {
    if (!isMountedRef.current) return
    abortControllerRef.current?.abort()
    const controller = new AbortController()
    abortControllerRef.current = controller
    const requestId = ++requestIdRef.current

    const isCurrentRequest = () => (
      isMountedRef.current
      && requestId === requestIdRef.current
      && !controller.signal.aborted
    )

    setStatus((current) => (
      refreshFirst || current !== 'idle' ? 'refreshing' : 'loading'
    ))
    setError(null)

    try {
      if (refreshFirst) {
        await api.refresh(requestCode, controller.signal)
        if (!isCurrentRequest()) return
      }

      const dates = getRangeDates(requestRange)
      const result = await api.loadResearch(
        requestCode,
        dates,
        controller.signal,
      )
      if (isCurrentRequest()) {
        setBundle(result)
        setStatus('ready')
      }
    } catch (err: any) {
      if (err?.name === 'AbortError') return
      if (isCurrentRequest()) {
        setError(err.message || (refreshFirst ? '刷新失败' : '加载数据失败'))
        setStatus('error')
      }
    } finally {
      if (requestId === requestIdRef.current) {
        abortControllerRef.current = null
      }
    }
  }, [])

  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
      cancelCurrentRequest()
    }
  }, [cancelCurrentRequest])

  useEffect(() => {
    void runResearchRequest(code, range, false)

    return () => {
      cancelCurrentRequest()
    }
  }, [cancelCurrentRequest, code, range, runResearchRequest])

  const refresh = useCallback(
    () => runResearchRequest(code, range, true),
    [code, range, runResearchRequest],
  )

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
