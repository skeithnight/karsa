"""CapabilityEngineFixture -- Sprint-11. Wave-7.

Shared test fixtures for capability engine integration tests.
Provides pre-built test data helpers and the bootstrapped container.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from karsa.capability_engine.domain.aggregates.capability_evolution import (
    CapabilityEvolution,
)
from karsa.capability_engine.domain.aggregates.capability_health_score import (
    CapabilityHealthScore,
)
from karsa.capability_engine.domain.entities.evolution_attribution_ref import (
    EvolutionAttributionRef,
)
from karsa.capability_engine.domain.entities.evolution_finding import (
    EvolutionFinding,
)
from karsa.capability_engine.domain.value_objects.capability_score_component import (
    CapabilityScoreComponent,
)
from karsa.capability_engine.domain.value_objects.enums import (
    EvolutionTriggerType,
    EvolutionType,
    ScoreComponentName,
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
from karsa.capability_engine.domain.value_objects.score_history_entry import (
    ScoreHistoryEntry,
)
from karsa.capability_engine.infrastructure.repositories.capability_evolution_version_registry_repository import (
    EvolutionVersionRegistryEntry,
)
from karsa.capability_engine.integration.capability_engine_bootstrap import (
    CapabilityEngineContainer,
    bootstrap,
)


def make_snapshot(
    capability: Optional[dict] = None,
    review: Optional[dict] = None,
    source_versions: Optional[dict] = None,
) -> EvolutionContextSnapshot:
    """Build a valid EvolutionContextSnapshot with correct hash."""
    cap = capability or {"version": "v1", "status": "ACTIVE"}
    rev = review or {"score": 0.8}
    sv = source_versions or {"review_projection": 1}
    data = {
        "capability": cap, "review": rev,
        "attribution": None, "execution": None,
        "source_versions": sv,
    }
    return EvolutionContextSnapshot(
        capability_snapshot=cap,
        review_snapshot=rev,
        snapshot_hash=_compute_snapshot_hash(data),
        snapshot_source_versions=sv,
    )


def make_evolution(
    evolution_id: Optional[str] = None,
    capability_family_id: str = "int-family-001",
    evaluation_id: str = "int-eval-001",
    trigger_type: str = EvolutionTriggerType.REVIEW_FINDING.value,
    evaluation_sequence: int = 1,
    before_score: float = 0.5,
    after_score: float = 0.7,
    **overrides,
) -> CapabilityEvolution:
    """Build a valid CapabilityEvolution for testing."""
    bps = (after_score - before_score) * 10000
    defaults = dict(
        evolution_id=evolution_id or f"urn:karsa:capability:evolution:{uuid.uuid4().hex}",
        capability_family_id=capability_family_id,
        evaluation_id=evaluation_id,
        trigger_type=trigger_type,
        capability_version_id=f"ver-{uuid.uuid4().hex[:8]}",
        capability_urn=f"urn:karsa:capability:ns:{capability_family_id}:v1",
        evolution_type=EvolutionType.SCORE_ADJUSTMENT.value,
        delta=EvolutionDelta(
            before_score=before_score,
            after_score=after_score,
            score_change_bps=bps,
            before_lifecycle_state="ACTIVE",
            after_lifecycle_state="ACTIVE",
            before_contract_fingerprint=None,
            after_contract_fingerprint=None,
        ),
        evidence=EvolutionEvidence(
            source_type="REVIEW",
            source_id=f"urn:karsa:review:{uuid.uuid4().hex[:8]}",
            finding_ids=[f"finding-{uuid.uuid4().hex[:8]}"],
        ),
        context_snapshot=make_snapshot(),
        evaluation_sequence=evaluation_sequence,
    )
    defaults.update(overrides)
    return CapabilityEvolution(**defaults)


def make_components() -> List[CapabilityScoreComponent]:
    """Build the standard 4-factor component set."""
    return [
        CapabilityScoreComponent(
            component_name=ScoreComponentName.EXECUTION_QUALITY.value,
            component_score=0.8, weight=0.25,
            evaluation_count=1, confidence=0.9,
        ),
        CapabilityScoreComponent(
            component_name=ScoreComponentName.ATTRIBUTION_ALIGNMENT.value,
            component_score=0.7, weight=0.25,
            evaluation_count=1, confidence=0.85,
        ),
        CapabilityScoreComponent(
            component_name=ScoreComponentName.REVIEW_SENTIMENT.value,
            component_score=0.6, weight=0.25,
            evaluation_count=1, confidence=0.8,
        ),
        CapabilityScoreComponent(
            component_name=ScoreComponentName.REGIME_FITNESS.value,
            component_score=0.9, weight=0.25,
            evaluation_count=1, confidence=0.95,
        ),
    ]


def make_history_entry(
    capability_family_id: str = "int-family-001",
    evaluation_id: str = "int-eval-001",
    evaluation_sequence: int = 1,
    score: float = 0.65,
    algorithm_version: str = "v1.0",
    capability_version_id: Optional[str] = None,
) -> ScoreHistoryEntry:
    """Build a ScoreHistoryEntry for testing."""
    return ScoreHistoryEntry(
        capability_family_id=capability_family_id,
        evaluation_id=evaluation_id,
        evaluation_sequence=evaluation_sequence,
        capability_version_id=capability_version_id or f"ver-{uuid.uuid4().hex[:8]}",
        score=score,
        algorithm_version=algorithm_version,
    )


def make_registry_entry(
    capability_family_id: str = "int-family-001",
    evaluation_id: str = "int-eval-001",
    trigger_type: str = "REVIEW_FINDING",
    evolution_id: str = "evo-001",
    evolution_status: str = "CANONICAL",
) -> EvolutionVersionRegistryEntry:
    """Build an EvolutionVersionRegistryEntry for testing."""
    return EvolutionVersionRegistryEntry(
        version_id=f"vreg-{uuid.uuid4().hex[:8]}",
        capability_family_id=capability_family_id,
        evaluation_id=evaluation_id,
        trigger_type=trigger_type,
        evolution_id=evolution_id,
        evolution_status=evolution_status,
    )
