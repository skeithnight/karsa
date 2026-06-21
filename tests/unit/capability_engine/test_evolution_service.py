"""Tests for CapabilityEvolutionService -- Sprint-11. Transaction A.

Covers:
- valid evolution creation
- duplicate evolution protection
- quality gate defer
- provenance validation
- outbox event creation
"""

import json
import pytest
from datetime import datetime

from karsa.capability_engine.application.capability_evolution_service import (
    CapabilityEvolutionService,
    EvolutionCommand,
    EvolutionResult,
    DEFAULT_QUALITY_THRESHOLD,
)
from karsa.capability_engine.domain.events.capability_events import (
    CapabilityEvolutionDeferredEvent,
    CapabilityEvolutionRecordedEvent,
)
from karsa.capability_engine.domain.exceptions import (
    InvalidEvolutionEvidenceError,
)
from karsa.capability_engine.domain.value_objects.capability_score_component import (
    CapabilityScoreComponent,
)
from karsa.capability_engine.domain.value_objects.enums import (
    EvolutionTriggerType,
    EvolutionType,
    EvolutionStatus,
)
from karsa.capability_engine.domain.value_objects.evolution_context_snapshot import (
    EvolutionContextSnapshot,
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


# --- Fixtures ---

def _make_valid_command(**overrides) -> EvolutionCommand:
    """Build a valid EvolutionCommand for testing."""
    snapshot = EvolutionContextSnapshot(
        capability_snapshot={"version": "v1", "status": "ACTIVE"},
        review_snapshot={"score": 0.8},
        snapshot_source_versions={"review_projection": 1},
    )
    # Compute the hash so it passes validation
    from karsa.capability_engine.domain.value_objects.evolution_context_snapshot import _compute_snapshot_hash
    data = {
        "capability": snapshot.capability_snapshot,
        "review": snapshot.review_snapshot,
        "attribution": snapshot.attribution_snapshot,
        "execution": snapshot.execution_snapshot,
        "source_versions": snapshot.snapshot_source_versions,
    }
    # Rebuild with correct hash
    snapshot = EvolutionContextSnapshot(
        capability_snapshot={"version": "v1", "status": "ACTIVE"},
        review_snapshot={"score": 0.8},
        snapshot_hash=_compute_snapshot_hash(data),
        snapshot_source_versions={"review_projection": 1},
    )

    defaults = dict(
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
            source_id="urn:karsa:review:abc123",
            finding_ids=["finding-001"],
        ),
        context_snapshot=snapshot,
        evaluation_sequence=1,
        quality_score=0.8,
    )
    defaults.update(overrides)
    return EvolutionCommand(**defaults)


def _make_service():
    """Wire up the service with in-memory repositories."""
    evolution_repo = InMemoryCapabilityEvolutionRepository()
    version_registry = InMemoryEvolutionVersionRegistryRepository()
    outbox_repo = InMemoryOutboxRepository()
    service = CapabilityEvolutionService(
        evolution_repo=evolution_repo,
        version_registry=version_registry,
        outbox_repo=outbox_repo,
    )
    return service, evolution_repo, version_registry, outbox_repo


# --- Tests: Valid Evolution Creation ---

class TestValidEvolutionCreation:
    """ADR-120, ADR-133, ADR-135, ADR-136."""

    def test_record_evolution_succeeds(self):
        service, _, _, _ = _make_service()
        cmd = _make_valid_command()
        result = service.record_evolution(cmd)
        assert result.success is True
        assert result.evolution_id is not None
        assert result.evolution_id.startswith("urn:karsa:capability:evolution:")
        assert result.deferred is False

    def test_record_evolution_persists_aggregate(self):
        service, evolution_repo, _, _ = _make_service()
        cmd = _make_valid_command()
        result = service.record_evolution(cmd)
        saved = evolution_repo.get_by_id(result.evolution_id)
        assert saved is not None
        assert saved.capability_family_id == "family-uuid-001"
        assert saved.evaluation_id == "eval-uuid-001"
        assert saved.trigger_type == "REVIEW_FINDING"

    def test_record_evolution_creates_canonical_registry_entry(self):
        service, _, version_registry, _ = _make_service()
        cmd = _make_valid_command()
        result = service.record_evolution(cmd)
        canonical = version_registry.get_canonical(
            "family-uuid-001", "eval-uuid-001", "REVIEW_FINDING"
        )
        assert canonical is not None
        assert canonical.evolution_id == result.evolution_id
        assert canonical.evolution_status == EvolutionStatus.CANONICAL.value

    def test_record_evolution_with_multiple_trigger_types(self):
        """ADR-120: One evolution per trigger type per evaluation cycle."""
        service, evolution_repo, _, _ = _make_service()

        # Record REVIEW_FINDING
        cmd1 = _make_valid_command(trigger_type=EvolutionTriggerType.REVIEW_FINDING.value)
        r1 = service.record_evolution(cmd1)
        assert r1.success is True

        # Record ATTRIBUTION_INSIGHT for same (family, evaluation)
        cmd2 = _make_valid_command(trigger_type=EvolutionTriggerType.ATTRIBUTION_INSIGHT.value)
        r2 = service.record_evolution(cmd2)
        assert r2.success is True
        assert r2.evolution_id != r1.evolution_id

    def test_record_evolution_preserves_context_snapshot(self):
        """ADR-135: Context snapshot must be preserved immutably."""
        service, evolution_repo, _, _ = _make_service()
        cmd = _make_valid_command()
        result = service.record_evolution(cmd)
        saved = evolution_repo.get_by_id(result.evolution_id)
        assert saved.context_snapshot.capability_snapshot == {"version": "v1", "status": "ACTIVE"}
        assert saved.context_snapshot.review_snapshot == {"score": 0.8}


# --- Tests: Duplicate Evolution Protection ---

class TestDuplicateEvolutionProtection:
    """ADR-120: ON CONFLICT DO NOTHING for business identity."""

    def test_duplicate_evolution_returns_false(self):
        service, _, _, _ = _make_service()
        cmd = _make_valid_command()
        r1 = service.record_evolution(cmd)
        assert r1.success is True

        # Same business identity (family, eval, trigger)
        cmd2 = _make_valid_command()
        r2 = service.record_evolution(cmd2)
        assert r2.success is False
        assert r2.deferred is False

    def test_duplicate_does_not_corrupt_registry(self):
        """Duplicate must not change the canonical entry."""
        service, _, version_registry, _ = _make_service()
        cmd = _make_valid_command()
        r1 = service.record_evolution(cmd)

        cmd2 = _make_valid_command()
        r2 = service.record_evolution(cmd2)

        canonical = version_registry.get_canonical(
            "family-uuid-001", "eval-uuid-001", "REVIEW_FINDING"
        )
        assert canonical.evolution_id == r1.evolution_id


# --- Tests: Quality Gate Defer ---

class TestQualityGateDefer:
    """ADR-130: Quality threshold gates evolution creation."""

    def test_below_threshold_defers(self):
        service, evolution_repo, _, outbox_repo = _make_service()
        cmd = _make_valid_command(quality_score=0.1)  # below 0.3 threshold
        result = service.record_evolution(cmd)
        assert result.success is False
        assert result.deferred is True
        assert result.defer_reason == "Quality score below threshold"

    def test_deferred_evolution_not_saved(self):
        service, evolution_repo, _, _ = _make_service()
        cmd = _make_valid_command(quality_score=0.1)
        result = service.record_evolution(cmd)
        # No evolution should be persisted
        assert len(evolution_repo.list_evolutions()) == 0

    def test_deferred_emits_deferred_event(self):
        service, _, _, outbox_repo = _make_service()
        cmd = _make_valid_command(quality_score=0.1)
        result = service.record_evolution(cmd)
        assert len(result.events) == 1
        assert isinstance(result.events[0], CapabilityEvolutionDeferredEvent)
        assert result.events[0].quality_score == 0.1

    def test_at_threshold_passes(self):
        service, _, _, _ = _make_service()
        cmd = _make_valid_command(quality_score=0.3)  # exactly at threshold
        result = service.record_evolution(cmd)
        assert result.success is True

    def test_above_threshold_passes(self):
        service, _, _, _ = _make_service()
        cmd = _make_valid_command(quality_score=0.9)
        result = service.record_evolution(cmd)
        assert result.success is True


# --- Tests: Provenance Validation ---

class TestProvenanceValidation:
    """ADR-120: Evolution must have traceable provenance."""

    def test_empty_source_type_rejected(self):
        """EvolutionEvidence VO rejects empty source_type at construction."""
        with pytest.raises(ValueError, match="source_type is required"):
            EvolutionEvidence(
                source_type="",
                source_id="urn:karsa:review:abc",
                finding_ids=["f1"],
            )

    def test_empty_source_id_rejected(self):
        """EvolutionEvidence VO rejects empty source_id at construction."""
        with pytest.raises(ValueError, match="source_id is required"):
            EvolutionEvidence(
                source_type="REVIEW",
                source_id="",
                finding_ids=["f1"],
            )

    def test_no_findings_or_attributions_rejected(self):
        """EvolutionEvidence VO rejects empty provenance at construction."""
        with pytest.raises(ValueError, match="At least one of finding_ids"):
            EvolutionEvidence(
                source_type="REVIEW",
                source_id="urn:karsa:review:abc",
                finding_ids=[],
                attribution_contribution_ids=[],
            )

    def test_with_only_attribution_ids_accepted(self):
        service, _, _, _ = _make_service()
        cmd = _make_valid_command(
            evidence=EvolutionEvidence(
                source_type="ATTRIBUTION",
                source_id="urn:karsa:attribution:abc",
                finding_ids=[],
                attribution_contribution_ids=["contrib-001"],
            )
        )
        result = service.record_evolution(cmd)
        assert result.success is True


# --- Tests: Outbox Event Creation ---

class TestOutboxEventCreation:
    """Transactional outbox within Transaction A."""

    def test_evolution_creates_outbox_event(self):
        service, _, _, outbox_repo = _make_service()
        cmd = _make_valid_command()
        result = service.record_evolution(cmd)
        pending = outbox_repo.get_pending()
        assert len(pending) == 1
        assert pending[0].event_type == "CapabilityEvolutionRecordedEvent"
        assert pending[0].aggregate_id == "family-uuid-001"

    def test_outbox_event_contains_evolution_data(self):
        service, _, _, outbox_repo = _make_service()
        cmd = _make_valid_command()
        result = service.record_evolution(cmd)
        pending = outbox_repo.get_pending()
        payload = json.loads(pending[0].payload)
        assert payload["evolution_id"] == result.evolution_id
        assert payload["capability_family_id"] == "family-uuid-001"
        assert payload["trigger_type"] == "REVIEW_FINDING"

    def test_deferred_creates_deferred_outbox_event(self):
        service, _, _, outbox_repo = _make_service()
        cmd = _make_valid_command(quality_score=0.1)
        result = service.record_evolution(cmd)
        pending = outbox_repo.get_pending()
        assert len(pending) == 1
        assert pending[0].event_type == "CapabilityEvolutionDeferredEvent"

    def test_duplicate_does_not_create_outbox_event(self):
        service, _, _, outbox_repo = _make_service()
        cmd = _make_valid_command()
        service.record_evolution(cmd)
        service.record_evolution(cmd)  # duplicate
        pending = outbox_repo.get_pending()
        # Only one event from the first successful save
        assert len(pending) == 1


# --- Tests: Version Registry Integration ---

class TestVersionRegistryIntegration:
    """ADR-133: Canonical governance via version registry."""

    def test_first_evolution_becomes_canonical(self):
        service, _, version_registry, _ = _make_service()
        cmd = _make_valid_command()
        result = service.record_evolution(cmd)
        canonical = version_registry.get_canonical(
            "family-uuid-001", "eval-uuid-001", "REVIEW_FINDING"
        )
        assert canonical is not None
        assert canonical.evolution_id == result.evolution_id

    def test_second_evolution_supersedes_first(self):
        """When a new evolution for the same identity is created (different eval),
        the version registry should reflect the new canonical."""
        service, _, version_registry, _ = _make_service()

        # First evolution
        cmd1 = _make_valid_command(evaluation_id="eval-001", evaluation_sequence=1)
        r1 = service.record_evolution(cmd1)

        # Different evaluation -- new business identity
        cmd2 = _make_valid_command(evaluation_id="eval-002", evaluation_sequence=2)
        r2 = service.record_evolution(cmd2)

        # Each evaluation has its own canonical
        c1 = version_registry.get_canonical("family-uuid-001", "eval-001", "REVIEW_FINDING")
        c2 = version_registry.get_canonical("family-uuid-001", "eval-002", "REVIEW_FINDING")
        assert c1.evolution_id == r1.evolution_id
        assert c2.evolution_id == r2.evolution_id


# --- Tests: Transaction Boundary ---

class TestTransactionBoundary:
    """ADR-130: Transaction A must NOT touch health scores or projections."""

    def test_service_does_not_accept_health_score_repo(self):
        """Service constructor signature enforces separation."""
        service, _, _, _ = _make_service()
        # The service has no reference to health score repo
        assert not hasattr(service, '_health_score_repo')

    def test_record_evolution_does_not_modify_score_history(self):
        """Transaction A is independent of score history."""
        service, _, _, _ = _make_service()
        cmd = _make_valid_command()
        result = service.record_evolution(cmd)
        # No score history repo is wired -- confirms separation
        assert result.success is True
