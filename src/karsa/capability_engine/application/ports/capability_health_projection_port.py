"""CapabilityHealthProjectionPort -- Sprint-11. Wave-9R. TD-004.

Port interface for health projection read model.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class CapabilityHealthProjectionPort(ABC):
    """Read-only port for capability health scores."""

    @abstractmethod
    def get_health_score(
        self, capability_family_id: str
    ) -> Optional[Dict[str, Any]]:
        """Current health score for a capability family."""

    @abstractmethod
    def get_health_scores_above(
        self, threshold: float
    ) -> List[Dict[str, Any]]:
        """Capabilities above score threshold."""

    @abstractmethod
    def get_health_scores_below(
        self, threshold: float
    ) -> List[Dict[str, Any]]:
        """Capabilities below score threshold."""

    @abstractmethod
    def rebuild_all(self) -> None:
        """Full projection rebuild from source tables."""
