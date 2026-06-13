import time
import logging
from decimal import Decimal
from datetime import datetime

from ..infrastructure.repositories import PerformanceProjectionRepository, DecisionContextMissingError
from ..domain.projections import DecisionPerformanceRecord
from ..domain.value_objects import DecisionPerformanceIdentity
from ..domain.events import PerformanceDLQEvent
from .orchestration import ProjectionInvalidationOrchestrator

logger = logging.getLogger(__name__)

class PerformanceEventIngestionService:
    def __init__(self, repository: PerformanceProjectionRepository, orchestrator: ProjectionInvalidationOrchestrator, bus):
        self.repository = repository
        self.orchestrator = orchestrator
        self.bus = bus
        self.retry_schedule = [1, 5, 15, 60]

    def handle_attribution_calculated(self, event: dict, retry_count: int = 0):
        max_attempts = 5
        try:
            self._process_event(event)
        except DecisionContextMissingError as e:
            if retry_count >= max_attempts:
                logger.error(f"DLQ Routing: Max attempts reached for {event['decision_id']}")
                self.bus.publish("performance_dlq", PerformanceDLQEvent(
                    original_event=event,
                    error_reason=str(e),
                    failed_at=datetime.utcnow()
                ))
            else:
                # Fail fast to trigger broker-level retry
                raise e

    def _process_event(self, event: dict):
        decision_id = event["decision_id"]
        outcome_sequence_id = event["outcome_sequence_id"]
        incoming_generation = event["attribution_generation"]
        incoming_gross_pnl = Decimal(str(event["gross_pnl"]))
        incoming_net_pnl = Decimal(str(event.get("net_pnl", event["gross_pnl"])))
        occurred_at = datetime.fromisoformat(event["occurred_at"])

        # 1. Retrieve Context
        context = self.repository.get_context(decision_id)

        # 2. Determine Effective Generation State
        effective_record = self.repository.get_effective_generation_record(decision_id, outcome_sequence_id)
        effective_gen_before = effective_record.identity.attribution_generation if effective_record else 0
        pnl_gross_before = effective_record.gross_pnl if effective_record else Decimal('0')
        pnl_net_before = effective_record.net_pnl if effective_record else Decimal('0')
        
        # 3. Calculate Identity-Aware Delta
        delta_gross = Decimal('0')
        delta_net = Decimal('0')
        
        if incoming_generation > effective_gen_before:
            delta_gross = incoming_gross_pnl - pnl_gross_before
            delta_net = incoming_net_pnl - pnl_net_before
        
        # 4. Append to Root Table
        record = DecisionPerformanceRecord(
            identity=DecisionPerformanceIdentity(
                decision_id=decision_id,
                outcome_sequence_id=outcome_sequence_id,
                attribution_generation=incoming_generation
            ),
            worker_id=context.worker_id,
            strategy_id=context.strategy_id,
            thesis_id=context.thesis_id,
            regime_id=event.get("regime_id"),
            gross_pnl=incoming_gross_pnl,
            net_pnl=incoming_net_pnl,
            stated_confidence=context.stated_confidence,
            decision_timestamp=context.decision_timestamp
        )
        self.repository.append_decision_record(record)

        # 5. Apply Delta & Trigger Invalidation
        if delta_gross != 0 or delta_net != 0:
            date_bucket = context.decision_timestamp.date()
            
            self.repository.apply_bucket_delta("WORKER", context.worker_id, date_bucket, delta_gross, delta_net)
            self.repository.apply_bucket_delta("STRATEGY", context.strategy_id, date_bucket, delta_gross, delta_net)
            self.repository.apply_bucket_delta("THESIS", context.thesis_id, date_bucket, delta_gross, delta_net)
            
            self.orchestrator.trigger_invalidation(
                worker_id=context.worker_id,
                strategy_id=context.strategy_id,
                thesis_id=context.thesis_id,
                occurred_at=occurred_at
            )
