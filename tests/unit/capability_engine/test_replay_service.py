"""Tests for CapabilityEvolutionReplayService -- Sprint-11. ADR-135.

Covers:
- deterministic replay
- stale snapshot detection
- snapshot version validation
"""

import pytest
from datetime import datetime

from karsa.capability_engine.application.capability_evolution_replay_service import (
    CapabilityEvolutionReplayService,
    ReplayVerificationResult,
    SnapshotVersionResult,
)
from karsa.capability_engine.domain.aggregates.capability_evolution import (
    CapabilityEvolution,
)
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
    InMemoryScoreHistoryRepository,
)
from karsa.capability_engine.infrastructure.repositories.capability_evolution_version_registry_repository import (
    EvolutionVersionRegistryEntry,
)


# --- Helpers ---

def _make_snapshot_with_hash(capability=None, review=None, source_versions=None):
    """Build an EvolutionContextSnapshot with a valid hash."""
    cap = capability or {"version": "v1", "status": "ACTIVE"}
    rev = review or {"score": 0.8}
    sv = source_versions or {"review_projection": 1, "attribution_projection": 1}

    data = {
        "capability": cap,
        "review": rev,
        "attribution": None,
        "execution": None,
        "source_versions": sv,
    }
    return EvolutionContextSnapshot(
        capability_snapshot=cap,
        review_snapshot=rev,
        snapshot_hash=_compute_snapshot_hash(data),
        snapshot_source_versions=sv,
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
        context_snapshot=_make_snapshot_with_hash(),
        evaluation_sequence=1,
    )
    defaults.update(overrides)
    return CapabilityEvolution(**defaults)


def _make_service():
    evolution_repo = InMemoryCapabilityEvolutionRepository()
    version_registry = InMemoryEvolutionVersionRegistryRepository()
    history_repo = InMemoryScoreHistoryRepository()

    service = CapabilityEvolutionReplayService(
        evolution_repo=evolution_repo,
        version_registry=version_registry,
        score_history_repo=history_repo,
    )
    return service, evolution_repo, version_registry


# --- Tests: Deterministic Replay ---

class TestDeterministicReplay:
    """ADR-135: Immutable context snapshots for deterministic replay."""

    def test_valid_snapshot_passes_verification(self):
        service, evolution_repo, _ = _make_service()
        evolution = _make_evolution()
        evolution_repo.save(evolution)

        result = service.verify_replay_determinism(evolution.evolution_id)
        assert result.is_deterministic is True
        assert result.snapshot_hash_valid is True
        assert result.source_versions_match is True
        assert result.error is None

    def test_missing_evolution_fails_verification(self):
        service, _, _ = _make_service()
        result = service.verify_replay_determinism("nonexistent-id")
        assert result.is_deterministic is False
        assert result.error == "Evolution not found"

    def test_empty_source_versions_fails(self):
        """Snapshot without source versions is not replayable."""
        service, evolution_repo, _ = _make_service()

        # Build snapshot with empty source versions but valid hash
        cap = {"version": "v1"}
        rev = {"score": 0.8}
        data = {
            "capability": cap,
            "review": rev,
            "attribution": None,
            "execution": None,
            "source_versions": {},
        }
        snapshot = EvolutionContextSnapshot(
            capability_snapshot=cap,
            review_snapshot=rev,
            snapshot_hash=_compute_snapshot_hash(data),
            snapshot_source_versions={},
        )
        evolution = _make_evolution(context_snapshot=snapshot)
        evolution_repo.save(evolution)

        result = service.verify_replay_determinism(evolution.evolution_id)
        assert result.is_deterministic is False
        assert result.source_versions_match is False

    def test_hash_integrity_check(self):
        """Snapshot hash must match the SHA-256 of snapshot data."""
        service, evolution_repo, _ = _make_service()
        evolution = _make_evolution()
        evolution_repo.save(evolution)

        result = service.verify_replay_determinism(evolution.evolution_id)
        assert result.snapshot_hash_valid is True

        # Verify the hash can be independently recomputed
        snapshot = evolution.context_snapshot
        assert snapshot.verify_hash() is True


# --- Tests: Stale Snapshot Detection ---

class TestStaleSnapshotDetection:
    """ADR-135: Stale snapshots may produce non-deterministic replay."""

    def test_current_versions_not_stale(self):
        service, evolution_repo, _ = _make_service()
        evolution = _make_evolution()
        evolution_repo.save(evolution)

        current_versions = {"review_projection": 1, "attribution_projection": 1}
        result = service.verify_snapshot_version(
            evolution.evolution_id, current_versions
        )
        assert result.is_stale is False
        assert result.stale_sources is None

    def test_advanced_source_detected_as_stale(self):
        """Source projection advanced beyond captured version."""
        service, evolution_repo, _ = _make_service()
        evolution = _make_evolution()
        evolution_repo.save(evolution)

        # Source has advanced from version 1 to version 3
        current_versions = {"review_projection": 3, "attribution_projection": 1}
        result = service.verify_snapshot_version(
            evolution.evolution_id, current_versions
        )
        assert result.is_stale is True
        assert result.stale_sources is not None
        assert any("review_projection" in s for s in result.stale_sources)

    def test_missing_source_detected_as_stale(self):
        """Source projection no longer available."""
        service, evolution_repo, _ = _make_service()
        evolution = _make_evolution()
        evolution_repo.save(evolution)

        # attribution_projection is missing from current
        current_versions = {"review_projection": 1}
        result = service.verify_snapshot_version(
            evolution.evolution_id, current_versions
        )
        assert result.is_stale is True
        assert any("missing" in s for s in result.stale_sources)

    def test_nonexistent_evolution_is_stale(self):
        service, _, _ = _make_service()
        result = service.verify_snapshot_version("nonexistent", {"review_projection": 1})
        assert result.is_stale is True

    def test_same_versions_not_stale(self):
        service, evolution_repo, _ = _make_service()

        snapshot = _make_snapshot_with_hash(
            source_versions={"review_projection": 5, "attribution_projection": 3}
        )
        evolution = _make_evolution(context_snapshot=snapshot)
        evolution_repo.save(evolution)

        current = {"review_projection": 5, "attribution_projection": 3}
        result = service.verify_snapshot_version(evolution.evolution_id, current)
        assert result.is_stale is False


# --- Tests: Snapshot Version Validation ---

class TestSnapshotVersionValidation:
    """ADR-135: Snapshot source versions must be recorded."""

    def test_source_versions_recorded_in_snapshot(self):
        service, evolution_repo, _ = _make_service()
        evolution = _make_evolution()
        evolution_repo.save(evolution)

        snapshot = evolution.context_snapshot
        assert "review_projection" in snapshot.snapshot_source_versions
        assert "attribution_projection" in snapshot.snapshot_source_versions

    def test_version_result_includes_snapshot_versions(self):
        service, evolution_repo, _ = _make_service()
        evolution = _make_evolution()
        evolution_repo.save(evolution)

        result = service.verify_snapshot_version(
            evolution.evolution_id, {"review_projection": 1}
        )
        assert result.snapshot_source_versions == {
            "review_projection": 1,
            "attribution_projection": 1,
        }

    def test_version_result_includes_current_versions(self):
        service, evolution_repo, _ = _make_service()
        evolution = _make_evolution()
        evolution_repo.save(evolution)

        current = {"review_projection": 2, "attribution_projection": 1}
        result = service.verify_snapshot_version(evolution.evolution_id, current)
        assert result.current_source_versions == current


# --- Tests: Canonical Evolution Lookup ---

class TestCanonicalLookup:
    """ADR-133: Canonical via version registry."""

    def test_get_canonical_returns_evolution(self):
        service, evolution_repo, version_registry = _make_service()
        evolution = _make_evolution()
        evolution_repo.save(evolution)

        # Register as canonical
        entry = EvolutionVersionRegistryEntry(
            version_id="vreg-001",
            capability_family_id="family-uuid-001",
            evaluation_id="eval-uuid-001",
            trigger_type="REVIEW_FINDING",
            evolution_id=evolution.evolution_id,
            evolution_status=EvolutionStatus.CANONICAL.value,
        )
        version_registry.save(entry)

        result = service.get_canonical_evolution(
            "family-uuid-001", "eval-uuid-001", "REVIEW_FINDING"
        )
        assert result is not None
        assert result.evolution_id == evolution.evolution_id

    def test_get_canonical_returns_none_when_none(self):
        service, _, _ = _make_service()
        result = service.get_canonical_evolution(
            "nonexistent", "eval", "REVIEW_FINDING"
        )
        assert result is None

    def test_get_evolution_history_returns_sorted(self):
        service, evolution_repo, version_registry = _make_service()

        e1 = _make_evolution(evolution_id="evo-1", evaluation_sequence=3)
        e2 = _make_evolution(
            evolution_id="evo-2",
            evaluation_id="eval-002",
            evaluation_sequence=1,
        )
        e3 = _make_evolution(
            evolution_id="evo-3",
            evaluation_id="eval-003",
            evaluation_sequence=2,
        )
        evolution_repo.save(e1)
        evolution_repo.save(e2)
        evolution_repo.save(e3)

        for e in [e1, e2, e3]:
            version_registry.save(EvolutionVersionRegistryEntry(
                version_id=f"vreg-{e.evolution_id}",
                capability_family_id="family-uuid-001",
                evaluation_id=e.evaluation_id,
                trigger_type="REVIEW_FINDING",
                evolution_id=e.evolution_id,
                evolution_status="CANONICAL",
            ))

        history = service.get_evolution_history("family-uuid-001")
        assert len(history) == 3
        # Should be sorted by evaluation_sequence
        assert history[0].evaluation_sequence == 1
        assert history[1].evaluation_sequence == 2
        assert history[2].evaluation_sequence == 3
