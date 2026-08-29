# Project Review Findings

Review date: 2026-08-29  
Scope: stock data fetching and caching, chart visualization, indicator analysis, conclusion generation, onboarding guidance, asset profiles, API behavior, backtesting, frontend state, accessibility, and test infrastructure.

This report consolidates the original multi-agent review. File locations describe the review snapshot; some line numbers and provider-specific files changed during the subsequent cache-first/Tushare-only refactor.

## Status legend

- **Open**: still requires work.
- **Fixed**: addressed by the cache-first/Tushare-only change.
- **Partially fixed**: part of the original problem was removed, but a broader issue remains.
- **Obsolete**: the affected provider or mode was removed.

## Summary

| Priority | Count |
| --- | ---: |
| High | 9 |
| Medium | 19 |
| Low | 6 |
| Total | 34 |

The first data-fetching issue and its closely related stale-cache defect have been fixed. SQLite is now checked first, Tushare Pro is the only external provider, and cache completeness is proved per calendar date instead of inferred from price boundaries. Partial responses and partial stale cache cannot enter analysis as complete data.

## A. Stock data fetching, providers, and cache

### DF-01 — Partial provider responses were marked as fully synchronized

- Priority: **High**
- Status: **Fixed**
- Original locations: `backend/src/quantlab/services/market_data.py`, `backend/src/quantlab/cache.py`

Any non-empty provider response previously caused the entire requested calendar range to be written to `sync_ranges`. For example, one returned bar for a month-long request made the cache claim the whole month was complete, so missing data was never retried. A current-day request made before publication could also permanently suppress that day.

The calendar-v2 fix records exchange calendar facts and confirmed no-bar dates, rechecks every unexplained historical open date with a one-day request, and commits only fully verified results in one transaction. Current open-session empties remain retryable, future ranges are truncated explicitly, and old Tushare range metadata is invalidated without deleting any cached price row.

### DF-02 — Partial stale cache was accepted for a full request

- Priority: **High**
- Status: **Fixed**
- Original location: `backend/src/quantlab/services/market_data.py::_valid_stale_cache`

The stale-cache path only required one valid cached bar. A one-day cache could therefore be returned with HTTP success for a one-year request after a provider failure, allowing downstream analysis to present a one-observation result as a yearly analysis.

The fallback now requires cache coverage for the complete requested range; partial cache produces a data-unavailable error.

### DF-03 — Impossible and non-finite price values cross the model boundary

- Priority: **High**
- Status: **Open**
- Locations: `backend/src/quantlab/models.py`, `backend/src/quantlab/services/quality.py`, `backend/src/quantlab/services/market_data.py`

`PriceBar` numeric fields are insufficiently constrained. Negative volume is detected but was not fatal, nonfatal quality warnings were discarded, and NaN/Infinity values can evade comparison-based checks. Bad values can be cached, returned without warnings, or cause an uncaught SQLite/model error.

Recommended action: add finite/range constraints at model normalization, make impossible volume and missing numeric fields fatal, and add malformed-data tests.

### DF-04 — Provider schema and conversion failures bypass controlled error handling

- Priority: **High**
- Status: **Partially fixed**
- Locations: `backend/src/quantlab/providers/tushare_provider.py`, `backend/src/quantlab/services/market_data.py`

Only expected remote-call errors are consistently represented as `ProviderError`. Missing columns, invalid dates, casts, Pydantic validation failures, and cache-write failures may still escape as `KeyError`, `ValueError`, or validation exceptions and become HTTP 500 responses.

AkShare fallback behavior is now obsolete, but Tushare normalization still needs a complete exception boundary and malformed-frame contract tests.

### DF-05 — Legitimate empty ranges triggered provider cooldown

- Priority: **Medium**
- Status: **Fixed**
- Original location: `backend/src/quantlab/services/market_data.py`

Weekend, holiday, or future-only requests were classified as provider failures. This started a cooldown that could block a valid request immediately afterward.

Successful historical empty responses are now cacheable as confirmed ranges, while current/future empty responses remain retryable and do not become provider failures.

### DF-06 — Market endpoints do not validate instrument membership

- Priority: **Medium**
- Status: **Partially fixed**
- Locations: `backend/src/quantlab/api/market.py`, provider instrument catalog path

The daily endpoint normalizes a syntactically valid code but does not first confirm that the instrument exists. The removed demo provider could fabricate price data for unknown securities; that concrete behavior is gone, but the API-level validation gap remains.

Recommended action: validate through `AssetService` before loading market data and test unknown but syntactically valid codes.

### DF-07 — Index benchmark codes are routed through non-index endpoints

- Priority: **Medium**
- Status: **Open**
- Locations: `backend/src/quantlab/api/market.py`, `backend/src/quantlab/providers/tushare_provider.py`

Benchmark codes such as `000300.SH` can be sent through equity/fund daily endpoints instead of a dedicated index-history endpoint. The benchmark failure is then swallowed, leaving beta, correlation, and excess return unavailable without a clear reason.

Recommended action: add an index-capable provider method/type and expose a benchmark-unavailable warning.

### DF-08 — Partial AkShare catalog refresh could replace a healthy catalog

- Priority: **Medium**
- Status: **Obsolete**
- Original location: removed `backend/src/quantlab/providers/akshare_provider.py`

Independent stock/ETF catalog failures could allow a partial result to replace the full cached catalog for six hours, causing false not-found responses. AkShare has now been removed from runtime and dependencies.

### DF-09 — Broad API exception handling defeats stable error envelopes

- Priority: **Medium**
- Status: **Open**
- Locations: `backend/src/quantlab/api/market.py`, `backend/src/quantlab/main.py`

Daily and refresh routes broadly catch exceptions and convert them to raw `HTTPException(500, detail=str(error))`. This can bypass structured global handlers, leak internal details, and turn invalid inputs or data-source failures into inconsistent errors.

Recommended action: remove broad catches or map only expected exceptions to sanitized, stable error codes.

### DF-10 — Provenance metadata misrepresents cache freshness

- Priority: **Medium**
- Status: **Open**
- Locations: `backend/src/quantlab/services/market_data.py`, `backend/src/quantlab/api/instruments.py`, `backend/src/quantlab/services/assets.py`

Cached bars are returned with `fetched_at` set to response time rather than their actual fetch time. Instrument/profile metadata can also report `cache_hit=false` when an in-memory profile cache supplied the response. The UI may therefore label old data as newly updated.

Recommended action: preserve actual cache timestamps/status and include requested versus available ranges in metadata.

### DF-11 — Date ranges are ordered but unbounded

- Priority: **Medium**
- Status: **Open**
- Location: `backend/src/quantlab/api/market.py`

The API enforces date ordering but no maximum lookback or row count. Extremely large ranges can trigger oversized upstream calls, CPU work, cache activity, and responses.

Recommended action: define a supported lookback/row cap and reject requests beyond it.

### DF-12 — SQLite `:memory:` mode is unusable

- Priority: **Low**
- Status: **Open**
- Location: `backend/src/quantlab/cache.py`

Initialization creates tables on one in-memory connection and closes it. Every later method opens a different empty database and fails with `no such table`.

Recommended action: retain a persistent connection or use a shared-memory URI.

### DF-13 — Demo equity price classification used substring matching

- Priority: **Low**
- Status: **Obsolete**
- Original location: removed `backend/src/quantlab/providers/demo_provider.py`

Codes containing `51` could be incorrectly treated as ETF-like instruments. Demo mode and its provider have now been removed.

### DF-14 — The declared HTTP test stack hangs

- Priority: **Low**
- Status: **Open**
- Locations: `backend/pyproject.toml`, `backend/tests/conftest.py`

With the reviewed environment—FastAPI 0.141.1, Starlette 1.6.0, and httpx 0.28.1—even a health request through `TestClient` hangs. Starlette warns that the test client should use `httpx2`.

Recommended action: pin a compatible test stack or migrate the test-client dependency.

## B. Indicator analysis, conclusions, and backtesting

### AN-01 — NaN metrics can break JSON serialization

- Priority: **High**
- Status: **Open**
- Locations: `backend/src/quantlab/services/backtest.py`, `backend/src/quantlab/services/analytics.py`, related API routes

Sample volatility with exactly one return produces NaN, and constant aligned series can produce NaN correlation. These values enter response models and fail strict JSON encoding with an out-of-range float error.

Recommended action: gate every outgoing metric with `np.isfinite`/`pd.notna`, require sufficient observations for sample statistics, and add endpoint serialization tests.

### AN-02 — Technical indicators ignore loaded warm-up history

- Priority: **High**
- Status: **Open**
- Locations: `backend/src/quantlab/api/market.py`, `backend/src/quantlab/services/analytics.py`

The API fetches warm-up history, but MA, MACD, RSI, Bollinger bands, ATR, and technical diagnostics are calculated only from the selected-range frame. Short selected ranges therefore restart every indicator, producing missing values and weak scores instead of the current technical state.

Recommended action: calculate indicators on the full historical context, slice their output to selected dates, and represent diagnostics as unavailable when lookback requirements are not met.

### AN-03 — Benchmark returns are compared over unequal intervals

- Priority: **High**
- Status: **Open**
- Location: `backend/src/quantlab/services/analytics.py`

Asset and benchmark returns are calculated independently before their dates are joined. If the benchmark misses a session, its next return spans two sessions while the asset return at the same endpoint spans one, distorting beta and correlation.

Recommended action: join asset and benchmark prices first, then calculate both return series over common endpoints.

### AN-04 — Zero and insufficient-return conclusions contradict each other

- Priority: **Medium**
- Status: **Open**
- Locations: `backend/src/quantlab/services/analytics.py`, `frontend/src/utils/learningScores.ts`, `frontend/src/components/ResearchWorkspace.tsx`

One price is treated as zero return and zero drawdown and may receive a confident score. A zero return is variously described as mildly positive, negative, and positive in different UI branches. Flat data also receives a false maximum-drawdown date. Exact -10% and -20% thresholds differ between scoring and copy.

Recommended action: require at least two prices, add an explicit flat-result branch, align threshold predicates, and render “no drawdown” or “insufficient data” rather than a false event date.

### AN-05 — Backtest win rate ignores transaction costs

- Priority: **Medium**
- Status: **Open**
- Location: `backend/src/quantlab/services/backtest.py`

A round trip is counted as a win whenever exit execution price exceeds entry execution price, even if fees and slippage make net P&L negative.

Recommended action: calculate per-round-trip net P&L including both entry and exit costs.

### AN-06 — Backtest API does not enforce its parameter contract

- Priority: **Medium**
- Status: **Open**
- Locations: `backend/src/quantlab/models.py`, `backend/src/quantlab/api/backtests.py`

Backend models accept negative slippage, fees, and initial cash, as well as out-of-contract cost rates. Bounds only existed in a dormant frontend component, so direct API callers bypass them.

Recommended action: add Pydantic constraints matching the intended window/cost limits, require positive finite initial cash, and return a stable validation envelope.

### AN-07 — 20-day and five-days-ago rules are off by one

- Priority: **Medium**
- Status: **Open**
- Locations: `backend/src/quantlab/services/analytics.py`, `frontend/src/components/TechnicalWorkspace.tsx`

The 20-day return uses the last value divided by the 20th-from-last value, spanning 19 returns. A rule described as comparing against five trading days ago uses a point only four transitions earlier.

Recommended action: use 21 prices and index `-21` for a 20-session return, and six observations with index `-6` for five sessions ago.

### AN-08 — Benchmark unavailability is silently swallowed

- Priority: **Medium**
- Status: **Open**
- Locations: `backend/src/quantlab/api/market.py`, `backend/src/quantlab/services/analytics.py`

Benchmark fetch failures and insufficient overlap both result in null relative metrics without an availability reason. Users cannot distinguish not-applicable, fetch-failed, and insufficient-history states.

Recommended action: return explicit warnings/availability reasons and avoid discarding all benchmark exceptions.

### AN-09 — Analysis and backtest use different Sharpe definitions

- Priority: **Medium**
- Status: **Open**
- Locations: `backend/src/quantlab/services/analytics.py`, `backend/src/quantlab/services/backtest.py`

General analysis subtracts a default 2% risk-free rate; backtesting divides annualized return by volatility without subtracting a risk-free rate. Both results are labeled simply “Sharpe.”

Recommended action: use one configurable definition or explicitly name and document the zero-rate backtest metric.

### AN-10 — Short samples receive overconfident annualized-risk labels

- Priority: **Low**
- Status: **Open**
- Locations: `backend/src/quantlab/services/analytics.py`, `frontend/src/utils/learningScores.ts`, `frontend/src/components/ResearchWorkspace.tsx`

Any available return sample is annualized, and the frontend immediately converts it into hard low/medium/high risk scores. A one-week sample can therefore appear as certain as a multi-year one.

Recommended action: return observation counts and short-sample status, then qualify or suppress scores below an agreed minimum.

## C. Frontend state, charts, accessibility, and guidance

### FE-01 — Failed loads render stale analysis under the new selection

- Priority: **High**
- Status: **Open**
- Locations: `frontend/src/hooks/useResearch.ts`, `frontend/src/App.tsx`

The hook retains the previous successful bundle after a failed range or instrument request. The app can then render that old bundle with the newly selected range or security, presenting stale analytics under incorrect context.

Recommended action: attach context to the last successful bundle and render it only when it matches, or revert the selection on failure.

### FE-02 — Data-quality warnings do not reach the main research UI

- Priority: **High**
- Status: **Partially fixed**
- Locations: `frontend/src/App.tsx`, `frontend/src/components/DataProvenance.tsx`

Market metadata was reduced to source and date; warnings and cache state were not presented beside scores and conclusions. The original demo-status concern is obsolete because demo mode was removed, but stale-cache, partial-range, and other quality warnings still need visible, user-readable treatment.

Recommended action: mount provenance near conclusions and translate warning codes into clear messages.

### FE-03 — Insufficient technical history is scored as a weak market condition

- Priority: **Medium**
- Status: **Open**
- Locations: `frontend/src/components/TechnicalWorkspace.tsx`, `frontend/src/api/types.ts`

Rules that cannot be evaluated because required lookback history is missing appear as failed conditions. The UI always presents a score out of 100, making incomplete and fully evaluated scores look comparable.

Recommended action: add evaluated-rule counts or an unavailable state and suppress the score/conclusion until required lookbacks exist.

### FE-04 — Search responses can race and show results for the wrong query

- Priority: **Medium**
- Status: **Open**
- Locations: `frontend/src/components/Header.tsx`, `frontend/src/hooks/useResearch.ts`

Any completed search writes directly into shared results without a request ID or abort signal. A slow earlier search can therefore populate results beneath newer input. Search error state is also mixed with research-load state.

Recommended action: sequence or abort searches and maintain separate search status/error state.

### FE-05 — Transient load failures lack a practical retry path

- Priority: **Medium**
- Status: **Open**
- Locations: `frontend/src/api/client.ts`, `frontend/src/components/StatePanel.tsx`, `frontend/src/App.tsx`

The API client discards the backend recovery action, the error panel displays text only, and the hook refresh action is not exposed. If the initial default request fails, selecting the same default instrument may not retrigger state.

Recommended action: preserve structured error information and provide an explicit Retry action.

### FE-06 — Mixed-unit chart tooltips use incorrect formatting

- Priority: **Medium**
- Status: **Open**
- Locations: `frontend/src/components/MarketChart.tsx`, `frontend/src/components/TechnicalChart.tsx`

The drawdown view applies percentage formatting to both drawdown and normalized net value, so a net value of 1.00 appears as 100%. ATR can appear raw while its axis/table presents a percentage.

Recommended action: format tooltips per series or per axis.

### FE-07 — Narrow-screen support is absent

- Priority: **Medium**
- Status: **Open, if mobile support is required**
- Location: `frontend/src/styles/app.css`

The page enforces a 1024px minimum width and retains a desktop two-column layout. A 390px viewport receives substantial horizontal overflow. Current documentation explicitly states desktop-only support, so this is a product scope gap rather than an undocumented regression.

Recommended action: if mobile is in scope, add a genuine stacked layout breakpoint.

### FE-08 — Playwright tests target an obsolete product flow

- Priority: **Medium**
- Status: **Open**
- Locations: `frontend/e2e/research.spec.ts`, `frontend/src/components/Header.tsx`, `frontend/src/App.tsx`

The E2E test expects an old search placeholder/button and a mounted backtest flow that the current app does not expose. Current search, range, failure, provenance, and chart interactions consequently lack working end-to-end protection.

Recommended action: rewrite the Playwright flow around the current UI and cache/Tushare configuration.

### FE-09 — Search listbox semantics are incomplete

- Priority: **Low**
- Status: **Open**
- Location: `frontend/src/components/Header.tsx`

Results use listbox/option roles, but the input lacks the corresponding combobox relationship, expanded state, active descendant, and arrow/Escape keyboard behavior.

Recommended action: implement the complete ARIA combobox pattern.

### FE-10 — Return learning scores ignore selected duration

- Priority: **Low**
- Status: **Open**
- Location: `frontend/src/utils/learningScores.ts`

The same absolute-return thresholds are used for every range. This can rate a short-period return less favorably than a slightly larger multi-year return without accounting for duration.

Recommended action: normalize by duration or clearly state that the score is not comparable across ranges.

## D. Reviewed areas without additional material findings

- The moving-average crossover signal uses closing information and executes on the next row's open; no ordinary same-bar look-ahead bias was found.
- Entry and exit cash accounting applies configured fees and slippage correctly; the backtest defect is specifically win-rate classification.
- With sufficiently long, finite, sorted data, cumulative return, annualized volatility, maximum drawdown, Bollinger bands, ATR, and next-open execution are internally coherent.
- Chart series preserve null gaps rather than visually interpolating missing values.
- Parameterized SQLite queries, provider-separated cache keys, atomic refresh replacement, code normalization, Tushare amount/market-cap unit conversions, secret-file precedence, and single-flight fetching were sound in the reviewed successful paths.
- `BeginnerMetricGuide` onboarding disclosure semantics and content had no additional material finding.
- `ChartDataTable` provides an accessible data fallback.
- ETF/equity profile branching, mounted ECharts resize/disposal, normal range-change cancellation, URL encoding, and the visible research disclaimer had no additional material finding.
- `BacktestLab`, refresh, `DataProvenance`, and `InstrumentHero` were unreachable from the reviewed `App`; `BacktestLab` also needs chart/`ResizeObserver` cleanup if remounted.

## E. Verification recorded during review

- Data-fetch/provider/cache service suites passed independently before the refactor; API tests hung on the current `TestClient` stack.
- Analytics/backtest tests: 9 passed in the focused review.
- Frontend tests: 15 passed.
- Frontend production build passed with a large main-chunk warning.
- Frontend lint passed with an exhaustive-dependencies warning in `useResearch.ts`.
- The cache-first/Tushare-only implementation later passed 36 non-HTTP backend tests, all 15 frontend tests, lint, build, Python compilation, and `git diff --check`.
