"""CapabilityEvolutionProjectionRepository ABC -- Sprint-11."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class CapabilityEvolutionProjectionRepository(ABC):
    """Read-only projection repository for capability evolution summaries."""

    @abstractmethod
    def get_evolution_summary(
        self, capability_family_id: str
    ) -> Optional[Dict[str, Any]]:
        """Evolution history summary for a capability family."""

    @abstractmethod
    def get_evolution_by_evaluation(
        self, evaluation_id: str
    ) -> List[Dict[str, Any]]:
        """All evolutions for a specific evaluation."""

    @abstractmethod
    def rebuild_all(self) -> None:
        """Full projection rebuild from source tables."""
