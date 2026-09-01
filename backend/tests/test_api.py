import json
from datetime import datetime, timedelta, timezone

import pytest

from quantlab.models import PriceBar
from quantlab.providers.base import ProviderError


def test_market_daily_wraps_data_and_provenance(client):
    response = client.get("/api/market/512480/daily?start=2026-01-01&end=2026-03-31")
    assert response.status_code == 200
    body = response.json()
    assert body["data"][0]["code"] == "512480.SH"
    assert body["meta"]["sources"] == ["fake"]
    assert body["meta"]["data_end_date"] == "2026-03-31"


def test_short_analysis_range_has_warmed_rolling_volatility(client):
    response = client.get(
        "/api/analysis/512480.SH?start=2026-01-01&end=2026-01-31"
    )
    assert response.status_code == 200
    series = response.json()["data"]["series"]
    assert len(series["dates"]) == 31
    assert all(value is not None for value in series["rolling_volatility"])


def test_flat_analysis_returns_null_for_uncomputable_values(client, monkeypatch):
    def get_flat_daily(code, start, end):
        fetched_at = datetime(2026, 8, 8, tzinfo=timezone.utc)
        return [
            PriceBar(
                code=code,
                trade_date=start + timedelta(days=index),
                open=1.0,
                high=1.0,
                low=1.0,
                close=1.0,
                volume=1000,
                source="fake",
                fetched_at=fetched_at,
            )
            for index in range((end - start).days + 1)
        ]

    monkeypatch.setattr(
        client.app.state.fake_provider,
        "get_daily",
        get_flat_daily,
    )

    response = client.get(
        "/api/analysis/600519.SH?start=2026-01-01&end=2026-03-31"
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["series"]["rolling_sharpe"][-1] is None
    json.dumps(data, allow_nan=False)


def test_manual_refresh_returns_real_status_and_provenance(client):
    response = client.post("/api/data/600519.SH/refresh")

    assert response.status_code == 200
    body = response.json()
    assert body["data"] == {"refreshed": True, "status": "refreshed"}
    assert body["meta"]["sources"] == ["fake"]
    assert body["meta"]["cache_hit"] is False
    assert body["meta"]["data_end_date"] is not None
    assert body["meta"]["fetched_at"] == "2026-08-08T00:00:00+00:00"
    assert "STALE_CACHE" not in body["meta"]["warnings"]


def test_manual_refresh_reports_stale_cache_fallback(client, monkeypatch):
    assert client.post("/api/data/600519.SH/refresh").status_code == 200

    def fail_daily(code, start, end):
        raise ProviderError("fake", code, "down")

    monkeypatch.setattr(client.app.state.fake_provider, "get_daily", fail_daily)

    response = client.post("/api/data/600519.SH/refresh")

    assert response.status_code == 200
    body = response.json()
    assert body["data"] == {"refreshed": False, "status": "stale_cache"}
    assert body["meta"]["cache_hit"] is True
    assert body["meta"]["sources"] == ["fake"]
    assert body["meta"]["data_end_date"] is not None
    assert body["meta"]["fetched_at"] == "2026-08-08T00:00:00+00:00"
    assert "STALE_CACHE" in body["meta"]["warnings"]


def test_manual_refresh_without_cache_uses_stable_error_shape(client, monkeypatch):
    def fail_daily(code, start, end):
        raise ProviderError("fake", code, "down")

    monkeypatch.setattr(client.app.state.fake_provider, "get_daily", fail_daily)

    response = client.post("/api/data/600520.SH/refresh")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "DATA_UNAVAILABLE"


def test_research_endpoint_returns_one_complete_bundle_without_profile_fetch(client):
    response = client.get(
        "/api/research/512480.SH?start=2026-01-01&end=2026-01-31"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["instrument"]["code"] == "512480.SH"
    assert len(body["data"]["market"]) == 31
    assert body["data"]["analysis"]["metrics"]["correlation"] is not None
    assert body["meta"]["sources"] == ["fake"]
    assert client.app.state.fake_provider.profile_calls == 0

def test_invalid_code_has_stable_error_shape(client):
    response = client.get("/api/instruments/not-a-code")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_INSTRUMENT_CODE"

def test_equity_instrument_exposes_formal_company_name(client):
    response = client.get("/api/instruments/600519.SH")
    assert response.status_code == 200
    assert response.json()["data"]["full_name"] == "贵州茅台酒股份有限公司"

def test_instrument_profile_has_provenance(client):
    response = client.get("/api/instruments/512480.SH/profile")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["asset_type"] == "etf"
    assert body["meta"]["sources"] == ["fake"]

def test_backtest_rejects_invalid_windows(client):
    response = client.post("/api/backtests/ma-cross", json={"code":"512480.SH", "fast_window":60, "slow_window":20})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_BACKTEST_PARAMETERS"


@pytest.mark.parametrize(
    "invalid_parameters",
    [
        {"fast_window": 0},
        {"slow_window": -1},
        {"fast_window": 20, "slow_window": 20},
        {"fee_rate": -0.0001},
        {"fee_rate": 0.100001},
        {"slippage_rate": -0.0001},
        {"slippage_rate": 1.0},
        {"initial_cash": 0},
        {"initial_cash": -1},
        {"start": "2026-02-01", "end": "2026-01-01"},
    ],
)
def test_backtest_rejects_invalid_request_fields(client, invalid_parameters):
    response = client.post(
        "/api/backtests/ma-cross",
        json={"code": "512480.SH", **invalid_parameters},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_BACKTEST_PARAMETERS"


@pytest.mark.parametrize(
    ("field", "non_finite"),
    [
        ("initial_cash", "NaN"),
        ("initial_cash", "Infinity"),
        ("fee_rate", "NaN"),
        ("slippage_rate", "Infinity"),
    ],
)
def test_backtest_rejects_non_finite_numbers(client, field, non_finite):
    response = client.post(
        "/api/backtests/ma-cross",
        content=f'{{"code":"512480.SH","{field}":{non_finite}}}',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_BACKTEST_PARAMETERS"
