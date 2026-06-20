"""ApplyCapabilityAdjustmentService — Sprint-07 Wave-3.

Applies capability score adjustments and updates projections.
Transaction boundary: CapabilityScoreAdjustment + OutboxEvent + Projection update.
"""
import uuid
from datetime import datetime

from karsa.review.domain.aggregates.capability_score_adjustment import CapabilityScoreAdjustment
from karsa.review.domain.aggregates.outbox_event import OutboxEvent
from karsa.review.domain.events.review_events import CapabilityScoreAdjustmentCreatedEvent
from karsa.review.domain.repositories.capability_score_adjustment_repository import CapabilityScoreAdjustmentRepository
from karsa.review.domain.repositories.capability_score_projection_repository import CapabilityScoreProjectionRepository
from karsa.review.domain.repositories.outbox_repository import OutboxRepository
from karsa.review.application.dto import ApplyCapabilityAdjustmentCommand, ApplyCapabilityAdjustmentResponse


class ApplyCapabilityAdjustmentService:
    """Applies capability score adjustments.

    Transaction boundary:
    1. Create CapabilityScoreAdjustment (immutable)
    2. Update CapabilityScoreProjection (UPSERT)
    3. Create OutboxEvent for CapabilityScoreAdjustmentCreatedEvent
    """

    def __init__(
        self,
        adjustment_repo: CapabilityScoreAdjustmentRepository,
        projection_repo: CapabilityScoreProjectionRepository,
        outbox_repo: OutboxRepository,
    ):
        self.adjustment_repo = adjustment_repo
        self.projection_repo = projection_repo
        self.outbox_repo = outbox_repo

    def execute(self, command: ApplyCapabilityAdjustmentCommand) -> ApplyCapabilityAdjustmentResponse:
        """Executes the capability adjustment command.

        All writes occur within a single transaction managed by the caller.

        Args:
            command: The apply capability adjustment command.

        Returns:
            ApplyCapabilityAdjustmentResponse with adjustment details.

        Raises:
            ValueError: If validation fails.
        """
        # 1. Validate inputs
        if not command.target_urn:
            raise ValueError("target_urn is required.")
        if not command.review_id:
            raise ValueError("review_id is required.")

        # 2. Create domain object
        now = datetime.utcnow()
        adjustment = CapabilityScoreAdjustment.from_attribution(
            adjustment_id=f"urn:karsa:review:adj:{uuid.uuid4().hex[:16]}",
            target_urn=command.target_urn,
            target_type=command.target_type,
            contribution_bps=command.contribution_bps,
            review_id=command.review_id,
            created_at=now,
        )

        # 3. Persist aggregate (write-once)
        self.adjustment_repo.save_adjustment(adjustment)

        # 4. Update projection
        self.projection_repo.upsert(
            target_urn=command.target_urn,
            target_type=command.target_type,
            score_delta=adjustment.score_delta,
            confidence_delta=adjustment.confidence_delta,
        )

        # 5. Create outbox event
        event = CapabilityScoreAdjustmentCreatedEvent(
            event_id=str(uuid.uuid4()),
            adjustment_id=adjustment.adjustment_id,
            target_urn=adjustment.target_urn,
            target_type=adjustment.target_type,
            score_delta=adjustment.score_delta,
            confidence_delta=adjustment.confidence_delta,
            review_id=adjustment.review_id,
            rationale=adjustment.rationale,
            created_at=now,
        )

        outbox_event = OutboxEvent(
            outbox_id=str(uuid.uuid4()),
            event_type=event.event_type,
            payload=event.to_dict(),
            aggregate_id=adjustment.adjustment_id,
            created_at=now,
        )
        self.outbox_repo.save_event(outbox_event)

        # 6. Return response
        return ApplyCapabilityAdjustmentResponse(
            adjustment_id=adjustment.adjustment_id,
            target_urn=adjustment.target_urn,
            score_delta=adjustment.score_delta,
            confidence_delta=adjustment.confidence_delta,
        )
