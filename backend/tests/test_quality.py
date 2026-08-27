from datetime import date, datetime, timezone
from quantlab.models import PriceBar
from quantlab.services.quality import validate_bars

def test_quality_reports_invalid_ohlc_and_duplicate_dates():
    fetched = datetime.now(timezone.utc)
    rows = [
        PriceBar(code="512480.SH", trade_date=date(2026,1,5), open=1.2, high=1.1, low=1.15, close=1.3, volume=10, source="fake", fetched_at=fetched),
        PriceBar(code="512480.SH", trade_date=date(2026,1,5), open=1.2, high=1.3, low=1.1, close=1.2, volume=10, source="fake", fetched_at=fetched),
    ]
    warnings = validate_bars(rows)
    assert "DUPLICATE_TRADE_DATE:2026-01-05" in warnings
    assert "INVALID_OHLC:2026-01-05" in warnings


def test_quality_rejects_open_outside_range_and_extreme_return():
    fetched = datetime.now(timezone.utc)
    rows = [
        PriceBar(code="512480.SH", trade_date=date(2026, 1, 5), open=1.0, high=1.1, low=0.9, close=1.0, volume=10, source="fake", fetched_at=fetched),
        PriceBar(code="512480.SH", trade_date=date(2026, 1, 6), open=4.2, high=4.1, low=3.9, close=4.0, volume=10, source="fake", fetched_at=fetched),
    ]

    warnings = validate_bars(rows)

    assert "INVALID_OHLC:2026-01-06" in warnings
    assert any(item.startswith("EXTREME_DAILY_RETURN:2026-01-06") for item in warnings)
