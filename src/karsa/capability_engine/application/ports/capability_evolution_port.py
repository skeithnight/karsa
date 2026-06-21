"""CapabilityEvolutionPort -- Sprint-11. Wave-9R. TD-004.

Port interface for capability evolution persistence.
Application layer owns this interface; infrastructure implements it.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class CapabilityEvolutionPort(ABC):
    """Write-once port for capability evolution records.

    ADR-120: Business identity is (capability_family_id, evaluation_id,
    trigger_type). ON CONFLICT DO NOTHING for idempotent inserts.
    """

    @abstractmethod
    def save(self, record: Any) -> bool:
        """Persist an evolution record. Returns False on duplicate."""

    @abstractmethod
    def get_by_id(self, evolution_id: str) -> Optional[Any]:
        """Technical lookup by evolution_id URN."""

    @abstractmethod
    def get_by_family_and_evaluation(
        self, capability_family_id: str, evaluation_id: str
    ) -> List[Any]:
        """Business identity lookup. Returns all trigger types for the pair."""

    @abstractmethod
    def get_by_family_evaluation_and_trigger(
        self,
        capability_family_id: str,
        evaluation_id: str,
        trigger_type: str,
    ) -> Optional[Any]:
        """Exact business identity lookup (ADR-120)."""

    @abstractmethod
    def list_evolutions(
        self, page: int = 1, size: int = 50
    ) -> List[Any]:
        """Paginated listing of all evolution records."""
