"""Tests for health router -- Sprint-12. Wave-1.

Covers:
- GET /health
- GET /ready
- GET /version
"""

import pytest
from fastapi.testclient import TestClient

from karsa.capability_engine.transport.http.app import build_fastapi_app


@pytest.fixture
def client():
    app = build_fastapi_app()
    return TestClient(app)


class TestHealthEndpoint:
    """GET /health returns healthy status."""

    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_healthy(self, client):
        response = client.get("/health")
        assert response.json() == {"status": "healthy"}

    def test_health_content_type(self, client):
        response = client.get("/health")
        assert response.headers["content-type"] == "application/json"


class TestReadyEndpoint:
    """GET /ready returns ready status."""

    def test_ready_returns_200(self, client):
        response = client.get("/ready")
        assert response.status_code == 200

    def test_ready_returns_ready(self, client):
        response = client.get("/ready")
        assert response.json() == {"status": "ready"}


class TestVersionEndpoint:
    """GET /version returns service version."""

    def test_version_returns_200(self, client):
        response = client.get("/version")
        assert response.status_code == 200

    def test_version_returns_service_info(self, client):
        response = client.get("/version")
        data = response.json()
        assert data["service"] == "capability-engine"
        assert data["version"] == "1.0.0"
