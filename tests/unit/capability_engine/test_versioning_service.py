"""Tests for CapabilityEvolutionVersioningService -- Sprint-11. ADR-133.

Covers:
- canonical lookup
- supersede workflow
- trigger-type governance
"""

import pytest
from datetime import datetime

from karsa.capability_engine.application.capability_evolution_versioning_service import (
    CapabilityEvolutionVersioningService,
)
from karsa.capability_engine.domain.aggregates.capability_evolution import (
    CapabilityEvolution,
)
from karsa.capability_engine.domain.events.capability_events import (
    CapabilityEvolutionCanonicalChangedEvent,
)
from karsa.capability_engine.domain.exceptions import InvalidEvolutionError
from karsa.capability_engine.domain.value_objects.enums import (
    EvolutionStatus,
    EvolutionTriggerType,
    EvolutionType,
)
from karsa.capability_engine.domain.value_objects.evolution_context_snapshot import (
    EvolutionContextSnapshot,
    _compute_snapshot_hash,
)
from karsa.capability_engine.domain.value_objects.evolution_delta import (
    EvolutionDelta,
)
from karsa.capability_engine.domain.value_objects.evolution_evidence import (
    EvolutionEvidence,
)
from karsa.capability_engine.infrastructure.persistence.in_memory_repositories import (
    InMemoryCapabilityEvolutionRepository,
    InMemoryEvolutionVersionRegistryRepository,
    InMemoryOutboxRepository,
)
from karsa.capability_engine.infrastructure.repositories.capability_evolution_version_registry_repository import (
    EvolutionVersionRegistryEntry,
)


# --- Helpers ---

def _make_snapshot():
    cap = {"version": "v1", "status": "ACTIVE"}
    rev = {"score": 0.8}
    data = {
        "capability": cap,
        "review": rev,
        "attribution": None,
        "execution": None,
        "source_versions": {"review_projection": 1},
    }
    return EvolutionContextSnapshot(
        capability_snapshot=cap,
        review_snapshot=rev,
        snapshot_hash=_compute_snapshot_hash(data),
        snapshot_source_versions={"review_projection": 1},
    )


def _make_evolution(evolution_id="urn:karsa:capability:evolution:test001", **overrides):
    defaults = dict(
        evolution_id=evolution_id,
        capability_family_id="family-uuid-001",
        evaluation_id="eval-uuid-001",
        trigger_type=EvolutionTriggerType.REVIEW_FINDING.value,
        capability_version_id="ver-uuid-001",
        capability_urn="urn:karsa:capability:ns:test:v1",
        evolution_type=EvolutionType.SCORE_ADJUSTMENT.value,
        delta=EvolutionDelta(
            before_score=0.5,
            after_score=0.7,
            score_change_bps=2000.0,
            before_lifecycle_state="ACTIVE",
            after_lifecycle_state="ACTIVE",
            before_contract_fingerprint=None,
            after_contract_fingerprint=None,
        ),
        evidence=EvolutionEvidence(
            source_type="REVIEW",
            source_id="urn:karsa:review:abc",
            finding_ids=["f1"],
        ),
        context_snapshot=_make_snapshot(),
        evaluation_sequence=1,
    )
    defaults.update(overrides)
    return CapabilityEvolution(**defaults)


def _make_service():
    evolution_repo = InMemoryCapabilityEvolutionRepository()
    version_registry = InMemoryEvolutionVersionRegistryRepository()
    outbox_repo = InMemoryOutboxRepository()

    service = CapabilityEvolutionVersioningService(
        evolution_repo=evolution_repo,
        version_registry=version_registry,
        outbox_repo=outbox_repo,
    )
    return service, evolution_repo, version_registry, outbox_repo


# --- Tests: Canonical Lookup ---

class TestCanonicalLookup:
    """ADR-133: Exactly one CANONICAL per (family, eval, trigger)."""

    def test_get_canonical_returns_entry(self):
        service, evolution_repo, version_registry, _ = _make_service()
        evolution = _make_evolution()
        evolution_repo.save(evolution)

        entry = EvolutionVersionRegistryEntry(
            version_id="vreg-001",
            capability_family_id="family-uuid-001",
            evaluation_id="eval-uuid-001",
            trigger_type="REVIEW_FINDING",
            evolution_id=evolution.evolution_id,
            evolution_status=EvolutionStatus.CANONICAL.value,
        )
        version_registry.save(entry)

        result = service.get_canonical(
            "family-uuid-001", "eval-uuid-001", "REVIEW_FINDING"
        )
        assert result is not None
        assert result.evolution_id == evolution.evolution_id
        assert result.evolution_status == EvolutionStatus.CANONICAL.value

    def test_get_canonical_returns_none_for_missing(self):
        service, _, _, _ = _make_service()
        result = service.get_canonical("nonexistent", "eval", "REVIEW_FINDING")
        assert result is None

    def test_get_canonical_returns_none_for_superseded(self):
        """Superseded entries are not canonical."""
        service, _, version_registry, _ = _make_service()

        entry = EvolutionVersionRegistryEntry(
            version_id="vreg-001",
            capability_family_id="family-uuid-001",
            evaluation_id="eval-uuid-001",
            trigger_type="REVIEW_FINDING",
            evolution_id="evo-001",
            evolution_status=EvolutionStatus.SUPERSEDED.value,
        )
        version_registry.save(entry)

        result = service.get_canonical(
            "family-uuid-001", "eval-uuid-001", "REVIEW_FINDING"
        )
        assert result is None


# --- Tests: Supersede Workflow ---

class TestSupersedeWorkflow:
    """ADR-133: Canonical governance via supersession."""

    def test_supersede_marks_previous_as_superseded(self):
        service, evolution_repo, version_registry, _ = _make_service()

        evo1 = _make_evolution(evolution_id="evo-001")
        evo2 = _make_evolution(
            evolution_id="evo-002",
            evaluation_id="eval-uuid-002",
            evaluation_sequence=2,
        )
        evolution_repo.save(evo1)
        evolution_repo.save(evo2)

        # Set evo1 as canonical for eval-001
        entry = EvolutionVersionRegistryEntry(
            version_id="vreg-001",
            capability_family_id="family-uuid-001",
            evaluation_id="eval-uuid-001",
            trigger_type="REVIEW_FINDING",
            evolution_id="evo-001",
            evolution_status=EvolutionStatus.CANONICAL.value,
        )
        version_registry.save(entry)

        # Supersede eval-001's canonical with evo-002 (from eval-002)
        event = service.supersede_previous(
            "family-uuid-001", "eval-uuid-001", "REVIEW_FINDING",
            "evo-002", changed_by="test-user"
        )

        assert event is not None
        assert event.previous_evolution_id == "evo-001"
        assert event.new_evolution_id == "evo-002"
        assert event.changed_by == "test-user"

    def test_supersede_creates_new_canonical(self):
        service, evolution_repo, version_registry, _ = _make_service()

        evo1 = _make_evolution(evolution_id="evo-001")
        evo2 = _make_evolution(
            evolution_id="evo-002",
            evaluation_id="eval-uuid-002",
            evaluation_sequence=2,
        )
        evolution_repo.save(evo1)
        evolution_repo.save(evo2)

        entry = EvolutionVersionRegistryEntry(
            version_id="vreg-001",
            capability_family_id="family-uuid-001",
            evaluation_id="eval-uuid-001",
            trigger_type="REVIEW_FINDING",
            evolution_id="evo-001",
            evolution_status=EvolutionStatus.CANONICAL.value,
        )
        version_registry.save(entry)

        service.supersede_previous(
            "family-uuid-001", "eval-uuid-001", "REVIEW_FINDING", "evo-002"
        )

        canonical = version_registry.get_canonical(
            "family-uuid-001", "eval-uuid-001", "REVIEW_FINDING"
        )
        assert canonical is not None
        assert canonical.evolution_id == "evo-002"

    def test_supersede_first_evolution_has_no_previous(self):
        service, evolution_repo, _, _ = _make_service()

        evo = _make_evolution(evolution_id="evo-001")
        evolution_repo.save(evo)

        event = service.supersede_previous(
            "family-uuid-001", "eval-uuid-001", "REVIEW_FINDING", "evo-001"
        )

        assert event is not None
        assert event.previous_evolution_id is None
        assert event.new_evolution_id == "evo-001"

    def test_supersede_rejects_missing_evolution(self):
        service, _, _, _ = _make_service()

        with pytest.raises(InvalidEvolutionError, match="not found"):
            service.supersede_previous(
                "family-uuid-001", "eval-uuid-001", "REVIEW_FINDING",
                "nonexistent-evo"
            )

    def test_supersede_emits_outbox_event(self):
        service, evolution_repo, _, outbox_repo = _make_service()

        evo = _make_evolution(evolution_id="evo-001")
        evolution_repo.save(evo)

        service.supersede_previous(
            "family-uuid-001", "eval-uuid-001", "REVIEW_FINDING", "evo-001"
        )

        pending = outbox_repo.get_pending()
        assert len(pending) == 1
        assert pending[0].event_type == "CapabilityEvolutionCanonicalChangedEvent"


# --- Tests: Promote Canonical ---

class TestPromoteCanonical:
    """ADR-133: promote_canonical is the primary governance entry point."""

    def test_promote_sets_canonical(self):
        service, evolution_repo, version_registry, _ = _make_service()

        evo = _make_evolution(evolution_id="evo-001")
        evolution_repo.save(evo)

        event = service.promote_canonical(
            "family-uuid-001", "eval-uuid-001", "REVIEW_FINDING", "evo-001"
        )

        assert isinstance(event, CapabilityEvolutionCanonicalChangedEvent)
        assert event.new_evolution_id == "evo-001"
        assert event.previous_evolution_id is None

    def test_promote_supersedes_existing(self):
        service, evolution_repo, version_registry, _ = _make_service()

        evo1 = _make_evolution(evolution_id="evo-001")
        evo2 = _make_evolution(
            evolution_id="evo-002",
            evaluation_id="eval-uuid-002",
            evaluation_sequence=2,
        )
        evolution_repo.save(evo1)
        evolution_repo.save(evo2)

        # First promote
        service.promote_canonical(
            "family-uuid-001", "eval-uuid-001", "REVIEW_FINDING", "evo-001"
        )

        # Second promote -- should supersede first
        event = service.promote_canonical(
            "family-uuid-001", "eval-uuid-001", "REVIEW_FINDING", "evo-002"
        )

        assert event.previous_evolution_id == "evo-001"
        assert event.new_evolution_id == "evo-002"

    def test_promote_rejects_invalid_trigger_type(self):
        service, evolution_repo, _, _ = _make_service()

        evo = _make_evolution(evolution_id="evo-001")
        evolution_repo.save(evo)

        with pytest.raises(InvalidEvolutionError, match="Invalid trigger_type"):
            service.promote_canonical(
                "family-uuid-001", "eval-uuid-001", "INVALID_TRIGGER", "evo-001"
            )

    def test_promote_rejects_missing_evolution(self):
        service, _, _, _ = _make_service()

        with pytest.raises(InvalidEvolutionError, match="not found"):
            service.promote_canonical(
                "family-uuid-001", "eval-uuid-001", "REVIEW_FINDING",
                "nonexistent-evo"
            )

    def test_promote_emits_canonical_changed_event(self):
        service, evolution_repo, _, outbox_repo = _make_service()

        evo = _make_evolution(evolution_id="evo-001")
        evolution_repo.save(evo)

        event = service.promote_canonical(
            "family-uuid-001", "eval-uuid-001", "REVIEW_FINDING", "evo-001",
            changed_by="admin"
        )

        assert event.changed_by == "admin"
        assert event.trigger_type == "REVIEW_FINDING"

        pending = outbox_repo.get_pending()
        assert len(pending) == 1


# --- Tests: Trigger-Type Governance ---

class TestTriggerTypeGovernance:
    """ADR-133: Trigger types govern separate canonical chains."""

    def test_different_triggers_independent_canonicals(self):
        service, evolution_repo, version_registry, _ = _make_service()

        evo_review = _make_evolution(
            evolution_id="evo-review",
            trigger_type=EvolutionTriggerType.REVIEW_FINDING.value,
        )
        evo_attribution = _make_evolution(
            evolution_id="evo-attribution",
            trigger_type=EvolutionTriggerType.ATTRIBUTION_INSIGHT.value,
        )
        evolution_repo.save(evo_review)
        evolution_repo.save(evo_attribution)

        service.promote_canonical(
            "family-uuid-001", "eval-uuid-001",
            EvolutionTriggerType.REVIEW_FINDING.value, "evo-review"
        )
        service.promote_canonical(
            "family-uuid-001", "eval-uuid-001",
            EvolutionTriggerType.ATTRIBUTION_INSIGHT.value, "evo-attribution"
        )

        c1 = version_registry.get_canonical(
            "family-uuid-001", "eval-uuid-001",
            EvolutionTriggerType.REVIEW_FINDING.value,
        )
        c2 = version_registry.get_canonical(
            "family-uuid-001", "eval-uuid-001",
            EvolutionTriggerType.ATTRIBUTION_INSIGHT.value,
        )

        assert c1.evolution_id == "evo-review"
        assert c2.evolution_id == "evo-attribution"

    def test_all_four_trigger_types_supported(self):
        """All four EvolutionTriggerType values must be valid for promotion."""
        service, evolution_repo, version_registry, _ = _make_service()

        for i, trigger in enumerate(EvolutionTriggerType):
            evo_id = f"evo-{trigger.value}"
            evo = _make_evolution(
                evolution_id=evo_id,
                trigger_type=trigger.value,
                evaluation_sequence=i + 1,
            )
            evolution_repo.save(evo)

            event = service.promote_canonical(
                "family-uuid-001", "eval-uuid-001", trigger.value, evo_id
            )
            assert event is not None
            assert event.trigger_type == trigger.value

        # All four should have independent canonicals
        for trigger in EvolutionTriggerType:
            canonical = version_registry.get_canonical(
                "family-uuid-001", "eval-uuid-001", trigger.value
            )
            assert canonical is not None
            assert canonical.evolution_id == f"evo-{trigger.value}"
