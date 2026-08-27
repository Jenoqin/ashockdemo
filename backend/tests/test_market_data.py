from datetime import date, datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
import time
import pytest
from quantlab.cache import MarketCache
from quantlab.models import PriceBar
from quantlab.providers.base import ProviderError
from quantlab.services.market_data import MarketDataService

class FakeProvider:
    def __init__(self, name, bars=None, error=None, delay=0.0):
        self.name = name
        self.bars = bars or []
        self.error = error
        self.delay = delay
        self.calls = []

    def get_daily(self, code, start, end):
        self.calls.append((code, start, end))
        if self.delay:
            time.sleep(self.delay)
        if self.error:
            raise ProviderError(self.name, code, self.error)
        return [row.model_copy(update={"source": self.name}) for row in self.bars if start <= row.trade_date <= end]

@pytest.fixture
def cache(tmp_path):
    return MarketCache(tmp_path / "market.db")

def make_bars(source="fake", close_offset=0.0):
    fetched = datetime(2026, 8, 8, tzinfo=timezone.utc)
    return [
        PriceBar(
            code="512480.SH", trade_date=date(2026, 1, 1) + timedelta(days=index),
            open=1.0 + index * 0.01, high=1.03 + index * 0.01,
            low=0.99 + index * 0.01, close=1.01 + index * 0.01 + close_offset,
            volume=1000 + index, amount=1000, source=source, fetched_at=fetched,
        )
        for index in range(25)
    ]

@pytest.fixture
def valid_bars():
    return make_bars()

@pytest.fixture
def primary_bars():
    return make_bars("akshare")

@pytest.fixture
def fallback_bars():
    return make_bars("tushare", close_offset=0.01)

def test_primary_failure_uses_fallback_and_reports_warning(cache, valid_bars):
    primary = FakeProvider("akshare", error="network unavailable")
    fallback = FakeProvider("tushare", bars=valid_bars)
    result = MarketDataService(cache, primary, fallback).get_daily(
        "512480", date(2026,1,1), date(2026,1,31)
    )
    assert result.meta.sources == ["tushare"]
    assert "PRIMARY_PROVIDER_FAILED" in result.meta.warnings
    expected = [b.model_copy(update={"source": "tushare"}) for b in valid_bars]
    for r, e in zip(result.bars, expected):
        assert r.trade_date == e.trade_date
        assert r.close == e.close
        assert r.source == e.source

def test_both_fail_returns_cache_with_stale_warning(cache, valid_bars):
    cached = [bar.model_copy(update={"source": "akshare"}) for bar in valid_bars]
    cache.upsert_bars("akshare", cached)
    service = MarketDataService(cache, FakeProvider("akshare", error="down"), FakeProvider("tushare", error="denied"))
    result = service.get_daily("512480.SH", date(2026,1,1), date(2026,1,31), refresh=True)
    assert result.meta.cache_hit is True
    assert "STALE_CACHE" in result.meta.warnings


def test_cached_demo_rows_are_not_mixed_with_live_fallback(cache, valid_bars):
    demo_rows = [bar.model_copy(update={"source": "Demo"}) for bar in valid_bars]
    cache.upsert_bars("Demo", demo_rows)
    cache.mark_synced("Demo", "512480.SH", date(2026, 1, 1), date(2026, 1, 31))

    result = MarketDataService(
        cache,
        FakeProvider("akshare", error="down"),
        FakeProvider("tushare", bars=valid_bars),
    ).get_daily("512480.SH", date(2026, 1, 1), date(2026, 1, 31))

    assert result.meta.sources == ["tushare"]
    assert {bar.source for bar in result.bars} == {"tushare"}
    assert len(result.bars) == len(valid_bars)


def test_complete_fallback_cache_bypasses_primary_provider(cache, valid_bars):
    fallback_rows = [bar.model_copy(update={"source": "tushare"}) for bar in valid_bars]
    cache.upsert_bars("tushare", fallback_rows)
    cache.mark_synced("tushare", "512480.SH", date(2026, 1, 1), date(2026, 1, 31))
    primary = FakeProvider("akshare", error="must not be called")
    fallback = FakeProvider("tushare", bars=valid_bars)

    result = MarketDataService(cache, primary, fallback).get_daily(
        "512480.SH", date(2026, 1, 1), date(2026, 1, 31)
    )

    assert result.meta.cache_hit is True
    assert result.meta.sources == ["tushare"]
    assert result.meta.warnings == []
    assert primary.calls == []
    assert fallback.calls == []


def test_recently_successful_fallback_fills_next_gap_before_primary(cache, valid_bars):
    primary = FakeProvider("akshare", error="down")
    fallback = FakeProvider("tushare", bars=valid_bars)
    service = MarketDataService(cache, primary, fallback)

    service.get_daily("512480.SH", date(2026, 1, 1), date(2026, 1, 10))
    result = service.get_daily("512480.SH", date(2026, 1, 1), date(2026, 1, 20))

    assert cache.get_preferred_provider("512480.SH") == "tushare"
    assert result.meta.sources == ["tushare"]
    assert len(primary.calls) == 1
    assert len(fallback.calls) == 2


def test_parallel_identical_requests_share_one_provider_fetch(cache, valid_bars):
    primary = FakeProvider("akshare", bars=valid_bars, delay=0.05)
    service = MarketDataService(cache, primary)

    def load():
        return service.get_daily(
            "512480.SH", date(2026, 1, 1), date(2026, 1, 20)
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: load(), range(2)))

    assert len(primary.calls) == 1
    assert {result.meta.cache_hit for result in results} == {False, True}
    assert all(len(result.bars) == 20 for result in results)


def test_boundary_jump_in_combined_cache_is_rejected(cache):
    primary_history = make_bars("akshare")[:2]
    cache.upsert_bars("akshare", primary_history)
    cache.mark_synced(
        "akshare",
        "512480.SH",
        primary_history[0].trade_date,
        primary_history[-1].trade_date,
    )
    fetched = primary_history[-1].model_copy(update={
        "trade_date": date(2026, 1, 3),
        "open": 4.0,
        "high": 4.1,
        "low": 3.9,
        "close": 4.0,
    })
    fallback_bars = make_bars("tushare")[:3]

    result = MarketDataService(
        cache,
        FakeProvider("akshare", bars=[fetched]),
        FakeProvider("tushare", bars=fallback_bars),
    ).get_daily("512480.SH", date(2026, 1, 1), date(2026, 1, 3))

    assert result.meta.sources == ["tushare"]
    assert "PRIMARY_PROVIDER_FAILED" in result.meta.warnings
    assert {bar.source for bar in result.bars} == {"tushare"}
    assert len(cache.get_bars("akshare", "512480.SH", date(2026, 1, 1), date(2026, 1, 3))) == 2

def test_manual_refresh_cross_checks_last_twenty_sessions(cache, primary_bars, fallback_bars):
    result = MarketDataService(cache, FakeProvider("akshare", bars=primary_bars), FakeProvider("tushare", bars=fallback_bars)).get_daily(
        "512480.SH", date(2026,1,1), date(2026,3,31), refresh=True
    )
    assert any(item.startswith("SOURCE_DIFFERENCE:") for item in result.meta.warnings)
