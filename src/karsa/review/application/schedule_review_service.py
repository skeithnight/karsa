"""ScheduleReviewService — Sprint-07 Wave-3.

Schedules new review cycles from CIO decisions.
Transaction boundary: ReviewCycle + OutboxEvent + Projection update.
"""
import uuid
from datetime import datetime
from typing import Optional

from karsa.review.domain.aggregates.review_cycle import ReviewCycle
from karsa.review.domain.aggregates.outbox_event import OutboxEvent, OutboxStatus
from karsa.review.domain.events.review_events import ReviewCycleCreatedEvent
from karsa.review.domain.value_objects.review_verdict import ReviewType
from karsa.review.domain.value_objects.decision_snapshot import DecisionSnapshot
from karsa.review.domain.value_objects.schedule_policy import SchedulePolicy
from karsa.review.domain.value_objects.review_template import ReviewTemplate
from karsa.review.domain.repositories.review_cycle_repository import ReviewCycleRepository
from karsa.review.domain.repositories.outbox_repository import OutboxRepository
from karsa.review.domain.repositories.review_coverage_projection_repository import ReviewCoverageProjectionRepository
from karsa.review.domain.repositories.review_cycle_status_projection_repository import ReviewCycleStatusProjectionRepository
from karsa.review.application.dto import ScheduleReviewCommand, ScheduleReviewResponse
from karsa.review.infrastructure.jsonb_serializers import (
    serialize_decision_snapshot, serialize_schedule_policy, serialize_review_template,
)


class ScheduleReviewService:
    """Schedules new review cycles.

    Transaction boundary:
    1. Create ReviewCycle (immutable)
    2. Create OutboxEvent for ReviewCycleCreatedEvent
    3. Update ReviewCoverageProjection (cycle_id, due_date)
    4. Update ReviewCycleStatusProjection (CREATED)
    """

    def __init__(
        self,
        cycle_repo: ReviewCycleRepository,
        outbox_repo: OutboxRepository,
        coverage_repo: ReviewCoverageProjectionRepository,
        status_repo: ReviewCycleStatusProjectionRepository,
    ):
        self.cycle_repo = cycle_repo
        self.outbox_repo = outbox_repo
        self.coverage_repo = coverage_repo
        self.status_repo = status_repo

    def execute(self, command: ScheduleReviewCommand) -> ScheduleReviewResponse:
        """Executes the schedule review command.

        All writes occur within a single transaction managed by the caller.

        Args:
            command: The schedule review command.

        Returns:
            ScheduleReviewResponse with cycle details.

        Raises:
            ValueError: If validation fails.
            DuplicateCycleError: If cycle already exists for this decision.
        """
        # 1. Validate inputs
        if not command.decision_id:
            raise ValueError("decision_id is required.")
        if not command.journal_ref:
            raise ValueError("journal_ref is required.")

        # 2. Check for duplicate cycle (idempotency)
        existing = self.cycle_repo.get_cycle_by_decision_id(command.decision_id)
        if existing:
            return ScheduleReviewResponse(
                cycle_id=existing.cycle_id,
                decision_id=existing.decision_id,
                review_type=existing.review_type.value,
                due_date=existing.schedule_due_date.isoformat(),
                created_at=existing.created_at.isoformat(),
            )

        # 3. Create domain objects
        cycle_id = f"urn:karsa:review:cycle:{uuid.uuid4().hex[:16]}"
        now = datetime.utcnow()

        decision_snapshot = DecisionSnapshot(
            decision_id=command.decision_id,
            proposal_id=command.proposal_id,
            journal_ref=command.journal_ref,
            action_type=command.decision_snapshot.get("action_type", "APPROVE_ALLOCATION"),
            target_node_type=command.decision_snapshot.get("target_node_type", "WORKER"),
            target_node_id=command.decision_snapshot.get("target_node_id", "portfolio-main"),
            allocated_weights=command.decision_snapshot.get("allocated_weights", {}),
            policy_snapshot=command.decision_snapshot.get("policy_snapshot", {}),
            expected_return_bps=command.decision_snapshot.get("expected_return_bps", 0.0),
            expected_drawdown_pct=command.decision_snapshot.get("expected_drawdown_pct", 0.0),
            expected_sharpe_ratio=command.decision_snapshot.get("expected_sharpe_ratio", 0.0),
            expected_horizon_days=command.decision_snapshot.get("expected_horizon_days", 30),
            confidence_level=command.decision_snapshot.get("confidence_level", 0.5),
            benchmark_urn=command.decision_snapshot.get("benchmark_urn"),
            regime_at_decision=command.decision_snapshot.get("regime_at_decision"),
            key_assumptions=[],
            attribution_expectations=command.decision_snapshot.get("attribution_expectations", {}),
            decision_rationale=command.decision_snapshot.get("decision_rationale", ""),
            decision_confidence=command.decision_snapshot.get("decision_confidence", 0.5),
            decision_timestamp=command.decision_snapshot.get("decision_timestamp", now.isoformat()),
            cryptographic_signature=command.decision_snapshot.get("cryptographic_signature", ""),
            snapshot_hash=command.decision_snapshot.get("snapshot_hash", ""),
        )

        schedule_policy = SchedulePolicy.create(
            observation_window_days=command.schedule_policy.get("observation_window_days", 30),
            overdue_threshold_days=command.schedule_policy.get("overdue_threshold_days", 7),
            created_at=now,
        )

        review_template = ReviewTemplate(
            template_id=command.review_template.get("template_id", "tmpl-default"),
            review_type=ReviewType(command.review_type),
            required_metrics=command.review_template.get("required_metrics", []),
            required_assumptions=command.review_template.get("required_assumptions", []),
            evaluation_criteria=command.review_template.get("evaluation_criteria", {}),
            scoring_rules=command.review_template.get("scoring_rules", {}),
        )

        cycle = ReviewCycle(
            cycle_id=cycle_id,
            decision_id=command.decision_id,
            proposal_id=command.proposal_id,
            journal_ref=command.journal_ref,
            review_type=ReviewType(command.review_type),
            decision_snapshot=decision_snapshot,
            schedule_policy=schedule_policy,
            review_template=review_template,
            eligibility_event_ref=command.eligibility_event_ref,
            created_at=now,
            created_by=command.created_by,
        )

        # 4. Persist aggregate (write-once)
        inserted = self.cycle_repo.save_cycle(cycle)

        # 4a. If not inserted, another request won the race — return existing
        if not inserted:
            existing = self.cycle_repo.get_cycle_by_decision_id(command.decision_id)
            if existing:
                return ScheduleReviewResponse(
                    cycle_id=existing.cycle_id,
                    decision_id=existing.decision_id,
                    review_type=existing.review_type.value,
                    due_date=existing.schedule_due_date.isoformat(),
                    created_at=existing.created_at.isoformat(),
                )

        # 5. Create outbox event (only if aggregate was actually persisted)
        event = ReviewCycleCreatedEvent(
            event_id=str(uuid.uuid4()),
            cycle_id=cycle_id,
            decision_id=command.decision_id,
            proposal_id=command.proposal_id,
            journal_ref=command.journal_ref,
            review_type=command.review_type,
            decision_snapshot=serialize_decision_snapshot(decision_snapshot),
            schedule_policy=serialize_schedule_policy(schedule_policy),
            review_template=serialize_review_template(review_template),
            eligibility_event_ref=command.eligibility_event_ref,
            created_by=command.created_by,
            created_at=now,
        )

        outbox_event = OutboxEvent(
            outbox_id=str(uuid.uuid4()),
            event_type=event.event_type,
            payload=event.to_dict(),
            aggregate_id=cycle_id,
            created_at=now,
        )
        self.outbox_repo.save_event(outbox_event)

        # 6. Update projections
        self.coverup_repo_update(command.decision_id, cycle_id, schedule_policy)
        self.status_repo.upsert_created(cycle_id, event_sequence=0)

        # 7. Return response
        return ScheduleReviewResponse(
            cycle_id=cycle_id,
            decision_id=command.decision_id,
            review_type=command.review_type,
            due_date=schedule_policy.review_due_date,
            created_at=now.isoformat(),
        )

    def coverup_repo_update(self, decision_id: str, cycle_id: str, schedule_policy: SchedulePolicy) -> None:
        """Updates coverage projection with cycle information."""
        self.coverage_repo.update_status(
            decision_id=decision_id,
            review_status="PENDING",
            cycle_id=cycle_id,
            review_due_date=schedule_policy.due_date,
        )
