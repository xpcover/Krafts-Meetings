from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_ok():
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "workflow-api"
    assert "database_configured" in response.json()
    assert response.json()["vexa_api_url"] == "http://api-gateway:8000"
