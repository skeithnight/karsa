"""CapabilityEvolution aggregate -- Sprint-11. ADR-120, ADR-133."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from karsa.capability_engine.domain.entities.evolution_attribution_ref import (
    EvolutionAttributionRef,
)
from karsa.capability_engine.domain.entities.evolution_finding import (
    EvolutionFinding,
)
from karsa.capability_engine.domain.exceptions import InvalidEvolutionError
from karsa.capability_engine.domain.value_objects.evolution_context_snapshot import (
    EvolutionContextSnapshot,
)
from karsa.capability_engine.domain.value_objects.evolution_delta import (
    EvolutionDelta,
)
from karsa.capability_engine.domain.value_objects.evolution_evidence import (
    EvolutionEvidence,
)


class ImmutableLedgerEntry:
    """Write-once base class. Raises AttributeError on mutation after init.

    Pattern from review_engine (ADR-106) and attribution_engine (ADR-093).
    Each bounded context defines this locally -- no shared base.
    """

    def __setattr__(self, name: str, value: object) -> None:
        if "_initialized" in self.__dict__ and self._initialized:
            raise AttributeError(
                f"Cannot set attribute '{name}' on immutable ledger entry"
            )
        super().__setattr__(name, value)

    def __delattr__(self, name: str) -> None:
        raise AttributeError(
            f"Cannot delete attribute '{name}' on immutable ledger entry"
        )


@dataclass
class CapabilityEvolution(ImmutableLedgerEntry):
    """Immutable ledger entry recording a measurable capability change.

    ADR-120: Business identity is (capability_family_id, evaluation_id,
    trigger_type). One evolution record per trigger type per evaluation cycle.

    ADR-133: Canonical governance via separate version registry. This
    aggregate never stores canonical status.

    Write-once semantics: no update or delete after construction.
    """

    # Technical identity
    evolution_id: str  # URN: urn:karsa:capability:evolution:<hex>

    # Business identity (ADR-120)
    capability_family_id: str  # UUID, immutable across versions
    evaluation_id: str  # UUID, links to evaluation cycle
    trigger_type: str  # EvolutionTriggerType enum value

    # Capability reference (at time of evolution)
    capability_version_id: str  # UUID, specific version that evolved
    capability_urn: str  # URN of the capability at evolution time

    # Optional upstream references
    attribution_id: Optional[str] = None  # URN to attribution record
    review_id: Optional[str] = None  # URN to review assessment

    # Evolution classification
    evolution_type: str = ""  # EvolutionType enum value

    # Measured change
    delta: EvolutionDelta = field(default_factory=lambda: EvolutionDelta(
        before_score=0.0,
        after_score=0.0,
        score_change_bps=0.0,
        before_lifecycle_state="",
        after_lifecycle_state="",
        before_contract_fingerprint=None,
        after_contract_fingerprint=None,
    ))

    # Provenance chain (ADR-120: must have at least one source)
    evidence: EvolutionEvidence = field(default_factory=lambda: EvolutionEvidence(
        source_type="",
        source_id="",
    ))

    # Child entities (stored as JSONB, no independent lifecycle)
    findings: List[EvolutionFinding] = field(default_factory=list)
    attribution_refs: List[EvolutionAttributionRef] = field(default_factory=list)

    # Immutable context for deterministic replay (ADR-135)
    context_snapshot: EvolutionContextSnapshot = field(
        default_factory=lambda: EvolutionContextSnapshot(
            capability_snapshot={},
        )
    )

    # Evaluation ordering (ADR-136)
    evaluation_sequence: int = 0  # monotonic, assigned by scheduler

    # Timestamps
    reviewed_at: datetime = field(default_factory=datetime.utcnow)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        self._initialized = True
        self._validate()

    @property
    def is_canonical(self) -> None:
        """Canonical status is NOT stored on this aggregate.

        ADR-133: Governed by capability_evolution_version_registry.
        """
        raise NotImplementedError(
            "Canonical status is governed by the version registry, "
            "not by this aggregate"
        )

    def _validate(self) -> None:
        if not self.evolution_id:
            raise InvalidEvolutionError("evolution_id is required")
        if not self.capability_family_id:
            raise InvalidEvolutionError("capability_family_id is required")
        if not self.evaluation_id:
            raise InvalidEvolutionError("evaluation_id is required")
        if not self.trigger_type:
            raise InvalidEvolutionError("trigger_type is required")
        if not self.capability_version_id:
            raise InvalidEvolutionError("capability_version_id is required")
        if not self.capability_urn:
            raise InvalidEvolutionError("capability_urn is required")
        if not self.evolution_type:
            raise InvalidEvolutionError("evolution_type is required")
        if self.evaluation_sequence < 0:
            raise InvalidEvolutionError(
                f"evaluation_sequence must be >= 0, "
                f"got {self.evaluation_sequence}"
            )
        # Validate child entities
        for f in self.findings:
            f._validate()
        for a in self.attribution_refs:
            a._validate()
