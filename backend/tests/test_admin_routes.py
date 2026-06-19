from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_saas_dashboard_requires_authentication():
    response = client.get("/api/v1/dashboard/metrics")
    assert response.status_code == 401


def test_agents_requires_authentication():
    response = client.get("/api/v1/agents")
    assert response.status_code == 401


def test_settings_requires_authentication():
    response = client.get("/api/v1/settings")
    assert response.status_code == 401
