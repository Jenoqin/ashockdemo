import math
from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from quantlab.models import PriceBar
from quantlab.services.quality import validate_bars


def unsafe_bar(**overrides) -> PriceBar:
    values = {
        "code": "512480.SH",
        "trade_date": date(2026, 1, 5),
        "open": 1.0,
        "high": 1.1,
        "low": 0.9,
        "close": 1.0,
        "volume": 10,
        "amount": 100,
        "source": "fake",
        "fetched_at": datetime.now(timezone.utc),
    }
    values.update(overrides)
    return PriceBar.model_construct(**values)


def test_quality_reports_invalid_ohlc_and_duplicate_dates():
    rows = [
        unsafe_bar(open=1.2, high=1.1, low=1.15, close=1.3),
        unsafe_bar(open=1.2, high=1.3, low=1.1, close=1.2),
    ]
    warnings = validate_bars(rows)
    assert "DUPLICATE_TRADE_DATE:2026-01-05" in warnings
    assert "INVALID_OHLC:2026-01-05" in warnings


def test_quality_rejects_open_outside_range_and_extreme_return():
    rows = [
        unsafe_bar(),
        unsafe_bar(
            trade_date=date(2026, 1, 6),
            open=4.2,
            high=4.1,
            low=3.9,
            close=4.0,
        ),
    ]

    warnings = validate_bars(rows)

    assert "INVALID_OHLC:2026-01-06" in warnings
    assert any(item.startswith("EXTREME_DAILY_RETURN:2026-01-06") for item in warnings)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("open", 0),
        ("high", -1),
        ("open", -math.inf),
        ("low", math.nan),
        ("close", math.inf),
        ("volume", -1),
        ("volume", math.inf),
        ("amount", -1),
        ("amount", math.nan),
    ],
)
def test_price_bar_rejects_impossible_numeric_values(field, value):
    values = unsafe_bar().model_dump()
    values[field] = value

    with pytest.raises(ValidationError):
        PriceBar.model_validate(values)


@pytest.mark.parametrize(
    "updates",
    [
        {"high": 0.8},
        {"open": 1.2},
        {"close": 0.8},
    ],
)
def test_price_bar_rejects_invalid_ohlc_relationships(updates):
    values = unsafe_bar().model_dump()
    values.update(updates)

    with pytest.raises(ValidationError):
        PriceBar.model_validate(values)


def test_price_bar_requires_ohlcv_but_allows_zero_volume_and_missing_amount():
    values = unsafe_bar(volume=0, amount=None).model_dump()
    assert PriceBar.model_validate(values).volume == 0

    values.pop("close")
    with pytest.raises(ValidationError):
        PriceBar.model_validate(values)


def test_price_bar_allows_small_rounding_tolerance_at_ohlc_boundaries():
    values = unsafe_bar(open=1.100005, close=0.899995).model_dump()

    result = PriceBar.model_validate(values)

    assert result.open == pytest.approx(1.100005)
    assert result.close == pytest.approx(0.899995)


def test_quality_flags_non_finite_and_negative_values_if_model_is_bypassed():
    warnings = validate_bars([
        unsafe_bar(high=math.inf, volume=-1, amount=math.nan),
    ])

    assert "NON_FINITE_NUMERIC:2026-01-05:price" in warnings
    assert "NEGATIVE_VOLUME:2026-01-05" in warnings
    assert "NON_FINITE_NUMERIC:2026-01-05:amount" in warnings
