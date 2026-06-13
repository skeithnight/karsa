from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any

@dataclass
class ArtifactPublishedEvent:
    event_id: str
    snapshot_id: str
    namespace: str
    schema_id: str
    published_at: datetime
    
class EventBus:
    def publish(self, event: Any) -> None:
        pass
