import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { api, type ResearchBundle } from '../api/client'
import type { Envelope, RefreshResult } from '../api/types'
import { useResearch } from '../hooks/useResearch'
import { researchBundle } from './fixtures'

vi.mock('../api/client', () => ({
  api: {
    searchInstruments: vi.fn(),
    loadResearch: vi.fn(),
    refresh: vi.fn(),
    runBacktest: vi.fn(),
  },
}))

function deferred<T>() {
  let resolve!: (value: T | PromiseLike<T>) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise
    reject = rejectPromise
  })
  return { promise, resolve, reject }
}

function bundleFor(code: string, periodReturn: number): ResearchBundle {
  return {
    instrument: {
      ...researchBundle.instrument,
      data: { ...researchBundle.instrument.data, code },
    },
    market: researchBundle.market,
    analysis: {
      ...researchBundle.analysis,
      data: {
        ...researchBundle.analysis.data,
        metrics: {
          ...researchBundle.analysis.data.metrics,
          period_return: periodReturn,
        },
      },
    },
  }
}

const refreshSuccess: Envelope<RefreshResult> = {
  data: { refreshed: true, status: 'refreshed' },
  meta: researchBundle.market.meta,
}

describe('useResearch request lifecycle', () => {
  beforeEach(() => {
    vi.mocked(api.loadResearch).mockResolvedValue(researchBundle)
    vi.mocked(api.refresh).mockResolvedValue(refreshSuccess)
    vi.mocked(api.searchInstruments).mockResolvedValue({
      data: [],
      meta: researchBundle.instrument.meta,
    })
  })

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('does not let an old-code refresh overwrite the new instrument', async () => {
    const oldRefresh = deferred<Envelope<RefreshResult>>()
    const newLoad = deferred<ResearchBundle>()
    vi.mocked(api.refresh).mockReturnValueOnce(oldRefresh.promise)
    vi.mocked(api.loadResearch)
      .mockResolvedValueOnce(researchBundle)
      .mockReturnValueOnce(newLoad.promise)
    const { result } = renderHook(() => useResearch())
    await waitFor(() => expect(result.current.status).toBe('ready'))

    let oldCompletion!: Promise<void>
    act(() => {
      oldCompletion = result.current.refresh()
    })
    await waitFor(() => expect(api.refresh).toHaveBeenCalledTimes(1))
    const oldSignal = vi.mocked(api.refresh).mock.calls[0][1]

    act(() => result.current.setCode('600519.SH'))
    await waitFor(() => expect(api.loadResearch).toHaveBeenCalledTimes(2))
    expect(oldSignal).toBeInstanceOf(AbortSignal)
    expect(oldSignal?.aborted).toBe(true)

    await act(async () => newLoad.resolve(bundleFor('600519.SH', 0.2)))
    await waitFor(() => expect(result.current.bundle?.instrument.data.code).toBe('600519.SH'))

    await act(async () => {
      oldRefresh.resolve(refreshSuccess)
      await oldCompletion
    })
    expect(api.loadResearch).toHaveBeenCalledTimes(2)
    expect(result.current.bundle?.instrument.data.code).toBe('600519.SH')
  })

  it('does not let an old-range refresh overwrite the new range', async () => {
    const oldRefresh = deferred<Envelope<RefreshResult>>()
    const newLoad = deferred<ResearchBundle>()
    vi.mocked(api.refresh).mockReturnValueOnce(oldRefresh.promise)
    vi.mocked(api.loadResearch)
      .mockResolvedValueOnce(researchBundle)
      .mockReturnValueOnce(newLoad.promise)
    const { result } = renderHook(() => useResearch())
    await waitFor(() => expect(result.current.status).toBe('ready'))

    let oldCompletion!: Promise<void>
    act(() => {
      oldCompletion = result.current.refresh()
    })
    await waitFor(() => expect(api.refresh).toHaveBeenCalledTimes(1))

    act(() => result.current.setRange('3m'))
    await waitFor(() => expect(api.loadResearch).toHaveBeenCalledTimes(2))
    await act(async () => newLoad.resolve(bundleFor('512480.SH', 0.3)))
    await waitFor(() => expect(result.current.bundle?.analysis.data.metrics.period_return).toBe(0.3))

    await act(async () => {
      oldRefresh.resolve(refreshSuccess)
      await oldCompletion
    })
    expect(api.loadResearch).toHaveBeenCalledTimes(2)
    expect(result.current.bundle?.analysis.data.metrics.period_return).toBe(0.3)
  })

  it('allows only the latest consecutive refresh to commit', async () => {
    const firstRefresh = deferred<Envelope<RefreshResult>>()
    const secondRefresh = deferred<Envelope<RefreshResult>>()
    vi.mocked(api.refresh)
      .mockReturnValueOnce(firstRefresh.promise)
      .mockReturnValueOnce(secondRefresh.promise)
    vi.mocked(api.loadResearch)
      .mockResolvedValueOnce(researchBundle)
      .mockResolvedValueOnce(bundleFor('512480.SH', 0.4))
    const { result } = renderHook(() => useResearch())
    await waitFor(() => expect(result.current.status).toBe('ready'))

    let firstCompletion!: Promise<void>
    let secondCompletion!: Promise<void>
    act(() => {
      firstCompletion = result.current.refresh()
    })
    await waitFor(() => expect(api.refresh).toHaveBeenCalledTimes(1))
    const firstSignal = vi.mocked(api.refresh).mock.calls[0][1]
    act(() => {
      secondCompletion = result.current.refresh()
    })
    await waitFor(() => expect(api.refresh).toHaveBeenCalledTimes(2))

    expect(firstSignal).toBeInstanceOf(AbortSignal)
    expect(firstSignal?.aborted).toBe(true)
    await act(async () => {
      secondRefresh.resolve(refreshSuccess)
      await secondCompletion
    })
    expect(result.current.bundle?.analysis.data.metrics.period_return).toBe(0.4)

    await act(async () => {
      firstRefresh.resolve(refreshSuccess)
      await firstCompletion
    })
    expect(api.loadResearch).toHaveBeenCalledTimes(2)
    expect(result.current.bundle?.analysis.data.metrics.period_return).toBe(0.4)
  })

  it('invalidates a refresh when the component unmounts', async () => {
    const pendingRefresh = deferred<Envelope<RefreshResult>>()
    vi.mocked(api.refresh).mockReturnValueOnce(pendingRefresh.promise)
    const { result, unmount } = renderHook(() => useResearch())
    await waitFor(() => expect(result.current.status).toBe('ready'))

    let completion!: Promise<void>
    act(() => {
      completion = result.current.refresh()
    })
    await waitFor(() => expect(api.refresh).toHaveBeenCalledTimes(1))
    const signal = vi.mocked(api.refresh).mock.calls[0][1]

    unmount()
    expect(signal).toBeInstanceOf(AbortSignal)
    expect(signal?.aborted).toBe(true)
    await act(async () => {
      pendingRefresh.resolve(refreshSuccess)
      await completion
    })
    expect(api.loadResearch).toHaveBeenCalledTimes(1)
  })
})
