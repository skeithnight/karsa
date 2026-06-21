"""Tests for request DTO validation -- Sprint-12. Wave-2.

Covers:
- missing family_id
- missing evaluation_id
- invalid score
- invalid trigger type
- invalid component weight
- invalid payload shape
- 422 returned correctly
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


def _make_client():
    facade = MagicMock(spec=CapabilityCommandFacade)
    facade.record_evolution.return_value = CommandResult(
        success=True, message="ok"
    )
    facade.update_health.return_value = CommandResult(
        success=True, message="ok"
    )
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_command_facade] = lambda: facade
    return TestClient(app)


def _valid_evolution():
    return {
        "capability_family_id": "fam-001",
        "evaluation_id": "eval-001",
        "trigger_type": "REVIEW_FINDING",
        "capability_version_id": "ver-001",
        "capability_urn": "urn:test",
        "evolution_type": "SCORE_ADJUSTMENT",
        "before_score": 0.5,
        "after_score": 0.7,
        "score_change_bps": 2000.0,
        "before_lifecycle_state": "ACTIVE",
        "after_lifecycle_state": "ACTIVE",
        "source_type": "REVIEW",
        "source_id": "urn:test",
        "evaluation_sequence": 1,
    }


def _valid_health():
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
    }


class TestEvolutionRequestValidation:
    """Validate RecordCapabilityEvolutionRequest fields."""

    def test_missing_family_id_returns_422(self):
        client = _make_client()
        payload = _valid_evolution()
        del payload["capability_family_id"]

        response = client.post("/capabilities/evolutions", json=payload)
        assert response.status_code == 422

    def test_empty_family_id_returns_422(self):
        client = _make_client()
        payload = _valid_evolution()
        payload["capability_family_id"] = ""

        response = client.post("/capabilities/evolutions", json=payload)
        assert response.status_code == 422

    def test_missing_evaluation_id_returns_422(self):
        client = _make_client()
        payload = _valid_evolution()
        del payload["evaluation_id"]

        response = client.post("/capabilities/evolutions", json=payload)
        assert response.status_code == 422

    def test_invalid_trigger_type_returns_422(self):
        client = _make_client()
        payload = _valid_evolution()
        payload["trigger_type"] = "INVALID_TYPE"

        response = client.post("/capabilities/evolutions", json=payload)
        assert response.status_code == 422

    def test_score_out_of_range_returns_422(self):
        client = _make_client()
        payload = _valid_evolution()
        payload["before_score"] = 1.5

        response = client.post("/capabilities/evolutions", json=payload)
        assert response.status_code == 422

    def test_negative_score_returns_422(self):
        client = _make_client()
        payload = _valid_evolution()
        payload["after_score"] = -0.1

        response = client.post("/capabilities/evolutions", json=payload)
        assert response.status_code == 422

    def test_negative_sequence_returns_422(self):
        client = _make_client()
        payload = _valid_evolution()
        payload["evaluation_sequence"] = -1

        response = client.post("/capabilities/evolutions", json=payload)
        assert response.status_code == 422

    def test_invalid_evolution_type_returns_422(self):
        client = _make_client()
        payload = _valid_evolution()
        payload["evolution_type"] = "NOT_A_TYPE"

        response = client.post("/capabilities/evolutions", json=payload)
        assert response.status_code == 422

    def test_empty_payload_returns_422(self):
        client = _make_client()
        response = client.post("/capabilities/evolutions", json={})
        assert response.status_code == 422

    def test_wrong_shape_returns_422(self):
        client = _make_client()
        response = client.post(
            "/capabilities/evolutions", json="not a dict"
        )
        assert response.status_code == 422


class TestHealthRequestValidation:
    """Validate UpdateCapabilityHealthRequest fields."""

    def test_missing_family_id_returns_422(self):
        client = _make_client()
        payload = _valid_health()
        del payload["capability_family_id"]

        response = client.post("/capabilities/health", json=payload)
        assert response.status_code == 422

    def test_score_out_of_range_returns_422(self):
        client = _make_client()
        payload = _valid_health()
        payload["score"] = 1.5

        response = client.post("/capabilities/health", json=payload)
        assert response.status_code == 422

    def test_empty_components_returns_422(self):
        client = _make_client()
        payload = _valid_health()
        payload["components"] = []

        response = client.post("/capabilities/health", json=payload)
        assert response.status_code == 422

    def test_component_weight_zero_returns_422(self):
        client = _make_client()
        payload = _valid_health()
        payload["components"][0]["weight"] = 0.0

        response = client.post("/capabilities/health", json=payload)
        assert response.status_code == 422

    def test_component_weight_negative_returns_422(self):
        client = _make_client()
        payload = _valid_health()
        payload["components"][0]["weight"] = -0.1

        response = client.post("/capabilities/health", json=payload)
        assert response.status_code == 422

    def test_component_score_out_of_range_returns_422(self):
        client = _make_client()
        payload = _valid_health()
        payload["components"][0]["component_score"] = 1.5

        response = client.post("/capabilities/health", json=payload)
        assert response.status_code == 422

    def test_missing_components_returns_422(self):
        client = _make_client()
        payload = _valid_health()
        del payload["components"]

        response = client.post("/capabilities/health", json=payload)
        assert response.status_code == 422

    def test_negative_evaluation_sequence_returns_422(self):
        client = _make_client()
        payload = _valid_health()
        payload["evaluation_sequence"] = -1

        response = client.post("/capabilities/health", json=payload)
        assert response.status_code == 422
