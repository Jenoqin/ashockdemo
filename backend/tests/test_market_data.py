from datetime import date, datetime, timedelta, timezone
import pytest
from quantlab.cache import MarketCache
from quantlab.models import PriceBar
from quantlab.providers.base import ProviderError
from quantlab.services.market_data import MarketDataService

class FakeProvider:
    def __init__(self, name, bars=None, error=None):
        self.name = name
        self.bars = bars or []
        self.error = error

    def get_daily(self, code, start, end):
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
    cache.upsert_bars(valid_bars)
    service = MarketDataService(cache, FakeProvider("akshare", error="down"), FakeProvider("tushare", error="denied"))
    result = service.get_daily("512480.SH", date(2026,1,1), date(2026,1,31), refresh=True)
    assert result.meta.cache_hit is True
    assert "STALE_CACHE" in result.meta.warnings

def test_manual_refresh_cross_checks_last_twenty_sessions(cache, primary_bars, fallback_bars):
    result = MarketDataService(cache, FakeProvider("akshare", bars=primary_bars), FakeProvider("tushare", bars=fallback_bars)).get_daily(
        "512480.SH", date(2026,1,1), date(2026,3,31), refresh=True
    )
    assert any(item.startswith("SOURCE_DIFFERENCE:") for item in result.meta.warnings)
