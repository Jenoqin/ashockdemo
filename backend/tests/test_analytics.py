import math
import numpy as np
import pandas as pd
import pytest
from datetime import date, datetime, timezone
from quantlab.models import PriceBar
from quantlab.services.analytics import analyze_market, max_drawdown, performance_metrics, technical_frame, score_diagnostics

def test_max_drawdown_uses_running_peak():
    drawdown, duration = max_drawdown(pd.Series([1.0, 1.2, 0.9, 1.1, 0.8]))
    assert drawdown == pytest.approx(-1 / 3)
    assert duration == 3

def test_performance_metrics_annualizes_daily_returns():
    metrics = performance_metrics(pd.Series([0.01, -0.005, 0.02]), risk_free_rate=0.0)
    expected_vol = pd.Series([0.01, -0.005, 0.02]).std(ddof=1) * math.sqrt(252)
    assert metrics.annualized_volatility == pytest.approx(expected_vol)

def test_technical_frame_has_declared_columns():
    close_series = pd.Series(np.linspace(1.0, 2.0, 90))
    frame = technical_frame(close_series, close_series * 1.01, close_series * 0.99)
    assert {"ma5", "ma10", "ma20", "ma60", "macd", "macd_signal", "macd_hist", "rsi14", "boll_upper", "boll_mid", "boll_lower", "atr14_percent"} <= set(frame.columns)
    assert frame["atr14_percent"].dropna().iloc[-1] > 0

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
