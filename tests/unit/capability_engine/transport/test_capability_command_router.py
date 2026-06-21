"""Tests for capability command router -- Sprint-12. Wave-2.

Covers:
- record evolution success
- update health success
- rebuild projections success
- reconcile success
- facade invoked correctly
- error mapping integration
"""

import pytest
from unittest.mock import MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from karsa.capability_engine.integration.capability_command_facade import (
    CapabilityCommandFacade,
    CommandResult,
)
from karsa.capability_engine.transport.http.dependencies import (
    get_command_facade,
)
from karsa.capability_engine.transport.http.routers.capability_command_router import (
    router,
)


def _make_app(facade_mock):
    """Build test app with mocked facade dependency."""
    from karsa.capability_engine.transport.http.middleware.exception_mapper import (
        register_exception_handlers,
    )

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)
    app.dependency_overrides[get_command_facade] = lambda: facade_mock
    return TestClient(app, raise_server_exceptions=False)


def _valid_evolution_payload():
    return {
        "capability_family_id": "fam-001",
        "evaluation_id": "eval-001",
        "trigger_type": "REVIEW_FINDING",
        "capability_version_id": "ver-001",
        "capability_urn": "urn:karsa:capability:ns:fam-001:v1",
        "evolution_type": "SCORE_ADJUSTMENT",
        "before_score": 0.5,
        "after_score": 0.7,
        "score_change_bps": 2000.0,
        "before_lifecycle_state": "ACTIVE",
        "after_lifecycle_state": "ACTIVE",
        "source_type": "REVIEW",
        "source_id": "urn:karsa:review:001",
        "finding_ids": ["f-001"],
        "capability_snapshot": {"version": "v1"},
        "review_snapshot": {"score": 0.7},
        "snapshot_source_versions": {"review": 1},
        "evaluation_sequence": 1,
        "quality_score": 0.8,
    }


def _valid_health_payload():
    return {
        "capability_family_id": "fam-001",
        "evaluation_id": "eval-001",
        "evaluation_sequence": 1,
        "capability_version_id": "ver-001",
        "score": 0.75,
        "components": [
            {
                "component_name": "EXECUTION_QUALITY",
                "component_score": 0.8,
                "weight": 0.25,
                "evaluation_count": 1,
                "confidence": 0.9,
            }
        ],
        "algorithm_version": "v1.0",
    }


class TestRecordEvolutionEndpoint:
    """POST /capabilities/evolutions."""

    def test_success_returns_201(self):
        facade = MagicMock(spec=CapabilityCommandFacade)
        facade.record_evolution.return_value = CommandResult(
            success=True,
            message="Evolution recorded",
            data={"evolution_id": "evo-001"},
        )
        client = _make_app(facade)

        response = client.post(
            "/capabilities/evolutions", json=_valid_evolution_payload()
        )

        assert response.status_code == 201
        body = response.json()
        assert body["success"] is True
        assert body["message"] == "Evolution recorded"
        assert body["data"]["evolution_id"] == "evo-001"
        assert body["request_id"] is not None

    def test_facade_invoked_once(self):
        facade = MagicMock(spec=CapabilityCommandFacade)
        facade.record_evolution.return_value = CommandResult(
            success=True, message="ok"
        )
        client = _make_app(facade)

        client.post("/capabilities/evolutions", json=_valid_evolution_payload())

        facade.record_evolution.assert_called_once()
        call_arg = facade.record_evolution.call_args[0][0]
        assert call_arg.capability_family_id == "fam-001"
        assert call_arg.trigger_type == "REVIEW_FINDING"

    def test_duplicate_returns_success_false(self):
        facade = MagicMock(spec=CapabilityCommandFacade)
        facade.record_evolution.return_value = CommandResult(
            success=False, message="Duplicate or failed"
        )
        client = _make_app(facade)

        response = client.post(
            "/capabilities/evolutions", json=_valid_evolution_payload()
        )

        assert response.status_code == 201
        assert response.json()["success"] is False

    def test_deferred_returns_success_false(self):
        facade = MagicMock(spec=CapabilityCommandFacade)
        facade.record_evolution.return_value = CommandResult(
            success=False, message="Deferred: Quality score below threshold"
        )
        client = _make_app(facade)

        response = client.post(
            "/capabilities/evolutions", json=_valid_evolution_payload()
        )

        assert response.status_code == 201
        assert "Deferred" in response.json()["message"]


class TestUpdateHealthEndpoint:
    """POST /capabilities/health."""

    def test_success_returns_200(self):
        facade = MagicMock(spec=CapabilityCommandFacade)
        facade.update_health.return_value = CommandResult(
            success=True,
            message="Health updated",
            data={"health_score_id": "hs-001", "occ_retries": 0},
        )
        client = _make_app(facade)

        response = client.post(
            "/capabilities/health", json=_valid_health_payload()
        )

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["health_score_id"] == "hs-001"

    def test_facade_invoked_once(self):
        facade = MagicMock(spec=CapabilityCommandFacade)
        facade.update_health.return_value = CommandResult(
            success=True, message="ok"
        )
        client = _make_app(facade)

        client.post("/capabilities/health", json=_valid_health_payload())

        facade.update_health.assert_called_once()

    def test_components_passed_to_facade(self):
        facade = MagicMock(spec=CapabilityCommandFacade)
        facade.update_health.return_value = CommandResult(
            success=True, message="ok"
        )
        client = _make_app(facade)

        client.post("/capabilities/health", json=_valid_health_payload())

        call_arg = facade.update_health.call_args[0][0]
        assert len(call_arg.components) == 1
        assert call_arg.components[0]["component_name"] == "EXECUTION_QUALITY"


class TestRebuildProjectionsEndpoint:
    """POST /capabilities/projections/rebuild."""

    def test_success_returns_200(self):
        facade = MagicMock(spec=CapabilityCommandFacade)
        facade.rebuild_projections.return_value = CommandResult(
            success=True,
            message="Rebuilt 3 projections",
            data={"projections": [{"name": "evolution", "rows": 5}]},
        )
        client = _make_app(facade)

        response = client.post(
            "/capabilities/projections/rebuild", json={}
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_with_checkpoint_fields(self):
        facade = MagicMock(spec=CapabilityCommandFacade)
        facade.rebuild_projections.return_value = CommandResult(
            success=True, message="ok"
        )
        client = _make_app(facade)

        response = client.post(
            "/capabilities/projections/rebuild",
            json={"source_checkpoint": 5, "current_checkpoint": 10},
        )

        assert response.status_code == 200
        call_arg = facade.rebuild_projections.call_args[0][0]
        assert call_arg.source_checkpoint == 5
        assert call_arg.current_checkpoint == 10


class TestReconcileEndpoint:
    """POST /capabilities/reconcile."""

    def test_success_returns_200(self):
        facade = MagicMock(spec=CapabilityCommandFacade)
        facade.reconcile.return_value = CommandResult(
            success=True,
            message="Reconciliation complete",
            data={"orphaned": [], "stale": [], "missing_history": [], "rebuilds": 0},
        )
        client = _make_app(facade)

        response = client.post(
            "/capabilities/reconcile", json={}
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_dry_run_passed_to_facade(self):
        facade = MagicMock(spec=CapabilityCommandFacade)
        facade.reconcile.return_value = CommandResult(
            success=True, message="ok"
        )
        client = _make_app(facade)

        client.post("/capabilities/reconcile", json={"dry_run": True})

        call_arg = facade.reconcile.call_args[0][0]
        assert call_arg.dry_run is True


class TestErrorMappingIntegration:
    """Exception mapper integration with command endpoints."""

    def test_facade_exception_mapped(self):
        facade = MagicMock(spec=CapabilityCommandFacade)
        facade.record_evolution.side_effect = ValueError("bad input")
        client = _make_app(facade)

        response = client.post(
            "/capabilities/evolutions", json=_valid_evolution_payload()
        )

        assert response.status_code == 400
        body = response.json()
        assert body["error_code"] == "VALIDATION_ERROR"
        assert body["message"] == "bad input"


class TestOpenAPIIntegration:
    """Command endpoints appear in OpenAPI schema."""

    def test_all_command_endpoints_in_schema(self):
        facade = MagicMock(spec=CapabilityCommandFacade)
        facade.record_evolution.return_value = CommandResult(
            success=True, message="ok"
        )
        facade.update_health.return_value = CommandResult(
            success=True, message="ok"
        )
        facade.rebuild_projections.return_value = CommandResult(
            success=True, message="ok"
        )
        facade.reconcile.return_value = CommandResult(
            success=True, message="ok"
        )

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_command_facade] = lambda: facade

        from fastapi.testclient import TestClient as TC

        client = TC(app)
        response = client.get("/openapi.json")
        schema = response.json()
        paths = schema["paths"]

        assert "/capabilities/evolutions" in paths
        assert "post" in paths["/capabilities/evolutions"]
        assert "/capabilities/health" in paths
        assert "post" in paths["/capabilities/health"]
        assert "/capabilities/projections/rebuild" in paths
        assert "post" in paths["/capabilities/projections/rebuild"]
        assert "/capabilities/reconcile" in paths
        assert "post" in paths["/capabilities/reconcile"]

    def test_request_schemas_generated(self):
        facade = MagicMock(spec=CapabilityCommandFacade)
        facade.record_evolution.return_value = CommandResult(
            success=True, message="ok"
        )

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_command_facade] = lambda: facade

        from fastapi.testclient import TestClient as TC

        client = TC(app)
        schema = client.get("/openapi.json").json()

        assert "RecordCapabilityEvolutionRequest" in str(schema)
        assert "CommandResultResponse" in str(schema)
