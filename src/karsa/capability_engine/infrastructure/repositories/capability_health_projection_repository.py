"""CapabilityHealthProjectionRepository ABC -- Sprint-11."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class CapabilityHealthProjectionRepository(ABC):
    """Read-only projection repository for capability health scores."""

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
        """Capabilities below score threshold (for allocation blocking)."""

    @abstractmethod
    def rebuild_all(self) -> None:
        """Full projection rebuild from source tables."""
