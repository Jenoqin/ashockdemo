from datetime import date, datetime, timedelta, timezone
import pytest
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
    with pytest.raises(ValueError, match="快线周期必须小于慢线周期"):
        run_ma_cross(BacktestRequest(code="512480.SH", fast_window=20, slow_window=20, fee_rate=0, slippage_rate=0, initial_cash=10000), crossing_bars())
