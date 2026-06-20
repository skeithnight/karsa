"""ReviewCycleStatusProjectionRepository contract — Sprint-07 Wave-2C."""
from abc import ABC, abstractmethod
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ReviewCycleStatusProjection:
    """Read-side projection tracking review cycle lifecycle status."""
    cycle_id: str
    status: str  # CREATED, DUE, OVERDUE, EXECUTED
    review_id: Optional[str] = None
    executed_at: Optional[datetime] = None
    event_sequence: int = 0


class ReviewCycleStatusProjectionRepository(ABC):
    """Repository contract for ReviewCycleStatusProjection.

    Derived projection: tracks review cycle lifecycle status.
    CREATED → DUE → OVERDUE or EXECUTED.
    """

    @abstractmethod
    def get_by_cycle_id(self, cycle_id: str) -> Optional[ReviewCycleStatusProjection]:
        """Retrieves the status projection for a given cycle."""
        pass

    @abstractmethod
    def list_by_status(self, status: str) -> List[ReviewCycleStatusProjection]:
        """Lists status projections filtered by status."""
        pass

    @abstractmethod
    def upsert_created(self, cycle_id: str, event_sequence: int) -> None:
        """Inserts CREATED status for a new cycle."""
        pass

    @abstractmethod
    def upsert_due(self, cycle_id: str, event_sequence: int) -> None:
        """Updates status to DUE."""
        pass

    @abstractmethod
    def upsert_overdue(self, cycle_id: str, event_sequence: int) -> None:
        """Updates status to OVERDUE."""
        pass

    @abstractmethod
    def upsert_executed(self, cycle_id: str, review_id: str, executed_at: datetime, event_sequence: int) -> None:
        """Updates status to EXECUTED."""
        pass

    @abstractmethod
    def rebuild(self) -> None:
        """Rebuilds projection from event journal."""
        pass
