from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any

@dataclass
class AttributionRecordedEvent:
    event_id: str
    attribution_id: str
    execution_id: str
    trace_id: str
    calculated_cost: Dict[str, Any]
    research_run_id: str
    thesis_id: str
    worker_id: str
    portfolio_id: str
    strategy_id: str
    extended_dimensions: Dict[str, str]
    timestamp: datetime

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": "AttributionRecordedEvent",
            "attribution_id": self.attribution_id,
            "execution_id": self.execution_id,
            "trace_id": self.trace_id,
            "calculated_cost": self.calculated_cost,
            "research_run_id": self.research_run_id,
            "thesis_id": self.thesis_id,
            "worker_id": self.worker_id,
            "portfolio_id": self.portfolio_id,
            "strategy_id": self.strategy_id,
            "extended_dimensions": self.extended_dimensions,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class AttributionAdjustmentCreatedEvent:
    event_id: str
    adjustment_id: str
    original_attribution_id: str
    adjustment_amount: Dict[str, Any]
    adjustment_reason: str
    timestamp: datetime

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": "AttributionAdjustmentCreatedEvent",
            "adjustment_id": self.adjustment_id,
            "original_attribution_id": self.original_attribution_id,
            "adjustment_amount": self.adjustment_amount,
            "adjustment_reason": self.adjustment_reason,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class LedgerProjectionRebuiltEvent:
    event_id: str
    timestamp: datetime
    record_count: int
    adjustment_count: int

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": "LedgerProjectionRebuiltEvent",
            "timestamp": self.timestamp.isoformat(),
            "record_count": self.record_count,
            "adjustment_count": self.adjustment_count
        }
