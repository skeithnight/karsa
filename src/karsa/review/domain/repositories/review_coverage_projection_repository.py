"""ReviewCoverageProjectionRepository contract — Sprint-07 Wave-2B."""
from abc import ABC, abstractmethod
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ReviewCoverageProjection:
    """Read-side projection tracking review coverage for all evaluated decisions."""
    decision_id: str
    proposal_id: Optional[str]
    cycle_id: Optional[str]
    eligible: bool
    review_type: Optional[str]
    strategy_name: Optional[str]
    strategy_version: Optional[str]
    evaluation_reason: Optional[str]
    review_status: str  # NO_REVIEW, PENDING, DUE, OVERDUE, EXECUTED
    review_due_date: Optional[datetime]
    executed_at: Optional[datetime]
    days_overdue: Optional[int]
    evaluated_at: datetime


class ReviewCoverageProjectionRepository(ABC):
    """Repository contract for ReviewCoverageProjection.

    Derived projection: tracks review coverage for all evaluated decisions.
    NO_REVIEW derived from eligible=false event (not from absence of events).
    """

    @abstractmethod
    def get_by_decision_id(self, decision_id: str) -> Optional[ReviewCoverageProjection]:
        """Retrieves the review coverage for a given decision.

        Args:
            decision_id: The CIO decision identifier.

        Returns:
            The ReviewCoverageProjection if found, None otherwise.
        """
        pass

    @abstractmethod
    def list_by_status(self, status: str) -> List[ReviewCoverageProjection]:
        """Lists review coverage entries filtered by status.

        Args:
            status: The review status to filter by (NO_REVIEW, PENDING, DUE, OVERDUE, EXECUTED).

        Returns:
            List of ReviewCoverageProjection instances.
        """
        pass

    @abstractmethod
    def list_overdue(self) -> List[ReviewCoverageProjection]:
        """Lists all overdue review coverage entries.

        Returns:
            List of ReviewCoverageProjection instances where review_status = 'OVERDUE'.
        """
        pass

    @abstractmethod
    def upsert_from_eligibility(
        self,
        decision_id: str,
        eligible: bool,
        review_type: Optional[str],
        strategy_name: str,
        strategy_version: str,
        evaluation_reason: str,
        evaluated_at: datetime,
    ) -> None:
        """Inserts or updates coverage from a ReviewEligibilityEvaluatedEvent.

        On conflict (decision_id already exists):
            Updates eligibility fields and evaluated_at.

        Args:
            decision_id: The CIO decision identifier.
            eligible: Whether the decision is eligible for review.
            review_type: The review type if eligible, None otherwise.
            strategy_name: The eligibility strategy name.
            strategy_version: The eligibility strategy version.
            evaluation_reason: The reason for the eligibility decision.
            evaluated_at: When the eligibility was evaluated.
        """
        pass

    @abstractmethod
    def update_status(
        self,
        decision_id: str,
        review_status: str,
        cycle_id: Optional[str] = None,
        review_due_date: Optional[datetime] = None,
        executed_at: Optional[datetime] = None,
        days_overdue: Optional[int] = None,
    ) -> None:
        """Updates the review status and related fields.

        Args:
            decision_id: The CIO decision identifier.
            review_status: The new review status.
            cycle_id: The review cycle identifier (set when cycle created).
            review_due_date: The review due date (set when cycle created).
            executed_at: When the review was executed.
            days_overdue: Days overdue (set when overdue detected).
        """
        pass

    @abstractmethod
    def rebuild(self) -> None:
        """Rebuilds the projection from scratch.

        Truncates the projection table and recomputes from
        ReviewEligibilityEvaluatedEvent in the event journal.

        This is a destructive operation. Use only during replay.
        """
        pass
