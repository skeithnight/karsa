"""ExecuteReviewService — Sprint-07 Wave-3.

Executes reviews against actual outcomes.
Transaction boundary: ReviewRecord + AttributionEntries + CapabilityAdjustments + OutboxEvents.
"""
import uuid
from datetime import datetime
from typing import List, Dict, Any

from karsa.review.domain.aggregates.review_record import ReviewRecord
from karsa.review.domain.aggregates.attribution_entry import AttributionEntry
from karsa.review.domain.aggregates.capability_score_adjustment import CapabilityScoreAdjustment
from karsa.review.domain.aggregates.outbox_event import OutboxEvent
from karsa.review.domain.events.review_events import (
    ReviewExecutedEvent,
    AttributionGeneratedEvent,
    CapabilityScoreAdjustmentCreatedEvent,
)
from karsa.review.domain.value_objects.review_verdict import (
    ReviewType, ReviewVerdict, AttributionDimension, AttributionType,
)
from karsa.review.domain.value_objects.actual_outcome_snapshot import ActualOutcomeSnapshot
from karsa.review.domain.value_objects.variance_analysis import VarianceAnalysis
from karsa.review.domain.repositories.review_cycle_repository import ReviewCycleRepository
from karsa.review.domain.repositories.review_record_repository import ReviewRecordRepository
from karsa.review.domain.repositories.attribution_entry_repository import AttributionEntryRepository
from karsa.review.domain.repositories.capability_score_adjustment_repository import CapabilityScoreAdjustmentRepository
from karsa.review.domain.repositories.outbox_repository import OutboxRepository
from karsa.review.domain.repositories.review_coverage_projection_repository import ReviewCoverageProjectionRepository
from karsa.review.domain.repositories.review_cycle_status_projection_repository import ReviewCycleStatusProjectionRepository
from karsa.review.infrastructure.jsonb_serializers import (
    serialize_actual_outcome, serialize_variance,
)
from karsa.review.application.dto import ExecuteReviewCommand, ExecuteReviewResponse


class ExecuteReviewService:
    """Executes reviews against actual outcomes.

    Transaction boundary:
    1. Create ReviewRecord (immutable)
    2. Create AttributionEntry[] (immutable, variable cardinality)
    3. Create CapabilityScoreAdjustment[] (immutable)
    4. Create OutboxEvent[] for all domain events
    5. Update projections
    """

    def __init__(
        self,
        cycle_repo: ReviewCycleRepository,
        record_repo: ReviewRecordRepository,
        attribution_repo: AttributionEntryRepository,
        adjustment_repo: CapabilityScoreAdjustmentRepository,
        outbox_repo: OutboxRepository,
        coverage_repo: ReviewCoverageProjectionRepository,
        status_repo: ReviewCycleStatusProjectionRepository,
    ):
        self.cycle_repo = cycle_repo
        self.record_repo = record_repo
        self.attribution_repo = attribution_repo
        self.adjustment_repo = adjustment_repo
        self.outbox_repo = outbox_repo
        self.coverage_repo = coverage_repo
        self.status_repo = status_repo

    def execute(self, command: ExecuteReviewCommand) -> ExecuteReviewResponse:
        """Executes the review command.

        All writes occur within a single transaction managed by the caller.

        Args:
            command: The execute review command.

        Returns:
            ExecuteReviewResponse with review details.

        Raises:
            ValueError: If cycle not found or validation fails.
        """
        # 1. Load review cycle
        cycle = self.cycle_repo.get_cycle_by_id(command.cycle_id)
        if not cycle:
            raise ValueError(f"Review cycle {command.cycle_id} not found.")

        # 2. Parse actual outcome
        actual_outcome = ActualOutcomeSnapshot(
            evaluation_id=command.actual_outcome.get("evaluation_id", str(uuid.uuid4())),
            target_urn=command.actual_outcome.get("target_urn", cycle.decision_id),
            observation_window_days=command.actual_outcome.get("observation_window_days", cycle.schedule_policy.observation_window_days),
            realized_return_bps=command.actual_outcome.get("realized_return_bps", 0.0),
            realized_drawdown_pct=command.actual_outcome.get("realized_drawdown_pct", 0.0),
            realized_sharpe_ratio=command.actual_outcome.get("realized_sharpe_ratio", 0.0),
            benchmark_return_bps=command.actual_outcome.get("benchmark_return_bps", 0.0),
            regime_during_period=command.actual_outcome.get("regime_during_period"),
            assumption_validations=[],
            actual_attribution=command.actual_outcome.get("actual_attribution", {}),
        )

        # 3. Compute variance
        variance = VarianceAnalysis.compute(
            expected_return_bps=cycle.decision_snapshot.expected_return_bps,
            expected_drawdown_pct=cycle.decision_snapshot.expected_drawdown_pct,
            expected_sharpe_ratio=cycle.decision_snapshot.expected_sharpe_ratio,
            realized_return_bps=actual_outcome.realized_return_bps,
            realized_drawdown_pct=actual_outcome.realized_drawdown_pct,
            realized_sharpe_ratio=actual_outcome.realized_sharpe_ratio,
            confidence_level=cycle.decision_snapshot.confidence_level,
            assumption_validations=[],
        )

        # 4. Determine verdict
        verdict = ReviewRecord.determine_verdict(variance)

        # 5. Create review record
        review_id = f"urn:karsa:review:record:{uuid.uuid4().hex[:16]}"
        now = datetime.utcnow()

        record = ReviewRecord(
            review_id=review_id,
            cycle_id=command.cycle_id,
            review_type=cycle.review_type,
            decision_snapshot=cycle.decision_snapshot,
            actual_outcome=actual_outcome,
            variance=variance,
            verdict=verdict,
            rationale=command.rationale,
            executed_at=now,
            executed_by=command.executed_by,
        )
        self.record_repo.save_record(record)

        # 6. Generate attributions (variable cardinality)
        attributions = self._generate_attributions(review_id, actual_outcome, now)
        if attributions:
            self.attribution_repo.save_entries(attributions)

        # 7. Generate capability adjustments
        adjustments = self._generate_adjustments(review_id, attributions, now)
        if adjustments:
            self.adjustment_repo.save_adjustments(adjustments)

        # 8. Create outbox events
        outbox_events = []

        # ReviewExecutedEvent
        review_event = ReviewExecutedEvent(
            event_id=str(uuid.uuid4()),
            review_id=review_id,
            cycle_id=command.cycle_id,
            review_type=cycle.review_type.value,
            actual_outcome=serialize_actual_outcome(actual_outcome),
            variance=serialize_variance(variance),
            verdict=verdict.value,
            rationale=command.rationale,
            executed_by=command.executed_by,
            executed_at=now,
        )
        outbox_events.append(OutboxEvent(
            outbox_id=str(uuid.uuid4()),
            event_type=review_event.event_type,
            payload=review_event.to_dict(),
            aggregate_id=review_id,
            created_at=now,
        ))

        # AttributionGeneratedEvent for each attribution
        for attr in attributions:
            attr_event = AttributionGeneratedEvent(
                event_id=str(uuid.uuid4()),
                attribution_id=attr.attribution_id,
                review_id=review_id,
                dimension=attr.dimension.value,
                target_urn=attr.target_urn,
                contribution_bps=attr.contribution_bps,
                contribution_pct=attr.contribution_pct,
                attribution_type=attr.attribution_type.value,
                evidence=attr.evidence,
                created_at=now,
            )
            outbox_events.append(OutboxEvent(
                outbox_id=str(uuid.uuid4()),
                event_type=attr_event.event_type,
                payload=attr_event.to_dict(),
                aggregate_id=attr.attribution_id,
                created_at=now,
            ))

        # CapabilityScoreAdjustmentCreatedEvent for each adjustment
        for adj in adjustments:
            adj_event = CapabilityScoreAdjustmentCreatedEvent(
                event_id=str(uuid.uuid4()),
                adjustment_id=adj.adjustment_id,
                target_urn=adj.target_urn,
                target_type=adj.target_type,
                score_delta=adj.score_delta,
                confidence_delta=adj.confidence_delta,
                review_id=adj.review_id,
                rationale=adj.rationale,
                created_at=now,
            )
            outbox_events.append(OutboxEvent(
                outbox_id=str(uuid.uuid4()),
                event_type=adj_event.event_type,
                payload=adj_event.to_dict(),
                aggregate_id=adj.adjustment_id,
                created_at=now,
            ))

        self.outbox_repo.save_events(outbox_events)

        # 9. Update projections
        self.coverage_repo.update_status(
            decision_id=cycle.decision_id,
            review_status="EXECUTED",
            executed_at=now,
        )
        self.status_repo.upsert_executed(
            cycle_id=command.cycle_id,
            review_id=review_id,
            executed_at=now,
            event_sequence=0,
        )

        # 10. Return response
        return ExecuteReviewResponse(
            review_id=review_id,
            cycle_id=command.cycle_id,
            verdict=verdict.value,
            executed_at=now.isoformat(),
            attribution_count=len(attributions),
            adjustment_count=len(adjustments),
        )

    def _generate_attributions(
        self,
        review_id: str,
        actual_outcome: ActualOutcomeSnapshot,
        now: datetime,
    ) -> List[AttributionEntry]:
        """Generates attribution entries from actual outcome."""
        attributions = []
        total_contribution = sum(actual_outcome.actual_attribution.values()) if actual_outcome.actual_attribution else 0.0

        for target_urn, contribution_bps in (actual_outcome.actual_attribution or {}).items():
            attr = AttributionEntry.from_contribution(
                attribution_id=f"urn:karsa:review:attr:{uuid.uuid4().hex[:16]}",
                review_id=review_id,
                dimension=AttributionDimension.WORKER,
                target_urn=target_urn,
                contribution_bps=contribution_bps,
                total_bps=total_contribution,
                evidence={"source": "actual_outcome"},
                created_at=now,
            )
            attributions.append(attr)

        return attributions

    def _generate_adjustments(
        self,
        review_id: str,
        attributions: List[AttributionEntry],
        now: datetime,
    ) -> List[CapabilityScoreAdjustment]:
        """Generates capability score adjustments from attributions."""
        adjustments = []
        for attr in attributions:
            adj = CapabilityScoreAdjustment.from_attribution(
                adjustment_id=f"urn:karsa:review:adj:{uuid.uuid4().hex[:16]}",
                target_urn=attr.target_urn,
                target_type="WORKER",
                contribution_bps=attr.contribution_bps,
                review_id=review_id,
                created_at=now,
            )
            adjustments.append(adj)
        return adjustments
