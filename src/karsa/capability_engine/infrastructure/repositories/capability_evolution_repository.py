"""CapabilityEvolutionRepository ABC -- Sprint-11. ADR-120, ADR-133."""

from abc import ABC, abstractmethod
from typing import List, Optional

from karsa.capability_engine.domain.aggregates.capability_evolution import (
    CapabilityEvolution,
)


class CapabilityEvolutionRepository(ABC):
    """Write-once repository for capability evolution records.

    ADR-120: Business identity is (capability_family_id, evaluation_id,
    trigger_type). ON CONFLICT DO NOTHING for idempotent inserts.

    ADR-133: No update or delete methods. Canonical status is governed
    by the version registry, not this repository.
    """

    @abstractmethod
    def save(self, record: CapabilityEvolution) -> bool:
        """Persist an evolution record. Returns False on duplicate."""

    @abstractmethod
    def get_by_id(self, evolution_id: str) -> Optional[CapabilityEvolution]:
        """Technical lookup by evolution_id URN."""

    @abstractmethod
    def get_by_family_and_evaluation(
        self, capability_family_id: str, evaluation_id: str
    ) -> List[CapabilityEvolution]:
        """Business identity lookup. Returns all trigger types for the pair."""

    @abstractmethod
    def get_by_family_evaluation_and_trigger(
        self,
        capability_family_id: str,
        evaluation_id: str,
        trigger_type: str,
    ) -> Optional[CapabilityEvolution]:
        """Exact business identity lookup (ADR-120)."""

    @abstractmethod
    def list_evolutions(
        self, page: int = 1, size: int = 50
    ) -> List[CapabilityEvolution]:
        """Paginated listing of all evolution records."""
