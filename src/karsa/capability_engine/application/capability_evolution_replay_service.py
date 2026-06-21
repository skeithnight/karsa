"""CapabilityEvolutionReplayService -- Sprint-11. ADR-135.

Deterministic replay verification for capability evolution records.

Supports:
- get_canonical_evolution(): retrieve the canonical evolution for a business identity
- get_evolution_history(): retrieve full evolution history for a family
- verify_replay_determinism(): verify context snapshot hash integrity
- verify_snapshot_version(): detect stale snapshots (ADR-135)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from karsa.capability_engine.domain.aggregates.capability_evolution import (
    CapabilityEvolution,
)
from karsa.capability_engine.domain.exceptions import (
    InvalidContextSnapshotError,
)
from karsa.capability_engine.application.ports.capability_evolution_port import (
    CapabilityEvolutionPort,
)
from karsa.capability_engine.application.ports.capability_score_history_port import (
    CapabilityScoreHistoryPort,
)
from karsa.capability_engine.application.ports.capability_version_registry_port import (
    CapabilityVersionRegistryPort,
    VersionRegistryEntry,
)


@dataclass
class ReplayVerificationResult:
    """Result of replay determinism verification."""

    is_deterministic: bool
    evolution_id: str
    snapshot_hash_valid: bool
    source_versions_match: bool
    error: Optional[str] = None


@dataclass
class SnapshotVersionResult:
    """Result of snapshot version validation."""

    is_stale: bool
    evolution_id: str
    snapshot_source_versions: Dict
    current_source_versions: Optional[Dict] = None
    stale_sources: Optional[List[str]] = None


class CapabilityEvolutionReplayService:
    """Replay verification service for deterministic evolution reconstruction.

    ADR-135: Immutable context snapshots enable deterministic replay.
    Stale snapshot detection ensures replay uses current data.
    Algorithm version validation ensures scoring consistency.
    """

    def __init__(
        self,
        evolution_repo: CapabilityEvolutionPort,
        version_registry: CapabilityVersionRegistryPort,
        score_history_repo: CapabilityScoreHistoryPort,
    ) -> None:
        self._evolution_repo = evolution_repo
        self._version_registry = version_registry
        self._score_history_repo = score_history_repo

    def get_canonical_evolution(
        self,
        capability_family_id: str,
        evaluation_id: str,
        trigger_type: str,
    ) -> Optional[CapabilityEvolution]:
        """Retrieve the canonical evolution for a business identity.

        ADR-133: Canonical status is in the version registry, not the aggregate.
        """
        entry = self._version_registry.get_canonical(
            capability_family_id, evaluation_id, trigger_type
        )
        if entry is None:
            return None
        return self._evolution_repo.get_by_id(entry.evolution_id)

    def get_evolution_history(
        self,
        capability_family_id: str,
    ) -> List[CapabilityEvolution]:
        """Retrieve all evolution records for a capability family.

        Returns records ordered by evaluation_sequence.
        """
        entries = self._version_registry.list_by_family(capability_family_id)
        evolutions = []
        for entry in entries:
            evolution = self._evolution_repo.get_by_id(entry.evolution_id)
            if evolution is not None:
                evolutions.append(evolution)
        # Sort by evaluation_sequence for deterministic ordering
        evolutions.sort(key=lambda e: e.evaluation_sequence)
        return evolutions

    def verify_replay_determinism(
        self,
        evolution_id: str,
    ) -> ReplayVerificationResult:
        """Verify that an evolution's context snapshot is intact.

        ADR-135: The snapshot_hash is a SHA-256 of all snapshot data.
        If the hash doesn't match, the snapshot has been tampered with
        or corrupted, and replay cannot be deterministic.
        """
        evolution = self._evolution_repo.get_by_id(evolution_id)
        if evolution is None:
            return ReplayVerificationResult(
                is_deterministic=False,
                evolution_id=evolution_id,
                snapshot_hash_valid=False,
                source_versions_match=False,
                error="Evolution not found",
            )

        # Verify snapshot hash integrity
        hash_valid = evolution.context_snapshot.verify_hash()

        # Verify source versions are recorded
        source_versions_match = bool(
            evolution.context_snapshot.snapshot_source_versions
        )

        is_deterministic = hash_valid and source_versions_match

        return ReplayVerificationResult(
            is_deterministic=is_deterministic,
            evolution_id=evolution_id,
            snapshot_hash_valid=hash_valid,
            source_versions_match=source_versions_match,
            error=None if is_deterministic else "Snapshot integrity check failed",
        )

    def verify_snapshot_version(
        self,
        evolution_id: str,
        current_source_versions: Dict,
    ) -> SnapshotVersionResult:
        """Detect stale snapshots by comparing source versions.

        ADR-135: A snapshot is stale if any source projection has advanced
        beyond the version captured in the snapshot. Stale snapshots
        may produce non-deterministic replay results.
        """
        evolution = self._evolution_repo.get_by_id(evolution_id)
        if evolution is None:
            return SnapshotVersionResult(
                is_stale=True,
                evolution_id=evolution_id,
                snapshot_source_versions={},
                current_source_versions=current_source_versions,
                stale_sources=["evolution_not_found"],
            )

        snapshot_versions = evolution.context_snapshot.snapshot_source_versions
        stale_sources = []

        for source, captured_version in snapshot_versions.items():
            current_version = current_source_versions.get(source)
            if current_version is None:
                stale_sources.append(f"{source}:missing")
            elif current_version > captured_version:
                stale_sources.append(
                    f"{source}:captured={captured_version},current={current_version}"
                )

        return SnapshotVersionResult(
            is_stale=len(stale_sources) > 0,
            evolution_id=evolution_id,
            snapshot_source_versions=snapshot_versions,
            current_source_versions=current_source_versions,
            stale_sources=stale_sources if stale_sources else None,
        )
