"""CapabilityEvolutionProjectionPort -- Sprint-11. Wave-9R. TD-004.

Port interface for evolution projection read model.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class CapabilityEvolutionProjectionPort(ABC):
    """Read-only port for capability evolution summaries."""

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
