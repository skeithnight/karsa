from dataclasses import dataclass
from karsa.shared.events.envelope import PlatformEventEnvelope
import time
import uuid

@dataclass
class ThesisEvaluatedPayload:
    thesis_id: str
    evaluation_grade: dict
    metric_version: str
    algorithm_hash: str
    evaluated_at: str

@dataclass
class PerformanceProfileUpdatedPayload:
    target_identity: dict
    window_identity: dict
    prediction_metrics: dict
    investment_metrics: dict
    update_reason_thesis_id: str

def build_thesis_evaluated_event(payload: ThesisEvaluatedPayload) -> PlatformEventEnvelope:
    return PlatformEventEnvelope(
        event_id=str(uuid.uuid4()),
        event_type="ThesisEvaluatedEvent",
        correlation_id="",
        causation_id="",
        aggregate_type="ThesisEvaluation",
        aggregate_id=payload.thesis_id,
        aggregate_version=1,
        occurred_at=str(int(time.time())),
        schema_version="1.0",
        payload=payload.__dict__
    )

def build_profile_updated_event(payload: PerformanceProfileUpdatedPayload) -> PlatformEventEnvelope:
    return PlatformEventEnvelope(
        event_id=str(uuid.uuid4()),
        event_type="PerformanceProfileUpdatedEvent",
        correlation_id="",
        causation_id="",
        aggregate_type="PerformanceProfileWindow",
        aggregate_id=payload.target_identity["target_id"],
        aggregate_version=1,
        occurred_at=str(int(time.time())),
        schema_version="1.0",
        payload=payload.__dict__
    )
