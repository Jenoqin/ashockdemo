import math
import numpy as np
import pandas as pd
import pytest
from quantlab.services.analytics import max_drawdown, performance_metrics, technical_frame, score_diagnostics

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
    frame = technical_frame(close_series)
    assert {"ma5", "ma10", "ma20", "ma60", "macd", "macd_signal", "macd_hist", "rsi14", "boll_upper", "boll_mid", "boll_lower"} <= set(frame.columns)

def test_scores_expose_points_and_triggered_rules():
    uptrend_frame = technical_frame(pd.Series(np.linspace(1.0, 2.0, 90)))
    scores = score_diagnostics(uptrend_frame)
    assert 0 <= scores.trend.score <= 100
    assert sum(rule.points for rule in scores.trend.rules if rule.triggered) == scores.trend.score
    assert {"trend", "momentum", "volatility", "drawdown"} == set(scores.model_dump())
