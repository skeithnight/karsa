from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any
import uuid

@dataclass
class DomainEvent:
    """Base class for domain events."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    stream_id: str = ""
    aggregate_id: str = ""
    aggregate_type: str = ""
    schema_version: int = 1
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def event_name(self) -> str:
        return self.__class__.__name__

    def to_dict(self) -> Dict[str, Any]:
        """Subclasses should implement this to provide payload data."""
        return {
            "event_id": str(self.event_id),
            "occurred_at": self.occurred_at.isoformat(),
            "version": self.version,
            "event_name": self.event_name
        }
