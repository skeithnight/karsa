from dataclasses import dataclass
from typing import Any, Dict
from datetime import datetime
import json

@dataclass(frozen=True)
class PlatformEventEnvelope:
    """Standardized event envelope for all platform events."""
    event_id: str
    event_type: str
    correlation_id: str
    causation_id: str
    aggregate_type: str
    aggregate_id: str
    aggregate_version: int
    occurred_at: str
    schema_version: str
    payload: Dict[str, Any]

    def serialize(self) -> str:
        """Serialize envelope to JSON."""
        # Using default asdict equivalent but ensuring payload handles complex types if needed
        data = {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "aggregate_type": self.aggregate_type,
            "aggregate_id": self.aggregate_id,
            "aggregate_version": self.aggregate_version,
            "occurred_at": self.occurred_at,
            "schema_version": self.schema_version,
            "payload": self.payload
        }
        return json.dumps(data)

    @classmethod
    def deserialize(cls, data_str: str) -> 'PlatformEventEnvelope':
        """Deserialize from JSON string."""
        data = json.loads(data_str)
        return cls(**data)
