"""Tests for capability query router -- Sprint-12. Wave-3.

Covers:
- health query success
- health query not found
- evolution query success
- timeseries query success
- timeseries version filter
- governance query success
- facade invoked once
- 404 handling
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from karsa.capability_engine.contracts.capability_health_dto import (
    CapabilityHealthDTO,
)
from karsa.capability_engine.contracts.capability_evolution_dto import (
    CapabilityEvolutionDTO,
)
from karsa.capability_engine.contracts.capability_timeseries_dto import (
    CapabilityTimeseriesDTO,
    CapabilityTimeseriesEntryDTO,
)
from karsa.capability_engine.contracts.governance_status_dto import (
    GovernanceStatusDTO,
)
from karsa.capability_engine.integration.capability_query_facade import (
    CapabilityQueryFacade,
)
from karsa.capability_engine.transport.http.middleware.exception_mapper import (
    register_exception_handlers,
)
from karsa.capability_engine.transport.http.dependencies import (
    get_query_facade,
)
from karsa.capability_engine.transport.http.routers.capability_query_router import (
    router,
)


def _make_client(facade_mock):
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)
    app.dependency_overrides[get_query_facade] = lambda: facade_mock
    return TestClient(app, raise_server_exceptions=False)


def _sample_health_dto():
    return CapabilityHealthDTO(
        capability_family_id="fam-001",
        capability_urn="urn:test",
        current_score=0.75,
        algorithm_version="v1.0",
        execution_quality_score=0.8,
        attribution_alignment_score=0.7,
        review_sentiment_score=0.6,
        regime_fitness_score=0.9,
        evaluation_count=5,
        data_completeness=1.0,
        score_trend="IMPROVING",
        lifecycle_state="ACTIVE",
        consecutive_low_scores=0,
        consecutive_high_scores=2,
    )


def _sample_evolution_dto():
    return CapabilityEvolutionDTO(
        capability_family_id="fam-001",
        evaluation_id="eval-001",
        capability_urn="urn:test",
        total_evolutions=3,
        trigger_type_breakdown={"REVIEW_FINDING": 2, "ATTRIBUTION_INSIGHT": 1},
        positive_evolutions=2,
        negative_evolutions=1,
        avg_score_change_bps=500.0,
        last_score_change_bps=1000.0,
        last_evolution_type="SCORE_ADJUSTMENT",
    )


def _sample_timeseries_dto():
    return CapabilityTimeseriesDTO(
        capability_family_id="fam-001",
        entries=(
            CapabilityTimeseriesEntryDTO(
                capability_family_id="fam-001",
                capability_version_id="ver-001",
                evaluation_id="eval-001",
                evaluation_sequence=1,
                score=0.6,
                algorithm_version="v1.0",
                recorded_at=datetime(2025, 1, 1),
            ),
            CapabilityTimeseriesEntryDTO(
                capability_family_id="fam-001",
                capability_version_id="ver-001",
                evaluation_id="eval-002",
                evaluation_sequence=2,
                score=0.75,
                algorithm_version="v1.0",
                recorded_at=datetime(2025, 1, 2),
            ),
        ),
    )


def _sample_governance_dto():
    return GovernanceStatusDTO(
        capability_family_id="fam-001",
        capability_urn="urn:test",
        lifecycle_state="ACTIVE",
        consecutive_low_scores=0,
        consecutive_high_scores=1,
        suspension_threshold=3,
        unsuspension_threshold=2,
        is_suspended=False,
    )


class TestHealthQuery:
    """GET /capabilities/{family_id}/health."""

    def test_success_returns_200(self):
        facade = MagicMock(spec=CapabilityQueryFacade)
        facade.get_health.return_value = _sample_health_dto()
        client = _make_client(facade)

        response = client.get("/capabilities/fam-001/health")

        assert response.status_code == 200
        body = response.json()
        assert body["capability_family_id"] == "fam-001"
        assert body["current_score"] == 0.75
        assert body["score_trend"] == "IMPROVING"

    def test_facade_invoked_once(self):
        facade = MagicMock(spec=CapabilityQueryFacade)
        facade.get_health.return_value = _sample_health_dto()
        client = _make_client(facade)

        client.get("/capabilities/fam-001/health")

        facade.get_health.assert_called_once()
        call_arg = facade.get_health.call_args[0][0]
        assert call_arg.capability_family_id == "fam-001"

    def test_not_found_returns_404(self):
        facade = MagicMock(spec=CapabilityQueryFacade)
        facade.get_health.return_value = None
        client = _make_client(facade)

        response = client.get("/capabilities/nonexistent/health")

        assert response.status_code == 404
        body = response.json()
        assert "not found" in body["detail"].lower()

    def test_component_scores_exposed(self):
        facade = MagicMock(spec=CapabilityQueryFacade)
        facade.get_health.return_value = _sample_health_dto()
        client = _make_client(facade)

        response = client.get("/capabilities/fam-001/health")
        body = response.json()

        assert body["execution_quality_score"] == 0.8
        assert body["attribution_alignment_score"] == 0.7
        assert body["review_sentiment_score"] == 0.6
        assert body["regime_fitness_score"] == 0.9

    def test_governance_counters_exposed(self):
        facade = MagicMock(spec=CapabilityQueryFacade)
        facade.get_health.return_value = _sample_health_dto()
        client = _make_client(facade)

        response = client.get("/capabilities/fam-001/health")
        body = response.json()

        assert body["consecutive_low_scores"] == 0
        assert body["consecutive_high_scores"] == 2


class TestEvolutionQuery:
    """GET /capabilities/{family_id}/evolution."""

    def test_success_returns_200(self):
        facade = MagicMock(spec=CapabilityQueryFacade)
        facade.get_evolution_history.return_value = _sample_evolution_dto()
        client = _make_client(facade)

        response = client.get("/capabilities/fam-001/evolution")

        assert response.status_code == 200
        body = response.json()
        assert body["capability_family_id"] == "fam-001"
        assert body["total_evolutions"] == 3
        assert body["trigger_type_breakdown"]["REVIEW_FINDING"] == 2

    def test_not_found_returns_404(self):
        facade = MagicMock(spec=CapabilityQueryFacade)
        facade.get_evolution_history.return_value = None
        client = _make_client(facade)

        response = client.get("/capabilities/nonexistent/evolution")

        assert response.status_code == 404

    def test_no_internal_fields_leaked(self):
        facade = MagicMock(spec=CapabilityQueryFacade)
        facade.get_evolution_history.return_value = _sample_evolution_dto()
        client = _make_client(facade)

        response = client.get("/capabilities/fam-001/evolution")
        body = response.json()

        # Must not expose internal registry fields
        assert "version_id" not in body
        assert "superseded_by" not in body
        assert "aggregate_version" not in body


class TestTimeseriesQuery:
    """GET /capabilities/{family_id}/timeseries."""

    def test_success_returns_200(self):
        facade = MagicMock(spec=CapabilityQueryFacade)
        facade.get_timeseries.return_value = _sample_timeseries_dto()
        client = _make_client(facade)

        response = client.get("/capabilities/fam-001/timeseries")

        assert response.status_code == 200
        body = response.json()
        assert body["capability_family_id"] == "fam-001"
        assert len(body["entries"]) == 2
        assert body["entries"][0]["evaluation_sequence"] == 1
        assert body["entries"][0]["score"] == 0.6

    def test_version_filter_passed_to_facade(self):
        facade = MagicMock(spec=CapabilityQueryFacade)
        facade.get_timeseries.return_value = _sample_timeseries_dto()
        client = _make_client(facade)

        client.get(
            "/capabilities/fam-001/timeseries?capability_version_id=ver-002"
        )

        call_arg = facade.get_timeseries.call_args[0][0]
        assert call_arg.capability_version_id == "ver-002"

    def test_version_filter_optional(self):
        facade = MagicMock(spec=CapabilityQueryFacade)
        facade.get_timeseries.return_value = _sample_timeseries_dto()
        client = _make_client(facade)

        client.get("/capabilities/fam-001/timeseries")

        call_arg = facade.get_timeseries.call_args[0][0]
        assert call_arg.capability_version_id is None

    def test_not_found_returns_404(self):
        facade = MagicMock(spec=CapabilityQueryFacade)
        facade.get_timeseries.return_value = None
        client = _make_client(facade)

        response = client.get("/capabilities/nonexistent/timeseries")

        assert response.status_code == 404

    def test_empty_entries(self):
        facade = MagicMock(spec=CapabilityQueryFacade)
        facade.get_timeseries.return_value = CapabilityTimeseriesDTO(
            capability_family_id="fam-001", entries=()
        )
        client = _make_client(facade)

        response = client.get("/capabilities/fam-001/timeseries")
        body = response.json()

        assert body["entries"] == []


class TestGovernanceQuery:
    """GET /capabilities/{family_id}/governance."""

    def test_success_returns_200(self):
        facade = MagicMock(spec=CapabilityQueryFacade)
        facade.get_governance_status.return_value = _sample_governance_dto()
        client = _make_client(facade)

        response = client.get("/capabilities/fam-001/governance")

        assert response.status_code == 200
        body = response.json()
        assert body["capability_family_id"] == "fam-001"
        assert body["status"] == "ACTIVE"
        assert body["consecutive_low_scores"] == 0

    def test_suspended_status(self):
        facade = MagicMock(spec=CapabilityQueryFacade)
        facade.get_governance_status.return_value = GovernanceStatusDTO(
            capability_family_id="fam-001",
            capability_urn="urn:test",
            lifecycle_state="SUSPENDED",
            consecutive_low_scores=3,
            consecutive_high_scores=0,
            is_suspended=True,
        )
        client = _make_client(facade)

        response = client.get("/capabilities/fam-001/governance")
        body = response.json()

        assert body["status"] == "SUSPENDED"
        assert body["consecutive_low_scores"] == 3

    def test_not_found_returns_404(self):
        facade = MagicMock(spec=CapabilityQueryFacade)
        facade.get_governance_status.return_value = None
        client = _make_client(facade)

        response = client.get("/capabilities/nonexistent/governance")

        assert response.status_code == 404


class TestOpenAPIIntegration:
    """Query endpoints appear in OpenAPI schema."""

    def test_all_query_endpoints_in_schema(self):
        facade = MagicMock(spec=CapabilityQueryFacade)
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_query_facade] = lambda: facade

        from fastapi.testclient import TestClient as TC

        client = TC(app)
        schema = client.get("/openapi.json").json()
        paths = schema["paths"]

        assert "/capabilities/{family_id}/health" in paths
        assert "get" in paths["/capabilities/{family_id}/health"]
        assert "/capabilities/{family_id}/evolution" in paths
        assert "get" in paths["/capabilities/{family_id}/evolution"]
        assert "/capabilities/{family_id}/timeseries" in paths
        assert "get" in paths["/capabilities/{family_id}/timeseries"]
        assert "/capabilities/{family_id}/governance" in paths
        assert "get" in paths["/capabilities/{family_id}/governance"]

    def test_timeseries_query_parameter(self):
        facade = MagicMock(spec=CapabilityQueryFacade)
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_query_facade] = lambda: facade

        from fastapi.testclient import TestClient as TC

        client = TC(app)
        schema = client.get("/openapi.json").json()
        ts_path = schema["paths"]["/capabilities/{family_id}/timeseries"]
        params = ts_path["get"]["parameters"]
        param_names = [p["name"] for p in params]

        assert "capability_version_id" in param_names

    def test_response_schemas_generated(self):
        facade = MagicMock(spec=CapabilityQueryFacade)
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_query_facade] = lambda: facade

        from fastapi.testclient import TestClient as TC

        client = TC(app)
        schema = client.get("/openapi.json").json()

        assert "CapabilityHealthResponse" in str(schema)
        assert "CapabilityEvolutionResponse" in str(schema)
        assert "CapabilityTimeseriesResponse" in str(schema)
        assert "GovernanceStatusResponse" in str(schema)
