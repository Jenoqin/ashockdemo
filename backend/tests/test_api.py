def test_market_daily_wraps_data_and_provenance(client):
    response = client.get("/api/market/512480/daily?start=2026-01-01&end=2026-03-31")
    assert response.status_code == 200
    body = response.json()
    assert body["data"][0]["code"] == "512480.SH"
    assert body["meta"]["sources"] == ["fake"]
    assert body["meta"]["is_demo"] is False

def test_invalid_code_has_stable_error_shape(client):
    response = client.get("/api/instruments/not-a-code")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_INSTRUMENT_CODE"

def test_backtest_rejects_invalid_windows(client):
    response = client.post("/api/backtests/ma-cross", json={"code":"512480.SH", "fast_window":60, "slow_window":20})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_BACKTEST_PARAMETERS"
