"""Tests for GovernanceACL -- Sprint-11. Wave-8.

Scenario 3: Governance Suspension -> GovernanceACL -> GovernanceStatusDTO
Verifies: Capability lifecycle reflected correctly.
"""

import pytest
from datetime import datetime

from karsa.capability_engine.acl.governance_acl import (
    GovernanceACL,
    SUSPENSION_THRESHOLD,
    UNSUSPENSION_THRESHOLD,
)
from karsa.capability_engine.contracts.governance_status_dto import (
    GovernanceStatusDTO,
)


@pytest.fixture
def acl():
    return GovernanceACL()


class TestGovernanceACLTranslation:
    """Governance state translated into public DTO."""

    def test_active_status(self, acl):
        dto = acl.translate_health_score_to_governance_status(
            capability_family_id="gov-family-001",
            capability_urn="urn:test",
            consecutive_low_scores=0,
            consecutive_high_scores=0,
        )

        assert isinstance(dto, GovernanceStatusDTO)
        assert dto.is_suspended is False
        assert dto.lifecycle_state == "ACTIVE"
        assert dto.suspension_reason is None

    def test_suspended_status(self, acl):
        dto = acl.translate_health_score_to_governance_status(
            capability_family_id="gov-family-002",
            capability_urn="urn:test",
            consecutive_low_scores=3,
            consecutive_high_scores=0,
        )

        assert dto.is_suspended is True
        assert dto.lifecycle_state == "SUSPENDED"
        assert "Consecutive low scores" in dto.suspension_reason

    def test_threshold_boundary_below(self, acl):
        dto = acl.translate_health_score_to_governance_status(
            capability_family_id="gov-family-003",
            capability_urn="urn:test",
            consecutive_low_scores=SUSPENSION_THRESHOLD - 1,
            consecutive_high_scores=0,
        )

        assert dto.is_suspended is False

    def test_threshold_boundary_at(self, acl):
        dto = acl.translate_health_score_to_governance_status(
            capability_family_id="gov-family-004",
            capability_urn="urn:test",
            consecutive_low_scores=SUSPENSION_THRESHOLD,
            consecutive_high_scores=0,
        )

        assert dto.is_suspended is True

    def test_translate_from_projection(self, acl):
        projection = {
            "capability_family_id": "gov-family-005",
            "capability_urn": "urn:test",
            "consecutive_low_scores": 2,
            "consecutive_high_scores": 1,
            "last_evaluated_at": datetime.utcnow(),
        }

        dto = acl.translate_from_projection(projection)

        assert isinstance(dto, GovernanceStatusDTO)
        assert dto.capability_family_id == "gov-family-005"
        assert dto.is_suspended is False

    def test_thresholds_exposed_in_dto(self, acl):
        dto = acl.translate_health_score_to_governance_status(
            capability_family_id="gov-family-006",
            capability_urn="urn:test",
            consecutive_low_scores=0,
            consecutive_high_scores=0,
        )

        assert dto.suspension_threshold == SUSPENSION_THRESHOLD
        assert dto.unsuspension_threshold == UNSUSPENSION_THRESHOLD
