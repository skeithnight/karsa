"""Tests for query response DTO mapping -- Sprint-12. Wave-3.

Covers:
- DTO serialization
- field exposure
- no internal field leakage
- timestamp serialization
- empty collections
"""

import pytest
from datetime import datetime

from karsa.capability_engine.transport.http.responses.capability_health_response import (
    CapabilityHealthResponse,
)
from karsa.capability_engine.transport.http.responses.capability_evolution_response import (
    CapabilityEvolutionResponse,
)
from karsa.capability_engine.transport.http.responses.capability_timeseries_response import (
    CapabilityTimeseriesResponse,
    TimeseriesEntryResponse,
)
from karsa.capability_engine.transport.http.responses.governance_status_response import (
    GovernanceStatusResponse,
)


class TestHealthResponseDTO:
    """CapabilityHealthResponse serialization."""

    def test_serialization(self):
        dto = CapabilityHealthResponse(
            capability_family_id="fam-001",
            current_score=0.75,
            algorithm_version="v1.0",
        )
        data = dto.model_dump()
        assert data["capability_family_id"] == "fam-001"
        assert data["current_score"] == 0.75

    def test_defaults_populated(self):
        dto = CapabilityHealthResponse(
            capability_family_id="fam-001",
            current_score=0.5,
            algorithm_version="v1.0",
        )
        data = dto.model_dump()
        assert data["score_trend"] == "UNKNOWN"
        assert data["lifecycle_state"] == "ACTIVE"
        assert data["evaluation_count"] == 0
        assert data["data_completeness"] == 0.0
        assert data["consecutive_low_scores"] == 0
        assert data["consecutive_high_scores"] == 0

    def test_no_internal_fields(self):
        dto = CapabilityHealthResponse(
            capability_family_id="fam-001",
            current_score=0.5,
            algorithm_version="v1.0",
        )
        data = dto.model_dump()
        assert "aggregate_version" not in data
        assert "health_score_id" not in data
        assert "last_recorded_sequence" not in data

    def test_timestamp_serialization(self):
        now = datetime(2025, 6, 15, 12, 0, 0)
        dto = CapabilityHealthResponse(
            capability_family_id="fam-001",
            current_score=0.5,
            algorithm_version="v1.0",
            last_evaluated_at=now,
        )
        data = dto.model_dump()
        assert data["last_evaluated_at"] is not None


class TestEvolutionResponseDTO:
    """CapabilityEvolutionResponse serialization."""

    def test_serialization(self):
        dto = CapabilityEvolutionResponse(
            capability_family_id="fam-001",
            evaluation_id="eval-001",
            capability_urn="urn:test",
            total_evolutions=3,
        )
        data = dto.model_dump()
        assert data["total_evolutions"] == 3

    def test_trigger_breakdown(self):
        dto = CapabilityEvolutionResponse(
            capability_family_id="fam-001",
            evaluation_id="eval-001",
            capability_urn="urn:test",
            trigger_type_breakdown={"REVIEW_FINDING": 2},
        )
        data = dto.model_dump()
        assert data["trigger_type_breakdown"]["REVIEW_FINDING"] == 2

    def test_no_internal_fields(self):
        dto = CapabilityEvolutionResponse(
            capability_family_id="fam-001",
            evaluation_id="eval-001",
            capability_urn="urn:test",
        )
        data = dto.model_dump()
        assert "version_id" not in data
        assert "superseded_by" not in data
        assert "evolution_status" not in data


class TestTimeseriesResponseDTO:
    """CapabilityTimeseriesResponse serialization."""

    def test_serialization(self):
        dto = CapabilityTimeseriesResponse(
            capability_family_id="fam-001",
            entries=[
                TimeseriesEntryResponse(
                    evaluation_sequence=1,
                    score=0.6,
                    algorithm_version="v1.0",
                    recorded_at=datetime(2025, 1, 1),
                )
            ],
        )
        data = dto.model_dump()
        assert len(data["entries"]) == 1
        assert data["entries"][0]["score"] == 0.6

    def test_empty_entries(self):
        dto = CapabilityTimeseriesResponse(
            capability_family_id="fam-001",
            entries=[],
        )
        data = dto.model_dump()
        assert data["entries"] == []

    def test_version_id_optional(self):
        entry = TimeseriesEntryResponse(
            evaluation_sequence=1,
            score=0.5,
            algorithm_version="v1.0",
            recorded_at=datetime(2025, 1, 1),
        )
        data = entry.model_dump()
        assert data["capability_version_id"] is None


class TestGovernanceResponseDTO:
    """GovernanceStatusResponse serialization."""

    def test_serialization(self):
        dto = GovernanceStatusResponse(
            capability_family_id="fam-001",
            status="ACTIVE",
        )
        data = dto.model_dump()
        assert data["status"] == "ACTIVE"
        assert data["suspension_threshold"] == 3
        assert data["unsuspension_threshold"] == 2

    def test_suspended_state(self):
        dto = GovernanceStatusResponse(
            capability_family_id="fam-001",
            status="SUSPENDED",
            consecutive_low_scores=3,
        )
        data = dto.model_dump()
        assert data["status"] == "SUSPENDED"
        assert data["consecutive_low_scores"] == 3
