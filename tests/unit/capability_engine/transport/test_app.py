"""Tests for FastAPI application -- Sprint-12. Wave-1.

Covers:
- app builds successfully
- OpenAPI available
- Swagger available
- ReDoc available
- router registration works
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from karsa.capability_engine.transport.http.app import (
    build_fastapi_app,
    APP_TITLE,
    APP_VERSION,
)


@pytest.fixture
def app():
    return build_fastapi_app()


@pytest.fixture
def client(app):
    return TestClient(app)


class TestAppBuilds:
    """Application factory produces valid FastAPI instance."""

    def test_build_returns_fastapi(self, app):
        assert isinstance(app, FastAPI)

    def test_app_title(self, app):
        assert app.title == APP_TITLE

    def test_app_version(self, app):
        assert app.version == APP_VERSION


class TestOpenAPI:
    """OpenAPI schema is available."""

    def test_openapi_json_available(self, client):
        response = client.get("/openapi.json")
        assert response.status_code == 200

    def test_openapi_has_paths(self, client):
        response = client.get("/openapi.json")
        schema = response.json()
        assert "paths" in schema
        assert "/health" in schema["paths"]
        assert "/ready" in schema["paths"]
        assert "/version" in schema["paths"]

    def test_openapi_title(self, client):
        response = client.get("/openapi.json")
        schema = response.json()
        assert schema["info"]["title"] == APP_TITLE
        assert schema["info"]["version"] == APP_VERSION


class TestSwaggerUI:
    """Swagger UI is available."""

    def test_swagger_available(self, client):
        response = client.get("/docs")
        assert response.status_code == 200


class TestReDoc:
    """ReDoc is available."""

    def test_redoc_available(self, client):
        response = client.get("/redoc")
        assert response.status_code == 200


class TestRouterRegistration:
    """Routers are registered correctly."""

    def test_health_router_registered(self, app):
        routes = [r.path for r in app.routes]
        assert "/health" in routes
        assert "/ready" in routes
        assert "/version" in routes

    def test_command_routes_registered(self, app):
        """Wave-2: Command endpoints registered."""
        routes = [r.path for r in app.routes]
        assert "/capabilities/evolutions" in routes
        assert "/capabilities/health" in routes
        assert "/capabilities/projections/rebuild" in routes
        assert "/capabilities/reconcile" in routes
