import json
import math
import numpy as np
import pandas as pd
import pytest
from datetime import date, datetime, timedelta, timezone
from quantlab.models import AnalysisSeries, PerformanceMetrics, PriceBar
from quantlab.services.analytics import analyze_market, max_drawdown, performance_metrics, technical_frame, score_diagnostics

def test_max_drawdown_uses_running_peak():
    drawdown, duration = max_drawdown(pd.Series([1.0, 1.2, 0.9, 1.1, 0.8]))
    assert drawdown == pytest.approx(-1 / 3)
    assert duration == 3

def test_performance_metrics_annualizes_daily_returns():
    metrics = performance_metrics(pd.Series([0.01, -0.005, 0.02]), risk_free_rate=0.0)
    expected_vol = pd.Series([0.01, -0.005, 0.02]).std(ddof=1) * math.sqrt(252)
    assert metrics.annualized_volatility == pytest.approx(expected_vol)


@pytest.mark.parametrize("non_finite", [math.nan, math.inf, -math.inf])
def test_analysis_models_convert_non_finite_floats_to_none(non_finite):
    metrics = PerformanceMetrics(sharpe=non_finite)
    series = AnalysisSeries(cumulative_return=[non_finite])

    assert metrics.sharpe is None
    assert series.cumulative_return == [None]

def test_technical_frame_has_declared_columns():
    close_series = pd.Series(np.linspace(1.0, 2.0, 90))
    frame = technical_frame(close_series, close_series * 1.01, close_series * 0.99)
    assert {"ma5", "ma10", "ma20", "ma60", "macd", "macd_signal", "macd_hist", "rsi14", "return_20d", "boll_upper", "boll_mid", "boll_lower", "atr14_percent"} <= set(frame.columns)
    assert frame["atr14_percent"].dropna().iloc[-1] > 0


def test_technical_frame_uses_full_session_offsets():
    close = pd.Series(np.arange(1.0, 27.0))
    frame = technical_frame(close)

    assert frame["return_20d"].iloc[-1] == pytest.approx(26.0 / 6.0 - 1)

    scores = score_diagnostics(frame)
    slope_rule = next(rule for rule in scores.trend.rules if rule.label == "MA20 最近 5 日上行")
    return_rule = next(rule for rule in scores.momentum.rules if rule.label == "近 20 日收益为正")
    assert slope_rule.triggered is True
    assert return_rule.triggered is True

def test_scores_expose_points_and_triggered_rules():
    uptrend_frame = technical_frame(pd.Series(np.linspace(1.0, 2.0, 90)))
    scores = score_diagnostics(uptrend_frame)
    assert 0 <= scores.trend.score <= 100
    assert sum(rule.points for rule in scores.trend.rules if rule.triggered) == scores.trend.score
    assert {"trend", "momentum", "volatility", "drawdown"} == set(scores.model_dump())

def test_analysis_exposes_beginner_metrics_and_linked_series():
    bars = [
        PriceBar(
            code="512480.SH", trade_date=date(2026, 1, day), open=close,
            high=close, low=close, close=close, volume=1000, source="demo",
            fetched_at=datetime.now(timezone.utc),
        )
        for day, close in enumerate([1.0, 1.1, 0.9, 1.2], start=1)
    ]
    result = analyze_market(bars)
    assert result.metrics.period_return == pytest.approx(0.2)
    assert result.metrics.max_drawdown == pytest.approx(0.9 / 1.1 - 1)
    assert len(result.series.dates) == len(bars)
    assert result.series.drawdown[2] == pytest.approx(0.9 / 1.1 - 1)
    assert len(result.series.ma20) == len(bars)
    assert len(result.series.atr14_percent) == len(bars)


def test_analysis_warms_rolling_volatility_without_changing_selected_metrics():
    fetched_at = datetime.now(timezone.utc)
    history = [
        PriceBar(
            code="512480.SH",
            trade_date=date(2026, 1, 1) + timedelta(days=index),
            open=close,
            high=close,
            low=close,
            close=close,
            volume=1000,
            source="demo",
            fetched_at=fetched_at,
        )
        for index, close in enumerate(np.linspace(1.0, 1.4, 40))
    ]
    selected = history[-10:]

    result = analyze_market(selected, history_bars=history)

    assert result.metrics.period_return == pytest.approx(
        selected[-1].close / selected[0].close - 1
    )
    assert len(result.series.rolling_volatility) == len(selected)
    assert all(value is not None for value in result.series.rolling_volatility)


def test_analysis_warms_technical_indicators_for_short_selected_range():
    fetched_at = datetime.now(timezone.utc)
    history = [
        PriceBar(
            code="512480.SH",
            trade_date=date(2026, 1, 1) + timedelta(days=index),
            open=close,
            high=close * 1.01,
            low=close * 0.99,
            close=close,
            volume=1000,
            source="demo",
            fetched_at=fetched_at,
        )
        for index, close in enumerate(np.linspace(1.0, 2.0, 90))
    ]
    selected = history[-5:]

    result = analyze_market(selected, history_bars=history)

    assert len(result.series.ma60) == len(selected)
    assert all(value is not None for value in result.series.ma60)
    assert all(value is not None for value in result.series.rsi14)
    assert all(value is not None for value in result.series.return_20d)
    assert result.diagnostics.trend.score > 0


def test_flat_analysis_uses_null_for_uncomputable_metrics_and_serializes_strictly():
    fetched_at = datetime.now(timezone.utc)
    bars = [
        PriceBar(
            code="600519.SH",
            trade_date=date(2026, 1, 1) + timedelta(days=index),
            open=1.0,
            high=1.0,
            low=1.0,
            close=1.0,
            volume=1000,
            source="demo",
            fetched_at=fetched_at,
        )
        for index in range(80)
    ]

    result = analyze_market(bars, benchmark_bars=bars)

    assert result.series.rolling_sharpe[-20:] == [None] * 20
    assert result.metrics.beta is None
    assert result.metrics.correlation is None
    json.dumps(result.model_dump(mode="json"), allow_nan=False)
