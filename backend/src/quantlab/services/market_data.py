from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from threading import Lock
from typing import Callable, Iterable, List, Mapping
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from quantlab.cache import MarketCache
from quantlab.errors import DataUnavailableError
from quantlab.models import PriceBar, ResponseMeta
from quantlab.providers.base import (
    MarketDataProvider,
    ProviderError,
    normalize_code,
    normalize_index_code,
)
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
MARKET_TIMEZONE = ZoneInfo("Asia/Shanghai")
# Tushare's daily close is not guaranteed to be ready immediately at 15:00.
# Before this cut-off, today is deliberately excluded from end-of-day analysis.
DAILY_DATA_READY_TIME = time(18, 0)

# Fixed stripes avoid an unbounded lock registry while still coalescing
# concurrent requests for the same code/data kind/provider.
FETCH_LOCKS = tuple(Lock() for _ in range(64))


class MarketDataResult(BaseModel):
    bars: List[PriceBar]
    meta: ResponseMeta


def _calendar_exchange(code: str) -> str:
    suffix = code.rsplit(".", maxsplit=1)[1]
    if suffix == "SZ":
        return "SZSE"
    # BJ securities and domestic cross-market index families share the SSE
    # open/closed calendar for completeness checks.
    return "SSE"


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
        now_fn: Callable[[], datetime] | None = None,
    ):
        self.cache = cache
        self.provider = provider
        self._now_fn = now_fn or (lambda: datetime.now(MARKET_TIMEZONE))

    def _market_now(self) -> datetime:
        value = self._now_fn()
        if value.tzinfo is None:
            return value.replace(tzinfo=MARKET_TIMEZONE)
        return value.astimezone(MARKET_TIMEZONE)

    def _today(self) -> date:
        return self._market_now().date()

    @staticmethod
    def _dataset(provider_name: str, data_kind: str) -> str:
        return provider_name if data_kind == "daily" else f"{provider_name}:index_daily"

    @staticmethod
    def _adjustment(data_kind: str) -> str:
        return "hfq" if data_kind == "daily" else "none"

    @staticmethod
    def _fatal_quality_errors(bars: List[PriceBar]) -> list[str]:
        return [
            warning
            for warning in validate_bars(bars)
            if warning.startswith(FATAL_QUALITY_ERRORS)
        ]

    def _response_meta(
        self,
        bars: list[PriceBar],
        *,
        cache_hit: bool,
        warnings: list[str],
    ) -> ResponseMeta:
        if bars:
            latest_date = max(bar.trade_date for bar in bars)
            fetched_at = max(
                bar.fetched_at for bar in bars if bar.trade_date == latest_date
            )
        else:
            latest_date = None
            fetched_at = datetime.now(timezone.utc)
        return ResponseMeta(
            sources=[self.provider.name],
            fetched_at=fetched_at,
            cache_hit=cache_hit,
            data_end_date=latest_date,
            warnings=list(dict.fromkeys(warnings)),
        )

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
        self, code: str, start: date, end: date, data_kind: str
    ) -> tuple[list[PriceBar], dict[date, bool], dict[date, str]]:
        dataset = self._dataset(self.provider.name, data_kind)
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
        today = self._today()
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
        self, code: str, start: date, end: date, data_kind: str
    ) -> List[PriceBar] | None:
        bars, calendar, no_bars = self._cache_snapshot(
            code, start, end, data_kind
        )
        if self._unresolved_dates(start, end, bars, calendar, no_bars):
            return None
        if self._fatal_quality_errors(bars):
            return None
        return bars

    def _fetch_missing_calendars(
        self,
        code: str,
        calendar: dict[date, bool],
        required_dates: Iterable[date],
    ) -> dict[date, bool]:
        exchange = _calendar_exchange(code)
        staged: dict[date, bool] = {}
        years = sorted({day.year for day in required_dates if day not in calendar})
        today = self._today()
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
        self, code: str, days: list[date], data_kind: str
    ) -> set[date]:
        digits = code.split(".", maxsplit=1)[0]
        method = getattr(self.provider, "get_suspension_dates", None)
        if (
            data_kind != "daily"
            or not days
            or digits.startswith(("1", "5"))
            or method is None
        ):
            return set()
        try:
            return set(method(code, min(days), max(days)))
        except ProviderError:
            # Suspension data only enriches the reason. A successful one-day
            # daily query remains the completeness authority.
            return set()

    def _provider_daily(
        self, code: str, start: date, end: date, data_kind: str
    ) -> list[PriceBar]:
        if data_kind == "daily":
            return self.provider.get_daily(code, start, end)
        method = getattr(self.provider, "get_index_daily", None)
        if method is None:
            raise ProviderError(
                self.provider.name, code, "Provider does not support index daily data"
            )
        return method(code, start, end)

    def _fetch_and_verify(
        self,
        code: str,
        start: date,
        end: date,
        refresh: bool,
        data_kind: str,
    ) -> tuple[List[PriceBar], bool, bool]:
        dataset = self._dataset(self.provider.name, data_kind)
        exchange = _calendar_exchange(code)
        today = self._today()

        cached_bars, calendar, cached_no_bars = self._cache_snapshot(
            code, start, end, data_kind
        )
        if not refresh:
            unresolved = self._unresolved_dates(
                start, end, cached_bars, calendar, cached_no_bars
            )
            if not unresolved and not self._fatal_quality_errors(cached_bars):
                return cached_bars, True, False
            calendar_required = unresolved
        else:
            calendar_required = list(_date_range(start, end))

        staged_calendar = self._fetch_missing_calendars(
            code, calendar, calendar_required
        )

        if refresh:
            candidates = list(_date_range(start, end))
        else:
            candidates = self._unresolved_dates(
                start, end, cached_bars, calendar, cached_no_bars
            )

        # Closed dates can be resolved without loading the security catalog.
        candidates = [day for day in candidates if calendar.get(day) is not False]
        listing_date = (
            self.provider.get_listing_date(code)
            if candidates and data_kind == "daily"
            else None
        )

        staged_no_bars: dict[date, str] = {}
        pre_listing = [
            day
            for day in candidates
            if listing_date is not None and day < listing_date
        ]
        for day in pre_listing:
            if day < today:
                staged_no_bars[day] = "not_listed"

        targets = [
            day
            for day in candidates
            if listing_date is None or day >= listing_date
        ]
        staged_bars: dict[date, PriceBar] = {}
        for range_start, range_end in _chunk_dates(targets):
            fetched = self._provider_daily(code, range_start, range_end, data_kind)
            self._validate_provider_bars(code, range_start, range_end, fetched)
            for bar in fetched:
                if bar.trade_date in targets:
                    staged_bars[bar.trade_date] = bar

        missing_open_days = [day for day in targets if day not in staged_bars]
        historical_missing = [day for day in missing_open_days if day < today]
        if data_kind == "index_daily" and targets and not staged_bars:
            raise ProviderError(
                self.provider.name, code, "Index daily response is empty"
            )
        if data_kind == "index_daily":
            # Indexes do not suspend. The already chunked index_daily response
            # is authoritative for historical omissions and avoids thousands
            # of one-day probes before an index's inception.
            for day in historical_missing:
                staged_no_bars[day] = "provider_confirmed_empty"
            historical_missing = []
        suspended = self._suspension_dates(code, historical_missing, data_kind)
        for day in historical_missing:
            fetched = self._provider_daily(code, day, day, data_kind)
            self._validate_provider_bars(code, day, day, fetched)
            if fetched:
                staged_bars[day] = fetched[0]
            else:
                staged_no_bars[day] = (
                    "suspended" if day in suspended else "provider_confirmed_empty"
                )

        verified_targets = set(staged_bars) | set(staged_no_bars)
        unresolved_targets = [
            day for day in targets if day not in verified_targets
        ]
        if any(day != today for day in unresolved_targets):
            raise ProviderError(
                self.provider.name, code, "Unable to verify the requested range"
            )
        current_day_pending = today in unresolved_targets

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
        return (
            self.cache.get_bars(dataset, code, start, end),
            False,
            current_day_pending,
        )

    def _load_provider_singleflight(
        self,
        code: str,
        start: date,
        end: date,
        refresh: bool,
        data_kind: str,
    ) -> tuple[List[PriceBar], bool, bool]:
        lock_key = (self.cache.db_path, self.provider.name, data_kind, code)
        lock = FETCH_LOCKS[hash(lock_key) % len(FETCH_LOCKS)]
        with lock:
            return self._fetch_and_verify(code, start, end, refresh, data_kind)

    @staticmethod
    def _current_bar_needs_refresh(
        bars: list[PriceBar], market_now: datetime
    ) -> bool:
        today = market_now.date()
        today_bars = [bar for bar in bars if bar.trade_date == today]
        if not today_bars or market_now.time() < DAILY_DATA_READY_TIME:
            return False
        fetched_at = max(bar.fetched_at for bar in today_bars)
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=timezone.utc)
        ready_at = datetime.combine(
            today, DAILY_DATA_READY_TIME, tzinfo=MARKET_TIMEZONE
        )
        return fetched_at.astimezone(MARKET_TIMEZONE) < ready_at

    def _get_daily(
        self,
        code: str,
        start: date,
        end: date,
        refresh: bool,
        data_kind: str,
    ) -> MarketDataResult:
        code = normalize_code(code) if data_kind == "daily" else normalize_index_code(code)
        if start > end:
            raise ValueError("start must be on or before end")

        provider = self.provider
        warnings: list[str] = []
        market_now = self._market_now()
        today = market_now.date()
        effective_end = min(end, today)
        if end > today:
            warnings.append("FUTURE_RANGE_TRUNCATED")
        if end >= today and market_now.time() < DAILY_DATA_READY_TIME:
            effective_end = min(effective_end, today - timedelta(days=1))
            cached_today = self.cache.get_calendar(
                _calendar_exchange(code), today, today
            )
            if cached_today.get(today, today.weekday() < 5):
                warnings.append("CURRENT_SESSION_EXCLUDED")
        if effective_end < start:
            return MarketDataResult(
                bars=[],
                meta=self._response_meta([], cache_hit=True, warnings=warnings),
            )

        stale_cache = self._full_cached_result(code, start, effective_end, data_kind)
        auto_refresh_current = bool(
            not refresh
            and stale_cache is not None
            and effective_end == today
            and self._current_bar_needs_refresh(stale_cache, market_now)
        )
        if not refresh and stale_cache is not None and not auto_refresh_current:
            return MarketDataResult(
                bars=stale_cache,
                meta=self._response_meta(
                    stale_cache, cache_hit=True, warnings=warnings
                ),
            )

        adjustment = self._adjustment(data_kind)
        if (
            not refresh
            and not auto_refresh_current
            and self.cache.provider_in_cooldown(
                code, provider.name, data_kind, adjustment
            )
        ):
            raise DataUnavailableError(code, 1)

        fetch_start = today if auto_refresh_current else start
        fetch_end = today if auto_refresh_current else effective_end
        try:
            bars, cache_hit, current_day_pending = self._load_provider_singleflight(
                code,
                fetch_start,
                fetch_end,
                refresh or auto_refresh_current,
                data_kind,
            )
            if auto_refresh_current:
                bars = self.cache.get_bars(
                    self._dataset(provider.name, data_kind),
                    code,
                    start,
                    effective_end,
                )
            if current_day_pending:
                warnings.append("LATEST_BAR_PENDING")
        except ProviderError:
            self.cache.record_provider_failure(
                code, provider.name, data_kind, adjustment
            )
            if stale_cache is None:
                raise DataUnavailableError(code, 1)
            bars = stale_cache
            cache_hit = True
            warnings.append("STALE_CACHE")
        else:
            if not cache_hit:
                self.cache.record_provider_success(
                    code, provider.name, data_kind, adjustment
                )

        return MarketDataResult(
            bars=bars,
            meta=self._response_meta(
                bars, cache_hit=cache_hit, warnings=warnings
            ),
        )

    def get_daily(
        self,
        code: str,
        start: date,
        end: date,
        refresh: bool = False,
    ) -> MarketDataResult:
        return self._get_daily(code, start, end, refresh, "daily")

    def get_index_daily(
        self,
        code: str,
        start: date,
        end: date,
        refresh: bool = False,
    ) -> MarketDataResult:
        return self._get_daily(code, start, end, refresh, "index_daily")
