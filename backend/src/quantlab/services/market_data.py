from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from threading import Lock
from typing import Iterable, List, Mapping

from pydantic import BaseModel

from quantlab.cache import MarketCache
from quantlab.errors import DataUnavailableError
from quantlab.models import PriceBar, ResponseMeta
from quantlab.providers.base import MarketDataProvider, ProviderError, normalize_code
from quantlab.services.quality import validate_bars


FATAL_QUALITY_ERRORS = (
    "INVALID_OHLC",
    "NON_FINITE_NUMERIC",
    "NEGATIVE_VOLUME",
    "INVALID_AMOUNT",
    "DUPLICATE",
    "UNSORTED_DATES",
    "EXTREME_DAILY_RETURN",
    "MIXED_CODES",
    "MIXED_SOURCES",
)
MAX_DAILY_CHUNK_DAYS = 366

# Fixed stripes avoid an unbounded lock registry while still coalescing the
# parallel market/analysis requests for the same security and provider.
FETCH_LOCKS = tuple(Lock() for _ in range(64))


class _IncompleteRangeError(RuntimeError):
    pass


class MarketDataResult(BaseModel):
    bars: List[PriceBar]
    meta: ResponseMeta


def _calendar_exchange(code: str) -> str:
    suffix = code.rsplit(".", maxsplit=1)[1]
    return {"SH": "SSE", "SZ": "SZSE", "BJ": "SSE"}[suffix]


def _date_range(start: date, end: date) -> Iterable[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _chunk_dates(days: list[date]) -> list[tuple[date, date]]:
    """Group sparse dates into non-overlapping spans of at most 366 days."""
    if not days:
        return []
    ranges: list[tuple[date, date]] = []
    chunk_start = days[0]
    chunk_end = days[0]
    for current in days[1:]:
        if (current - chunk_start).days >= MAX_DAILY_CHUNK_DAYS:
            ranges.append((chunk_start, chunk_end))
            chunk_start = current
        chunk_end = current
    ranges.append((chunk_start, chunk_end))
    return ranges


class MarketDataService:
    def __init__(
        self,
        cache: MarketCache,
        provider: MarketDataProvider,
    ):
        self.cache = cache
        self.provider = provider

    @staticmethod
    def _fatal_quality_errors(bars: List[PriceBar]) -> list[str]:
        return [
            warning
            for warning in validate_bars(bars)
            if warning.startswith(FATAL_QUALITY_ERRORS)
        ]

    def _validate_provider_bars(
        self, code: str, start: date, end: date, bars: List[PriceBar]
    ) -> None:
        if any(bar.code != code for bar in bars):
            raise ProviderError(
                self.provider.name, code, "Provider returned another instrument"
            )
        if any(not start <= bar.trade_date <= end for bar in bars):
            raise ProviderError(
                self.provider.name, code, "Provider returned an out-of-range date"
            )
        dates = [bar.trade_date for bar in bars]
        if len(dates) != len(set(dates)):
            raise ProviderError(
                self.provider.name, code, "Provider returned duplicate dates"
            )
        if self._fatal_quality_errors(bars):
            raise ProviderError(
                self.provider.name, code, "Invalid provider response"
            )

    def _cache_snapshot(
        self, code: str, start: date, end: date
    ) -> tuple[list[PriceBar], dict[date, bool], dict[date, str]]:
        dataset = self.provider.name
        exchange = _calendar_exchange(code)
        return (
            self.cache.get_bars(dataset, code, start, end),
            self.cache.get_calendar(exchange, start, end),
            self.cache.get_no_bar_dates(dataset, code, start, end),
        )

    def _unresolved_dates(
        self,
        start: date,
        end: date,
        bars: Iterable[PriceBar],
        calendar: Mapping[date, bool],
        no_bars: Mapping[date, str],
        listing_date: date | None = None,
    ) -> list[date]:
        bar_dates = {bar.trade_date for bar in bars}
        today = date.today()
        unresolved: list[date] = []
        for current in _date_range(start, end):
            if current in bar_dates:
                continue
            if listing_date is not None and current < listing_date:
                continue
            if calendar.get(current) is False:
                continue
            if current < today and current in no_bars:
                continue
            unresolved.append(current)
        return unresolved

    def _full_cached_result(
        self, code: str, start: date, end: date
    ) -> List[PriceBar] | None:
        bars, calendar, no_bars = self._cache_snapshot(code, start, end)
        if self._unresolved_dates(start, end, bars, calendar, no_bars):
            return None
        if self._fatal_quality_errors(bars):
            return None
        return bars

    def _fetch_missing_calendars(
        self,
        code: str,
        start: date,
        end: date,
        calendar: dict[date, bool],
        required_dates: Iterable[date],
    ) -> dict[date, bool]:
        exchange = _calendar_exchange(code)
        staged: dict[date, bool] = {}
        years = sorted({day.year for day in required_dates if day not in calendar})
        today = date.today()
        for year in years:
            year_start = date(year, 1, 1)
            year_end = min(date(year, 12, 31), today)
            if year_start > year_end:
                continue
            fetched = self.provider.get_trade_calendar(
                exchange, year_start, year_end
            )
            expected = set(_date_range(year_start, year_end))
            if set(fetched) != expected:
                raise ProviderError(
                    self.provider.name, code, "Trading calendar response is incomplete"
                )
            if any(type(is_open) is not bool for is_open in fetched.values()):
                raise ProviderError(
                    self.provider.name, code, "Trading calendar contains invalid status"
                )
            staged.update(fetched)
            calendar.update(fetched)
        return staged

    def _suspension_dates(
        self, code: str, days: list[date]
    ) -> set[date]:
        digits = code.split(".", maxsplit=1)[0]
        method = getattr(self.provider, "get_suspension_dates", None)
        if not days or digits.startswith(("1", "5")) or method is None:
            return set()
        try:
            return set(method(code, min(days), max(days)))
        except ProviderError:
            # Suspension data only enriches the reason. A successful one-day
            # daily query remains the completeness authority.
            return set()

    def _fetch_and_verify(
        self, code: str, start: date, end: date, refresh: bool
    ) -> tuple[List[PriceBar], bool]:
        dataset = self.provider.name
        exchange = _calendar_exchange(code)

        cached_bars, calendar, cached_no_bars = self._cache_snapshot(
            code, start, end
        )
        if not refresh:
            unresolved = self._unresolved_dates(
                start, end, cached_bars, calendar, cached_no_bars
            )
            if not unresolved and not self._fatal_quality_errors(cached_bars):
                return cached_bars, True
            calendar_required = unresolved
        else:
            calendar_required = list(_date_range(start, end))

        staged_calendar = self._fetch_missing_calendars(
            code, start, end, calendar, calendar_required
        )

        if refresh:
            candidates = list(_date_range(start, end))
        else:
            candidates = self._unresolved_dates(
                start, end, cached_bars, calendar, cached_no_bars
            )

        # Closed dates can be resolved without loading the security catalog.
        candidates = [day for day in candidates if calendar.get(day) is not False]
        listing_date = self.provider.get_listing_date(code) if candidates else None

        staged_no_bars: dict[date, str] = {}
        pre_listing = [
            day
            for day in candidates
            if listing_date is not None and day < listing_date
        ]
        for day in pre_listing:
            if day < date.today():
                staged_no_bars[day] = "not_listed"

        targets = [
            day
            for day in candidates
            if listing_date is None or day >= listing_date
        ]
        staged_bars: dict[date, PriceBar] = {}
        for range_start, range_end in _chunk_dates(targets):
            fetched = self.provider.get_daily(code, range_start, range_end)
            self._validate_provider_bars(code, range_start, range_end, fetched)
            for bar in fetched:
                if bar.trade_date in targets:
                    staged_bars[bar.trade_date] = bar

        missing_open_days = [
            day for day in targets if day not in staged_bars
        ]
        historical_missing = [
            day for day in missing_open_days if day < date.today()
        ]
        suspended = self._suspension_dates(code, historical_missing)
        for day in historical_missing:
            fetched = self.provider.get_daily(code, day, day)
            self._validate_provider_bars(code, day, day, fetched)
            if fetched:
                staged_bars[day] = fetched[0]
            else:
                staged_no_bars[day] = (
                    "suspended" if day in suspended else "provider_confirmed_empty"
                )

        verified_targets = set(staged_bars) | set(staged_no_bars)
        if any(day not in verified_targets for day in targets):
            raise _IncompleteRangeError(code)

        combined_by_date = {bar.trade_date: bar for bar in cached_bars}
        combined_by_date.update(staged_bars)
        for day in staged_no_bars:
            combined_by_date.pop(day, None)
        combined = sorted(combined_by_date.values(), key=lambda bar: bar.trade_date)
        if self._fatal_quality_errors(combined):
            raise ProviderError(
                dataset, code, "Invalid combined cached/provider series"
            )

        self.cache.commit_verified(
            dataset,
            code,
            {exchange: staged_calendar},
            list(staged_bars.values()),
            staged_no_bars,
        )
        return self.cache.get_bars(dataset, code, start, end), False

    def _load_provider_singleflight(
        self, code: str, start: date, end: date, refresh: bool
    ) -> tuple[List[PriceBar], bool]:
        lock_key = (self.cache.db_path, self.provider.name, code)
        lock = FETCH_LOCKS[hash(lock_key) % len(FETCH_LOCKS)]
        with lock:
            return self._fetch_and_verify(code, start, end, refresh)

    def get_daily(
        self,
        code: str,
        start: date,
        end: date,
        refresh: bool = False,
    ) -> MarketDataResult:
        code = normalize_code(code)
        if start > end:
            raise ValueError("start must be on or before end")

        provider = self.provider
        warnings: list[str] = []
        today = date.today()
        effective_end = min(end, today)
        if end > today:
            warnings.append("FUTURE_RANGE_TRUNCATED")
        if effective_end < start:
            return MarketDataResult(
                bars=[],
                meta=ResponseMeta(
                    sources=[provider.name],
                    fetched_at=datetime.now(timezone.utc),
                    cache_hit=True,
                    warnings=warnings,
                ),
            )

        stale_cache = self._full_cached_result(code, start, effective_end)
        if not refresh and stale_cache is not None:
            return MarketDataResult(
                bars=stale_cache,
                meta=ResponseMeta(
                    sources=[provider.name],
                    fetched_at=datetime.now(timezone.utc),
                    cache_hit=True,
                    warnings=warnings,
                ),
            )

        if not refresh and self.cache.provider_in_cooldown(code, provider.name):
            raise DataUnavailableError(code, 1)

        try:
            bars, cache_hit = self._load_provider_singleflight(
                code, start, effective_end, refresh
            )
        except ProviderError:
            self.cache.record_provider_failure(code, provider.name)
            if stale_cache is None:
                raise DataUnavailableError(code, 1)
            bars = stale_cache
            cache_hit = True
            warnings.append("STALE_CACHE")
        except _IncompleteRangeError:
            # A legal empty result for the current open session remains
            # retryable and must not trigger provider cooldown.
            if stale_cache is None:
                raise DataUnavailableError(code, 1)
            bars = stale_cache
            cache_hit = True
            warnings.append("STALE_CACHE")
        else:
            if not cache_hit:
                self.cache.record_provider_success(code, provider.name)

        return MarketDataResult(
            bars=bars,
            meta=ResponseMeta(
                sources=[provider.name],
                fetched_at=datetime.now(timezone.utc),
                cache_hit=cache_hit,
                warnings=warnings,
            ),
        )
