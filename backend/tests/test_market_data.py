from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
import math
import sqlite3
import time
from zoneinfo import ZoneInfo

import pytest

from quantlab.cache import MarketCache
from quantlab.errors import DataUnavailableError
from quantlab.models import PriceBar
from quantlab.providers.base import ProviderError
from quantlab.providers.tushare_provider import TushareProvider
from quantlab.services.market_data import MarketDataService


DATASET = "Tushare Pro"
ETF = "512480.SH"


def make_bar(
    trade_date: date,
    *,
    code: str = ETF,
    close: float = 1.0,
) -> PriceBar:
    return PriceBar(
        code=code,
        trade_date=trade_date,
        open=close,
        high=close + 0.02,
        low=close - 0.02,
        close=close,
        volume=1000,
        amount=1000,
        source=DATASET,
        fetched_at=datetime(2026, 8, 8, tzinfo=timezone.utc),
    )


class FakeProvider:
    name = DATASET

    def __init__(
        self,
        bars=None,
        *,
        daily_error=None,
        calendar_error=None,
        listing_date=date(2000, 1, 1),
        delay=0.0,
    ):
        self.bars = bars or []
        self.daily_error = daily_error
        self.calendar_error = calendar_error
        self.listing_date = listing_date
        self.delay = delay
        self.responses = {}
        self.open_overrides = {}
        self.suspended = set()
        self.daily_calls = []
        self.index_daily_calls = []
        self.index_responses = {}
        self.calendar_calls = []
        self.listing_calls = []

    def get_trade_calendar(self, exchange, start, end):
        self.calendar_calls.append((exchange, start, end))
        if self.calendar_error:
            raise ProviderError(self.name, exchange, self.calendar_error)
        return {
            day: self.open_overrides.get(day, day.weekday() < 5)
            for day in days(start, end)
        }

    def get_listing_date(self, code):
        self.listing_calls.append(code)
        return self.listing_date

    def get_daily(self, code, start, end):
        self.daily_calls.append((code, start, end))
        if self.delay:
            time.sleep(self.delay)
        response = self.responses.get((start, end))
        if isinstance(response, Exception):
            raise response
        if response is not None:
            return response
        if self.daily_error:
            raise ProviderError(self.name, code, self.daily_error)
        return [bar for bar in self.bars if start <= bar.trade_date <= end]

    def get_index_daily(self, code, start, end):
        self.index_daily_calls.append((code, start, end))
        response = self.index_responses.get((start, end))
        if isinstance(response, Exception):
            raise response
        if response is not None:
            return response
        return [
            bar for bar in self.bars
            if bar.code == code and start <= bar.trade_date <= end
        ]

    def get_suspension_dates(self, code, start, end):
        return {day for day in self.suspended if start <= day <= end}


def days(start: date, end: date):
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


@pytest.fixture
def cache(tmp_path):
    return MarketCache(tmp_path / "market.db")


def seed_complete(cache, code, start, end, bars, *, open_days=None, no_bars=None):
    exchange = "SZSE" if code.endswith(".SZ") else "SSE"
    calendar = {
        day: (day in open_days if open_days is not None else day.weekday() < 5)
        for day in days(start, end)
    }
    cache.commit_verified(
        DATASET,
        code,
        {exchange: calendar},
        bars,
        no_bars or {},
    )


def insert_invalid_cached_bar(cache, trade_date: date):
    with sqlite3.connect(cache.db_path) as conn:
        conn.execute("""
            INSERT INTO price_bars (
                dataset, code, trade_date, open, high, low, close,
                volume, amount, source, fetched_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            DATASET, ETF, trade_date.isoformat(), 1.0, 1.1, 0.9, 1.0,
            -1, 1000, DATASET, "2026-08-08T00:00:00Z",
        ))


def test_complete_verified_cache_is_used_without_provider(cache):
    start, end = date(2026, 8, 3), date(2026, 8, 5)
    bars = [make_bar(day) for day in days(start, end)]
    seed_complete(cache, ETF, start, end, bars)
    provider = FakeProvider(daily_error="must not be called", calendar_error="no")

    result = MarketDataService(cache, provider).get_daily(ETF, start, end)

    assert result.meta.cache_hit is True
    assert result.meta.warnings == []
    assert provider.daily_calls == []
    assert provider.calendar_calls == []
    assert provider.listing_calls == []
    assert result.meta.fetched_at == bars[-1].fetched_at
    assert result.meta.data_end_date == end


def test_complete_verified_cache_works_with_unconfigured_tushare(cache):
    start, end = date(2026, 8, 3), date(2026, 8, 5)
    bars = [make_bar(day) for day in days(start, end)]
    seed_complete(cache, ETF, start, end, bars)

    result = MarketDataService(cache, TushareProvider(None)).get_daily(
        ETF, start, end
    )

    assert result.bars == bars
    assert result.meta.cache_hit is True


def test_internal_gap_is_rechecked_and_filled_before_success(cache):
    start, gap, end = date(2026, 8, 3), date(2026, 8, 4), date(2026, 8, 5)
    provider = FakeProvider()
    provider.responses[(start, end)] = [make_bar(start), make_bar(end)]
    provider.responses[(gap, gap)] = [make_bar(gap)]

    result = MarketDataService(cache, provider).get_daily(ETF, start, end)

    assert [bar.trade_date for bar in result.bars] == days(start, end)
    assert provider.daily_calls == [(ETF, start, end), (ETF, gap, gap)]
    assert cache.get_no_bar_dates(DATASET, ETF, start, end) == {}


def test_internal_gap_empty_is_recorded_only_after_single_day_confirmation(cache):
    start, gap, end = date(2026, 8, 3), date(2026, 8, 4), date(2026, 8, 5)
    provider = FakeProvider()
    provider.responses[(start, end)] = [make_bar(start), make_bar(end)]
    provider.responses[(gap, gap)] = []

    result = MarketDataService(cache, provider).get_daily(ETF, start, end)

    assert [bar.trade_date for bar in result.bars] == [start, end]
    assert cache.get_no_bar_dates(DATASET, ETF, start, end) == {
        gap: "provider_confirmed_empty"
    }
    provider.daily_calls.clear()
    assert MarketDataService(cache, provider).get_daily(ETF, start, end).meta.cache_hit
    assert provider.daily_calls == []


def test_failed_gap_confirmation_commits_no_partial_facts(cache):
    start, gap, end = date(2026, 8, 3), date(2026, 8, 4), date(2026, 8, 5)
    provider = FakeProvider()
    provider.responses[(start, end)] = [make_bar(start), make_bar(end)]
    provider.responses[(gap, gap)] = ProviderError(DATASET, ETF, "down")

    with pytest.raises(DataUnavailableError):
        MarketDataService(cache, provider).get_daily(ETF, start, end)

    assert cache.get_bars(DATASET, ETF, start, end) == []
    assert cache.get_calendar("SSE", start, end) == {}
    assert cache.get_no_bar_dates(DATASET, ETF, start, end) == {}


def test_failed_partial_refresh_preserves_every_cached_row(cache):
    start, gap, end = date(2026, 8, 3), date(2026, 8, 4), date(2026, 8, 5)
    original = [
        make_bar(day, close=1 + i * 0.01)
        for i, day in enumerate(days(start, end))
    ]
    seed_complete(cache, ETF, start, end, original)
    provider = FakeProvider()
    provider.responses[(start, end)] = [
        make_bar(start, close=1.10),
        make_bar(end, close=1.20),
    ]
    provider.responses[(gap, gap)] = ProviderError(DATASET, ETF, "down")

    result = MarketDataService(cache, provider).get_daily(
        ETF, start, end, refresh=True
    )

    assert result.meta.warnings == ["STALE_CACHE"]
    assert result.bars == original
    assert cache.get_bars(DATASET, ETF, start, end) == original


@pytest.mark.parametrize(
    "bad_rows",
    [
        [make_bar(date(2026, 8, 2))],
        [make_bar(date(2026, 8, 3), code="600519.SH")],
        [make_bar(date(2026, 8, 3)), make_bar(date(2026, 8, 3))],
        [make_bar(date(2026, 8, 3)).model_copy(update={"volume": -1})],
        [make_bar(date(2026, 8, 3)).model_copy(update={"high": math.inf})],
    ],
)
def test_invalid_provider_response_is_rejected_without_cache_mutation(cache, bad_rows):
    target = date(2026, 8, 3)
    provider = FakeProvider()
    provider.responses[(target, target)] = bad_rows

    with pytest.raises(DataUnavailableError):
        MarketDataService(cache, provider).get_daily(ETF, target, target)

    assert cache.get_bars(DATASET, ETF, target, target) == []
    assert cache.get_calendar("SSE", target, target) == {}


def test_invalid_cached_row_is_treated_as_a_gap_and_repaired(cache):
    target = date(2026, 8, 3)
    seed_complete(cache, ETF, target, target, [])
    insert_invalid_cached_bar(cache, target)
    provider = FakeProvider(bars=[make_bar(target)])

    result = MarketDataService(cache, provider).get_daily(ETF, target, target)

    assert result.bars == [make_bar(target)]
    assert result.meta.cache_hit is False
    assert provider.daily_calls == [(ETF, target, target)]
    assert cache.get_bars(DATASET, ETF, target, target) == [make_bar(target)]


def test_invalid_cached_row_is_not_used_as_stale_fallback(cache):
    target = date(2026, 8, 3)
    seed_complete(cache, ETF, target, target, [])
    insert_invalid_cached_bar(cache, target)

    with pytest.raises(DataUnavailableError):
        MarketDataService(cache, FakeProvider(daily_error="down")).get_daily(
            ETF, target, target
        )

    assert cache.get_bars(DATASET, ETF, target, target) == []


def test_weekend_holiday_and_pre_listing_dates_need_no_daily_query(cache):
    start, end = date(2020, 8, 1), date(2020, 8, 3)
    provider = FakeProvider(listing_date=date(2020, 8, 4))

    result = MarketDataService(cache, provider).get_daily(ETF, start, end)

    assert result.bars == []
    assert provider.daily_calls == []
    assert cache.get_no_bar_dates(DATASET, ETF, start, end) == {
        end: "not_listed"
    }


def test_stock_suspension_reason_is_preserved(cache):
    code = "600519.SH"
    target = date(2026, 8, 3)
    provider = FakeProvider()
    provider.suspended.add(target)

    result = MarketDataService(cache, provider).get_daily(code, target, target)

    assert result.bars == []
    assert cache.get_no_bar_dates(DATASET, code, target, target) == {
        target: "suspended"
    }
    assert len(provider.daily_calls) == 2


def test_etf_historical_empty_is_confirmed_by_single_day_query(cache):
    target = date(2026, 8, 3)
    provider = FakeProvider()

    result = MarketDataService(cache, provider).get_daily(ETF, target, target)

    assert result.bars == []
    assert cache.get_no_bar_dates(DATASET, ETF, target, target) == {
        target: "provider_confirmed_empty"
    }
    assert len(provider.daily_calls) == 2


def test_current_open_day_empty_returns_last_complete_data_without_cooldown(cache):
    target = date(2026, 8, 31)
    provider = FakeProvider()
    provider.open_overrides[target] = True
    now = datetime(2026, 8, 31, 20, tzinfo=ZoneInfo("Asia/Shanghai"))

    result = MarketDataService(
        cache, provider, now_fn=lambda: now
    ).get_daily(ETF, target, target)

    assert result.bars == []
    assert result.meta.warnings == ["LATEST_BAR_PENDING"]
    assert cache.get_calendar("SSE", target, target) == {target: True}
    assert cache.get_no_bar_dates(DATASET, ETF, target, target) == {}
    assert cache.provider_in_cooldown(ETF, DATASET) is False


def test_current_session_is_excluded_before_daily_publish_cutoff(cache):
    target = date(2026, 8, 31)
    provider = FakeProvider(daily_error="must not call", calendar_error="no")
    now = datetime(2026, 8, 31, 10, tzinfo=ZoneInfo("Asia/Shanghai"))

    result = MarketDataService(
        cache, provider, now_fn=lambda: now
    ).get_daily(ETF, target, target)

    assert result.bars == []
    assert result.meta.warnings == ["CURRENT_SESSION_EXCLUDED"]
    assert provider.daily_calls == []
    assert provider.calendar_calls == []


def test_current_bar_fetched_before_cutoff_is_refreshed_after_cutoff(cache):
    target = date(2026, 8, 31)
    old_bar = make_bar(target, close=1.0)
    seed_complete(cache, ETF, target, target, [old_bar])
    provider = FakeProvider()
    fresh_time = datetime(2026, 8, 31, 11, tzinfo=timezone.utc)
    fresh_bar = make_bar(target, close=1.2).model_copy(
        update={"fetched_at": fresh_time}
    )
    provider.responses[(target, target)] = [fresh_bar]
    now = datetime(2026, 8, 31, 20, tzinfo=ZoneInfo("Asia/Shanghai"))

    result = MarketDataService(
        cache, provider, now_fn=lambda: now
    ).get_daily(ETF, target, target)

    assert result.bars == [fresh_bar]
    assert result.meta.cache_hit is False
    assert result.meta.fetched_at == fresh_time
    assert provider.daily_calls == [(ETF, target, target)]


def test_index_daily_uses_dedicated_provider_and_cache_namespace(cache):
    code = "H30184.CSI"
    target = date(2026, 8, 3)
    index_bar = make_bar(target, code=code, close=1000)
    provider = FakeProvider()
    provider.index_responses[(target, target)] = [index_bar]

    result = MarketDataService(cache, provider).get_index_daily(
        code, target, target
    )

    assert result.bars == [index_bar]
    assert provider.index_daily_calls == [(code, target, target)]
    assert provider.daily_calls == []
    assert provider.listing_calls == []
    assert cache.get_bars(
        f"{DATASET}:index_daily", code, target, target
    ) == [index_bar]


def test_provider_failure_rejects_partial_stale_cache(cache):
    start, end = date(2026, 8, 3), date(2026, 8, 5)
    cache.upsert_bars(DATASET, [make_bar(start)])

    with pytest.raises(DataUnavailableError):
        MarketDataService(cache, FakeProvider(calendar_error="down")).get_daily(
            ETF, start, end
        )


def test_provider_failure_uses_complete_verified_stale_cache_on_refresh(cache):
    start, end = date(2026, 8, 3), date(2026, 8, 5)
    bars = [make_bar(day) for day in days(start, end)]
    seed_complete(cache, ETF, start, end, bars)

    result = MarketDataService(
        cache, FakeProvider(daily_error="down")
    ).get_daily(ETF, start, end, refresh=True)

    assert result.bars == bars
    assert result.meta.cache_hit is True
    assert result.meta.warnings == ["STALE_CACHE"]


def test_future_range_is_truncated_without_provider_call(cache):
    start = date.today() + timedelta(days=1)
    end = start + timedelta(days=10)
    provider = FakeProvider(daily_error="must not call", calendar_error="no")

    result = MarketDataService(cache, provider).get_daily(ETF, start, end)

    assert result.bars == []
    assert result.meta.warnings == ["FUTURE_RANGE_TRUNCATED"]
    assert provider.daily_calls == []
    assert provider.calendar_calls == []


def test_bj_security_reuses_sse_calendar(cache):
    code = "800001.BJ"
    target = date(2026, 8, 3)
    provider = FakeProvider(bars=[make_bar(target, code=code)])

    MarketDataService(cache, provider).get_daily(code, target, target)

    assert provider.calendar_calls[0][0] == "SSE"


def test_daily_requests_are_chunked_to_at_most_366_calendar_days(cache):
    start, end = date(2024, 1, 1), date(2025, 12, 31)
    requested_days = [day for day in days(start, end) if day.weekday() < 5]
    provider = FakeProvider(bars=[make_bar(day) for day in requested_days])

    MarketDataService(cache, provider).get_daily(ETF, start, end)

    assert len(provider.daily_calls) >= 2
    assert all(
        (range_end - range_start).days <= 365
        for _, range_start, range_end in provider.daily_calls
    )


def test_parallel_identical_requests_share_one_provider_fetch(cache):
    start, end = date(2026, 8, 3), date(2026, 8, 7)
    provider = FakeProvider(
        bars=[make_bar(day) for day in days(start, end)], delay=0.03
    )
    service = MarketDataService(cache, provider)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(
            lambda _: service.get_daily(ETF, start, end), range(2)
        ))

    assert len(provider.daily_calls) == 1
    assert {result.meta.cache_hit for result in results} == {False, True}
