"""Tests for RegistryACL -- Sprint-11. Wave-8.

Verifies: Registry internals not leaked to external contexts.
"""

import pytest

from karsa.capability_engine.acl.registry_acl import RegistryACL
from karsa.capability_engine.contracts.capability_evolution_dto import (
    CapabilityEvolutionDTO,
)


@pytest.fixture
def acl():
    return RegistryACL()


class TestRegistryACLTranslation:
    """Registry state translated into public DTOs."""

    def test_translate_evolution_to_dto(self, acl):
        data = {
            "capability_family_id": "reg-family-001",
            "evaluation_id": "reg-eval-001",
            "capability_urn": "urn:test",
            "total_evolutions": 3,
            "trigger_type_breakdown": {
                "REVIEW_FINDING": 2,
                "ATTRIBUTION_INSIGHT": 1,
            },
            "positive_evolutions": 2,
            "negative_evolutions": 1,
            "avg_score_change_bps": 500.0,
            "last_score_change_bps": 1000.0,
            "last_evolution_type": "SCORE_ADJUSTMENT",
            "last_evaluated_at": None,
        }

        dto = acl.translate_evolution_to_dto(data)

        assert isinstance(dto, CapabilityEvolutionDTO)
        assert dto.capability_family_id == "reg-family-001"
        assert dto.total_evolutions == 3
        assert dto.trigger_type_breakdown["REVIEW_FINDING"] == 2

    def test_translate_registry_entry(self, acl):
        entry = {
            "version_id": "vreg-001",
            "capability_family_id": "reg-family-002",
            "evaluation_id": "reg-eval-002",
            "trigger_type": "REVIEW_FINDING",
            "evolution_id": "evo-001",
            "evolution_status": "CANONICAL",
            "superseded_by": None,
        }

        result = acl.translate_registry_entry(entry)

        # Internal fields stripped
        assert "version_id" not in result
        assert "superseded_by" not in result

        # Public fields exposed
        assert result["capability_family_id"] == "reg-family-002"
        assert result["evolution_status"] == "CANONICAL"

    def test_translate_with_evolution_data(self, acl):
        entry = {
            "capability_family_id": "reg-family-003",
            "evaluation_id": "reg-eval-003",
            "trigger_type": "REVIEW_FINDING",
            "evolution_id": "evo-002",
            "evolution_status": "CANONICAL",
        }
        evolution_data = {
            "total_evolutions": 1,
            "positive_evolutions": 1,
        }

        result = acl.translate_registry_entry(entry, evolution_data)

        assert "evolution_summary" in result
        assert result["evolution_summary"]["total_evolutions"] == 1
