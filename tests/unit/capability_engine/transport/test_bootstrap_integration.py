"""Tests for bootstrap integration -- Sprint-12. Wave-4.

Covers:
- build_fastapi_app() produces valid app
- all routers registered
- dependencies resolved
- command facade injected
- query facade injected
- OpenAPI generation works
- routers use Depends() (no construction logic)
"""

import pytest
from unittest.mock import MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from karsa.capability_engine.integration.capability_engine_bootstrap import (
    CapabilityEngineContainer,
    bootstrap,
    build_fastapi_app,
)
from karsa.capability_engine.transport.http.dependencies import (
    get_command_facade,
    get_query_facade,
    clear_dependencies,
)


@pytest.fixture(autouse=True)
def cleanup():
    """Clear dependencies after each test."""
    yield
    clear_dependencies()


class TestBootstrapBuildsApp:
    """build_fastapi_app() produces a fully wired FastAPI instance."""

    def test_returns_fastapi_and_container(self):
        app, container = build_fastapi_app()

        assert isinstance(app, FastAPI)
        assert isinstance(container, CapabilityEngineContainer)

    def test_command_facade_on_container(self):
        _, container = build_fastapi_app()

        assert container.command_facade is not None

    def test_query_facade_on_container(self):
        _, container = build_fastapi_app()

        assert container.query_facade is not None

    def test_dependencies_wired(self):
        app, container = build_fastapi_app()

        # Dependency providers should return the container's facades
        assert get_command_facade() is container.command_facade
        assert get_query_facade() is container.query_facade


class TestRouterRegistration:
    """All routers registered on the app."""

    def test_health_routes_registered(self):
        app, _ = build_fastapi_app()
        routes = [r.path for r in app.routes]

        assert "/health" in routes
        assert "/ready" in routes
        assert "/version" in routes

    def test_command_routes_registered(self):
        app, _ = build_fastapi_app()
        routes = [r.path for r in app.routes]

        assert "/capabilities/evolutions" in routes
        assert "/capabilities/health" in routes
        assert "/capabilities/projections/rebuild" in routes
        assert "/capabilities/reconcile" in routes

    def test_query_routes_registered(self):
        app, _ = build_fastapi_app()
        routes = [r.path for r in app.routes]

        assert "/capabilities/{family_id}/health" in routes
        assert "/capabilities/{family_id}/evolution" in routes
        assert "/capabilities/{family_id}/timeseries" in routes
        assert "/capabilities/{family_id}/governance" in routes


class TestDependencyInjection:
    """Facades injected via Depends(), not constructed in routers."""

    def test_command_facade_resolved_via_depends(self):
        app, container = build_fastapi_app()
        client = TestClient(app)

        # The dependency provider should resolve to the container's facade
        assert get_command_facade() is container.command_facade

    def test_query_facade_resolved_via_depends(self):
        app, container = build_fastapi_app()
        client = TestClient(app)

        assert get_query_facade() is container.query_facade

    def test_health_endpoint_works_with_bootstrap(self):
        app, _ = build_fastapi_app()
        client = TestClient(app)

        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestOpenAPIFromBootstrap:
    """OpenAPI generation works with bootstrap-wired app."""

    def test_openapi_available(self):
        app, _ = build_fastapi_app()
        client = TestClient(app)

        response = client.get("/openapi.json")
        assert response.status_code == 200

    def test_all_endpoints_in_schema(self):
        app, _ = build_fastapi_app()
        client = TestClient(app)

        schema = client.get("/openapi.json").json()
        paths = schema["paths"]

        # System
        assert "/health" in paths
        # Commands
        assert "/capabilities/evolutions" in paths
        assert "/capabilities/health" in paths
        # Queries
        assert "/capabilities/{family_id}/health" in paths
        assert "/capabilities/{family_id}/evolution" in paths
        assert "/capabilities/{family_id}/timeseries" in paths
        assert "/capabilities/{family_id}/governance" in paths

    def test_swagger_available(self):
        app, _ = build_fastapi_app()
        client = TestClient(app)

        response = client.get("/docs")
        assert response.status_code == 200

    def test_redoc_available(self):
        app, _ = build_fastapi_app()
        client = TestClient(app)

        response = client.get("/redoc")
        assert response.status_code == 200


class TestBoundaryCompliance:
    """Routers have no construction logic. Bootstrap owns wiring."""

    def test_router_modules_do_not_import_bootstrap(self):
        """Routers must not import bootstrap or construct facades."""
        import karsa.capability_engine.transport.http.routers.capability_command_router as cmd_mod
        import karsa.capability_engine.transport.http.routers.capability_query_router as qry_mod

        cmd_source = open(cmd_mod.__file__).read()
        qry_source = open(qry_mod.__file__).read()

        assert "bootstrap" not in cmd_source.lower()
        assert "bootstrap" not in qry_source.lower()
        assert "InMemory" not in cmd_source
        assert "InMemory" not in qry_source

    def test_routers_use_depends(self):
        """Routers use Depends() for facade injection."""
        import karsa.capability_engine.transport.http.routers.capability_command_router as cmd_mod
        import karsa.capability_engine.transport.http.routers.capability_query_router as qry_mod

        cmd_source = open(cmd_mod.__file__).read()
        qry_source = open(qry_mod.__file__).read()

        assert "Depends(get_command_facade)" in cmd_source
        assert "Depends(get_query_facade)" in qry_source
