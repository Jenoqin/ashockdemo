from fastapi.testclient import TestClient
from quantlab.main import create_app

def test_health_reports_service_status():
    response = TestClient(create_app()).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "quantlab-api",
        "provider": "Tushare Pro",
    }
