from datetime import date
from quantlab.cache import MarketCache
from quantlab.models import PriceBar
from quantlab.providers.base import normalize_code

def bar(day: int, close: float) -> PriceBar:
    return PriceBar(
        code="512480.SH", trade_date=date(2026, 1, day),
        open=close, high=close + 0.02, low=close - 0.02,
        close=close, volume=1000, amount=1284,
        source="akshare", fetched_at="2026-08-08T00:00:00Z",
    )

def test_normalize_code_understands_shanghai_etf_and_stock():
    assert normalize_code("512480") == "512480.SH"
    assert normalize_code("600519.SH") == "600519.SH"

def test_cache_upserts_and_returns_sorted_bars(tmp_path):
    cache = MarketCache(tmp_path / "test.db")
    cache.upsert_bars([bar(3, 1.30), bar(2, 1.28), bar(3, 1.31)])
    rows = cache.get_bars("512480.SH", date(2026, 1, 1), date(2026, 1, 3))
    assert [(row.trade_date.day, row.close) for row in rows] == [(2, 1.28), (3, 1.31)]

def test_missing_ranges_subtracts_synced_intervals(tmp_path):
    cache = MarketCache(tmp_path / "test.db")
    cache.mark_synced("512480.SH", date(2026, 1, 3), date(2026, 1, 7))
    assert cache.missing_ranges("512480.SH", date(2026, 1, 1), date(2026, 1, 10)) == [
        (date(2026, 1, 1), date(2026, 1, 2)),
        (date(2026, 1, 8), date(2026, 1, 10)),
    ]
