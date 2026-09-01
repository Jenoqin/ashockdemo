from datetime import date, datetime, timedelta, timezone
import pytest
from pydantic import ValidationError
from quantlab.models import BacktestRequest, PriceBar
from quantlab.services.backtest import run_ma_cross

def crossing_bars():
    closes = [3.0, 2.0, 2.0, 4.0, 5.0, 2.0, 1.0, 1.0]
    fetched = datetime(2026, 8, 8, tzinfo=timezone.utc)
    return [
        PriceBar(
            code="512480.SH", trade_date=date(2026, 1, 1) + timedelta(days=index),
            open=close, high=close + 0.1, low=close - 0.1, close=close,
            volume=1000, amount=1000, source="fake", fetched_at=fetched,
        )
        for index, close in enumerate(closes)
    ]

def test_cross_signal_executes_at_next_open():
    bars = crossing_bars()
    result = run_ma_cross(
        BacktestRequest(code="512480.SH", fast_window=2, slow_window=3, fee_rate=0, slippage_rate=0, initial_cash=10_000),
        bars,
    )
    first_trade = result.trades[0]
    assert first_trade.signal_date == bars[3].trade_date
    assert first_trade.execution_date == bars[4].trade_date
    assert first_trade.execution_price == bars[4].open

def test_round_trip_deducts_fee_and_slippage():
    bars = crossing_bars()
    free = run_ma_cross(BacktestRequest(code="512480.SH", fast_window=2, slow_window=3, fee_rate=0, slippage_rate=0, initial_cash=10000), bars)
    costly = run_ma_cross(BacktestRequest(code="512480.SH", fast_window=2, slow_window=3, fee_rate=0.001, slippage_rate=0.001, initial_cash=10000), bars)
    assert costly.metrics.final_equity < free.metrics.final_equity

def test_rejects_fast_window_not_less_than_slow_window():
    with pytest.raises(ValidationError, match="fast_window must be less than slow_window"):
        BacktestRequest(
            code="512480.SH",
            fast_window=20,
            slow_window=20,
            fee_rate=0,
            slippage_rate=0,
            initial_cash=10000,
        )


@pytest.mark.parametrize(
    "updates",
    [
        {"fast_window": 0},
        {"slow_window": -1},
        {"fast_window": 3, "slow_window": 2},
        {"fee_rate": -0.0001},
        {"fee_rate": 0.100001},
        {"slippage_rate": -0.0001},
        {"slippage_rate": 1.0},
        {"initial_cash": 0},
        {"initial_cash": -1},
        {"initial_cash": float("nan")},
        {"initial_cash": float("inf")},
        {"start": date(2026, 2, 1), "end": date(2026, 1, 1)},
    ],
)
def test_backtest_request_rejects_invalid_parameters(updates):
    with pytest.raises(ValidationError):
        BacktestRequest(code="512480.SH", **updates)


def test_backtest_request_accepts_documented_boundaries():
    request = BacktestRequest(
        code="512480.SH",
        start=date(2026, 1, 1),
        end=date(2026, 1, 1),
        fast_window=1,
        slow_window=2,
        fee_rate=0.1,
        slippage_rate=0.999,
        initial_cash=0.01,
    )

    assert request.fast_window == 1
    assert request.fee_rate == 0.1
    assert request.slippage_rate == 0.999
    assert request.initial_cash == 0.01


@pytest.mark.parametrize(
    "updates",
    [
        {"fast_window": 0},
        {"slow_window": -1},
        {"fast_window": 60, "slow_window": 20},
        {"fee_rate": -0.1},
        {"slippage_rate": 1.0},
        {"initial_cash": 0},
        {"start": date(2026, 2, 1), "end": date(2026, 1, 1)},
    ],
)
def test_service_revalidates_constructed_requests(updates):
    request = BacktestRequest.model_construct(code="512480.SH", **updates)

    with pytest.raises(ValueError):
        run_ma_cross(request, crossing_bars())
