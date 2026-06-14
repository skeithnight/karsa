from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any

@dataclass
class DecisionEvaluatedEvent:
    event_id: str
    evaluation_id: str
    decision_id: str
    target_type: str
    target_id: str
    thesis_brier_score: str
    execution_slippage_bps: str
    allocation_sharpe: str
    regime_id: str
    timestamp: datetime
    event_version: int = 1

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": "DecisionEvaluatedEvent",
            "evaluation_id": self.evaluation_id,
            "decision_id": self.decision_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "thesis_brier_score": self.thesis_brier_score,
            "execution_slippage_bps": self.execution_slippage_bps,
            "allocation_sharpe": self.allocation_sharpe,
            "regime_id": self.regime_id,
            "timestamp": self.timestamp.isoformat(),
            "event_version": self.event_version
        }


@dataclass
class EvaluationSnapshotCreatedEvent:
    event_id: str
    snapshot_id: str
    evaluation_id: str
    target_type: str
    target_id: str
    timestamp: datetime
    event_version: int = 1

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": "EvaluationSnapshotCreatedEvent",
            "snapshot_id": self.snapshot_id,
            "evaluation_id": self.evaluation_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "timestamp": self.timestamp.isoformat(),
            "event_version": self.event_version
        }


@dataclass
class PerformanceProjectionUpdatedEvent:
    event_id: str
    projection_type: str                  # e.g., "THESIS", "WORKER"
    target_id: str
    metric_name: str                      # e.g., "rank", "calibrated_confidence"
    new_value: str
    timestamp: datetime
    event_version: int = 1

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": "PerformanceProjectionUpdatedEvent",
            "projection_type": self.projection_type,
            "target_id": self.target_id,
            "metric_name": self.metric_name,
            "new_value": self.new_value,
            "timestamp": self.timestamp.isoformat(),
            "event_version": self.event_version
        }
