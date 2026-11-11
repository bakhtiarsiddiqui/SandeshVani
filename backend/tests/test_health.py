from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "SandeshVani"
    assert data["environment"] == "local"
    assert data["version"] == "0.1.0"


def test_root_endpoint(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "SandeshVani API is operational" in data["message"]
    assert "/api/v1/health" in data["message"]
