"""CapabilityScoreProjectionRepository contract — Sprint-07 Wave-2B."""
from abc import ABC, abstractmethod
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CapabilityScoreProjection:
    """Read-side projection representing current capability score."""
    target_urn: str
    target_type: str
    current_score: float
    current_confidence: float
    adjustment_count: int
    last_updated: datetime


class CapabilityScoreProjectionRepository(ABC):
    """Repository contract for CapabilityScoreProjection.

    Derived projection: current_score = SUM(score_delta) from capability_score_adjustments.
    Mutable via UPSERT.
    """

    @abstractmethod
    def get_by_target_urn(self, target_urn: str) -> Optional[CapabilityScoreProjection]:
        """Retrieves the current capability score for a given target.

        Args:
            target_urn: The target URN (worker, thesis, strategy).

        Returns:
            The CapabilityScoreProjection if found, None otherwise.
        """
        pass

    @abstractmethod
    def list_all(self) -> List[CapabilityScoreProjection]:
        """Lists all capability score projections.

        Returns:
            List of CapabilityScoreProjection instances ordered by current_score DESC.
        """
        pass

    @abstractmethod
    def upsert(
        self,
        target_urn: str,
        target_type: str,
        score_delta: float,
        confidence_delta: float,
        adjustment_count_delta: int = 1,
    ) -> None:
        """Inserts or updates a capability score projection.

        On conflict (target_urn already exists):
            current_score += score_delta
            current_confidence += confidence_delta
            adjustment_count += adjustment_count_delta
            last_updated = now()

        Args:
            target_urn: The target URN.
            target_type: The target type (WORKER, THESIS, STRATEGY).
            score_delta: The score change to apply.
            confidence_delta: The confidence change to apply.
            adjustment_count_delta: The count change to apply (default 1).
        """
        pass

    @abstractmethod
    def rebuild(self) -> None:
        """Rebuilds the projection from scratch.

        Truncates the projection table and recomputes from
        capability_score_adjustments via GROUP BY target_urn.

        This is a destructive operation. Use only during replay.
        """
        pass
