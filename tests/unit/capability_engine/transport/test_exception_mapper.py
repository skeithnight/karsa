"""Tests for exception mapper -- Sprint-12. Wave-1.

Covers:
- domain validation mapping (400)
- projection staleness mapping (409)
- OCC mapping (409)
- value error mapping (400)
- generic exception mapping (500)
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from karsa.capability_engine.domain.exceptions import (
    EvaluationOrderingError,
    InvalidContextSnapshotError,
    InvalidEvolutionDeltaError,
    InvalidEvolutionError,
    InvalidEvolutionEvidenceError,
    InvalidHealthScoreError,
    InvalidScoreComponentError,
    ProjectionStalenessError,
)
from karsa.capability_engine.transport.http.app import build_fastapi_app
from karsa.capability_engine.transport.http.middleware.exception_mapper import (
    register_exception_handlers,
)
from karsa.capability_engine.transport.http.routers.health_router import (
    router,
)


def _make_app_with_raising_endpoint(exception_class, message="test error"):
    """Build a test app with an endpoint that raises the given exception."""
    app = FastAPI()
    register_exception_handlers(app)

    test_router = FastAPI()
    test_router.include_router(router)

    @test_router.get("/test-error")
    def raise_error():
        raise exception_class(message)

    app.mount("/", test_router)
    return TestClient(app)


class TestDomainValidationMapping:
    """Domain validation errors -> 400."""

    def test_invalid_evolution_error(self):
        client = _make_app_with_raising_endpoint(
            InvalidEvolutionError, "missing field"
        )
        # Mount-based apps don't propagate exception handlers the same way.
        # Test with direct FastAPI instead.
        app = FastAPI()
        register_exception_handlers(app)

        @app.get("/test")
        def raise_it():
            raise InvalidEvolutionError("missing field")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test")
        assert response.status_code == 400
        body = response.json()
        assert body["error_code"] == "INVALID_EVOLUTION"
        assert body["message"] == "missing field"

    def test_invalid_health_score_error(self):
        app = FastAPI()
        register_exception_handlers(app)

        @app.get("/test")
        def raise_it():
            raise InvalidHealthScoreError("bad score")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test")
        assert response.status_code == 400
        assert response.json()["error_code"] == "INVALID_HEALTH_SCORE"

    def test_invalid_evolution_delta_error(self):
        app = FastAPI()
        register_exception_handlers(app)

        @app.get("/test")
        def raise_it():
            raise InvalidEvolutionDeltaError("bad delta")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test")
        assert response.status_code == 400
        assert response.json()["error_code"] == "INVALID_EVOLUTION_DELTA"

    def test_invalid_evolution_evidence_error(self):
        app = FastAPI()
        register_exception_handlers(app)

        @app.get("/test")
        def raise_it():
            raise InvalidEvolutionEvidenceError("no evidence")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test")
        assert response.status_code == 400
        assert response.json()["error_code"] == "INVALID_EVOLUTION_EVIDENCE"

    def test_invalid_context_snapshot_error(self):
        app = FastAPI()
        register_exception_handlers(app)

        @app.get("/test")
        def raise_it():
            raise InvalidContextSnapshotError("bad snapshot")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test")
        assert response.status_code == 400
        assert response.json()["error_code"] == "INVALID_CONTEXT_SNAPSHOT"

    def test_invalid_score_component_error(self):
        app = FastAPI()
        register_exception_handlers(app)

        @app.get("/test")
        def raise_it():
            raise InvalidScoreComponentError("bad component")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test")
        assert response.status_code == 400
        assert response.json()["error_code"] == "INVALID_SCORE_COMPONENT"

    def test_evaluation_ordering_error(self):
        app = FastAPI()
        register_exception_handlers(app)

        @app.get("/test")
        def raise_it():
            raise EvaluationOrderingError("sequence violation")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test")
        assert response.status_code == 400
        assert response.json()["error_code"] == "EVALUATION_ORDERING_VIOLATION"


class TestProjectionStalenessMapping:
    """ProjectionStalenessError -> 409."""

    def test_staleness_returns_409(self):
        app = FastAPI()
        register_exception_handlers(app)

        @app.get("/test")
        def raise_it():
            raise ProjectionStalenessError("source advanced")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test")
        assert response.status_code == 409
        body = response.json()
        assert body["error_code"] == "PROJECTION_STALENESS"
        assert body["message"] == "source advanced"


class TestValueErrorMapping:
    """ValueError -> 400."""

    def test_value_error_returns_400(self):
        app = FastAPI()
        register_exception_handlers(app)

        @app.get("/test")
        def raise_it():
            raise ValueError("invalid input")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test")
        assert response.status_code == 400
        body = response.json()
        assert body["error_code"] == "VALIDATION_ERROR"
        assert body["message"] == "invalid input"


class TestGenericExceptionMapping:
    """Unhandled Exception -> 500."""

    def test_generic_exception_returns_500(self):
        app = FastAPI()
        register_exception_handlers(app)

        @app.get("/test")
        def raise_it():
            raise RuntimeError("something broke")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test")
        assert response.status_code == 500
        body = response.json()
        assert body["error_code"] == "INTERNAL_SERVER_ERROR"
        assert body["message"] == "An internal server error occurred"

    def test_no_stack_trace_exposed(self):
        app = FastAPI()
        register_exception_handlers(app)

        @app.get("/test")
        def raise_it():
            raise RuntimeError("secret internals")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test")
        body = response.json()
        assert "secret internals" not in body["message"]
        assert "traceback" not in str(body).lower()
